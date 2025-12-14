#include "cache_policy.hpp"

namespace b2 {

LRUCachePolicy::LRUCachePolicy(std::size_t capacity)
    : capacity_(capacity) {}

void LRUCachePolicy::record_access(VectorID id) {
    auto it = map_.find(id);
    if (it == map_.end()) {
        return;
    }
    lru_list_.splice(lru_list_.begin(), lru_list_, it->second);
}

bool LRUCachePolicy::on_insert(VectorID id, VectorID& evicted_id) {
    if (capacity_ == 0) {
        return false;
    }

    auto it = map_.find(id);
    if (it != map_.end()) {
        // Already present; just mark as most recently used.
        record_access(id);
        return false;
    }

    bool evicted = false;
    if (map_.size() >= capacity_) {
        // Evict least recently used (back of list).
        VectorID victim = lru_list_.back();
        lru_list_.pop_back();
        map_.erase(victim);
        evicted_id = victim;
        evicted = true;
    }

    lru_list_.push_front(id);
    map_[id] = lru_list_.begin();
    return evicted;
}

void LRUCachePolicy::erase(VectorID id) {
    auto it = map_.find(id);
    if (it == map_.end()) {
        return;
    }
    lru_list_.erase(it->second);
    map_.erase(it);
}

void LRUCachePolicy::clear() {
    lru_list_.clear();
    map_.clear();
}

LFUCachePolicy::LFUCachePolicy(std::size_t capacity)
    : capacity_(capacity) {}

void LFUCachePolicy::record_access(VectorID id) {
    auto it = entries_.find(id);
    if (it == entries_.end()) {
        return;
    }

    const std::size_t old_freq = it->second.freq;
    const std::size_t new_freq = old_freq + 1;

    freq_map_.erase(it->second.it);
    auto mm_it = freq_map_.emplace(new_freq, id);
    it->second.freq = new_freq;
    it->second.it = mm_it;
}

bool LFUCachePolicy::on_insert(VectorID id, VectorID& evicted_id) {
    if (capacity_ == 0) {
        return false;
    }

    auto it = entries_.find(id);
    if (it != entries_.end()) {
        record_access(id);
        return false;
    }

    bool evicted = false;
    if (entries_.size() >= capacity_) {
        auto victim_it = freq_map_.begin();
        if (victim_it != freq_map_.end()) {
            VectorID victim = victim_it->second;
            freq_map_.erase(victim_it);
            entries_.erase(victim);
            evicted_id = victim;
            evicted = true;
        }
    }

    auto mm_it = freq_map_.emplace(1, id);
    entries_.emplace(id, Entry{1, mm_it});
    return evicted;
}

void LFUCachePolicy::erase(VectorID id) {
    auto it = entries_.find(id);
    if (it == entries_.end()) {
        return;
    }

    freq_map_.erase(it->second.it);
    entries_.erase(it);
}

void LFUCachePolicy::clear() {
    freq_map_.clear();
    entries_.clear();
}

} // namespace b2
