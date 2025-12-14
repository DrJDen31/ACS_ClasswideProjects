#pragma once

#include "vector.hpp"
#include <string>
#include <vector>
#include <memory>

namespace b2 {

// Dataset loader and generator
class Dataset {
public:
    Dataset() = default;
    
    // Load dataset from file (fvecs/bvecs format)
    bool load_from_file(const std::string& filepath);
    
    // Generate synthetic dataset
    void generate_synthetic(size_t num_vectors, size_t dim, const std::string& distribution = "gaussian");
    
    // Accessors
    size_t size() const { return vectors_.size(); }
    size_t dimension() const { return dim_; }
    const float* get_vector(size_t idx) const { return vectors_[idx].data(); }
    const VectorData& get_vector_data(size_t idx) const { return vectors_[idx]; }
    
    // Ground truth computation (brute-force k-NN for recall evaluation)
    std::vector<std::vector<VectorID>> compute_ground_truth(
        const std::vector<VectorData>& queries,
        size_t k,
        DistanceMetric metric = DistanceMetric::L2
    ) const;

private:
    std::vector<VectorData> vectors_;
    size_t dim_ = 0;
};

} // namespace b2
