#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "../core/vector.hpp"
#include "../storage/io_stats.hpp"

namespace b2 {

class Dataset; // forward declaration; defined in core/dataset.hpp later

namespace simulator {
namespace ann_in_ssd {

// Configuration parameters for ANN-in-SSD simulations.
struct AnnInSsdConfig {
    // Dataset
    std::string dataset_name;
    std::string dataset_path;
    std::size_t dimension = 0;
    std::size_t num_vectors = 0;

    // Graph layout
    std::string placement_mode;   // "hash_home" or "locality_aware"
    std::size_t vectors_per_block = 0; // K
    std::size_t portal_degree = 0;     // P
    std::size_t neighbor_degree = 0;   // M
    std::size_t page_size_bytes = 0;
    std::string code_type;       // e.g., "pq8x8"

    // Device / hardware
    std::string hardware_level;  // "L0", "L1", "L2", "L3"
    std::size_t num_channels = 0;
    std::size_t queue_depth_per_channel = 0;
    double base_read_latency_us = 0.0;
    double internal_read_bandwidth_GBps = 0.0;
    double controller_flops_GF = 0.0;
    double per_block_unit_flops_GF = 0.0;

    // Search / workload
    std::size_t k = 10;
    std::size_t beam_width = 0;
    std::size_t max_steps = 0;
    std::string entry_block_strategy; // e.g., "centroid_knn"
    std::string termination;          // placeholder name
    std::size_t num_queries = 0;
    std::size_t concurrency = 0;
    std::string workload_distribution; // "uniform", "zipfian", "bursty"
    std::uint64_t seed = 0;

    // Logging
    std::string output_path;    // JSON log path
    bool record_per_query = false;
    bool record_per_block = false;
    std::string simulation_mode;
};

// One query to the simulator.
struct Query {
    VectorID id = 0;
    VectorData values;                     // query vector
    std::vector<VectorID> true_neighbors;  // optional ground truth ids
};

// Result and statistics for a single query.
struct QueryResult {
    VectorID query_id = 0;
    std::vector<VectorID> found_neighbors;
    std::vector<float> found_scores;

    std::size_t blocks_visited = 0;
    std::size_t portal_steps = 0;
    std::size_t internal_reads = 0;
    std::size_t distances_computed = 0;

    double estimated_latency_us = 0.0;
};

// Aggregate statistics across a batch of queries.
struct SimulationSummary {
    AnnInSsdConfig config;  // copy of config used for this run

    std::size_t k = 0;
    std::size_t num_queries = 0;

    double recall_at_k = 0.0;
    double qps = 0.0;

    double latency_us_p50 = 0.0;
    double latency_us_p95 = 0.0;
    double latency_us_p99 = 0.0;

    double avg_blocks_visited = 0.0;
    double avg_portal_steps = 0.0;
    double avg_internal_reads = 0.0;
    double avg_distances_computed = 0.0;

    std::uint64_t metadata_bytes = 0;

    IOStats io_stats;  // aggregate I/O stats for the simulated device
    double device_time_us = 0.0; // modeled SSD service time across the run
};

// Main ANN-in-SSD model entry point used by benchmarks.
class AnnInSsdModel {
public:
    AnnInSsdModel(const AnnInSsdConfig& config, const Dataset& dataset);

    // Single query (primarily for debugging and tests).
    QueryResult search_one(const Query& query);

    // Batch search with modeled concurrency.
    std::vector<QueryResult> search_batch(const std::vector<Query>& queries);

    // Access summary after running one or more batches.
    const SimulationSummary& summary() const { return summary_; }

    // Write JSON log summarizing the run. Implementation will follow design-doc schema.
    bool write_json_log(const std::string& path) const;

private:
    AnnInSsdConfig config_{};
    const Dataset* dataset_ = nullptr;  // not owned

    SimulationSummary summary_{};

    // Precomputed block-level metadata for graph navigation
    std::vector<VectorData> block_centroids_;
    std::vector<std::vector<std::size_t>> block_neighbors_;
    std::size_t graph_dim_ = 0;
    std::size_t graph_vectors_per_block_ = 0;

    // Maps logic block ID -> list of vector IDs
    std::vector<std::vector<VectorID>> block_assignment_;

    void build_block_graph_if_needed();
};

} // namespace ann_in_ssd
} // namespace simulator
} // namespace b2
