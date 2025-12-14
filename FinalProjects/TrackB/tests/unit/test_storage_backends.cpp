#include "storage/memory_backend.hpp"
#include "storage/file_backend.hpp"

#include <iostream>
#include <vector>

int main() {
    const size_t num_vectors = 10;
    const size_t dim = 4;

    std::vector<b2::VectorData> vectors;
    vectors.reserve(num_vectors);
    for (size_t i = 0; i < num_vectors; ++i) {
        b2::VectorData v(dim);
        for (size_t d = 0; d < dim; ++d) {
            v[d] = static_cast<float>(i * dim + d);
        }
        vectors.push_back(v);
    }

    b2::MemoryBackend mem_backend;
    b2::FileBackend file_backend("tests/data/test_storage_backend.bin", dim);

    for (size_t i = 0; i < num_vectors; ++i) {
        const b2::VectorID id = static_cast<b2::VectorID>(i);
        if (!mem_backend.write_node(id, vectors[i])) {
            std::cerr << "MemoryBackend write_node failed for id " << i << "\n";
            return 1;
        }
        if (!file_backend.write_node(id, vectors[i])) {
            std::cerr << "FileBackend write_node failed for id " << i << "\n";
            return 1;
        }
    }

    // Single-node reads
    for (size_t i = 0; i < num_vectors; ++i) {
        const b2::VectorID id = static_cast<b2::VectorID>(i);
        b2::VectorData a;
        b2::VectorData b;
        if (!mem_backend.read_node(id, a)) {
            std::cerr << "MemoryBackend read_node failed for id " << i << "\n";
            return 1;
        }
        if (!file_backend.read_node(id, b)) {
            std::cerr << "FileBackend read_node failed for id " << i << "\n";
            return 1;
        }
        if (a.size() != b.size()) {
            std::cerr << "Size mismatch for id " << i << "\n";
            return 1;
        }
        for (size_t d = 0; d < dim; ++d) {
            if (a[d] != b[d]) {
                std::cerr << "Value mismatch at id " << i << ", dim " << d << "\n";
                return 1;
            }
        }
    }

    // Batch read
    std::vector<b2::VectorID> ids;
    for (size_t i = 0; i < num_vectors; ++i) {
        ids.push_back(static_cast<b2::VectorID>(i));
    }

    std::vector<b2::VectorData> mem_batch;
    std::vector<b2::VectorData> file_batch;
    if (!mem_backend.batch_read_nodes(ids, mem_batch)) {
        std::cerr << "MemoryBackend batch_read_nodes reported failure" << "\n";
        return 1;
    }
    if (!file_backend.batch_read_nodes(ids, file_batch)) {
        std::cerr << "FileBackend batch_read_nodes reported failure" << "\n";
        return 1;
    }

    if (mem_batch.size() != file_batch.size()) {
        std::cerr << "Batch size mismatch" << "\n";
        return 1;
    }

    for (size_t i = 0; i < mem_batch.size(); ++i) {
        if (mem_batch[i].size() != file_batch[i].size()) {
            std::cerr << "Batch vector size mismatch at index " << i << "\n";
            return 1;
        }
        for (size_t d = 0; d < mem_batch[i].size(); ++d) {
            if (mem_batch[i][d] != file_batch[i][d]) {
                std::cerr << "Batch value mismatch at index " << i << ", dim " << d << "\n";
                return 1;
            }
        }
    }

    std::cout << "Storage backend tests passed" << std::endl;
    return 0;
}
