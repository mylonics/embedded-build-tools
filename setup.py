#!/usr/bin/env python3
"""
Embedded Build Tools — Bootstrap / Setup Script

Downloads and extracts portable build tools (GCC, GDB, CMake, Ninja, Python)
based on tool-manifest.json for the current platform.

Usage:
    python setup.py                  # download all tools for current platform
    python setup.py --tools gcc cmake # download specific tools
    python setup.py --platform linux-x64  # override platform detection
    python setup.py --verify         # verify checksums only
    python setup.py --clean          # remove all downloaded tools

No external dependencies — uses only Python stdlib.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import urlretrieve, Request, urlopen
from urllib.error import URLError, HTTPError

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "tool-manifest.json"
TOOLS_DIR = SCRIPT_DIR / "tools"
DOWNLOAD_CACHE_DIR = SCRIPT_DIR / ".cache"


class DownloadError(Exception):
    """Raised when a download fails after all retries."""
    pass


# ── Platform detection ──────────────────────────────────────────────────────

def detect_platform() -> str:
    """Detect the current platform in node-style format: os-arch."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    os_map = {
        "windows": "win32",
        "linux": "linux",
        "darwin": "darwin",
    }
    arch_map = {
        "x86_64": "x64",
        "amd64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }

    os_name = os_map.get(system)
    arch_name = arch_map.get(machine)

    if not os_name or not arch_name:
        print(f"ERROR: Unsupported platform: {system}-{machine}", file=sys.stderr)
        sys.exit(1)

    return f"{os_name}-{arch_name}"


# ── Manifest loading ────────────────────────────────────────────────────────

def load_manifest() -> dict:
    """Load and return the tool manifest."""
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Download helpers ────────────────────────────────────────────────────────

def download_file(url: str, dest: Path, retries: int = 3, show_progress: bool = True) -> Path:
    """Download a file with progress reporting and retry logic.

    Raises DownloadError if all retries are exhausted.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        if show_progress:
            print(f"  Using cached: {dest.name}")
        return dest

    if show_progress:
        print(f"  Downloading: {url}")
        print(f"  Destination: {dest}")

    for attempt in range(1, retries + 1):
        try:
            if show_progress:
                def _progress(block_num, block_size, total_size):
                    if total_size > 0:
                        downloaded = block_num * block_size
                        pct = min(100, downloaded * 100 // total_size)
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        print(f"\r  Progress: {pct:3d}% ({mb_down:.1f}/{mb_total:.1f} MB)", end="", flush=True)

                urlretrieve(url, str(dest), reporthook=_progress)
                print()  # newline after progress
            else:
                urlretrieve(url, str(dest))
            return dest
        except (URLError, HTTPError) as e:
            if dest.exists():
                dest.unlink()
            if attempt < retries:
                wait = 2 ** attempt
                print(f"\n  Retry {attempt}/{retries} in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise DownloadError(
                    f"Download failed after {retries} attempts: {e}"
                ) from e


def verify_sha256(file_path: Path, expected: str) -> bool:
    """Verify SHA-256 checksum of a file."""
    if not expected:
        print("  WARNING: No SHA-256 checksum in manifest, skipping verification")
        return True

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()

    if actual != expected:
        print(f"  ERROR: SHA-256 mismatch!", file=sys.stderr)
        print(f"    Expected: {expected}", file=sys.stderr)
        print(f"    Actual:   {actual}", file=sys.stderr)
        return False

    print(f"  SHA-256 OK: {actual[:16]}...")
    return True


# ── Extraction helpers ──────────────────────────────────────────────────────

def _safe_tar_extractall(tf: tarfile.TarFile, dest: Path):
    """Extract tarball safely, using data filter on Python 3.12+."""
    try:
        tf.extractall(dest, filter="data")
    except TypeError:
        # Python < 3.12 doesn't support the filter parameter
        tf.extractall(dest)


def extract_archive(archive_path: Path, dest_dir: Path, fmt: str, strip: int = 0):
    """Extract an archive to dest_dir, optionally stripping leading path components."""
    print(f"  Extracting to: {dest_dir}")

    # Clean destination
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if strip == 0:
        # Simple extraction
        if fmt == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest_dir)
        elif fmt in ("tar.gz", "tar.xz", "tar.bz2"):
            mode = {
                "tar.gz": "r:gz",
                "tar.xz": "r:xz",
                "tar.bz2": "r:bz2",
            }[fmt]
            with tarfile.open(archive_path, mode) as tf:
                _safe_tar_extractall(tf, dest_dir)
        else:
            print(f"  ERROR: Unknown archive format: {fmt}", file=sys.stderr)
            sys.exit(1)
    else:
        # Extract with strip (remove N leading path components)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            if fmt == "zip":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(tmpdir)
            elif fmt in ("tar.gz", "tar.xz", "tar.bz2"):
                mode = {
                    "tar.gz": "r:gz",
                    "tar.xz": "r:xz",
                    "tar.bz2": "r:bz2",
                }[fmt]
                with tarfile.open(archive_path, mode) as tf:
                    _safe_tar_extractall(tf, tmpdir)

            # Find the stripped root
            stripped = tmpdir
            for _ in range(strip):
                children = list(stripped.iterdir())
                if len(children) == 1 and children[0].is_dir():
                    stripped = children[0]
                else:
                    break

            # Move contents to destination
            for item in stripped.iterdir():
                target = dest_dir / item.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                shutil.move(str(item), str(target))

    # Fix permissions on Unix
    if os.name != "nt":
        _fix_permissions(dest_dir)

    # Remove macOS quarantine attributes (Gatekeeper blocks unsigned binaries)
    if platform.system() == "Darwin":
        _remove_macos_quarantine(dest_dir)

    print(f"  Extraction complete.")


def _fix_permissions(directory: Path):
    """Ensure executables in bin/ directories have execute permission."""
    for bin_dir in directory.rglob("bin"):
        if bin_dir.is_dir():
            for f in bin_dir.iterdir():
                if f.is_file():
                    f.chmod(f.stat().st_mode | 0o755)


def _remove_macos_quarantine(directory: Path):
    """Remove macOS Gatekeeper quarantine attribute from all files.

    macOS adds com.apple.quarantine to files downloaded from the internet,
    which causes Gatekeeper to block unsigned binaries with:
    '... cannot be opened because the developer cannot be verified.'
    """
    import subprocess
    try:
        subprocess.run(
            ["xattr", "-cr", str(directory)],
            check=True,
            capture_output=True,
        )
        print(f"  Removed macOS quarantine attributes from {directory.name}")
    except FileNotFoundError:
        pass  # xattr not available (not macOS)
    except subprocess.CalledProcessError as e:
        print(f"  WARNING: Failed to remove quarantine attributes: {e}", file=sys.stderr)


# ── Stamp / version tracking ───────────────────────────────────────────────

def get_installed_version(tool_name: str) -> str | None:
    """Read the installed version stamp for a tool."""
    stamp_file = TOOLS_DIR / tool_name / ".version"
    if stamp_file.exists():
        return stamp_file.read_text(encoding="utf-8").strip()
    return None


def write_version_stamp(tool_name: str, version: str):
    """Write a version stamp after successful installation."""
    stamp_file = TOOLS_DIR / tool_name / ".version"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    stamp_file.write_text(version, encoding="utf-8")


# ── Main logic ──────────────────────────────────────────────────────────────

TOOL_ALIASES = {
    "gcc": "arm-none-eabi-gcc",
    "arm-gcc": "arm-none-eabi-gcc",
    "cmake": "cmake",
    "ninja": "ninja-build",
    "python": "python",
    "gdb": "arm-none-eabi-gcc",  # GDB ships inside the GCC package
}


def resolve_tool_name(name: str) -> str:
    """Resolve a tool alias to its manifest name."""
    return TOOL_ALIASES.get(name.lower(), name)


def setup_tool(tool_name: str, tool_cfg: dict, plat: str, cache_dir: Path, force: bool = False) -> bool:
    """Download and extract a single tool. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"  Tool: {tool_name} v{tool_cfg['version']}")
    print(f"  Platform: {plat}")
    print(f"{'='*60}")

    if plat not in tool_cfg["platforms"]:
        print(f"  SKIP: No binary available for platform '{plat}'")
        return False

    plat_cfg = tool_cfg["platforms"][plat]

    # Check if already installed at this version
    installed = get_installed_version(tool_name)
    if installed == tool_cfg["version"] and not force:
        print(f"  Already installed (v{installed}). Use --force to reinstall.")
        return True

    url = plat_cfg["url"]
    sha256 = plat_cfg.get("sha256", "")
    fmt = plat_cfg["extract"]
    strip = plat_cfg.get("strip", 0)

    # Determine cache filename
    filename = url.rsplit("/", 1)[-1]
    cache_path = cache_dir / filename

    # Download
    try:
        download_file(url, cache_path)
    except DownloadError as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False

    # Verify checksum
    if not verify_sha256(cache_path, sha256):
        cache_path.unlink(missing_ok=True)
        return False

    # Extract
    tool_dir = TOOLS_DIR / tool_name
    extract_archive(cache_path, tool_dir, fmt, strip)

    # Write version stamp
    write_version_stamp(tool_name, tool_cfg["version"])

    print(f"  OK: {tool_name} v{tool_cfg['version']} installed successfully.")
    return True


