#include "tiered/tiered_hnsw.hpp"
#include "storage/memory_backend.hpp"
#include "storage/tiered_backend.hpp"

#include <iostream>
#include <memory>
#include <vector>

int main() {
    const std::size_t dim = 2;
    const std::size_t num = 16;

    std::vector<b2::VectorData> data;
    data.reserve(num);

    // Simple 1D line embedded in 2D: point i at (i, 0)
    for (std::size_t i = 0; i < num; ++i) {
        b2::VectorData v(dim);
        v[0] = static_cast<float>(i);
        v[1] = 0.0f;
        data.push_back(v);
    }

    auto backing = std::make_shared<b2::MemoryBackend>();
    auto tiered_storage = std::make_shared<b2::TieredBackend>(backing, 4); // small cache capacity

    b2::TieredHNSW index(dim, tiered_storage, 4, 50, b2::DistanceMetric::L2);
    index.build(data);

    // Verify nearest neighbor of each point is itself.
    for (std::size_t i = 0; i < num; ++i) {
        const auto& q = data[i];
        auto ids = index.search(q.data(), 1, 10);
        if (ids.empty()) {
            std::cerr << "Empty search result for point " << i << "\n";
            return 1;
        }
        if (ids[0] != static_cast<b2::VectorID>(i)) {
            std::cerr << "Incorrect nearest neighbor for point " << i
                      << ": got " << ids[0] << ", expected " << i << "\n";
            return 1;
        }
    }

    // Basic sanity: tiered storage should have seen some reads/misses.
    if (tiered_storage->cache_misses() == 0) {
        std::cerr << "Expected tiered storage to observe misses" << "\n";
        return 1;
    }

    std::cout << "tiered hnsw tests passed" << std::endl;
    return 0;
}
