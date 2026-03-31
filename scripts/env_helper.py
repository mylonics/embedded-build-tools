#!/usr/bin/env python3
"""
Embedded Build Tools — Environment Helper

Provides functions for downstream applications (Electron, portable apps)
to locate and configure the embedded build tools without any xPack dependency.

Usage from Python:
    from scripts.env_helper import EmbeddedToolchain
    tc = EmbeddedToolchain("/path/to/embedded-build-tools")
    env = tc.get_env()          # dict with PATH, etc. ready to use
    gcc = tc.gcc_path()         # full path to arm-none-eabi-gcc
    gdb = tc.gdb_path()         # full path to arm-none-eabi-gdb
    cmake = tc.cmake_path()     # full path to cmake
    ninja = tc.ninja_path()     # full path to ninja
    python = tc.python_path()   # full path to portable python

Usage from CLI:
    python scripts/env_helper.py --json   # JSON with all paths
    python scripts/env_helper.py --env    # export statements for shell
    python scripts/env_helper.py --path   # just the combined PATH value
"""

import json
import os
import platform
import sys
from pathlib import Path
from typing import Optional


def _detect_platform() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    os_map = {"windows": "win32", "linux": "linux", "darwin": "darwin"}
    arch_map = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}
    return f"{os_map.get(system, system)}-{arch_map.get(machine, machine)}"


