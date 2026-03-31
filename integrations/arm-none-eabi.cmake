# CMake Toolchain File — ARM Cortex-M Cross Compilation
#
# Usage:
#   cmake -DCMAKE_TOOLCHAIN_FILE=path/to/embedded-build-tools/integrations/arm-none-eabi.cmake ..
#
# This file auto-detects the tool paths relative to its own location.

# Determine the tools directory
get_filename_component(_TOOLCHAIN_DIR "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
set(_TOOLS_DIR "${_TOOLCHAIN_DIR}/tools")

# System
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# Detect host OS for executable extension
if(CMAKE_HOST_WIN32)
    set(_EXE_EXT ".exe")
else()
    set(_EXE_EXT "")
endif()

# Compilers
set(CMAKE_C_COMPILER "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-gcc${_EXE_EXT}" CACHE FILEPATH "C compiler" FORCE)
set(CMAKE_CXX_COMPILER "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-g++${_EXE_EXT}" CACHE FILEPATH "C++ compiler" FORCE)
set(CMAKE_ASM_COMPILER "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-gcc${_EXE_EXT}" CACHE FILEPATH "ASM compiler" FORCE)

# Binutils
set(CMAKE_OBJCOPY "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-objcopy${_EXE_EXT}" CACHE FILEPATH "objcopy" FORCE)
set(CMAKE_OBJDUMP "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-objdump${_EXE_EXT}" CACHE FILEPATH "objdump" FORCE)
set(CMAKE_SIZE_UTIL "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-size${_EXE_EXT}" CACHE FILEPATH "size" FORCE)
set(CMAKE_AR "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-ar${_EXE_EXT}" CACHE FILEPATH "archiver" FORCE)
set(CMAKE_RANLIB "${_TOOLS_DIR}/arm-none-eabi-gcc/bin/arm-none-eabi-ranlib${_EXE_EXT}" CACHE FILEPATH "ranlib" FORCE)

# Build tool
if(EXISTS "${_TOOLS_DIR}/ninja-build/bin/ninja${_EXE_EXT}")
    set(CMAKE_MAKE_PROGRAM "${_TOOLS_DIR}/ninja-build/bin/ninja${_EXE_EXT}" CACHE FILEPATH "Build program" FORCE)
endif()

# Search paths — only search the cross toolchain, not the host
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Common embedded flags (can be overridden by the project)
set(CMAKE_C_FLAGS_INIT "-fdata-sections -ffunction-sections")
set(CMAKE_CXX_FLAGS_INIT "-fdata-sections -ffunction-sections -fno-exceptions -fno-rtti")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-Wl,--gc-sections -specs=nosys.specs")
