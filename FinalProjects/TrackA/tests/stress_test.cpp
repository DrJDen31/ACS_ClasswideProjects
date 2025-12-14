/**
 * Stress test for concurrent hash table implementations
 * 
 * Spawns multiple threads performing random operations to test
 * thread-safety, detect data races, and verify no deadlocks occur.
 */

#include "hash_table.hpp"
#include "coarse_hash_table.hpp"
#include "fine_hash_table.hpp"
#include <iostream>
#include <thread>
#include <vector>
#include <random>
#include <atomic>
#include <chrono>

using namespace a4;

// Global counters for verification
std::atomic<size_t> total_inserts{0};
std::atomic<size_t> total_finds{0};
std::atomic<size_t> total_erases{0};

/**
 * Worker function: performs random operations on the hash table
 */
void worker(HashTable* table, size_t thread_id, size_t num_ops, uint64_t seed) {
    std::mt19937_64 rng(seed + thread_id);
    std::uniform_int_distribution<Key> key_dist(0, 100000);
    std::uniform_int_distribution<int> op_dist(0, 99);  // 0-99 for operation choice
    
    size_t local_inserts = 0;
    size_t local_finds = 0;
    size_t local_erases = 0;
    
    for (size_t i = 0; i < num_ops; i++) {
        Key key = key_dist(rng);
        Value value = key * 2;
        int op = op_dist(rng);
        
        if (op < 50) {
            // 50% find operations
            Value result;
            table->find(key, result);
            local_finds++;
        } else if (op < 85) {
            // 35% insert operations
            table->insert(key, value);
            local_inserts++;
        } else {
            // 15% erase operations
            table->erase(key);
            local_erases++;
        }
    }
    
    total_inserts += local_inserts;
    total_finds += local_finds;
    total_erases += local_erases;
}

/**
 * Run stress test for a given implementation
 */
void stress_test(const char* impl_name, size_t num_threads) {
    std::cout << "\n=== Stress Testing " << impl_name 
              << " with " << num_threads << " threads ===" << std::endl;
    
    // Create hash table
    HashTable* table = nullptr;
    if (std::string(impl_name) == "coarse") {
        table = new CoarseHashTable();
    } else if (std::string(impl_name) == "fine") {
        table = new FineHashTable();
    } else {
        std::cerr << "Unknown implementation: " << impl_name << std::endl;
        return;
    }
    
    // Reset counters
    total_inserts = 0;
    total_finds = 0;
    total_erases = 0;
    
    // Configuration
    const size_t ops_per_thread = 10000;
    const uint64_t seed = 42;
    
    // Launch threads
    std::cout << "Launching " << num_threads << " threads, "
              << ops_per_thread << " ops each..." << std::endl;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<std::thread> threads;
    for (size_t i = 0; i < num_threads; i++) {
        threads.emplace_back(worker, table, i, ops_per_thread, seed);
    }
    
    // Wait for completion
    for (auto& t : threads) {
        t.join();
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // Report results
    std::cout << "Completed in " << duration.count() << " ms" << std::endl;
    std::cout << "Operations:" << std::endl;
    std::cout << "  Inserts: " << total_inserts << std::endl;
    std::cout << "  Finds:   " << total_finds << std::endl;
    std::cout << "  Erases:  " << total_erases << std::endl;
    std::cout << "  Total:   " << (total_inserts + total_finds + total_erases) << std::endl;
    std::cout << "Final table size: " << table->size() << std::endl;
    std::cout << "Throughput: " 
              << (total_inserts + total_finds + total_erases) * 1000.0 / duration.count()
              << " ops/sec" << std::endl;
    
    delete table;
    
    std::cout << "✓ No crashes or deadlocks detected!" << std::endl;
}

int main(int argc, char* argv[]) {
    size_t num_threads = 8;
    
    if (argc > 1) {
        num_threads = std::stoul(argv[1]);
    }
    
    std::cout << "==================================" << std::endl;
    std::cout << "Hash Table Stress Test" << std::endl;
    std::cout << "==================================" << std::endl;
    std::cout << "Hardware concurrency: " << std::thread::hardware_concurrency() << std::endl;
    std::cout << "Testing with: " << num_threads << " threads" << std::endl;
    
    // Test each implementation
    stress_test("coarse", num_threads);
    stress_test("fine", num_threads);
    // TODO: Add rwlock when implemented
    
    std::cout << "\n==================================" << std::endl;
    std::cout << "All stress tests completed!" << std::endl;
    std::cout << "If you see this message, no deadlocks occurred." << std::endl;
    std::cout << "Run with ThreadSanitizer to detect data races:" << std::endl;
    std::cout << "  make tsan" << std::endl;
    std::cout << "==================================" << std::endl;
    
    return 0;
}
