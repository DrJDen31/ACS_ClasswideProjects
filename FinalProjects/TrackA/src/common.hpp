#ifndef COMMON_HPP
#define COMMON_HPP

#include <cstdint>
#include <cstddef>

namespace a4 {

// Type aliases for keys and values
using Key = uint64_t;
using Value = uint64_t;

// Node structure for chaining
struct Node {
    Key key;
    Value value;
    Node* next;

    Node(Key k, Value v) : key(k), value(v), next(nullptr) {}
};

// Hash function - simple modulo
inline size_t hash(Key key, size_t num_buckets) {
    return key % num_buckets;
}

// Configuration constants
constexpr size_t DEFAULT_NUM_BUCKETS = 1024;
constexpr size_t CACHE_LINE_SIZE = 64;

} // namespace a4

#endif // COMMON_HPP