class EmbeddedToolchain:
    """Locate and provide paths for all embedded build tools."""

    def __init__(self, root: str | Path, plat: Optional[str] = None):
        self.root = Path(root).resolve()
        self.tools_dir = self.root / "tools"
        self.platform = plat or _detect_platform()
        self._is_windows = self.platform.startswith("win32")
        self._ext = ".exe" if self._is_windows else ""

        # Load manifest for version info
        manifest_path = self.root / "tool-manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                self._manifest = json.load(f)
        else:
            self._manifest = {}

    # ── Individual tool paths ───────────────────────────────────────────

    def gcc_path(self) -> Optional[Path]:
        """Path to arm-none-eabi-gcc executable."""
        p = self.tools_dir / "arm-none-eabi-gcc" / "bin" / f"arm-none-eabi-gcc{self._ext}"
        return p if p.exists() else None

    def gpp_path(self) -> Optional[Path]:
        """Path to arm-none-eabi-g++ executable."""
        p = self.tools_dir / "arm-none-eabi-gcc" / "bin" / f"arm-none-eabi-g++{self._ext}"
        return p if p.exists() else None

    def gdb_path(self) -> Optional[Path]:
        """Path to arm-none-eabi-gdb executable."""
        p = self.tools_dir / "arm-none-eabi-gcc" / "bin" / f"arm-none-eabi-gdb{self._ext}"
        return p if p.exists() else None

    def cmake_path(self) -> Optional[Path]:
        """Path to cmake executable."""
        p = self.tools_dir / "cmake" / "bin" / f"cmake{self._ext}"
        return p if p.exists() else None

    def ninja_path(self) -> Optional[Path]:
        """Path to ninja executable."""
        p = self.tools_dir / "ninja-build" / "bin" / f"ninja{self._ext}"
        return p if p.exists() else None

    def python_path(self) -> Optional[Path]:
        """Path to portable python executable."""
        if self._is_windows:
            # python-build-standalone on Windows: python/python.exe
            p = self.tools_dir / "python" / "python" / f"python{self._ext}"
            if p.exists():
                return p
        p = self.tools_dir / "python" / "bin" / f"python3{self._ext}"
        return p if p.exists() else None

    def objcopy_path(self) -> Optional[Path]:
        """Path to arm-none-eabi-objcopy executable."""
        p = self.tools_dir / "arm-none-eabi-gcc" / "bin" / f"arm-none-eabi-objcopy{self._ext}"
        return p if p.exists() else None

    def size_path(self) -> Optional[Path]:
        """Path to arm-none-eabi-size executable."""
        p = self.tools_dir / "arm-none-eabi-gcc" / "bin" / f"arm-none-eabi-size{self._ext}"
        return p if p.exists() else None

    # ── Directories ─────────────────────────────────────────────────────

    def gcc_bin_dir(self) -> Optional[Path]:
        return self.tools_dir / "arm-none-eabi-gcc" / "bin"

    def cmake_bin_dir(self) -> Optional[Path]:
        return self.tools_dir / "cmake" / "bin"

    def ninja_bin_dir(self) -> Optional[Path]:
        return self.tools_dir / "ninja-build" / "bin"

    def python_bin_dir(self) -> Optional[Path]:
        if self._is_windows:
            d = self.tools_dir / "python" / "python"
            if d.exists():
                return d
        return self.tools_dir / "python" / "bin"

    # ── Combined PATH / env ─────────────────────────────────────────────

    def bin_dirs(self) -> list[Path]:
        """Return list of bin directories that exist."""
        dirs = []
        for d in [self.gcc_bin_dir(), self.cmake_bin_dir(), self.ninja_bin_dir(), self.python_bin_dir()]:
            if d and d.exists():
                dirs.append(d)
        return dirs

    def path_string(self, prepend_to_system: bool = True) -> str:
        """Combined PATH string with all tool bin directories."""
        sep = ";" if self._is_windows else ":"
        tool_paths = sep.join(str(d) for d in self.bin_dirs())
        if prepend_to_system:
            system_path = os.environ.get("PATH", "")
            return f"{tool_paths}{sep}{system_path}" if tool_paths else system_path
        return tool_paths

    def get_env(self, inherit: bool = True) -> dict[str, str]:
        """
        Return a dict suitable for subprocess.Popen(env=...).
        
        Includes PATH with tools prepended, plus convenience variables.
        """
        env = dict(os.environ) if inherit else {}
        env["PATH"] = self.path_string(prepend_to_system=inherit)

        # Convenience variables for downstream use
        gcc = self.gcc_path()
        if gcc:
            env["ARM_GCC"] = str(gcc)
            env["ARM_GCC_DIR"] = str(gcc.parent.parent)

        gdb = self.gdb_path()
        if gdb:
            env["ARM_GDB"] = str(gdb)

        cmake = self.cmake_path()
        if cmake:
            env["CMAKE"] = str(cmake)

        ninja = self.ninja_path()
        if ninja:
            env["NINJA"] = str(ninja)

        py = self.python_path()
        if py:
            env["PYTHON"] = str(py)

        return env

    def cmake_toolchain_vars(self) -> dict[str, str]:
        """Return CMake variable definitions for cross-compilation."""
        gcc = self.gcc_path()
        gpp = self.gpp_path()
        objcopy = self.objcopy_path()
        size_tool = self.size_path()

        vars = {
            "CMAKE_SYSTEM_NAME": "Generic",
            "CMAKE_SYSTEM_PROCESSOR": "arm",
            "CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",
        }
        if gcc:
            vars["CMAKE_C_COMPILER"] = str(gcc)
        if gpp:
            vars["CMAKE_CXX_COMPILER"] = str(gpp)
        if objcopy:
            vars["CMAKE_OBJCOPY"] = str(objcopy)
        if size_tool:
            vars["CMAKE_SIZE"] = str(size_tool)
        ninja = self.ninja_path()
        if ninja:
            vars["CMAKE_MAKE_PROGRAM"] = str(ninja)

        return vars

    def versions(self) -> dict[str, str]:
        """Return installed version for each tool."""
        result = {}
        for tool_name in ["arm-none-eabi-gcc", "cmake", "ninja-build", "python"]:
            stamp = self.tools_dir / tool_name / ".version"
            if stamp.exists():
                result[tool_name] = stamp.read_text(encoding="utf-8").strip()
        return result

    def is_complete(self) -> bool:
        """Check if all expected tools are installed."""
        return all([
            self.gcc_path(),
            self.cmake_path(),
            self.ninja_path(),
            self.python_path(),
        ])

    def to_json(self) -> dict:
        """Serialize all paths and versions to a JSON-friendly dict."""
        return {
            "platform": self.platform,
            "root": str(self.root),
            "tools_dir": str(self.tools_dir),
            "complete": self.is_complete(),
            "versions": self.versions(),
            "paths": {
                "gcc": str(self.gcc_path()) if self.gcc_path() else None,
                "g++": str(self.gpp_path()) if self.gpp_path() else None,
                "gdb": str(self.gdb_path()) if self.gdb_path() else None,
                "objcopy": str(self.objcopy_path()) if self.objcopy_path() else None,
                "size": str(self.size_path()) if self.size_path() else None,
                "cmake": str(self.cmake_path()) if self.cmake_path() else None,
                "ninja": str(self.ninja_path()) if self.ninja_path() else None,
                "python": str(self.python_path()) if self.python_path() else None,
            },
            "bin_dirs": [str(d) for d in self.bin_dirs()],
            "path_string": self.path_string(prepend_to_system=False),
        }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Embedded build tools environment helper")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Root directory of embedded-build-tools")
    parser.add_argument("--platform", help="Override platform (e.g., linux-x64)")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="Output JSON with all paths")
    group.add_argument("--env", action="store_true", help="Output shell export statements")
    group.add_argument("--path", action="store_true", help="Output just the PATH value")
    group.add_argument("--cmake-vars", action="store_true", help="Output CMake -D flags")

    args = parser.parse_args()
    tc = EmbeddedToolchain(args.root, plat=args.platform)

    if args.json:
        print(json.dumps(tc.to_json(), indent=2))
    elif args.env:
        env = tc.get_env(inherit=False)
        is_win = tc.platform.startswith("win32")
        for k, v in sorted(env.items()):
            if is_win:
                print(f'set "{k}={v}"')
            else:
                print(f'export {k}="{v}"')
    elif args.path:
        print(tc.path_string(prepend_to_system=False))
    elif args.cmake_vars:
        for k, v in tc.cmake_toolchain_vars().items():
            print(f"-D{k}={v}")
    else:
        # Default: print a summary
        info = tc.to_json()
        print(f"Platform: {info['platform']}")
        print(f"Root:     {info['root']}")
        print(f"Versions: {json.dumps(info['versions'], indent=2)}")
        print(f"\nTool Paths:")
        for name, path in info["paths"].items():
            status = "✓" if path else "✗ (not installed)"
            print(f"  {name:10s}: {path or status}")
        print(f"\nPATH: {info['path_string']}")


if __name__ == "__main__":
    main()
