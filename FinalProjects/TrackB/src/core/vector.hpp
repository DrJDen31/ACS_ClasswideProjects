#pragma once

#include <vector>
#include <cstdint>
#include <cmath>
#if defined(__AVX2__)
#include <immintrin.h>
#endif

namespace b2 {

// Vector data structure and distance metrics
using VectorData = std::vector<float>;
using VectorID = uint64_t;

// Distance metrics
enum class DistanceMetric {
    L2,           // Euclidean distance (squared)
    InnerProduct, // Dot product (for cosine with normalized vectors)
    Cosine        // Cosine similarity
};

// Compute L2 (Euclidean) distance squared between two vectors
// AVX2-optimized path when available, with scalar fallback for portability.
inline float l2_distance_squared(const float* a, const float* b, size_t dim) {
#if defined(__AVX2__)
    const size_t kBlock = 8; // 8 floats per 256-bit register
    size_t i = 0;
    __m256 acc = _mm256_setzero_ps();

    for (; i + kBlock <= dim; i += kBlock) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        __m256 diff = _mm256_sub_ps(va, vb);
#if defined(__FMA__)
        acc = _mm256_fmadd_ps(diff, diff, acc);
#else
        __m256 sq = _mm256_mul_ps(diff, diff);
        acc = _mm256_add_ps(acc, sq);
#endif
    }

    alignas(32) float buf[8];
    _mm256_store_ps(buf, acc);
    float dist = buf[0] + buf[1] + buf[2] + buf[3] + buf[4] + buf[5] + buf[6] + buf[7];

    // Tail
    for (; i < dim; ++i) {
        float diff = a[i] - b[i];
        dist += diff * diff;
    }
    return dist;
#else
    float dist = 0.0f;
    for (size_t i = 0; i < dim; ++i) {
        float diff = a[i] - b[i];
        dist += diff * diff;
    }
    return dist;
#endif
}

// Compute inner product (dot product) between two vectors
// TODO: Add SIMD optimizations
inline float inner_product(const float* a, const float* b, size_t dim) {
    float result = 0.0f;
    for (size_t i = 0; i < dim; ++i) {
        result += a[i] * b[i];
    }
    return result;
}

// Compute cosine similarity between two vectors
inline float cosine_similarity(const float* a, const float* b, size_t dim) {
    float dot = inner_product(a, b, dim);
    float norm_a = std::sqrt(inner_product(a, a, dim));
    float norm_b = std::sqrt(inner_product(b, b, dim));
    return dot / (norm_a * norm_b + 1e-8f);
}

// Generic distance function
inline float compute_distance(const float* a, const float* b, size_t dim, DistanceMetric metric) {
    switch (metric) {
        case DistanceMetric::L2:
            return l2_distance_squared(a, b, dim);
        case DistanceMetric::InnerProduct:
            return -inner_product(a, b, dim); // Negative for max-heap
        case DistanceMetric::Cosine:
            return -cosine_similarity(a, b, dim); // Negative for max-heap
        default:
            return l2_distance_squared(a, b, dim);
    }
}

} // namespace b2
