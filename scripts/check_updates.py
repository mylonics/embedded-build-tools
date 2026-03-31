#!/usr/bin/env python3
"""
Check for new releases of embedded build tools on GitHub.

This script queries the GitHub API for the latest releases of each tool
defined in tool-manifest.json, compares against current versions, and
optionally updates the manifest.

Usage:
    python scripts/check_updates.py --output updates.json   # check only
    python scripts/check_updates.py --apply                  # check + update manifest
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
MANIFEST_PATH = ROOT_DIR / "tool-manifest.json"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

PLATFORM_SUFFIXES = {
    "win32-x64": ["win32-x64.zip"],
    "linux-x64": ["linux-x64.tar.gz"],
    "linux-arm64": ["linux-arm64.tar.gz"],
    "darwin-x64": ["darwin-x64.tar.gz"],
    "darwin-arm64": ["darwin-arm64.tar.gz"],
}

# python-build-standalone uses different naming
PYTHON_PLATFORM_MAP = {
    "win32-x64": "x86_64-pc-windows-msvc-install_only_stripped.tar.gz",
    "linux-x64": "x86_64-unknown-linux-gnu-install_only_stripped.tar.gz",
    "linux-arm64": "aarch64-unknown-linux-gnu-install_only_stripped.tar.gz",
    "darwin-x64": "x86_64-apple-darwin-install_only_stripped.tar.gz",
    "darwin-arm64": "aarch64-apple-darwin-install_only_stripped.tar.gz",
}


def github_api(url: str) -> dict:
    """Make an authenticated GitHub API request."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"  WARNING: API request failed for {url}: {e}", file=sys.stderr)
        return {}


def get_latest_xpack_release(repo: str) -> dict | None:
    """Get the latest release from an xPack GitHub repo."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    data = github_api(url)
    if not data or "tag_name" not in data:
        return None
    return data


def get_latest_python_release(repo: str) -> dict | None:
    """Get the latest release from python-build-standalone."""
    url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
    releases = github_api(url)
    if not releases:
        return None
    
    # Find the latest release that has cpython-3.12.x builds
    for release in releases:
        tag = release.get("tag_name", "")
        assets = release.get("assets", [])
        # Check if this release has Python 3.12 install_only_stripped builds
        has_312 = any(
            "cpython-3.12" in a["name"] and "install_only_stripped" in a["name"]
            for a in assets
        )
        if has_312:
            return release
    
    return None


def extract_xpack_version(tag_name: str) -> str:
    """Extract version from xPack tag like 'v13.3.1-1.1' -> '13.3.1-1.1'."""
    return tag_name.lstrip("v")


def extract_python_version_from_assets(assets: list[dict]) -> str | None:
    """Extract Python version from asset names like 'cpython-3.12.6+20240909-...'."""
    for asset in assets:
        m = re.search(r"cpython-(\d+\.\d+\.\d+)\+(\d+)", asset["name"])
        if m:
            return f"{m.group(1)}-{m.group(2)[:1]}"  # e.g., "3.12.6-2"
    return None


def find_xpack_asset_url(assets: list[dict], platform_suffix: str) -> str | None:
    """Find the download URL for a specific platform asset."""
    for asset in assets:
        if asset["name"].endswith(platform_suffix):
            return asset["browser_download_url"]
    return None


def find_python_asset_url(assets: list[dict], platform_pattern: str) -> str | None:
    """Find the download URL for a python-build-standalone asset."""
    for asset in assets:
        if platform_pattern in asset["name"] and "cpython-3.12" in asset["name"]:
            return asset["browser_download_url"]
    return None


def check_tool_update(tool_name: str, tool_cfg: dict) -> dict | None:
    """Check if a tool has a newer version available. Returns update info or None."""
    repo = tool_cfg.get("repo", "")
    current_version = tool_cfg["version"]

    print(f"  Checking {tool_name} (current: {current_version})...")

    if tool_name == "python":
        release = get_latest_python_release(repo)
    else:
        release = get_latest_xpack_release(repo)

    if not release:
        print(f"    Could not fetch latest release for {repo}")
        return None

    tag = release["tag_name"]
    assets = release.get("assets", [])

    if tool_name == "python":
        # For python-build-standalone, we extract version differently
        py_version = extract_python_version_from_assets(assets)
        if not py_version:
            print(f"    Could not determine Python version from assets")
            return None
        new_version = py_version
    else:
        new_version = extract_xpack_version(tag)

    if new_version == current_version:
        print(f"    Up to date: {current_version}")
        return None

    print(f"    Update available: {current_version} -> {new_version}")

    # Build new platform URLs
    new_platforms = {}
    for plat_key in tool_cfg["platforms"]:
        if tool_name == "python":
            pattern = PYTHON_PLATFORM_MAP.get(plat_key)
            if pattern:
                url = find_python_asset_url(assets, pattern)
        else:
            suffixes = PLATFORM_SUFFIXES.get(plat_key, [])
            url = None
            for suffix in suffixes:
                url = find_xpack_asset_url(assets, suffix)
                if url:
                    break

        if url:
            new_platforms[plat_key] = {
                **tool_cfg["platforms"][plat_key],
                "url": url,
                "sha256": "",  # Will need to be computed after download
            }
        else:
            print(f"    WARNING: No asset found for {plat_key}")
            new_platforms[plat_key] = tool_cfg["platforms"][plat_key]

    return {
        "tool": tool_name,
        "current_version": current_version,
        "new_version": new_version,
        "tag": tag,
        "platforms": new_platforms,
    }


def main():
    parser = argparse.ArgumentParser(description="Check for tool updates")
    parser.add_argument("--output", "-o", type=Path, help="Write results to JSON file")
    parser.add_argument("--apply", action="store_true", help="Apply updates to manifest")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    tools = manifest["tools"]

    print("Checking for updates...")
    updates = []

    for tool_name, tool_cfg in tools.items():
        update = check_tool_update(tool_name, tool_cfg)
        if update:
            updates.append(update)

    has_updates = len(updates) > 0
    summary_lines = []
    for u in updates:
        summary_lines.append(f"- **{u['tool']}**: {u['current_version']} → {u['new_version']}")

    result = {
        "has_updates": has_updates,
        "updates": updates,
        "summary": "\n".join(summary_lines) if summary_lines else "All tools up to date.",
    }

    if args.output:
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nResults written to {args.output}")

    if args.apply and has_updates:
        print("\nApplying updates to manifest...")
        for update in updates:
            tool_name = update["tool"]
            manifest["tools"][tool_name]["version"] = update["new_version"]
            manifest["tools"][tool_name]["platforms"] = update["platforms"]

            # Update URLs that might contain version in the path
            # (xPack repos embed version in tag/URL)
            print(f"  Updated {tool_name} -> {update['new_version']}")

        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Manifest updated: {MANIFEST_PATH}")

    if has_updates:
        print(f"\n{len(updates)} update(s) available:")
        for line in summary_lines:
            print(f"  {line}")
    else:
        print("\nAll tools are up to date.")


if __name__ == "__main__":
    main()
