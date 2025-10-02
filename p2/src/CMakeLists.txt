cmake_minimum_required(VERSION 3.16)
project(P2_MemoryKernels CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -Wall")
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")

# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/../bin)

# Experiment 6: Cache Miss Impact Kernel
add_executable(cache_miss_kernel cache_miss_kernel.cpp)

# Experiment 7: TLB Miss Kernel (Experiment 7)
if(WIN32)
    # Windows version using VirtualAlloc
    add_executable(tlb_miss_kernel tlb_miss_kernel_windows.cpp)
    target_compile_options(tlb_miss_kernel PRIVATE ${COMMON_FLAGS})
else()
    # Linux version using mmap
    add_executable(tlb_miss_kernel tlb_miss_kernel.cpp)
    target_compile_options(tlb_miss_kernel PRIVATE ${COMMON_FLAGS})
endif()
set_target_properties(tlb_miss_kernel PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${OUTPUT_DIRECTORY}")

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "Output directory: ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")
