#include "ann/hnsw.hpp"
#include "core/vector.hpp"

#include <iostream>
#include <string>
#include <vector>

int main() {
    const size_t dim = 2;
    const size_t num = 10;

    std::vector<b2::VectorData> data;
    data.reserve(num);

    // Simple 1D line embedded in 2D: point i at (i, 0)
    for (size_t i = 0; i < num; ++i) {
        b2::VectorData v(dim);
        v[0] = static_cast<float>(i);
        v[1] = 0.0f;
        data.push_back(v);
    }

    b2::HNSW index(dim, 4, 50, b2::DistanceMetric::L2);
    index.build(data);

    // Query each point with itself; nearest neighbor should be the same id
    for (size_t i = 0; i < num; ++i) {
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

    // Simple save/load sanity check
    const std::string index_path = "tests/data/hnsw_test_index.bin";
    if (!index.save(index_path)) {
        std::cerr << "Failed to save HNSW index" << "\n";
        return 1;
    }

    b2::HNSW loaded(dim, 4, 50, b2::DistanceMetric::L2);
    if (!loaded.load(index_path.c_str())) {
        std::cerr << "Failed to load HNSW index" << "\n";
        return 1;
    }

    for (size_t i = 0; i < num; ++i) {
        const auto& q = data[i];
        auto ids = loaded.search(q.data(), 1, 10);
        if (ids.empty() || ids[0] != static_cast<b2::VectorID>(i)) {
            std::cerr << "Loaded index returned wrong neighbor for point " << i << "\n";
            return 1;
        }
    }

    std::cout << "hnsw tests passed" << std::endl;
    return 0;
}
