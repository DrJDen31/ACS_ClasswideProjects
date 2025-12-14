#include "file_backend.hpp"

#include <fstream>

namespace b2 {

FileBackend::FileBackend(const std::string& path, size_t dim)
    : path_(path), dim_(dim) {}

bool FileBackend::read_node(VectorID node_id, VectorData& out_data) {
    if (dim_ == 0) {
        return false;
    }

    std::ifstream in(path_, std::ios::binary);
    if (!in) {
        return false;
    }

    const std::streamoff offset = static_cast<std::streamoff>(node_id) *
        static_cast<std::streamoff>(dim_ * sizeof(float));
    in.seekg(offset);
    if (!in) {
        return false;
    }

    out_data.resize(dim_);
    in.read(reinterpret_cast<char*>(out_data.data()),
            static_cast<std::streamsize>(dim_ * sizeof(float)));
    if (!in) {
        return false;
    }

    stats_.num_reads += 1;
    stats_.bytes_read += dim_ * sizeof(float);
    return true;
}

bool FileBackend::write_node(VectorID node_id, const VectorData& data) {
    if (dim_ == 0) {
        dim_ = data.size();
    }
    if (data.size() != dim_) {
        return false;
    }

    std::fstream io(path_, std::ios::in | std::ios::out | std::ios::binary);
    if (!io.is_open()) {
        io.open(path_, std::ios::out | std::ios::binary);
        if (!io) {
            return false;
        }
        io.close();
        io.open(path_, std::ios::in | std::ios::out | std::ios::binary);
        if (!io) {
            return false;
        }
    }

    const std::streamoff offset = static_cast<std::streamoff>(node_id) *
        static_cast<std::streamoff>(dim_ * sizeof(float));
    io.seekp(offset);
    if (!io) {
        return false;
    }

    io.write(reinterpret_cast<const char*>(data.data()),
             static_cast<std::streamsize>(dim_ * sizeof(float)));
    if (!io) {
        return false;
    }

    io.flush();
    stats_.num_writes += 1;
    stats_.bytes_written += dim_ * sizeof(float);
    return true;
}

bool FileBackend::batch_read_nodes(const std::vector<VectorID>& node_ids,
                                   std::vector<VectorData>& out_data) {
    out_data.clear();
    out_data.reserve(node_ids.size());
    bool all_ok = true;
    for (VectorID id : node_ids) {
        VectorData data;
        if (!read_node(id, data)) {
            all_ok = false;
        }
        out_data.push_back(std::move(data));
    }
    return all_ok;
}

} // namespace b2