def clean_tools():
    """Remove all downloaded tools and cache."""
    if TOOLS_DIR.exists():
        print(f"Removing tools directory: {TOOLS_DIR}")
        shutil.rmtree(TOOLS_DIR)
    if DOWNLOAD_CACHE_DIR.exists():
        print(f"Removing cache directory: {DOWNLOAD_CACHE_DIR}")
        shutil.rmtree(DOWNLOAD_CACHE_DIR)
    print("Clean complete.")


def print_env_info(plat: str, manifest: dict):
    """Print environment variable info for integrating the tools."""
    print(f"\n{'='*60}")
    print("  Environment Setup")
    print(f"{'='*60}")
    
    bin_paths = []
    for tool_name, tool_cfg in manifest["tools"].items():
        tool_dir = TOOLS_DIR / tool_name
        if not tool_dir.exists():
            continue
        # Common bin subdirectory
        bin_dir = tool_dir / "bin"
        if bin_dir.exists():
            bin_paths.append(str(bin_dir))
        # Python has a different layout on Windows
        if tool_name == "python" and plat.startswith("win32"):
            python_dir = tool_dir / "python"
            if python_dir.exists():
                bin_paths.append(str(python_dir))

    if bin_paths:
        sep = ";" if plat.startswith("win32") else ":"
        path_str = sep.join(bin_paths)
        print(f"\n  Add to PATH:\n    {path_str}")
    
    print()


