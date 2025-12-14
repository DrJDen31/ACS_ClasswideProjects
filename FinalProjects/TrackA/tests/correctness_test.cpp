/**
 * Correctness tests for hash table implementations
 * 
 * Tests basic operations in single-threaded mode to verify
 * correctness of insert, find, and erase operations.
 */

#include "hash_table.hpp"
#include "coarse_hash_table.hpp"
#include "fine_hash_table.hpp"
#include <iostream>
#include <cassert>
#include <vector>
#include <algorithm>

using namespace a4;

// Test counter
int tests_passed = 0;
int tests_failed = 0;

#define TEST(name) \
    void test_##name(HashTable* table)

#define RUN_TEST(name, table, impl_name) \
    do { \
        std::cout << "Running test: " << #name << " (" << impl_name << ")... "; \
        try { \
            test_##name(table); \
            std::cout << "PASSED" << std::endl; \
            tests_passed++; \
        } catch (const std::exception& e) { \
            std::cout << "FAILED: " << e.what() << std::endl; \
            tests_failed++; \
        } \
    } while(0)

#define ASSERT(condition, message) \
    if (!(condition)) { \
        throw std::runtime_error(std::string("Assertion failed: ") + message); \
    }

// Test: Insert and find a single key
TEST(insert_and_find_single) {
    ASSERT(table->empty(), "Table should be empty initially");
    ASSERT(table->insert(1, 100), "Should insert key 1");
    ASSERT(table->size() == 1, "Size should be 1");
    
    Value val;
    ASSERT(table->find(1, val), "Should find key 1");
    ASSERT(val == 100, "Value should be 100");
}

// Test: Find missing key
TEST(find_missing_key) {
    Value val;
    ASSERT(!table->find(999, val), "Should not find missing key");
}

// Test: Insert duplicate key
TEST(insert_duplicate) {
    ASSERT(table->insert(1, 100), "Should insert key 1");
    ASSERT(!table->insert(1, 200), "Should not insert duplicate key 1");
    
    Value val;
    ASSERT(table->find(1, val), "Should find key 1");
    ASSERT(val == 100, "Value should still be 100");
}

// Test: Erase existing key
TEST(erase_existing) {
    ASSERT(table->insert(1, 100), "Should insert key 1");
    ASSERT(table->erase(1), "Should erase key 1");
    ASSERT(table->size() == 0, "Size should be 0 after erase");
    
    Value val;
    ASSERT(!table->find(1, val), "Should not find erased key");
}

// Test: Erase missing key
TEST(erase_missing) {
    ASSERT(!table->erase(999), "Should not erase missing key");
}

// Test: Multiple inserts
TEST(multiple_inserts) {
    const size_t N = 100;
    for (size_t i = 0; i < N; i++) {
        ASSERT(table->insert(i, i * 10), "Should insert key " + std::to_string(i));
    }
    ASSERT(table->size() == N, "Size should be " + std::to_string(N));
    
    for (size_t i = 0; i < N; i++) {
        Value val;
        ASSERT(table->find(i, val), "Should find key " + std::to_string(i));
        ASSERT(val == i * 10, "Value should match for key " + std::to_string(i));
    }
}

// Test: Insert, erase, re-insert
TEST(insert_erase_reinsert) {
    ASSERT(table->insert(1, 100), "Should insert key 1");
    ASSERT(table->erase(1), "Should erase key 1");
    ASSERT(table->insert(1, 200), "Should re-insert key 1 with new value");
    
    Value val;
    ASSERT(table->find(1, val), "Should find key 1");
    ASSERT(val == 200, "Value should be 200 after re-insert");
}

// Test: Large dataset
TEST(large_dataset) {
    const size_t N = 10000;
    std::vector<Key> keys(N);
    for (size_t i = 0; i < N; i++) {
        keys[i] = i;
    }
    
    // Shuffle for more realistic access pattern
    std::random_shuffle(keys.begin(), keys.end());
    
    // Insert
    for (Key key : keys) {
        ASSERT(table->insert(key, key * 2), "Should insert key " + std::to_string(key));
    }
    ASSERT(table->size() == N, "Size should be " + std::to_string(N));
    
    // Verify
    for (Key key : keys) {
        Value val;
        ASSERT(table->find(key, val), "Should find key " + std::to_string(key));
        ASSERT(val == key * 2, "Value mismatch for key " + std::to_string(key));
    }
}

// Helper to create a table based on implementation name
HashTable* create_table(const char* name) {
    if (std::string(name) == "coarse") return new CoarseHashTable();
    if (std::string(name) == "fine") return new FineHashTable();
    return nullptr;
}

// Run all tests for a given hash table implementation
void run_all_tests(const char* impl_name) {
    std::cout << "\n=== Testing " << impl_name << " ===" << std::endl;
    
    HashTable* table = nullptr;
    
    #define RUN_AND_RESET(test_name) \
        delete table; \
        table = create_table(impl_name); \
        RUN_TEST(test_name, table, impl_name)
    
    RUN_AND_RESET(insert_and_find_single);
    RUN_AND_RESET(find_missing_key);
    RUN_AND_RESET(insert_duplicate);
    RUN_AND_RESET(erase_existing);
    RUN_AND_RESET(erase_missing);
    RUN_AND_RESET(multiple_inserts);
    RUN_AND_RESET(insert_erase_reinsert);
    RUN_AND_RESET(large_dataset);
    
    delete table;
    
    #undef RUN_AND_RESET
}

int main() {
    std::cout << "==================================" << std::endl;
    std::cout << "Hash Table Correctness Tests" << std::endl;
    std::cout << "==================================" << std::endl;
    
    // Test coarse-grained implementation
    run_all_tests("coarse");
    
    // Test fine-grained implementation
    run_all_tests("fine");
    
    // TODO: Test rwlock implementation when available
    
    // Summary
    std::cout << "\n==================================" << std::endl;
    std::cout << "Test Summary:" << std::endl;
    std::cout << "  Passed: " << tests_passed << std::endl;
    std::cout << "  Failed: " << tests_failed << std::endl;
    std::cout << "==================================" << std::endl;
    
    return tests_failed > 0 ? 1 : 0;
}
