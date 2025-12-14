#include "fine_hash_table.hpp"

namespace a4 {

FineHashTable::FineHashTable(size_t num_buckets)
    : num_buckets_(num_buckets),
      buckets_(num_buckets, nullptr),
      bucket_mutexes_(num_buckets),
      size_(0) {
}

FineHashTable::~FineHashTable() {
    // Clean up all nodes in all buckets
    // No need to lock since destructor assumes exclusive access
    for (size_t i = 0; i < num_buckets_; ++i) {
        Node* current = buckets_[i];
        while (current != nullptr) {
            Node* next = current->next;
            delete current;
            current = next;
        }
    }
}

bool FineHashTable::insert(Key key, Value value) {
    size_t bucket_idx = hash(key, num_buckets_);
    
    // Lock only the specific bucket
    std::lock_guard<std::mutex> lock(bucket_mutexes_[bucket_idx]);
    
    // Check if key already exists
    if (find_in_bucket(bucket_idx, key) != nullptr) {
        return false;  // Duplicate key
    }
    
    // Insert at head of bucket
    Node* new_node = new Node(key, value);
    new_node->next = buckets_[bucket_idx];
    buckets_[bucket_idx] = new_node;
    
    size_++;
    return true;
}

bool FineHashTable::find(Key key, Value& value_out) const {
    size_t bucket_idx = hash(key, num_buckets_);
    
    // Lock only the specific bucket
    std::lock_guard<std::mutex> lock(bucket_mutexes_[bucket_idx]);
    
    Node* node = find_in_bucket(bucket_idx, key);
    
    if (node != nullptr) {
        value_out = node->value;
        return true;
    }
    
    return false;
}

bool FineHashTable::erase(Key key) {
    size_t bucket_idx = hash(key, num_buckets_);
    
    // Lock only the specific bucket
    std::lock_guard<std::mutex> lock(bucket_mutexes_[bucket_idx]);
    
    Node* current = buckets_[bucket_idx];
    Node* prev = nullptr;
    
    while (current != nullptr) {
        if (current->key == key) {
            // Found the key, remove it
            if (prev == nullptr) {
                // Removing head of bucket
                buckets_[bucket_idx] = current->next;
            } else {
                // Removing middle or end node
                prev->next = current->next;
            }
            delete current;
            size_--;
            return true;
        }
        prev = current;
        current = current->next;
    }
    
    return false;  // Key not found
}

size_t FineHashTable::size() const {
    return size_.load();
}

Node* FineHashTable::find_in_bucket(size_t bucket_idx, Key key) const {
    Node* current = buckets_[bucket_idx];
    while (current != nullptr) {
        if (current->key == key) {
            return current;
        }
        current = current->next;
    }
    return nullptr;
}

} // namespace a4
