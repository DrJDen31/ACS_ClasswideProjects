#include "memory_backend.hpp"

namespace b2 {

bool MemoryBackend::read_node(VectorID node_id, VectorData& out_data) {
    std::lock_guard<std::mutex> lock(mutex_);
    const size_t idx = static_cast<size_t>(node_id);
    if (idx >= data_.size() || idx >= present_.size() || !present_[idx]) {
        return false;
    }
    out_data = data_[idx];
    stats_.num_reads += 1;
    stats_.bytes_read += out_data.size() * sizeof(float);
    return true;
}

bool MemoryBackend::write_node(VectorID node_id, const VectorData& data) {
    std::lock_guard<std::mutex> lock(mutex_);
    const size_t idx = static_cast<size_t>(node_id);
    if (data_.size() <= idx) {
        data_.resize(idx + 1);
        present_.resize(idx + 1, false);
    }
    data_[idx] = data;
    present_[idx] = true;
    stats_.num_writes += 1;
    stats_.bytes_written += data.size() * sizeof(float);
    return true;
}

bool MemoryBackend::batch_read_nodes(const std::vector<VectorID>& node_ids,
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
