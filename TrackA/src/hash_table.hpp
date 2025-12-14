#ifndef HASH_TABLE_HPP
#define HASH_TABLE_HPP

#include "common.hpp"

namespace a4 {

/**
 * Abstract base class for thread-safe hash table implementations.
 * 
 * All operations must be thread-safe and maintain the following invariants:
 * - Keys are unique (no duplicate keys)
 * - Operations are linearizable
 * - No memory leaks
 */
class HashTable {
public:
    virtual ~HashTable() = default;

    /**
     * Insert a key-value pair into the hash table.
     * 
     * @param key The key to insert
     * @param value The value associated with the key
     * @return true if insertion succeeded, false if key already exists
     */
    virtual bool insert(Key key, Value value) = 0;

    /**
     * Find a value by key.
     * 
     * @param key The key to search for
     * @param value_out Output parameter for the value if found
     * @return true if key was found, false otherwise
     */
    virtual bool find(Key key, Value& value_out) const = 0;

    /**
     * Remove a key-value pair from the hash table.
     * 
     * @param key The key to remove
     * @return true if key was found and removed, false otherwise
     */
    virtual bool erase(Key key) = 0;

    /**
     * Get the current number of elements in the hash table.
     * 
     * @return The number of key-value pairs
     */
    virtual size_t size() const = 0;

    /**
     * Check if the hash table is empty.
     * 
     * @return true if size() == 0
     */
    virtual bool empty() const { return size() == 0; }

    /**
     * Get a human-readable name for this implementation.
     * 
     * @return Strategy name (e.g., "coarse", "fine", "rwlock")
     */
    virtual const char* name() const = 0;
};

} // namespace a4

#endif // HASH_TABLE_HPP
