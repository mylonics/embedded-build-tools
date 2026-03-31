# Embedded Build Tools — Set environment variables for current shell
# Usage: . .\env.ps1   (or: . env.ps1)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ToolsRoot = Join-Path $ScriptDir "tools"

if (Test-Path (Join-Path $ToolsRoot "arm-none-eabi-gcc\bin")) {
    $env:PATH = "$(Join-Path $ToolsRoot 'arm-none-eabi-gcc\bin');$env:PATH"
    $env:ARM_GCC = Join-Path $ToolsRoot "arm-none-eabi-gcc\bin\arm-none-eabi-gcc.exe"
    $env:ARM_GDB = Join-Path $ToolsRoot "arm-none-eabi-gcc\bin\arm-none-eabi-gdb.exe"
    $env:ARM_GCC_DIR = Join-Path $ToolsRoot "arm-none-eabi-gcc"
}

if (Test-Path (Join-Path $ToolsRoot "cmake\bin")) {
    $env:PATH = "$(Join-Path $ToolsRoot 'cmake\bin');$env:PATH"
    $env:CMAKE = Join-Path $ToolsRoot "cmake\bin\cmake.exe"
}

if (Test-Path (Join-Path $ToolsRoot "ninja-build\bin")) {
    $env:PATH = "$(Join-Path $ToolsRoot 'ninja-build\bin');$env:PATH"
    $env:NINJA = Join-Path $ToolsRoot "ninja-build\bin\ninja.exe"
}

if (Test-Path (Join-Path $ToolsRoot "python\python")) {
    $env:PATH = "$(Join-Path $ToolsRoot 'python\python');$env:PATH"
    $env:PYTHON = Join-Path $ToolsRoot "python\python\python.exe"
}

Write-Host "Embedded build tools added to PATH."
