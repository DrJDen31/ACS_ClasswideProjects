/*
 * Cache Miss Impact Kernel - Experiment 6
 * 
 * This kernel implements a simple operation (multiply or SAXPY) while allowing
 * control over cache miss rate through working set size manipulation.
 * 
 * Compile: g++ -O3 -march=native -o cache_miss_kernel cache_miss_kernel.cpp
 * Run: ./cache_miss_kernel <working_set_size_kb> <iterations>
 */

#include <iostream>
#include <vector>
#include <chrono>
#include <cstring>
#include <cstdlib>
#include <random>

// Simple kernel: vector multiply-add (similar to SAXPY)
// y[i] = a * x[i] + y[i]
void saxpy_kernel(float a, const float* x, float* y, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        y[i] = a * x[i] + y[i];
    }
}

// Sequential access pattern
void sequential_access(float* data, size_t n, float multiplier) {
    for (size_t i = 0; i < n; ++i) {
        data[i] = data[i] * multiplier + 1.0f;
    }
}

// Strided access pattern to induce cache misses
void strided_access(float* data, size_t n, size_t stride, float multiplier) {
    for (size_t i = 0; i < n; i += stride) {
        data[i] = data[i] * multiplier + 1.0f;
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <working_set_size_kb> <iterations> [stride]" << std::endl;
        std::cerr << "Example: " << argv[0] << " 32 1000 1" << std::endl;
        std::cerr << "  working_set_size_kb: Size of data array in KB" << std::endl;
        std::cerr << "  iterations: Number of times to run the kernel" << std::endl;
        std::cerr << "  stride: Access stride (default: 1 for sequential)" << std::endl;
        return 1;
    }

    size_t working_set_kb = std::atoi(argv[1]);
    size_t iterations = std::atoi(argv[2]);
    size_t stride = (argc > 3) ? std::atoi(argv[3]) : 1;

    // Calculate array size
    size_t n = (working_set_kb * 1024) / sizeof(float);
    
    if (n == 0) {
        std::cerr << "Error: Working set size too small" << std::endl;
        return 1;
    }

    std::cout << "Cache Miss Impact Kernel - Experiment 6" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Working Set Size: " << working_set_kb << " KB" << std::endl;
    std::cout << "Array Elements: " << n << std::endl;
    std::cout << "Iterations: " << iterations << std::endl;
    std::cout << "Stride: " << stride << std::endl;
    std::cout << "Memory Footprint: " << (n * sizeof(float) / 1024.0) << " KB" << std::endl;
    std::cout << std::endl;

    // Allocate memory
    std::vector<float> data(n);
    
    // Initialize with random values
    std::mt19937 rng(42);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    for (size_t i = 0; i < n; ++i) {
        data[i] = dist(rng);
    }

    // Warm-up
    std::cout << "Warming up..." << std::endl;
    for (int i = 0; i < 3; ++i) {
        if (stride == 1) {
            sequential_access(data.data(), n, 1.1f);
        } else {
            strided_access(data.data(), n, stride, 1.1f);
        }
    }

    // Benchmark
    std::cout << "Running benchmark..." << std::endl;
    auto start = std::chrono::high_resolution_clock::now();
    
    for (size_t iter = 0; iter < iterations; ++iter) {
        if (stride == 1) {
            sequential_access(data.data(), n, 1.1f);
        } else {
            strided_access(data.data(), n, stride, 1.1f);
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    
    // Calculate timing
    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    double seconds = duration / 1e9;
    double ops = static_cast<double>(n) * iterations;
    double gflops = (ops * 2) / (seconds * 1e9); // 2 ops per element (multiply + add)
    
    std::cout << std::endl;
    std::cout << "Results:" << std::endl;
    std::cout << "  Total Time: " << seconds << " seconds" << std::endl;
    std::cout << "  Time per Iteration: " << (seconds / iterations * 1e6) << " µs" << std::endl;
    std::cout << "  Throughput: " << gflops << " GFLOP/s" << std::endl;
    std::cout << "  Bandwidth: " << ((n * sizeof(float) * iterations * 2) / (seconds * 1e9)) << " GB/s" << std::endl;
    
    // Prevent optimization
    volatile float sum = 0.0f;
    for (size_t i = 0; i < std::min(n, size_t(100)); ++i) {
        sum += data[i];
    }
    
    std::cout << std::endl;
    std::cout << "To measure cache misses, run with:" << std::endl;
    std::cout << "  perf stat -e cache-references,cache-misses,L1-dcache-load-misses,LLC-load-misses \\" << std::endl;
    std::cout << "    ./cache_miss_kernel " << working_set_kb << " " << iterations << " " << stride << std::endl;

    return 0;
}
