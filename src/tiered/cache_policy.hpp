#pragma once

#include "../core/vector.hpp"

#include <cstddef>
#include <list>
#include <map>
#include <unordered_map>

namespace b2 {

// Abstract cache policy interface used by tiered storage.
// Policies decide which keys to evict when the cache is full.
class CachePolicy {
public:
    virtual ~CachePolicy() = default;

    // Record access to an existing key (e.g., on cache hit).
    virtual void record_access(VectorID id) = 0;

    // Insert a key into the policy state. If an eviction occurs,
    // returns true and sets evicted_id to the victim.
    virtual bool on_insert(VectorID id, VectorID& evicted_id) = 0;

    // Remove a key from the policy (e.g., when explicitly erased).
    virtual void erase(VectorID id) = 0;

    // Clear all state.
    virtual void clear() = 0;

    virtual std::size_t size() const = 0;
    virtual std::size_t capacity() const = 0;
};

// Simple LRU (Least Recently Used) cache policy.
class LRUCachePolicy : public CachePolicy {
public:
    explicit LRUCachePolicy(std::size_t capacity);

    void record_access(VectorID id) override;
    bool on_insert(VectorID id, VectorID& evicted_id) override;
    void erase(VectorID id) override;
    void clear() override;

    std::size_t size() const override { return map_.size(); }
    std::size_t capacity() const override { return capacity_; }

private:
    std::size_t capacity_;
    std::list<VectorID> lru_list_;
    std::unordered_map<VectorID, std::list<VectorID>::iterator> map_;
};

// Simple LFU (Least Frequently Used) cache policy.
// Evicts the key with the smallest access count on insert when full.
class LFUCachePolicy : public CachePolicy {
public:
    explicit LFUCachePolicy(std::size_t capacity);

    void record_access(VectorID id) override;
    bool on_insert(VectorID id, VectorID& evicted_id) override;
    void erase(VectorID id) override;
    void clear() override;

    std::size_t size() const override { return entries_.size(); }
    std::size_t capacity() const override { return capacity_; }

private:
    std::size_t capacity_;
    struct Entry {
        std::size_t freq;
        std::multimap<std::size_t, VectorID>::iterator it;
    };

    std::multimap<std::size_t, VectorID> freq_map_;
    std::unordered_map<VectorID, Entry> entries_;
};

} // namespace b2
