#pragma once

#include <cstddef>

#include "../storage/io_stats.hpp"

namespace b2 {
namespace simulator {

// Basic SSD device configuration used by the simulator.
struct SsdDeviceConfig {
    std::size_t num_channels = 0;
    std::size_t queue_depth_per_channel = 0;
    double base_read_latency_us = 0.0;
    double internal_read_bandwidth_GBps = 0.0;
};

// Minimal SSD simulator stub. This will later be extended to
// track per-channel timelines and contention.
class SsdSimulator {
public:
    explicit SsdSimulator(const SsdDeviceConfig& config) : config_(config) {}

    const SsdDeviceConfig& config() const { return config_; }

    // Record a logical read of the given number of bytes. This updates
    // IOStats and accumulates a simple estimate of device service time
    // based on per-read latency and internal bandwidth, scaled by an
    // effective parallelism factor from channels and queue depth.
    void record_read(std::size_t bytes) {
        io_stats_.num_reads += 1;
        io_stats_.bytes_read += bytes;

        double bw_bytes_per_us = 0.0;
        if (config_.internal_read_bandwidth_GBps > 0.0) {
            bw_bytes_per_us = config_.internal_read_bandwidth_GBps * 1e9 / 1e6;
        }

        double t_us = config_.base_read_latency_us;
        if (bw_bytes_per_us > 0.0) {
            t_us += static_cast<double>(bytes) / bw_bytes_per_us;
        }

        std::size_t parallel = config_.num_channels * config_.queue_depth_per_channel;
        if (parallel == 0) {
            parallel = 1;
        }

        total_time_us_ += t_us / static_cast<double>(parallel);
    }

    const IOStats& stats() const { return io_stats_; }

    double total_time_us() const { return total_time_us_; }

    void reset_stats() {
        io_stats_ = IOStats{};
        total_time_us_ = 0.0;
    }

private:
    SsdDeviceConfig config_{};
    IOStats io_stats_{};
    double total_time_us_ = 0.0;
};

} // namespace simulator
} // namespace b2
