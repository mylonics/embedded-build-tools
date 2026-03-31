# Embedded Build Tools

Portable, self-contained build environment for embedded targets (ARM Cortex-M).  
Includes **GCC**, **GDB**, **CMake**, **Ninja**, and **Python** — all pre-built and ready to use on Windows, Linux, and macOS with zero external dependencies.

## Why?

- **Portable** — No system-wide installation required. Drop into any project, Electron app, or CI pipeline.
- **No xPack dependency** — Uses xPack binaries as the upstream source, but downstream consumers never need the xPack CLI or npm.
- **Cross-platform** — Windows (x64), Linux (x64/arm64), macOS (x64/arm64).
- **Reproducible** — Pinned versions in `tool-manifest.json`. Every developer and CI runner gets the exact same tools.
- **Auto-updating** — GitHub Action checks for new releases weekly and opens a PR.

## Quick Start

### Option A: Clone and download tools

```bash
git clone https://github.com/mylonics/embedded-build-tools.git
cd embedded-build-tools
python setup.py
```

This downloads and extracts all tools into the `tools/` directory (~1.5 GB).

### Option B: One-line installer

Single-command installers that auto-detect your platform and download the correct release:

**Bash (Linux / macOS):**

```bash
curl -fsSL https://github.com/mylonics/embedded-build-tools/releases/latest/download/install.sh | bash
```

**Python (any platform):**

```bash
curl -fsSL -o install.py https://github.com/mylonics/embedded-build-tools/releases/latest/download/install.py && python install.py
```

**Node.js:**

```bash
curl -fsSL -o install.js https://github.com/mylonics/embedded-build-tools/releases/latest/download/install.js && node install.js
```

**Windows (cmd):**

```bat
powershell -Command "Invoke-WebRequest -Uri https://github.com/mylonics/embedded-build-tools/releases/latest/download/install.bat -OutFile install.bat" && install.bat
```

All installers support `--version <tag>` to pin a specific release and `--dest <dir>` to choose the install location.

### Option C: Manual download

