#include "core/vector.hpp"

#include <cmath>
#include <iostream>

int main() {
    const size_t dim = 3;
    float a[dim] = {1.0f, 2.0f, 3.0f};
    float b[dim] = {4.0f, 6.0f, 8.0f};

    float l2 = b2::l2_distance_squared(a, b, dim);
    float ip = b2::inner_product(a, b, dim);
    float cos = b2::cosine_similarity(a, b, dim);

    float expected_l2 = 9.0f + 16.0f + 25.0f;
    float expected_ip = 1.0f * 4.0f + 2.0f * 6.0f + 3.0f * 8.0f;

    if (std::fabs(l2 - expected_l2) > 1e-5f) {
        std::cerr << "l2_distance_squared mismatch" << std::endl;
        return 1;
    }

    if (std::fabs(ip - expected_ip) > 1e-5f) {
        std::cerr << "inner_product mismatch" << std::endl;
        return 1;
    }

    if (!(cos > 0.0f && cos <= 1.0f)) {
        std::cerr << "cosine_similarity out of expected range" << std::endl;
        return 1;
    }

    std::cout << "vector tests passed" << std::endl;
    return 0;
}
