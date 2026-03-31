# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Updated GitHub Actions to Node.js 24-compatible versions:
  - `actions/checkout` v4 → v6
  - `actions/setup-python` v5 → v6
  - `actions/upload-artifact` v4 → v7
  - `actions/download-artifact` v4 → v8
  - `peter-evans/create-pull-request` v6 → v8
- Replaced deprecated `macos-13` CI runner with `macos-15-intel`
- Release notes now include a full table of all included tool versions

## [vgcc-13.3.1-1.1] - 2025-01-01

### Added

- Initial release of portable embedded build tools
- ARM GCC cross-compiler (`arm-none-eabi-gcc`) v13.3.1-1.1
- CMake v3.28.6-1
- Ninja Build v1.12.1-1
- Python v3.12.6-1
- Support for Windows x64, Linux x64/arm64, macOS x64/arm64
- Automated weekly update checks via GitHub Actions
- Environment helper scripts (`env.sh`, `env.bat`, `env_helper.py`)
- CMake toolchain file for ARM cross-compilation
- Node.js/Electron integration helper
