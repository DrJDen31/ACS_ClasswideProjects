/*
 * TLB Miss Impact Kernel - Experiment 7 (Windows Version)
 * 
 * This kernel stresses the TLB by accessing memory across many pages.
 * Windows version using VirtualAlloc with LARGE_PAGES.
 * 
 * Compile: cl /O2 /EHsc tlb_miss_kernel_windows.cpp
 * Or with CMake (already configured)
 * 
 * Run: tlb_miss_kernel_windows.exe <total_size_mb> <page_stride_kb> <iterations> [use_large_pages]
 */

#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <cstdlib>
#include <random>
#include <algorithm>
#include <windows.h>

// Page sizes
const size_t PAGE_SIZE_4K = 4096;
const size_t PAGE_SIZE_2M = 2 * 1024 * 1024;

// Access pattern that touches one element per page
void page_strided_access(char* data, size_t total_size, size_t page_stride, size_t iterations) {
    size_t num_pages = total_size / page_stride;
    volatile char temp = 0;
    
    for (size_t iter = 0; iter < iterations; ++iter) {
        for (size_t page = 0; page < num_pages; ++page) {
            size_t offset = page * page_stride;
            if (offset < total_size) {
                temp += data[offset];
                data[offset] = static_cast<char>(temp);
            }
        }
    }
}

// Random page access pattern (induces more TLB misses)
void random_page_access(char* data, size_t total_size, size_t page_stride, size_t iterations) {
    size_t num_pages = total_size / page_stride;
    
    // Create random page order
    std::vector<size_t> page_order(num_pages);
    for (size_t i = 0; i < num_pages; ++i) {
        page_order[i] = i;
    }
    
    std::mt19937 rng(42);
    std::shuffle(page_order.begin(), page_order.end(), rng);
    
    volatile char temp = 0;
    
    for (size_t iter = 0; iter < iterations; ++iter) {
        for (size_t idx = 0; idx < num_pages; ++idx) {
            size_t page = page_order[idx];
            size_t offset = page * page_stride;
            if (offset < total_size) {
                temp += data[offset];
                data[offset] = static_cast<char>(temp);
            }
        }
    }
}

// Allocate memory with optional large pages
char* allocate_memory(size_t size, bool use_large_pages) {
    char* ptr = nullptr;
    
    if (use_large_pages) {
        // Enable large page privilege (may require admin)
        HANDLE token;
        if (OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &token)) {
            TOKEN_PRIVILEGES tp;
            tp.PrivilegeCount = 1;
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;
            
            if (LookupPrivilegeValue(NULL, SE_LOCK_MEMORY_NAME, &tp.Privileges[0].Luid)) {
                AdjustTokenPrivileges(token, FALSE, &tp, 0, NULL, NULL);
            }
            CloseHandle(token);
        }
        
        // Try to allocate large pages
        ptr = static_cast<char*>(VirtualAlloc(NULL, size, 
            MEM_COMMIT | MEM_RESERVE | MEM_LARGE_PAGES, 
            PAGE_READWRITE));
        
        if (ptr) {
            std::cout << "Using Large Pages (2MB)" << std::endl;
        } else {
            std::cout << "Large Page allocation failed, falling back to standard pages" << std::endl;
            std::cout << "Note: Large pages may require administrator privileges" << std::endl;
        }
    }
    
    // Fallback to standard allocation
    if (!ptr) {
        ptr = static_cast<char*>(VirtualAlloc(NULL, size, 
            MEM_COMMIT | MEM_RESERVE, 
            PAGE_READWRITE));
        
        if (ptr) {
            std::cout << "Using Standard Pages (4KB)" << std::endl;
        }
    }
    
    return ptr;
}

void free_memory(char* ptr, size_t size) {
    if (ptr) {
        VirtualFree(ptr, 0, MEM_RELEASE);
    }
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <total_size_mb> <page_stride_kb> <iterations> [use_large_pages]" << std::endl;
        std::cerr << "Example: " << argv[0] << " 100 4 1000 0" << std::endl;
        std::cerr << "  total_size_mb: Total memory to allocate (MB)" << std::endl;
        std::cerr << "  page_stride_kb: Stride between accesses (KB)" << std::endl;
        std::cerr << "  iterations: Number of passes over memory" << std::endl;
        std::cerr << "  use_large_pages: 0=standard 4KB, 1=large 2MB (requires admin)" << std::endl;
        return 1;
    }

    size_t total_size_mb = std::atoi(argv[1]);
    size_t page_stride_kb = std::atoi(argv[2]);
    size_t iterations = std::atoi(argv[3]);
    bool use_large_pages = (argc > 4) ? (std::atoi(argv[4]) != 0) : false;

    size_t total_size = total_size_mb * 1024 * 1024;
    size_t page_stride = page_stride_kb * 1024;

    std::cout << "TLB Miss Impact Kernel - Experiment 7 (Windows)" << std::endl;
    std::cout << "================================================" << std::endl;
    std::cout << "Total Size: " << total_size_mb << " MB" << std::endl;
    std::cout << "Page Stride: " << page_stride_kb << " KB" << std::endl;
    std::cout << "Iterations: " << iterations << std::endl;
    std::cout << "Pages Touched: " << (total_size / page_stride) << std::endl;
    std::cout << std::endl;

    // Allocate memory
    char* data = allocate_memory(total_size, use_large_pages);
    
    if (!data) {
        std::cerr << "Error: Failed to allocate memory" << std::endl;
        return 1;
    }

    // Initialize memory
    std::cout << "Initializing memory..." << std::endl;
    memset(data, 0, total_size);

    // Warm-up
    std::cout << "Warming up..." << std::endl;
    page_strided_access(data, total_size, page_stride, 3);

    // Benchmark
    std::cout << "Running benchmark..." << std::endl;
    auto start = std::chrono::high_resolution_clock::now();
    
    page_strided_access(data, total_size, page_stride, iterations);
    
    auto end = std::chrono::high_resolution_clock::now();

    // Calculate timing
    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    double seconds = duration / 1e9;
    size_t pages_accessed = (total_size / page_stride) * iterations;
    double pages_per_sec = pages_accessed / seconds;

    std::cout << std::endl;
    std::cout << "Results:" << std::endl;
    std::cout << "  Total Time: " << seconds << " seconds" << std::endl;
    std::cout << "  Time per Iteration: " << (seconds / iterations * 1e6) << " µs" << std::endl;
    std::cout << "  Pages Accessed: " << pages_accessed << std::endl;
    std::cout << "  Pages per Second: " << pages_per_sec << std::endl;
    std::cout << "  Bandwidth: " << ((pages_accessed * page_stride) / (seconds * 1e9)) << " GB/s" << std::endl;

    // Cleanup
    free_memory(data, total_size);

    std::cout << std::endl;
    std::cout << "To measure TLB misses with PCM, run:" << std::endl;
    std::cout << "  pcm.exe -e -- " << argv[0] << " " << total_size_mb << " " << page_stride_kb << " " << iterations << " " << (use_large_pages ? "1" : "0") << std::endl;

    return 0;
}
