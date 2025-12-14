#include "tiered/cache_policy.hpp"
#include "storage/memory_backend.hpp"
#include "storage/tiered_backend.hpp"

#include <iostream>
#include <memory>

int main() {
    // --- Test 1: LRU cache policy eviction order ---------------------------
    {
        b2::LRUCachePolicy policy(2);
        b2::VectorID evicted = 0;

        policy.on_insert(1, evicted); // {1}
        policy.on_insert(2, evicted); // {2,1} (2 most recent)
        policy.record_access(1);      // {1,2}

        bool did_evict = policy.on_insert(3, evicted); // expect eviction of 2
        if (!did_evict || evicted != 2) {
            std::cerr << "LRU policy eviction failed: expected 2, got " << evicted << "\n";
            return 1;
        }
    }

    // --- Test 2: TieredBackend correctness and basic cache stats ----------
    {
        const std::size_t num = 4;
        const std::size_t dim = 4;

        auto backing = std::make_shared<b2::MemoryBackend>();
        for (std::size_t i = 0; i < num; ++i) {
            b2::VectorData v(dim);
            for (std::size_t d = 0; d < dim; ++d) {
                v[d] = static_cast<float>(i * dim + d);
            }
            if (!backing->write_node(static_cast<b2::VectorID>(i), v)) {
                std::cerr << "Backing write_node failed for id " << i << "\n";
                return 1;
            }
        }

        b2::TieredBackend tier(backing, 2); // small cache capacity

        // First pass: all misses, but data must match backing
        for (std::size_t i = 0; i < num; ++i) {
            b2::VectorData out;
            if (!tier.read_node(static_cast<b2::VectorID>(i), out)) {
                std::cerr << "TieredBackend read_node failed for id " << i << "\n";
                return 1;
            }
            if (out.size() != dim) {
                std::cerr << "Unexpected vector size for id " << i << "\n";
                return 1;
            }
            for (std::size_t d = 0; d < dim; ++d) {
                float expected = static_cast<float>(i * dim + d);
                if (out[d] != expected) {
                    std::cerr << "Value mismatch for id " << i << ", dim " << d << "\n";
                    return 1;
                }
            }
        }

        if (tier.cache_misses() == 0 || tier.cache_hits() != 0) {
            std::cerr << "Expected initial reads to be all misses" << "\n";
            return 1;
        }

        // Second phase: use a working set that fits in the cache to observe hits.
        // Warm the cache with ids 0 and 1.
        for (std::size_t i = 0; i < 2; ++i) {
            b2::VectorData out;
            if (!tier.read_node(static_cast<b2::VectorID>(i), out)) {
                std::cerr << "TieredBackend warmup read failed for id " << i << "\n";
                return 1;
            }
        }

        std::uint64_t prev_hits = tier.cache_hits();
        std::uint64_t prev_misses = tier.cache_misses();

        // Re-access ids 0 and 1; these should now be cache hits.
        for (std::size_t repeat = 0; repeat < 4; ++repeat) {
            for (std::size_t i = 0; i < 2; ++i) {
                b2::VectorData out;
                if (!tier.read_node(static_cast<b2::VectorID>(i), out)) {
                    std::cerr << "TieredBackend cached read failed for id " << i << "\n";
                    return 1;
                }
            }
        }

        if (tier.cache_hits() <= prev_hits) {
            std::cerr << "Cache hits did not increase during cached access phase" << "\n";
            return 1;
        }
        if (tier.cache_misses() < prev_misses) {
            std::cerr << "Cache misses decreased unexpectedly" << "\n";
            return 1;
        }

        if (tier.cache_size() > tier.cache_capacity()) {
            std::cerr << "Cache size exceeds capacity" << "\n";
            return 1;
        }
    }

    std::cout << "cache and tiered backend tests passed" << std::endl;
    return 0;
}
