#pragma once

#include <chrono>

namespace b2 {

// High-resolution timer for benchmarking
class Timer {
public:
    Timer() : start_(std::chrono::high_resolution_clock::now()) {}
    
    void reset() {
        start_ = std::chrono::high_resolution_clock::now();
    }
    
    // Get elapsed time in microseconds
    double elapsed_us() const {
        auto end = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double, std::micro>(end - start_).count();
    }
    
    // Get elapsed time in milliseconds
    double elapsed_ms() const {
        return elapsed_us() / 1000.0;
    }
    
    // Get elapsed time in seconds
    double elapsed_s() const {
        return elapsed_us() / 1000000.0;
    }

private:
    std::chrono::high_resolution_clock::time_point start_;
};

} // namespace b2
