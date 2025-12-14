#ifndef COARSE_HASH_TABLE_HPP
#define COARSE_HASH_TABLE_HPP

#include "hash_table.hpp"
#include <vector>
#include <mutex>
#include <atomic>

namespace a4 {

/**
 * Coarse-grained locking hash table implementation.
 * 
 * Uses a single global mutex to protect all operations.
 * Simple and correct, but poor scalability under contention.
 * 
 * Synchronization strategy:
 * - All operations acquire the global lock
 * - No deadlocks possible (single lock)
 * - Sequential consistency guaranteed
 */
class CoarseHashTable : public HashTable {
public:
    explicit CoarseHashTable(size_t num_buckets = DEFAULT_NUM_BUCKETS);
    ~CoarseHashTable() override;

    // HashTable interface implementation
    bool insert(Key key, Value value) override;
    bool find(Key key, Value& value_out) const override;
    bool erase(Key key) override;
    size_t size() const override;
    const char* name() const override { return "coarse"; }

private:
    // Disable copy and move
    CoarseHashTable(const CoarseHashTable&) = delete;
    CoarseHashTable& operator=(const CoarseHashTable&) = delete;

    // Helper function to find a node in a bucket (assumes lock is held)
    Node* find_in_bucket(size_t bucket_idx, Key key) const;

    size_t num_buckets_;
    std::vector<Node*> buckets_;  // Array of bucket heads
    mutable std::mutex global_mutex_;  // Single lock for everything
    std::atomic<size_t> size_;  // Number of elements (atomic for lock-free reads)
};

} // namespace a4

#endif // COARSE_HASH_TABLE_HPP
