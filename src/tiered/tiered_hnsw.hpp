#pragma once

#include "../ann/ann_index.hpp"
#include "../core/vector.hpp"
#include "../storage/storage_backend.hpp"

#include <memory>
#include <unordered_map>
#include <utility>
#include <vector>
#include <mutex>
#include <cstdint>

namespace b2 {

// Tier-aware HNSW variant that stores vector data via a StorageBackend
// (e.g., a TieredBackend) while keeping the graph structure in DRAM.
class TieredHNSW : public ANNIndex {
public:
    TieredHNSW(std::size_t dim,
               std::shared_ptr<StorageBackend> storage,
               std::size_t M = 16,
               std::size_t ef_construction = 200,
               DistanceMetric metric = DistanceMetric::L2);

    void build(const std::vector<VectorData>& data) override;
    void build_parallel(const std::vector<VectorData>& data,
                        std::size_t num_threads);

    std::vector<VectorID> search(const float* query,
                                 std::size_t k,
                                 std::size_t ef_search = 100) override;

    bool save(const std::string& filepath) const override;
    bool load(const std::string& filepath) override;

    std::size_t get_num_vectors() const override { return num_vectors_; }
    std::size_t get_dimension() const override { return dim_; }

    std::shared_ptr<StorageBackend> storage() const { return storage_; }

private:
    struct Node {
        VectorID id;
        std::vector<std::vector<VectorID>> neighbors; // neighbors[layer]
    };

    std::size_t dim_;
    std::size_t M_;
    std::size_t ef_construction_;
    DistanceMetric metric_;

    std::shared_ptr<StorageBackend> storage_;

    std::vector<VectorData> vectors_;
    std::vector<Node> nodes_;
    VectorID entry_point_;
    std::size_t max_layer_;
    std::size_t num_vectors_;

    std::size_t assign_layer();
    void insert_node(VectorID id, const VectorData& vec);
    void insert_node_parallel(
        VectorID id,
        const VectorData& vec,
        std::vector<std::uint32_t>& visited,
        std::uint32_t& visited_epoch);
    std::vector<VectorID> select_neighbors_heuristic(
        const std::vector<std::pair<VectorID, float>>& candidates,
        std::size_t M,
        const VectorData& query);
    std::vector<std::pair<VectorID, float>> search_layer(
        const float* query,
        VectorID entry_point,
        std::size_t ef,
        std::size_t layer);

    std::vector<std::pair<VectorID, float>> search_layer_parallel(
        const float* query,
        VectorID entry_point,
        std::size_t ef,
        std::size_t layer,
        std::vector<std::uint32_t>& visited,
        std::uint32_t& visited_epoch);

    void reset_for_build(const std::vector<VectorData>& data);

    bool load_vector(VectorID id, VectorData& out) const;

    std::unique_ptr<std::mutex[]> node_mutexes_;
    std::mutex global_mutex_;
};

} // namespace b2
