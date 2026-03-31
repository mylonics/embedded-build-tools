@echo off
REM Embedded Build Tools — Set environment variables for current shell
REM Usage: call env.bat

set "TOOLS_ROOT=%~dp0tools"

if exist "%TOOLS_ROOT%\arm-none-eabi-gcc\bin" (
    set "PATH=%TOOLS_ROOT%\arm-none-eabi-gcc\bin;%PATH%"
    set "ARM_GCC=%TOOLS_ROOT%\arm-none-eabi-gcc\bin\arm-none-eabi-gcc.exe"
    set "ARM_GDB=%TOOLS_ROOT%\arm-none-eabi-gcc\bin\arm-none-eabi-gdb.exe"
    set "ARM_GCC_DIR=%TOOLS_ROOT%\arm-none-eabi-gcc"
)

if exist "%TOOLS_ROOT%\cmake\bin" (
    set "PATH=%TOOLS_ROOT%\cmake\bin;%PATH%"
    set "CMAKE=%TOOLS_ROOT%\cmake\bin\cmake.exe"
)

if exist "%TOOLS_ROOT%\ninja-build\bin" (
    set "PATH=%TOOLS_ROOT%\ninja-build\bin;%PATH%"
    set "NINJA=%TOOLS_ROOT%\ninja-build\bin\ninja.exe"
)

if exist "%TOOLS_ROOT%\python\python" (
    set "PATH=%TOOLS_ROOT%\python\python;%PATH%"
    set "PYTHON=%TOOLS_ROOT%\python\python\python.exe"
)

echo Embedded build tools added to PATH.
