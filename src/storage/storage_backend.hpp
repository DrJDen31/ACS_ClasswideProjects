#pragma once

#include "../core/vector.hpp"
#include "io_stats.hpp"
#include <vector>
#include <memory>

namespace b2 {

// Abstract storage backend interface
// Allows swapping between pure DRAM, file-based, and tiered storage
class StorageBackend {
public:
    virtual ~StorageBackend() = default;
    
    // Read a single node's data
    virtual bool read_node(VectorID node_id, VectorData& out_data) = 0;
    
    // Write a single node's data
    virtual bool write_node(VectorID node_id, const VectorData& data) = 0;
    
    // Batch read for efficiency
    virtual bool batch_read_nodes(const std::vector<VectorID>& node_ids, std::vector<VectorData>& out_data) = 0;
    
    // Get I/O statistics
    virtual IOStats get_stats() const = 0;
    
    // Reset statistics
    virtual void reset_stats() = 0;
};

} // namespace b2