def list_tools(manifest: dict, plat: str):
    """List all available tools with their versions and installed status."""
    print(f"\n{'='*60}")
    print(f"  Available Tools (platform: {plat})")
    print(f"{'='*60}")
    print(f"  {'Tool':<25} {'Version':<15} {'Status':<15}")
    print(f"  {'-'*25} {'-'*15} {'-'*15}")

    for tool_name, tool_cfg in manifest["tools"].items():
        version = tool_cfg["version"]
        installed = get_installed_version(tool_name)
        if installed == version:
            status = "Installed"
        elif installed:
            status = f"Outdated ({installed})"
        else:
            status = "Not installed"

        available = plat in tool_cfg.get("platforms", {})
        if not available:
            status = "N/A (no binary)"

        print(f"  {tool_name:<25} {version:<15} {status:<15}")

    print(f"\n  Aliases:")
    for alias, target in sorted(TOOL_ALIASES.items()):
        if alias != target:
            print(f"    {alias} -> {target}")
    print()


def compute_checksums(manifest: dict, plat: str, cache_dir: Path):
    """Download tools and compute SHA-256 checksums, updating the manifest."""
    print(f"Computing checksums for platform: {plat}")
    updated = False

    for tool_name, tool_cfg in manifest["tools"].items():
        if plat not in tool_cfg["platforms"]:
            continue

        plat_cfg = tool_cfg["platforms"][plat]
        url = plat_cfg["url"]
        filename = url.rsplit("/", 1)[-1]
        cache_path = cache_dir / filename

        print(f"\n  {tool_name}:")
        try:
            download_file(url, cache_path)
        except DownloadError as e:
            print(f"    ERROR: {e}")
            continue

        sha256 = hashlib.sha256()
        with open(cache_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        old = plat_cfg.get("sha256", "")
        if old != checksum:
            plat_cfg["sha256"] = checksum
            print(f"    SHA-256: {checksum}")
            if old:
                print(f"    (was:    {old})")
            updated = True
        else:
            print(f"    SHA-256 unchanged: {checksum[:16]}...")

    if updated:
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            f.write("\n")
        print(f"\nManifest updated: {MANIFEST_PATH}")
    else:
        print("\nNo changes to manifest.")


def main():
    parser = argparse.ArgumentParser(
        description="Download and set up portable embedded build tools."
    )
    parser.add_argument(
        "--tools", "-t",
        nargs="*",
        help="Specific tools to install. Aliases: gcc, cmake, ninja, python",
    )
    parser.add_argument(
        "--platform", "-p",
        help="Override platform detection (e.g., linux-x64, darwin-arm64, win32-x64)",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force reinstall even if version matches",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Download and verify checksums only; do not extract",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove all downloaded tools and cache",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tools with versions and install status",
    )
    parser.add_argument(
        "--compute-checksums",
        action="store_true",
        help="Download tools and compute SHA-256 checksums, updating the manifest",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Override download cache directory",
    )
    args = parser.parse_args()

    if args.clean:
        clean_tools()
        return

    plat = args.platform or detect_platform()
    print(f"Platform: {plat}")

    cache_dir = args.cache_dir or DOWNLOAD_CACHE_DIR

    manifest = load_manifest()
    all_tools = manifest["tools"]

    # --list: show tool info and exit
    if args.list:
        list_tools(manifest, plat)
        return

    # --compute-checksums: download + hash + update manifest
    if args.compute_checksums:
        compute_checksums(manifest, plat, cache_dir)
        return

    # Determine which tools to set up
    if args.tools:
        selected = [resolve_tool_name(t) for t in args.tools]
        for t in selected:
            if t not in all_tools:
                print(f"ERROR: Unknown tool '{t}'. Available: {list(all_tools.keys())}", file=sys.stderr)
                sys.exit(1)
    else:
        selected = list(all_tools.keys())
        print(f"Installing all tools: {', '.join(selected)}")

    if args.verify:
        # --verify: download and verify checksums only
        print("\nVerify mode: downloading and checking checksums only.\n")
        results = {}
        for tool_name in selected:
            tool_cfg = all_tools[tool_name]
            if plat not in tool_cfg["platforms"]:
                print(f"  {tool_name}: SKIP (no binary for {plat})")
                results[tool_name] = True
                continue
            plat_cfg = tool_cfg["platforms"][plat]
            url = plat_cfg["url"]
            sha256 = plat_cfg.get("sha256", "")
            filename = url.rsplit("/", 1)[-1]
            cache_path = cache_dir / filename
            print(f"  {tool_name}:")
            try:
                download_file(url, cache_path)
                ok = verify_sha256(cache_path, sha256)
                results[tool_name] = ok
            except DownloadError as e:
                print(f"    ERROR: {e}")
                results[tool_name] = False
    else:
        # Normal mode: parallel download to warm cache, then sequential extract
        to_download = []
        for tool_name in selected:
            tool_cfg = all_tools[tool_name]
            installed = get_installed_version(tool_name)
            if installed == tool_cfg["version"] and not args.force:
                continue
            if plat not in tool_cfg["platforms"]:
                continue
            plat_cfg = tool_cfg["platforms"][plat]
            url = plat_cfg["url"]
            filename = url.rsplit("/", 1)[-1]
            cache_path = cache_dir / filename
            if not cache_path.exists():
                to_download.append((tool_name, url, cache_path))

        if to_download:
            print(f"\nDownloading {len(to_download)} archive(s) in parallel...")
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for tool_name, url, cache_path in to_download:
                    future = executor.submit(download_file, url, cache_path, 3, False)
                    futures[future] = tool_name
                for future in as_completed(futures):
                    tname = futures[future]
                    try:
                        future.result()
                        print(f"  Downloaded: {tname}")
                    except DownloadError as e:
                        print(f"  FAILED: {tname}: {e}")

        # Extract sequentially (downloads are cached from parallel phase)
        results = {}
        for tool_name in selected:
            ok = setup_tool(tool_name, all_tools[tool_name], plat, cache_dir, force=args.force)
            results[tool_name] = ok

    # Summary
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {name}: {status}")

    # Print env info
    print_env_info(plat, manifest)

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
