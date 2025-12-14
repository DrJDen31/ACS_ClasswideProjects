#pragma once

#include "storage_backend.hpp"
#include <string>
#include <vector>

namespace b2 {

// Simple file-backed storage backend that stores fixed-dimension vectors
// in a flat binary file. Each node occupies dim * sizeof(float) bytes.
class FileBackend : public StorageBackend {
public:
    FileBackend(const std::string& path, size_t dim);

    bool read_node(VectorID node_id, VectorData& out_data) override;
    bool write_node(VectorID node_id, const VectorData& data) override;
    bool batch_read_nodes(const std::vector<VectorID>& node_ids,
                          std::vector<VectorData>& out_data) override;

    IOStats get_stats() const override { return stats_; }
    void reset_stats() override { stats_ = IOStats{}; }

    size_t dimension() const { return dim_; }
    const std::string& path() const { return path_; }

private:
    std::string path_;
    size_t dim_;
    IOStats stats_;
};

} // namespace b2
