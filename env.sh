#!/usr/bin/env bash
# Embedded Build Tools — Set environment variables for current shell
# Usage: source env.sh   (or: . env.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ROOT="$SCRIPT_DIR/tools"

if [ -d "$TOOLS_ROOT/arm-none-eabi-gcc/bin" ]; then
    export PATH="$TOOLS_ROOT/arm-none-eabi-gcc/bin:$PATH"
    export ARM_GCC="$TOOLS_ROOT/arm-none-eabi-gcc/bin/arm-none-eabi-gcc"
    export ARM_GDB="$TOOLS_ROOT/arm-none-eabi-gcc/bin/arm-none-eabi-gdb"
    export ARM_GCC_DIR="$TOOLS_ROOT/arm-none-eabi-gcc"
fi

if [ -d "$TOOLS_ROOT/cmake/bin" ]; then
    export PATH="$TOOLS_ROOT/cmake/bin:$PATH"
    export CMAKE="$TOOLS_ROOT/cmake/bin/cmake"
fi

if [ -d "$TOOLS_ROOT/ninja-build/bin" ]; then
    export PATH="$TOOLS_ROOT/ninja-build/bin:$PATH"
    export NINJA="$TOOLS_ROOT/ninja-build/bin/ninja"
fi

if [ -d "$TOOLS_ROOT/python/bin" ]; then
    export PATH="$TOOLS_ROOT/python/bin:$PATH"
    export PYTHON="$TOOLS_ROOT/python/bin/python3"
fi

echo "Embedded build tools added to PATH."
