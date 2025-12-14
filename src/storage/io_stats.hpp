#pragma once

#include <cstdint>

namespace b2 {

// I/O statistics tracking
struct IOStats {
    uint64_t num_reads = 0;
    uint64_t num_writes = 0;
    uint64_t bytes_read = 0;
    uint64_t bytes_written = 0;
    double total_read_latency_us = 0.0;   // Microseconds
    double total_write_latency_us = 0.0;  // Microseconds
    
    // Derived metrics
    double avg_read_latency_us() const {
        return num_reads > 0 ? total_read_latency_us / num_reads : 0.0;
    }
    
    double avg_write_latency_us() const {
        return num_writes > 0 ? total_write_latency_us / num_writes : 0.0;
    }
    
    // I/O amplification: total bytes read / (num queries * vector size)
    // This needs to be computed externally with query count and vector size
};

} // namespace b2
