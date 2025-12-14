#include "dataset.hpp"
#include "vector.hpp"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <random>

namespace b2 {

namespace {

static bool has_suffix(const std::string& str, const std::string& suffix) {
    if (suffix.size() > str.size()) {
        return false;
    }
    return std::equal(suffix.rbegin(), suffix.rend(), str.rbegin());
}

}  // namespace

bool Dataset::load_from_file(const std::string& filepath) {
    std::ifstream in(filepath, std::ios::binary);
    if (!in) {
        return false;
    }

    vectors_.clear();
    dim_ = 0;

    const bool is_fvecs = has_suffix(filepath, ".fvecs");
    const bool is_bvecs = has_suffix(filepath, ".bvecs");

    if (!is_fvecs && !is_bvecs) {
        return false;
    }

    while (true) {
        std::int32_t dim = 0;
        in.read(reinterpret_cast<char*>(&dim), sizeof(dim));
        if (!in) {
            break;
        }
        if (dim <= 0) {
            return false;
        }

        if (dim_ == 0) {
            dim_ = static_cast<size_t>(dim);
        } else if (dim_ != static_cast<size_t>(dim)) {
            return false;
        }

        if (is_fvecs) {
            VectorData vec(dim_);
            in.read(reinterpret_cast<char*>(vec.data()),
                    static_cast<std::streamsize>(dim_ * sizeof(float)));
            if (!in) {
                return false;
            }
            vectors_.push_back(std::move(vec));
        } else {
            std::vector<std::uint8_t> tmp(dim_);
            in.read(reinterpret_cast<char*>(tmp.data()),
                    static_cast<std::streamsize>(dim_ * sizeof(std::uint8_t)));
            if (!in) {
                return false;
            }
            VectorData vec(dim_);
            for (size_t i = 0; i < dim_; ++i) {
                vec[i] = static_cast<float>(tmp[i]);
            }
            vectors_.push_back(std::move(vec));
        }
    }

    return !vectors_.empty();
}

void Dataset::generate_synthetic(size_t num_vectors, size_t dim,
                                 const std::string& distribution) {
    vectors_.clear();
    dim_ = dim;

    std::mt19937_64 rng(42);

    if (distribution == "gaussian") {
        std::normal_distribution<float> dist(0.0f, 1.0f);
        vectors_.resize(num_vectors, VectorData(dim_));
        for (size_t i = 0; i < num_vectors; ++i) {
            for (size_t d = 0; d < dim_; ++d) {
                vectors_[i][d] = dist(rng);
            }
        }
    } else {
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);
        vectors_.resize(num_vectors, VectorData(dim_));
        for (size_t i = 0; i < num_vectors; ++i) {
            for (size_t d = 0; d < dim_; ++d) {
                vectors_[i][d] = dist(rng);
            }
        }
    }
}

std::vector<std::vector<VectorID>> Dataset::compute_ground_truth(
    const std::vector<VectorData>& queries,
    size_t k,
    DistanceMetric metric) const {
    std::vector<std::vector<VectorID>> result;
    result.reserve(queries.size());

    for (const auto& q : queries) {
        std::vector<std::pair<float, VectorID>> dists;
        dists.reserve(vectors_.size());

        for (size_t i = 0; i < vectors_.size(); ++i) {
            float dist = compute_distance(q.data(), vectors_[i].data(), dim_, metric);
            dists.emplace_back(dist, static_cast<VectorID>(i));
        }

        if (k < dists.size()) {
            std::nth_element(dists.begin(), dists.begin() + static_cast<std::ptrdiff_t>(k), dists.end(),
                             [](const auto& a, const auto& b) { return a.first < b.first; });
            dists.resize(k);
        }

        std::sort(dists.begin(), dists.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });

        std::vector<VectorID> top_ids;
        top_ids.reserve(std::min(k, dists.size()));
        for (size_t i = 0; i < std::min(k, dists.size()); ++i) {
            top_ids.push_back(dists[i].second);
        }
        result.push_back(std::move(top_ids));
    }

    return result;
}

}  // namespace b2
