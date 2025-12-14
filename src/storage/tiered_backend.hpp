#pragma once

#include "storage_backend.hpp"
#include "io_stats.hpp"
#include "../tiered/cache_policy.hpp"
#include "../core/vector.hpp"

#include "../simulator/ssd_simulator.hpp"

#include <memory>
#include <unordered_map>
#include <mutex>
#include <string>

namespace b2 {

// Tiered backend: DRAM cache in front of a backing StorageBackend
// (e.g., file-based). Tracks cache hits/misses and I/O statistics.
class TieredBackend : public StorageBackend {
public:
    TieredBackend(std::shared_ptr<StorageBackend> backing,
                  std::size_t cache_capacity_vectors,
                  const std::string& cache_policy = "lru");

    bool read_node(VectorID node_id, VectorData& out_data) override;
    bool write_node(VectorID node_id, const VectorData& data) override;
    bool batch_read_nodes(const std::vector<VectorID>& node_ids,
                          std::vector<VectorData>& out_data) override;

    IOStats get_stats() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return stats_;
    }
    void reset_stats() override;

    // Enable an SSD device timing model. When enabled, backing-store
    // reads are also recorded into the simulator, and the aggregated
    // modeled device service time can be queried via device_time_us().
    void enable_device_model(const simulator::SsdDeviceConfig& config);

    // Return the accumulated modeled SSD service time in microseconds
    // for all backing reads since the last reset_stats() call. Returns
    // 0.0 if no device model is enabled.
    double device_time_us() const;

    // Record a logical read or write of the given number of bytes without
    // touching the backing store. These are intended for analytic/cheated
    // modes where the index operates out of DRAM but we still want to
    // approximate IOStats and device_time_us.
    void record_logical_read_bytes(std::size_t bytes);
    void record_logical_write_bytes(std::size_t bytes);

    std::size_t cache_size() const { return cache_.size(); }
    std::size_t cache_capacity() const { return cache_capacity_; }
    std::uint64_t cache_hits() const { return cache_hits_; }
    std::uint64_t cache_misses() const { return cache_misses_; }

private:
    std::shared_ptr<StorageBackend> backing_;
    std::size_t cache_capacity_;
    std::unordered_map<VectorID, VectorData> cache_;
    std::unique_ptr<CachePolicy> policy_;
    IOStats stats_;
    std::uint64_t cache_hits_ = 0;
    std::uint64_t cache_misses_ = 0;

    // Optional SSD timing model. When present, each cache-miss read
    // against the backing store records a logical flash read into this
    // simulator.
    std::unique_ptr<simulator::SsdSimulator> ssd_sim_;

    mutable std::mutex mutex_;

    void insert_into_cache(VectorID id, const VectorData& data);
};

} // namespace b2
