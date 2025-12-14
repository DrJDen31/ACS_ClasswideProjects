#pragma once

#include "storage_backend.hpp"
#include <vector>
#include <mutex>

namespace b2 {

// In-memory storage backend using a contiguous vector of VectorData.
// Assumes VectorID values are small integers; resizes storage as needed.
class MemoryBackend : public StorageBackend {
public:
    MemoryBackend() = default;

    bool read_node(VectorID node_id, VectorData& out_data) override;
    bool write_node(VectorID node_id, const VectorData& data) override;
    bool batch_read_nodes(const std::vector<VectorID>& node_ids,
                          std::vector<VectorData>& out_data) override;

    IOStats get_stats() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return stats_;
    }
    void reset_stats() override {
        std::lock_guard<std::mutex> lock(mutex_);
        stats_ = IOStats{};
    }

    size_t size() const { return data_.size(); }

private:
    std::vector<VectorData> data_;
    std::vector<bool> present_;
    IOStats stats_;
    mutable std::mutex mutex_;
};

} // namespace b2
