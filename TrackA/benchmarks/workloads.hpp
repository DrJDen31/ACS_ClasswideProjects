#ifndef WORKLOADS_HPP
#define WORKLOADS_HPP

#include "hash_table.hpp"
#include <vector>
#include <random>

namespace a4 {

/**
 * Workload types for benchmarking
 */
enum class WorkloadType {
    LOOKUP_ONLY,   // 100% find() operations
    INSERT_ONLY,   // 100% insert() operations
    MIXED_70_30    // 70% find(), 30% insert()
};

/**
 * Configuration for a benchmark run
 */
struct WorkloadConfig {
    WorkloadType type;
    size_t dataset_size;      // Number of keys to operate on
    size_t num_operations;    // Total operations to perform
    size_t num_threads;       // Number of worker threads
    uint64_t seed;            // Random seed for reproducibility

    WorkloadConfig(WorkloadType t, size_t ds, size_t nops, size_t nt, uint64_t s = 12345)
        : type(t), dataset_size(ds), num_operations(nops), num_threads(nt), seed(s) {}
};

/**
 * Pre-populate a hash table with random key-value pairs
 */
void populate_table(HashTable* table, size_t num_keys, uint64_t seed = 12345);

/**
 * Generate a vector of random keys for benchmarking
 */
std::vector<a4::Key> generate_keys(size_t num_keys, uint64_t seed = 12345);

/**
 * Execute a workload on a hash table and measure throughput.
 * 
 * @param table The hash table to benchmark
 * @param config Workload configuration
 * @return Throughput in operations per second
 */
double run_workload(HashTable* table, const WorkloadConfig& config);

/**
 * Get workload type name as string
 */
const char* workload_name(WorkloadType type);

} // namespace a4

#endif // WORKLOADS_HPP
