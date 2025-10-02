/*
 * TLB Miss Impact Kernel - Experiment 7
 * 
 * This kernel stresses the TLB by accessing memory across many pages.
 * It compares performance with standard 4KB pages vs huge pages (2MB).
 * 
 * Compile: g++ -O3 -march=native -o tlb_miss_kernel tlb_miss_kernel.cpp
 * Run: ./tlb_miss_kernel <total_size_mb> <page_stride> <iterations>
 * 
 * For huge pages:
 *   1. Allocate huge pages: echo 512 | sudo tee /proc/sys/vm/nr_hugepages
 *   2. Compile with -DUSE_HUGEPAGES or use mmap with MAP_HUGETLB
 */

#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <cstdlib>
#include <random>
#include <algorithm>
#include <sys/mman.h>
#include <unistd.h>

// Standard page size
const size_t PAGE_SIZE_4K = 4096;
const size_t PAGE_SIZE_2M = 2 * 1024 * 1024;

// Access pattern that touches one element per page
void page_strided_access(char* data, size_t total_size, size_t page_stride, size_t iterations) {
    size_t num_pages = total_size / page_stride;
    
    for (size_t iter = 0; iter < iterations; ++iter) {
        for (size_t page = 0; page < num_pages; ++page) {
            size_t offset = page * page_stride;
            if (offset < total_size) {
                // Read and write to ensure TLB is used
                volatile char tmp = data[offset];
                data[offset] = tmp + 1;
            }
        }
    }
}

// Random page access pattern
void random_page_access(char* data, size_t total_size, size_t page_stride, size_t iterations) {
    size_t num_pages = total_size / page_stride;
    
    // Generate random page order
    std::vector<size_t> page_order(num_pages);
    for (size_t i = 0; i < num_pages; ++i) {
        page_order[i] = i;
    }
    
    std::mt19937 rng(42);
    std::shuffle(page_order.begin(), page_order.end(), rng);
    
    for (size_t iter = 0; iter < iterations; ++iter) {
        for (size_t i = 0; i < num_pages; ++i) {
            size_t offset = page_order[i] * page_stride;
            if (offset < total_size) {
                volatile char tmp = data[offset];
                data[offset] = tmp + 1;
            }
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <total_size_mb> <page_stride_kb> <iterations> [use_hugepages]" << std::endl;
        std::cerr << "Example: " << argv[0] << " 100 4 1000 0" << std::endl;
        std::cerr << "  total_size_mb: Total memory to allocate in MB" << std::endl;
        std::cerr << "  page_stride_kb: Stride between accesses in KB (4 for 4KB pages)" << std::endl;
        std::cerr << "  iterations: Number of full traversals" << std::endl;
        std::cerr << "  use_hugepages: 0 for standard pages, 1 for huge pages (default: 0)" << std::endl;
        return 1;
    }

    size_t total_size_mb = std::atoi(argv[1]);
    size_t page_stride_kb = std::atoi(argv[2]);
    size_t iterations = std::atoi(argv[3]);
    bool use_hugepages = (argc > 4) ? (std::atoi(argv[4]) != 0) : false;

    size_t total_size = total_size_mb * 1024 * 1024;
    size_t page_stride = page_stride_kb * 1024;
    size_t num_pages = total_size / page_stride;

    std::cout << "TLB Miss Impact Kernel - Experiment 7" << std::endl;
    std::cout << "======================================" << std::endl;
    std::cout << "Total Size: " << total_size_mb << " MB" << std::endl;
    std::cout << "Page Stride: " << page_stride_kb << " KB" << std::endl;
    std::cout << "Number of Pages Touched: " << num_pages << std::endl;
    std::cout << "Iterations: " << iterations << std::endl;
    std::cout << "Using Huge Pages: " << (use_hugepages ? "Yes (2MB)" : "No (4KB)") << std::endl;
    std::cout << std::endl;

    // Allocate memory
    char* data = nullptr;
    
    if (use_hugepages) {
        // Try to allocate with huge pages
        #ifdef __linux__
        data = (char*)mmap(nullptr, total_size, 
                          PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB,
                          -1, 0);
        if (data == MAP_FAILED) {
            std::cerr << "Failed to allocate huge pages. Make sure huge pages are enabled:" << std::endl;
            std::cerr << "  echo " << (total_size / PAGE_SIZE_2M + 1) << " | sudo tee /proc/sys/vm/nr_hugepages" << std::endl;
            data = (char*)mmap(nullptr, total_size,
                              PROT_READ | PROT_WRITE,
                              MAP_PRIVATE | MAP_ANONYMOUS,
                              -1, 0);
            if (data == MAP_FAILED) {
                std::cerr << "Memory allocation failed!" << std::endl;
                return 1;
            }
            std::cout << "WARNING: Fell back to standard pages" << std::endl;
        } else {
            std::cout << "Successfully allocated huge pages" << std::endl;
        }
        #else
        std::cerr << "Huge pages not supported on this platform" << std::endl;
        return 1;
        #endif
    } else {
        // Standard allocation
        data = (char*)mmap(nullptr, total_size,
                          PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANONYMOUS,
                          -1, 0);
        if (data == MAP_FAILED) {
            std::cerr << "Memory allocation failed!" << std::endl;
            return 1;
        }
    }

    // Touch all pages to ensure allocation
    std::cout << "Initializing memory..." << std::endl;
    memset(data, 0, total_size);

    // Warm-up
    std::cout << "Warming up..." << std::endl;
    for (int i = 0; i < 3; ++i) {
        page_strided_access(data, total_size, page_stride, 10);
    }

    // Benchmark
    std::cout << "Running benchmark..." << std::endl;
    auto start = std::chrono::high_resolution_clock::now();
    
    page_strided_access(data, total_size, page_stride, iterations);
    
    auto end = std::chrono::high_resolution_clock::now();

    // Calculate timing
    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    double seconds = duration / 1e9;
    double total_accesses = static_cast<double>(num_pages) * iterations;
    double accesses_per_sec = total_accesses / seconds;
    double ns_per_access = duration / total_accesses;

    std::cout << std::endl;
    std::cout << "Results:" << std::endl;
    std::cout << "  Total Time: " << seconds << " seconds" << std::endl;
    std::cout << "  Time per Iteration: " << (seconds / iterations * 1e6) << " µs" << std::endl;
    std::cout << "  Total Page Accesses: " << total_accesses << std::endl;
    std::cout << "  Accesses per Second: " << (accesses_per_sec / 1e6) << " M/s" << std::endl;
    std::cout << "  Nanoseconds per Access: " << ns_per_access << " ns" << std::endl;

    // Clean up
    munmap(data, total_size);

    std::cout << std::endl;
    std::cout << "To measure TLB misses, run with:" << std::endl;
    std::cout << "  perf stat -e dTLB-load-misses,dTLB-loads,dTLB-store-misses,iTLB-load-misses \\" << std::endl;
    std::cout << "    ./tlb_miss_kernel " << total_size_mb << " " << page_stride_kb << " " << iterations << " " << (use_hugepages ? "1" : "0") << std::endl;
    std::cout << std::endl;
    std::cout << "Compare standard vs huge pages:" << std::endl;
    std::cout << "  Standard: ./tlb_miss_kernel " << total_size_mb << " 4 " << iterations << " 0" << std::endl;
    std::cout << "  Huge:     ./tlb_miss_kernel " << total_size_mb << " 4 " << iterations << " 1" << std::endl;

    return 0;
}
