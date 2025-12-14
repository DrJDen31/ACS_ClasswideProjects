#include "workloads.hpp"
#include <thread>
#include <vector>
#include <chrono>
#include <algorithm>

namespace a4 {

void populate_table(HashTable* table, size_t num_keys, uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<Key> dist(0, UINT64_MAX);
    
    for (size_t i = 0; i < num_keys; ++i) {
        Key key = dist(rng);
        Value value = key * 2;  // Arbitrary value
        table->insert(key, value);
    }
}

std::vector<Key> generate_keys(size_t num_keys, uint64_t seed) {
    std::vector<Key> keys;
    keys.reserve(num_keys);
    
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<Key> dist(0, UINT64_MAX);
    
    for (size_t i = 0; i < num_keys; ++i) {
        keys.push_back(dist(rng));
    }
    
    return keys;
}

const char* workload_name(WorkloadType type) {
    switch (type) {
        case WorkloadType::LOOKUP_ONLY: return "lookup";
        case WorkloadType::INSERT_ONLY: return "insert";
        case WorkloadType::MIXED_70_30: return "mixed";
        default: return "unknown";
    }
}

// Worker function for threads
static void worker_thread(
    HashTable* table,
    const std::vector<Key>& keys,
    WorkloadType type,
    size_t start_idx,
    size_t end_idx,
    uint64_t seed
) {
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> op_dist(0, 99);  // 0-99 for operation choice
    
    for (size_t i = start_idx; i < end_idx; ++i) {
        Key key = keys[i % keys.size()];
        Value value = key * 2;
        
        switch (type) {
            case WorkloadType::LOOKUP_ONLY: {
                Value result;
                table->find(key, result);
                break;
            }
            
            case WorkloadType::INSERT_ONLY: {
                table->insert(key, value);
                break;
            }
            
            case WorkloadType::MIXED_70_30: {
                int op = op_dist(rng);
                if (op < 70) {
                    // 70% find
                    Value result;
                    table->find(key, result);
                } else {
                    // 30% insert
                    table->insert(key, value);
                }
                break;
            }
        }
    }
}

double run_workload(HashTable* table, const WorkloadConfig& config) {
    // Generate keys
    std::vector<Key> keys = generate_keys(config.dataset_size, config.seed);
    
    // Pre-populate table for lookup and mixed workloads
    if (config.type == WorkloadType::LOOKUP_ONLY) {
        populate_table(table, config.dataset_size, config.seed);
    } else if (config.type == WorkloadType::MIXED_70_30) {
        populate_table(table, config.dataset_size / 2, config.seed);
    }
    
    // Calculate operations per thread
    size_t ops_per_thread = config.num_operations / config.num_threads;
    
    // Launch worker threads
    std::vector<std::thread> threads;
    auto start_time = std::chrono::high_resolution_clock::now();
    
    for (size_t i = 0; i < config.num_threads; ++i) {
        size_t start_idx = i * ops_per_thread;
        size_t end_idx = (i == config.num_threads - 1) 
            ? config.num_operations  // Last thread handles remainder
            : (i + 1) * ops_per_thread;
        
        threads.emplace_back(
            worker_thread,
            table,
            std::cref(keys),
            config.type,
            start_idx,
            end_idx,
            config.seed + i  // Unique seed per thread
        );
    }
    
    // Wait for all threads to complete
    for (auto& t : threads) {
        t.join();
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    
    // Calculate throughput
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end_time - start_time
    ).count();
    
    double throughput = (config.num_operations * 1e6) / duration;  // ops/sec
    
    return throughput;
}

} // namespace a4
