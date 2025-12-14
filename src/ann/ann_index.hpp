#pragma once

#include "../core/vector.hpp"
#include <vector>
#include <string>

namespace b2 {

// Abstract interface for ANN index implementations
class ANNIndex {
public:
    virtual ~ANNIndex() = default;
    
    // Build the index from a dataset
    virtual void build(const std::vector<VectorData>& data) = 0;
    
    // Search for k nearest neighbors
    virtual std::vector<VectorID> search(
        const float* query,
        size_t k,
        size_t ef_search = 100
    ) = 0;
    
    // Save/load index
    virtual bool save(const std::string& filepath) const = 0;
    virtual bool load(const std::string& filepath) = 0;
    
    // Get statistics
    virtual size_t get_num_vectors() const = 0;
    virtual size_t get_dimension() const = 0;
};

} // namespace b2
