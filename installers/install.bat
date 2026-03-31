@echo off
setlocal enabledelayedexpansion
REM ─────────────────────────────────────────────────────────────────────────────
REM Embedded Build Tools — One-line installer for Windows
REM
REM Downloads and extracts the correct pre-built release for your platform.
REM
REM Usage (PowerShell — recommended):
REM   irm https://github.com/mylonics/embedded-build-tools/releases/latest/download/install.bat -OutFile install.bat; .\install.bat
REM
REM Usage (cmd):
REM   install.bat
REM   install.bat --version v1.0.0 --dest my-tools
REM
REM Options:
REM   --version <tag>   GitHub release tag (default: latest)
REM   --dest <dir>      Destination directory (default: embedded-build-tools)
REM ─────────────────────────────────────────────────────────────────────────────

set "REPO=mylonics/embedded-build-tools"
set "VERSION=latest"
set "DEST=embedded-build-tools"

REM ── Parse arguments ────────────────────────────────────────────────────────

:parse_args
if "%~1"=="" goto :detect_platform
if /i "%~1"=="--version" ( set "VERSION=%~2" & shift & shift & goto :parse_args )
if /i "%~1"=="-v"        ( set "VERSION=%~2" & shift & shift & goto :parse_args )
if /i "%~1"=="--dest"    ( set "DEST=%~2"    & shift & shift & goto :parse_args )
if /i "%~1"=="-d"        ( set "DEST=%~2"    & shift & shift & goto :parse_args )
if /i "%~1"=="--help"    ( goto :show_help )
if /i "%~1"=="-h"        ( goto :show_help )
echo Unknown option: %~1
exit /b 1

:show_help
echo Usage: install.bat [--version TAG] [--dest DIR]
echo.
echo   --version, -v TAG   GitHub release tag (default: latest)
echo   --dest, -d DIR      Destination directory (default: embedded-build-tools)
exit /b 0

REM ── Detect platform ────────────────────────────────────────────────────────

:detect_platform
set "PLATFORM=win32-x64"

REM Check for ARM64 Windows
if defined PROCESSOR_ARCHITECTURE (
    if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
        echo Error: Windows ARM64 is not currently supported.
        exit /b 1
    )
)

set "ARTIFACT=embedded-build-tools-%PLATFORM%.zip"

if "%VERSION%"=="latest" (
    set "URL=https://github.com/%REPO%/releases/latest/download/%ARTIFACT%"
) else (
    set "URL=https://github.com/%REPO%/releases/download/%VERSION%/%ARTIFACT%"
)

REM ── Download ───────────────────────────────────────────────────────────────

echo Platform:    %PLATFORM%
echo Version:     %VERSION%
echo Artifact:    %ARTIFACT%
echo Destination: %DEST%
echo.

set "TMPFILE=%TEMP%\ebt-installer-%RANDOM%.zip"

echo Downloading %URL%...

REM Try PowerShell first (available on all modern Windows)
where powershell >nul 2>&1
if %ERRORLEVEL% equ 0 (
    powershell -NoProfile -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%URL%' -OutFile '%TMPFILE%'"
    if !ERRORLEVEL! neq 0 (
        echo Error: Download failed.
        exit /b 1
    )
    goto :extract
)

REM Fallback to curl (ships with Windows 10+)
where curl >nul 2>&1
if %ERRORLEVEL% equ 0 (
    curl -fSL -o "%TMPFILE%" "%URL%"
    if !ERRORLEVEL! neq 0 (
        echo Error: Download failed.
        exit /b 1
    )
    goto :extract
)

echo Error: Neither PowerShell nor curl found. Cannot download.
exit /b 1

REM ── Extract ────────────────────────────────────────────────────────────────

:extract
echo Extracting to %DEST%...

if not exist "%DEST%" mkdir "%DEST%"

REM Use PowerShell to extract
powershell -NoProfile -Command ^
    "Expand-Archive -Path '%TMPFILE%' -DestinationPath '%DEST%' -Force"

if %ERRORLEVEL% neq 0 (
    echo Error: Extraction failed.
    del "%TMPFILE%" 2>nul
    exit /b 1
)

del "%TMPFILE%" 2>nul

REM ── Done ───────────────────────────────────────────────────────────────────

echo.
echo Embedded build tools installed to: %DEST%
echo.
echo Next steps:
echo   cd %DEST%
echo   call env.bat
echo.

endlocal
