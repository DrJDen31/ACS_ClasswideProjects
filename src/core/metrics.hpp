#pragma once

#include "vector.hpp"
#include <vector>
#include <set>
#include <algorithm>

namespace b2 {

// Compute recall@k: fraction of true k-NN found in retrieved results
inline float compute_recall_at_k(
    const std::vector<VectorID>& ground_truth,
    const std::vector<VectorID>& retrieved,
    size_t k
) {
    std::set<VectorID> gt_set(ground_truth.begin(), ground_truth.begin() + std::min(k, ground_truth.size()));
    size_t hits = 0;
    for (size_t i = 0; i < std::min(k, retrieved.size()); ++i) {
        if (gt_set.count(retrieved[i])) {
            hits++;
        }
    }
    return static_cast<float>(hits) / static_cast<float>(k);
}

// Compute precision@k
inline float compute_precision_at_k(
    const std::vector<VectorID>& ground_truth,
    const std::vector<VectorID>& retrieved,
    size_t k
) {
    std::set<VectorID> gt_set(ground_truth.begin(), ground_truth.end());
    size_t hits = 0;
    for (size_t i = 0; i < std::min(k, retrieved.size()); ++i) {
        if (gt_set.count(retrieved[i])) {
            hits++;
        }
    }
    return static_cast<float>(hits) / static_cast<float>(std::min(k, retrieved.size()));
}

} // namespace b2
