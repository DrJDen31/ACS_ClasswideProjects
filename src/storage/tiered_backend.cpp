#include "tiered_backend.hpp"

#include "../utils/timer.hpp"

namespace b2 {

TieredBackend::TieredBackend(std::shared_ptr<StorageBackend> backing,
                             std::size_t cache_capacity_vectors,
                             const std::string& cache_policy)
    : backing_(std::move(backing)),
      cache_capacity_(cache_capacity_vectors),
      cache_(),
      policy_(),
      stats_() {
    if (cache_capacity_ > 0) {
        if (cache_policy == "lfu") {
            policy_ = std::make_unique<LFUCachePolicy>(cache_capacity_);
        } else {
            // Default to LRU.
            policy_ = std::make_unique<LRUCachePolicy>(cache_capacity_);
        }
    }
}

void TieredBackend::reset_stats() {
    std::lock_guard<std::mutex> lock(mutex_);
    stats_ = IOStats{};
    cache_hits_ = 0;
    cache_misses_ = 0;
    if (backing_) {
        backing_->reset_stats();
    }
    if (ssd_sim_) {
        ssd_sim_->reset_stats();
    }
}

void TieredBackend::enable_device_model(const simulator::SsdDeviceConfig& config) {
    std::lock_guard<std::mutex> lock(mutex_);
    ssd_sim_ = std::make_unique<simulator::SsdSimulator>(config);
}

double TieredBackend::device_time_us() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!ssd_sim_) {
        return 0.0;
    }
    return ssd_sim_->total_time_us();
}

void TieredBackend::record_logical_read_bytes(std::size_t bytes) {
    std::lock_guard<std::mutex> lock(mutex_);
    stats_.num_reads += 1;
    stats_.bytes_read += bytes;

    if (ssd_sim_) {
        ssd_sim_->record_read(bytes);
    }
}

void TieredBackend::record_logical_write_bytes(std::size_t bytes) {
    std::lock_guard<std::mutex> lock(mutex_);
    stats_.num_writes += 1;
    stats_.bytes_written += bytes;
}

void TieredBackend::insert_into_cache(VectorID id, const VectorData& data) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (cache_capacity_ == 0 || !policy_) {
        return; // caching disabled
    }

    auto it = cache_.find(id);
    if (it != cache_.end()) {
        it->second = data;
        if (policy_) {
            policy_->record_access(id);
        }
        return;
    }

    VectorID evicted_id = 0;
    bool evicted = policy_->on_insert(id, evicted_id);
    if (evicted) {
        cache_.erase(evicted_id);
    }
    cache_.emplace(id, data);
}

bool TieredBackend::read_node(VectorID node_id, VectorData& out_data) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = cache_.find(node_id);
        if (it != cache_.end()) {
            out_data = it->second;
            if (policy_) {
                policy_->record_access(node_id);
            }
            ++cache_hits_;
            return true;
        }
    }

    if (!backing_) {
        return false;
    }

    Timer t;
    if (!backing_->read_node(node_id, out_data)) {
        return false;
    }
    double us = t.elapsed_us();
    std::size_t bytes = out_data.size() * sizeof(float);

    {
        std::lock_guard<std::mutex> lock(mutex_);
        stats_.num_reads += 1;
        stats_.bytes_read += bytes;
        stats_.total_read_latency_us += us;

        if (ssd_sim_) {
            ssd_sim_->record_read(bytes);
        }

        ++cache_misses_;
    }

    insert_into_cache(node_id, out_data);
    return true;
}

bool TieredBackend::write_node(VectorID node_id, const VectorData& data) {
    if (!backing_) {
        return false;
    }

    Timer t;
    if (!backing_->write_node(node_id, data)) {
        return false;
    }
    double us = t.elapsed_us();
    std::size_t bytes = data.size() * sizeof(float);

    {
        std::lock_guard<std::mutex> lock(mutex_);
        stats_.num_writes += 1;
        stats_.bytes_written += bytes;
        stats_.total_write_latency_us += us;
    }

    insert_into_cache(node_id, data);
    return true;
}

bool TieredBackend::batch_read_nodes(const std::vector<VectorID>& node_ids,
                                     std::vector<VectorData>& out_data) {
    out_data.clear();
    out_data.reserve(node_ids.size());
    bool all_ok = true;
    for (VectorID id : node_ids) {
        VectorData data;
        if (!read_node(id, data)) {
            all_ok = false;
        }
        out_data.push_back(std::move(data));
    }
    return all_ok;
}

} // namespace b2
