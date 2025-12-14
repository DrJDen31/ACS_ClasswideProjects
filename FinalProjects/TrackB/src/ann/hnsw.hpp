#pragma once

#include "ann_index.hpp"
#include "../core/vector.hpp"
#include <vector>
#include <unordered_map>
#include <cstdint>
#include <mutex>
#include <thread>
#include <atomic>
#include <memory>

namespace b2 {

// HNSW (Hierarchical Navigable Small World) implementation
// Baseline DRAM-resident ANN index
class HNSW : public ANNIndex {
public:
    HNSW(size_t dim, size_t M = 16, size_t ef_construction = 200, DistanceMetric metric = DistanceMetric::L2);
    
    void build(const std::vector<VectorData>& data) override;
    void build_parallel(const std::vector<VectorData>& data, size_t num_threads);
    
    std::vector<VectorID> search(const float* query, size_t k, size_t ef_search = 100) override;
    
    bool save(const std::string& filepath) const override;
    bool load(const std::string& filepath) override;
    
    size_t get_num_vectors() const override { return vectors_.size(); }
    size_t get_dimension() const override { return dim_; }

    // Optional search instrumentation: distance computation counter
    void reset_search_stats();
    void enable_search_stats(bool enable);
    std::uint64_t search_distance_computations() const;

    void export_graph(std::vector<std::vector<std::vector<VectorID>>>& out_neighbors,
                      VectorID& out_entry_point,
                      size_t& out_max_layer) const;

private:
    // Graph structure: each node has neighbors at each layer
    struct Node {
        VectorID id;
        std::vector<std::vector<VectorID>> neighbors; // neighbors[layer] = list of neighbor IDs
    };
    
    size_t dim_;
    size_t M_;                // Max connections per layer
    size_t ef_construction_;  // Size of dynamic candidate list during construction
    DistanceMetric metric_;
    
    std::vector<VectorData> vectors_;           // The actual vector data
    std::vector<Node> nodes_;                   // Graph nodes
    VectorID entry_point_;                      // Top-layer entry point
    size_t max_layer_;                          // Maximum layer in the graph

    // Scratch buffer for search_layer to track visited nodes without allocating
    mutable std::vector<std::uint32_t> visited_;
    mutable std::uint32_t visited_epoch_ = 0;

    std::unique_ptr<std::mutex[]> node_mutexes_;
    std::mutex global_mutex_;

    // Search instrumentation state (not thread-safe for concurrent search)
    mutable std::atomic<std::uint64_t> search_distance_computations_{0};
    mutable bool measure_search_stats_ = false;

    void reset_for_build(const std::vector<VectorData>& data);
    void insert_node_parallel(
        VectorID id,
        const VectorData& vec,
        std::vector<std::uint32_t>& visited,
        std::uint32_t& visited_epoch);
    std::vector<std::pair<VectorID, float>> search_layer_parallel(
        const float* query,
        VectorID entry_point,
        size_t ef,
        size_t layer,
        std::vector<std::uint32_t>& visited,
        std::uint32_t& visited_epoch);
    
    // Helper methods
    size_t assign_layer();  // Randomly assign layer to new node
    void insert_node(VectorID id, const VectorData& vec);
    std::vector<std::pair<VectorID, float>> search_layer(
        const float* query,
        VectorID entry_point,
        size_t ef,
        size_t layer
    );
    std::vector<VectorID> select_neighbors_heuristic(
        const std::vector<std::pair<VectorID, float>>& candidates,
        size_t M,
        const VectorData& query
    );

    float distance_with_stats(const float* a, const float* b) const;
};

} // namespace b2
