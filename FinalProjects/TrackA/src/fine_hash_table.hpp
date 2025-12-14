#ifndef FINE_HASH_TABLE_HPP
#define FINE_HASH_TABLE_HPP

#include "hash_table.hpp"
#include <vector>
#include <mutex>
#include <atomic>

namespace a4 {

/**
 * Fine-grained locking hash table implementation (lock striping).
 * 
 * Uses one mutex per bucket to allow parallel operations on different buckets.
 * Better scalability than coarse-grained, but still has contention on hot buckets.
 * 
 * Synchronization strategy:
 * - Each bucket has its own mutex
 * - Operations lock only the specific bucket they access
 * - No deadlocks (each operation touches at most one bucket)
 * - Linearizable per-bucket operations
 */
class FineHashTable : public HashTable {
public:
    explicit FineHashTable(size_t num_buckets = DEFAULT_NUM_BUCKETS);
    ~FineHashTable() override;

    // HashTable interface implementation
    bool insert(Key key, Value value) override;
    bool find(Key key, Value& value_out) const override;
    bool erase(Key key) override;
    size_t size() const override;
    const char* name() const override { return "fine"; }

private:
    // Disable copy and move
    FineHashTable(const FineHashTable&) = delete;
    FineHashTable& operator=(const FineHashTable&) = delete;

    // Helper function to find a node in a bucket (assumes lock is held)
    Node* find_in_bucket(size_t bucket_idx, Key key) const;

    size_t num_buckets_;
    std::vector<Node*> buckets_;  // Array of bucket heads
    mutable std::vector<std::mutex> bucket_mutexes_;  // One mutex per bucket
    std::atomic<size_t> size_;  // Number of elements
};

} // namespace a4

#endif // FINE_HASH_TABLE_HPP
