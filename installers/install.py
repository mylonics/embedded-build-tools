#!/usr/bin/env python3
"""
Embedded Build Tools — Cross-platform installer (Python, stdlib only)

Downloads and extracts the correct pre-built release for your platform.

Usage:
    python install.py
    python install.py --version v1.0.0 --dest ./my-tools
    python install.py --platform linux-arm64   # override detection

No external dependencies — uses only Python stdlib.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError

REPO = "mylonics/embedded-build-tools"


def detect_platform() -> str:
    """Detect the current platform in node-style format: os-arch."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    os_map = {"windows": "win32", "linux": "linux", "darwin": "darwin"}
    arch_map = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}

    os_name = os_map.get(system)
    arch_name = arch_map.get(machine)

    if not os_name or not arch_name:
        print(f"Error: Unsupported platform: {system}-{machine}", file=sys.stderr)
        sys.exit(1)

    return f"{os_name}-{arch_name}"


def download(url: str, dest: Path) -> Path:
    """Download a file with progress."""
    print(f"Downloading: {url}")

    def _progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            pct = min(100, downloaded * 100 // total_size)
            mb_down = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\r  Progress: {pct:3d}% ({mb_down:.1f}/{mb_total:.1f} MB)", end="", flush=True)

    try:
        urlretrieve(url, str(dest), reporthook=_progress)
        print()
        return dest
    except (URLError, HTTPError) as e:
        print(f"\nError: Download failed: {e}", file=sys.stderr)
        sys.exit(1)


def extract(archive: Path, dest: Path):
    """Extract archive to destination directory."""
    print(f"Extracting to: {dest}")
    dest.mkdir(parents=True, exist_ok=True)

    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(dest)
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive, "r:gz") as tf:
            try:
                tf.extractall(dest, filter="data")
            except TypeError:
                tf.extractall(dest)
    else:
        print(f"Error: Unknown archive format: {archive.name}", file=sys.stderr)
        sys.exit(1)


def remove_quarantine(directory: Path):
    """Remove macOS Gatekeeper quarantine attribute."""
    if platform.system() != "Darwin":
        return
    print("Removing macOS quarantine attributes...")
    try:
        subprocess.run(["xattr", "-cr", str(directory)], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Download and install Embedded Build Tools for your platform."
    )
    parser.add_argument(
        "--version", "-v",
        default="latest",
        help="GitHub release tag to download (default: latest)",
    )
    parser.add_argument(
        "--dest", "-d",
        type=Path,
        default=Path("embedded-build-tools"),
        help="Destination directory (default: ./embedded-build-tools)",
    )
    parser.add_argument(
        "--platform", "-p",
        help="Override platform detection (e.g., linux-x64, darwin-arm64, win32-x64)",
    )
    args = parser.parse_args()

    plat = args.platform or detect_platform()

    if plat.startswith("win32"):
        artifact = f"embedded-build-tools-{plat}.zip"
    else:
        artifact = f"embedded-build-tools-{plat}.tar.gz"

    if args.version == "latest":
        url = f"https://github.com/{REPO}/releases/latest/download/{artifact}"
    else:
        url = f"https://github.com/{REPO}/releases/download/{args.version}/{artifact}"

    print(f"Platform:    {plat}")
    print(f"Version:     {args.version}")
    print(f"Artifact:    {artifact}")
    print(f"Destination: {args.dest}")
    print()

    # Download to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / artifact
        download(url, tmp_path)
        extract(tmp_path, args.dest)

    # macOS quarantine removal
    remove_quarantine(args.dest)

    # Next steps
    print()
    print(f"Embedded build tools installed to: {args.dest}")
    print()
    if plat.startswith("win32"):
        print("Next steps:")
        print(f"  cd {args.dest}")
        print("  call env.bat        (cmd)")
        print("  . .\\env.ps1         (PowerShell)")
    else:
        print("Next steps:")
        print(f"  cd {args.dest}")
        print("  source env.sh")
    print()


if __name__ == "__main__":
    main()
