#include "core/dataset.hpp"

#include <iostream>

int main() {
    b2::Dataset ds;
    ds.generate_synthetic(10, 4, "gaussian");

    if (ds.size() != 10) {
        std::cerr << "Dataset size mismatch" << std::endl;
        return 1;
    }
    if (ds.dimension() != 4) {
        std::cerr << "Dataset dimension mismatch" << std::endl;
        return 1;
    }

    b2::VectorData q(4, 0.0f);
    std::vector<b2::VectorData> queries;
    queries.push_back(q);

    auto gt = ds.compute_ground_truth(queries, 3, b2::DistanceMetric::L2);
    if (gt.size() != 1 || gt[0].size() != 3) {
        std::cerr << "Ground truth size mismatch" << std::endl;
        return 1;
    }

    std::cout << "dataset tests passed" << std::endl;
    return 0;
}
