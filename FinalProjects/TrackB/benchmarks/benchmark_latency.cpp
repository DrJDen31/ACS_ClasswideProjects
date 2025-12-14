#include "core/dataset.hpp"
#include "ann/hnsw.hpp"
#include "utils/timer.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>
#include <random>
#include <string>
#include <vector>

struct OptionsLat {
    std::size_t num_base = 100000;
    std::size_t num_queries = 100000;
    std::size_t dim = 128;
    std::size_t ef_search = 100;
    unsigned int seed = 123;
};

static void print_usage_lat(const char* prog) {
    std::cerr << "Usage: " << prog
              << " [--num-base N] [--num-queries Q] [--dim D] [--ef-search EF] [--seed S]" << std::endl;
}

static OptionsLat parse_args_lat(int argc, char** argv) {
    OptionsLat opt;
    for (int i = 1; i < argc; ++i) {
        const char* a = argv[i];
        auto next = [&](std::size_t& out) {
            if (i + 1 >= argc) {
                print_usage_lat(argv[0]);
                std::exit(1);
            }
            out = static_cast<std::size_t>(std::stoull(argv[++i]));
        };
        auto next_u = [&](unsigned int& out) {
            if (i + 1 >= argc) {
                print_usage_lat(argv[0]);
                std::exit(1);
            }
            out = static_cast<unsigned int>(std::stoul(argv[++i]));
        };

        if (std::strcmp(a, "--num-base") == 0) {
            next(opt.num_base);
        } else if (std::strcmp(a, "--num-queries") == 0) {
            next(opt.num_queries);
        } else if (std::strcmp(a, "--dim") == 0) {
            next(opt.dim);
        } else if (std::strcmp(a, "--ef-search") == 0) {
            next(opt.ef_search);
        } else if (std::strcmp(a, "--seed") == 0) {
            next_u(opt.seed);
        } else if (std::strcmp(a, "--help") == 0 || std::strcmp(a, "-h") == 0) {
            print_usage_lat(argv[0]);
            std::exit(0);
        } else {
            std::cerr << "Unknown argument: " << a << std::endl;
            print_usage_lat(argv[0]);
            std::exit(1);
        }
    }
    return opt;
}

int main(int argc, char** argv) {
    OptionsLat opt = parse_args_lat(argc, argv);

    std::cout << "[benchmark_latency] Synthetic dataset, num_base=" << opt.num_base
              << ", num_queries=" << opt.num_queries
              << ", dim=" << opt.dim
              << ", ef_search=" << opt.ef_search << std::endl;

    b2::Dataset base;
    base.generate_synthetic(opt.num_base, opt.dim, "gaussian");

    std::vector<b2::VectorData> base_vecs;
    base_vecs.reserve(base.size());
    for (std::size_t i = 0; i < base.size(); ++i) {
        base_vecs.push_back(base.get_vector_data(i));
    }

    b2::HNSW index(opt.dim, 16, 200, b2::DistanceMetric::L2);

    {
        b2::Timer t;
        index.build(base_vecs);
        std::cout << "Index build time (s): " << t.elapsed_s() << std::endl;
    }

    // Reuse base vectors as queries to stress search latency
    std::vector<double> latencies_us;
    latencies_us.reserve(opt.num_queries);

    b2::Timer total_timer;
    for (std::size_t i = 0; i < opt.num_queries; ++i) {
        const b2::VectorData& q = base.get_vector_data(i % base.size());
        b2::Timer qtimer;
        auto ids = index.search(q.data(), 10, opt.ef_search);
        (void)ids; // ignore contents; focus on latency here
        latencies_us.push_back(qtimer.elapsed_us());
    }
    double total_s = total_timer.elapsed_s();

    std::sort(latencies_us.begin(), latencies_us.end());
    auto pct = [&](double p) {
        if (latencies_us.empty()) return 0.0;
        double idx = p * (latencies_us.size() - 1);
        std::size_t i = static_cast<std::size_t>(idx);
        return latencies_us[i];
    };

    double p50 = pct(0.50);
    double p95 = pct(0.95);
    double p99 = pct(0.99);

    const double qps = static_cast<double>(opt.num_queries) / total_s;

    std::cout << "QPS: " << qps << std::endl;
    std::cout << "Latency us p50/p95/p99: " << p50 << ", " << p95 << ", " << p99 << std::endl;

    return 0;
}