Pre-built bundles are available on the [Releases](https://github.com/mylonics/embedded-build-tools/releases) page:

| Platform | Artifact |
|----------|----------|
| Windows x64 | `embedded-build-tools-win32-x64.zip` |
| Linux x64 | `embedded-build-tools-linux-x64.tar.gz` |
| Linux arm64 | `embedded-build-tools-linux-arm64.tar.gz` |
| macOS x64 (Intel) | `embedded-build-tools-darwin-x64.tar.gz` |
| macOS arm64 (Apple Silicon) | `embedded-build-tools-darwin-arm64.tar.gz` |

**macOS only — remove quarantine attribute:**

macOS Gatekeeper blocks unsigned binaries downloaded from the internet. After extracting, run:

```bash
xattr -cr embedded-build-tools/tools
```

This is required once after download. The one-line installers and `python setup.py` handle this automatically.

### Use the tools

**Set up environment variables:**

```bash
# Linux / macOS
source env.sh

# Windows (cmd)
call env.bat

# Windows (PowerShell)
. .\env.ps1
```

**Or use the Python helper:**

```python
from scripts.env_helper import EmbeddedToolchain

tc = EmbeddedToolchain("/path/to/embedded-build-tools")
env = tc.get_env()  # Use with subprocess

# Individual paths
gcc = tc.gcc_path()
gdb = tc.gdb_path()
cmake = tc.cmake_path()
ninja = tc.ninja_path()
```

## Included Tools

| Tool | Source | Description |
|------|--------|-------------|
| `arm-none-eabi-gcc` | [xPack GNU Arm Embedded GCC](https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack) | Cross-compiler for ARM Cortex-M/R/A |
| `cmake` | [xPack CMake](https://github.com/xpack-dev-tools/cmake-xpack) | Build system generator |
| `ninja-build` | [xPack Ninja Build](https://github.com/xpack-dev-tools/ninja-build-xpack) | Fast build system |
| `python` | [python-build-standalone](https://github.com/indygreg/python-build-standalone) | Portable Python (GDB compatible) |

GDB is included with the GCC toolchain as `arm-none-eabi-gdb`.

## setup.py Reference

```bash
python setup.py                          # download all tools for current platform
python setup.py --tools gcc cmake        # download specific tools
python setup.py --platform linux-x64     # override platform detection
python setup.py --list                   # show available tools, versions, and install status
python setup.py --verify                 # download and verify checksums without extracting
python setup.py --compute-checksums      # download + compute SHA-256, update manifest
python setup.py --force                  # force reinstall even if version matches
python setup.py --clean                  # remove all downloaded tools and cache
```

Tool aliases: `gcc` → `arm-none-eabi-gcc`, `arm-gcc` → `arm-none-eabi-gcc`, `ninja` → `ninja-build`, `gdb` → `arm-none-eabi-gcc`

## Integration Guide

### Electron / Desktop Apps

```javascript
// CommonJS
const { EmbeddedToolchain } = require('./embedded-build-tools/integrations/node_helper');

// ESM
import { EmbeddedToolchain } from './embedded-build-tools/integrations/node_helper.mjs';

const tc = new EmbeddedToolchain('/path/to/embedded-build-tools');
const gcc = tc.gccPath();
const env = tc.getEnv();  // Use with child_process.spawn({ env })
```

### CMake Projects

```bash
# Generate CMake flags for cross-compilation
python scripts/env_helper.py --cmake-vars
# Output: -DCMAKE_C_COMPILER=.../arm-none-eabi-gcc -DCMAKE_MAKE_PROGRAM=.../ninja ...
```

Or use in a CMake preset:

```json
{
  "configurePresets": [{
    "name": "arm-debug",
    "generator": "Ninja",
    "binaryDir": "${sourceDir}/build",
    "cacheVariables": {
      "CMAKE_C_COMPILER": "${sourceDir}/tools/arm-none-eabi-gcc/bin/arm-none-eabi-gcc",
      "CMAKE_CXX_COMPILER": "${sourceDir}/tools/arm-none-eabi-gcc/bin/arm-none-eabi-g++",
      "CMAKE_MAKE_PROGRAM": "${sourceDir}/tools/ninja-build/bin/ninja",
      "CMAKE_SYSTEM_NAME": "Generic",
      "CMAKE_SYSTEM_PROCESSOR": "arm"
    }
  }]
}
```

### CI / GitHub Actions

```yaml
- name: Setup embedded tools
  run: python setup.py

- name: Build firmware
  run: |
    source env.sh
    cmake -B build -G Ninja
    cmake --build build
```

### Submodule Usage

Add to your project as a git submodule:

```bash
git submodule add https://github.com/mylonics/embedded-build-tools.git tools/embedded
cd tools/embedded && python setup.py
```

## Directory Structure

```
embedded-build-tools/
├── tool-manifest.json          # Pinned versions & download URLs
├── setup.py                    # Main download/extract script (stdlib only)
├── env.bat / env.sh / env.ps1  # Shell environment scripts
├── scripts/
│   ├── check_updates.py        # Update checker (used by GitHub Action)
│   └── env_helper.py           # Integration helper (Python API + CLI)
├── integrations/
│   ├── arm-none-eabi.cmake     # CMake toolchain file
│   ├── node_helper.js          # Node.js/Electron integration (CJS)
│   └── node_helper.mjs         # Node.js/Electron integration (ESM)
├── installers/
│   ├── install.sh              # One-line installer (bash)
│   ├── install.bat             # One-line installer (Windows cmd)
│   ├── install.py              # One-line installer (Python, stdlib only)
│   └── install.js              # One-line installer (Node.js, zero deps)
├── .github/workflows/
│   ├── check-updates.yml       # Weekly update checker → opens PRs
│   └── build.yml               # Validate tools on all platforms
└── tools/                      # Downloaded tools (gitignored)
    ├── arm-none-eabi-gcc/
    ├── cmake/
    ├── ninja-build/
    └── python/
```

## Updating Tools

### Automatic (recommended)

The `check-updates.yml` GitHub Action runs weekly and automatically opens a PR when new tool versions are available.

### Manual

1. Edit `tool-manifest.json` with the new version and URLs
2. Run `python setup.py --force` to redownload
3. Commit the manifest change

Or use the checker script locally:

```bash
python scripts/check_updates.py --apply
```

## Platform Support

| Platform | Architecture | Status |
|----------|-------------|--------|
| Windows  | x64         | ✅     |
| Linux    | x64         | ✅     |
| Linux    | arm64       | ✅     |
| macOS    | x64 (Intel) | ✅     |
| macOS    | arm64 (M1+) | ✅     |

## License

The scripts in this repository are MIT licensed. The downloaded tools retain their original licenses:
- GCC: GPL v3
- GDB: GPL v3  
- CMake: BSD 3-Clause
- Ninja: Apache 2.0
- Python: PSF License
