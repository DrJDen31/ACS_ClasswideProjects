#include "core/dataset.hpp"
#include "ann/hnsw.hpp"
#include "core/metrics.hpp"
#include "utils/timer.hpp"
#include "tiered/tiered_hnsw.hpp"
#include "storage/memory_backend.hpp"
#include "storage/tiered_backend.hpp"
#include "simulator/ann_in_ssd_model.hpp"
#include "simulator/ssd_simulator.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

static std::vector<std::vector<b2::VectorID>> compute_ground_truth_from_base(
    const std::vector<b2::VectorData>& base_vecs,
    const std::vector<b2::VectorData>& queries,
    std::size_t k) {
    std::vector<std::vector<b2::VectorID>> result;
    result.reserve(queries.size());

    const std::size_t dim = base_vecs.empty() ? 0 : base_vecs[0].size();

    for (const auto& q : queries) {
        std::vector<std::pair<float, b2::VectorID>> dists;
        dists.reserve(base_vecs.size());

        for (std::size_t i = 0; i < base_vecs.size(); ++i) {
            float dist = b2::compute_distance(q.data(), base_vecs[i].data(), dim,
                                              b2::DistanceMetric::L2);
            dists.emplace_back(dist, static_cast<b2::VectorID>(i));
        }

        const std::size_t kk = std::min<std::size_t>(k, dists.size());
        if (kk < dists.size()) {
            std::nth_element(
                dists.begin(),
                dists.begin() + static_cast<std::ptrdiff_t>(kk),
                dists.end(),
                [](const auto& a, const auto& b) { return a.first < b.first; });
            dists.resize(kk);
        }

        std::sort(dists.begin(), dists.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });

        std::vector<b2::VectorID> top_ids;
        top_ids.reserve(kk);
        for (std::size_t i = 0; i < kk; ++i) {
            top_ids.push_back(dists[i].second);
        }
        result.push_back(std::move(top_ids));
    }

    return result;
}

struct Options {
    std::size_t num_base = 100000;
    std::size_t num_queries = 1000;
    std::size_t dim = 128;
    std::size_t k = 10;
    std::size_t ef_search = 100;
    std::size_t M = 16;
    std::size_t ef_construction = 200;
    std::size_t hnsw_build_threads = 1;
    unsigned int seed = 42;
    std::string mode = "dram";            // "dram", "tiered", or "ann_ssd"
    std::size_t cache_capacity = 10000;   // used in tiered mode
    std::string cache_policy = "lru";     // used in tiered mode

    // SSD device model parameters for tiered mode (used when mode == "tiered")
    std::size_t ssd_num_channels = 4;
    std::size_t ssd_queue_depth_per_channel = 64;
    double ssd_base_read_latency_us = 80.0;
    double ssd_internal_read_bandwidth_GBps = 3.0;

    std::string dataset_path;             // optional: base dataset (fvecs/bvecs)
    std::string dataset_name;             // for logging (filled in main if empty)
    std::string query_path;               // optional: query vectors (fvecs)
    std::string groundtruth_path;         // optional: groundtruth (ivecs)

    std::string json_out;                 // optional JSON log path
    bool num_base_specified = false;
    std::string per_query_out;            // optional: write per-query neighbor IDs
    std::string ann_ssd_mode;
    std::string ann_hw_level;

    // ANN-in-SSD tuning knobs
    std::size_t ann_vectors_per_block = 0;
    std::size_t ann_max_steps = 0;
    std::size_t ann_portal_degree = 0;
    std::string ann_placement_mode; // e.g., "locality_aware"
    std::string ann_code_type;      // e.g., "micro_index"
};

static void print_usage(const char* prog) {
    std::cerr << "Usage: " << prog
              << " [--num-base N] [--num-queries Q] [--dim D] [--k K]"
              << " [--ef-search EF] [--M M] [--ef-construction EF_C] [--seed S]"
              << " [--mode dram|tiered|ann_ssd] [--cache-capacity C] [--cache-policy NAME]"
              << " [--dataset-path PATH] [--dataset-name NAME]"
              << " [--query-path PATH] [--groundtruth-path PATH]"
              << " [--json-out PATH] [--per-query-out PATH]"
              << " [--hnsw-build-threads T]"
              << " [--ann-ssd-mode faithful|cheated] [--ann-hw-level L0|L1|L2|L3]"
              << " [--ann-vectors-per-block K] [--ann-max-steps S] [--ann-portal-degree P]"
              << " [--placement-mode MODE] [--code-type TYPE]"
              << " [--ssd-base-latency-us L] [--ssd-internal-bw-GBps B] [--ssd-num-channels C] [--ssd-queue-depth Q]"
              << std::endl;
}

static void write_json_log_baseline(const Options& opt,
                                    const std::string& mode,
                                    double avg_recall,
                                    double qps_total,
                                    double qps_search,
                                    double p50,
                                    double p95,
                                    double p99,
                                    double build_s,
                                    double search_s,
                                    unsigned long long num_reads,
                                    unsigned long long bytes_read,
                                    double device_time_us) {
    if (opt.json_out.empty()) {
        return;
    }

    std::ofstream ofs(opt.json_out);
    if (!ofs) {
        return;
    }

    double effective_search_s = search_s + (device_time_us * 1e-6);
    double effective_qps = 0.0;
    if (effective_search_s > 0.0) {
        effective_qps = static_cast<double>(opt.num_queries) / effective_search_s;
    }

    ofs << "{\n";
    ofs << "  \"config\": {\n";
    ofs << "    \"dataset_name\": \"" << opt.dataset_name << "\",\n";
    ofs << "    \"dimension\": " << opt.dim << ",\n";
    ofs << "    \"num_vectors\": " << opt.num_base << ",\n";
    ofs << "    \"k\": " << opt.k << ",\n";
    ofs << "    \"ef_search\": " << opt.ef_search << ",\n";
    ofs << "    \"M\": " << opt.M << ",\n";
    ofs << "    \"ef_construction\": " << opt.ef_construction << ",\n";
    ofs << "    \"cache_capacity\": " << opt.cache_capacity << ",\n";
    ofs << "    \"cache_policy\": \"" << opt.cache_policy << "\",\n";
    ofs << "    \"mode\": \"" << mode << "\",\n";
    ofs << "    \"ssd_num_channels\": " << opt.ssd_num_channels << ",\n";
    ofs << "    \"ssd_queue_depth_per_channel\": " << opt.ssd_queue_depth_per_channel << ",\n";
    ofs << "    \"ssd_base_read_latency_us\": " << opt.ssd_base_read_latency_us << ",\n";
    ofs << "    \"ssd_internal_read_bandwidth_GBps\": " << opt.ssd_internal_read_bandwidth_GBps << "\n";
    ofs << "  },\n";

    ofs << "  \"aggregate\": {\n";
    ofs << "    \"k\": " << opt.k << ",\n";
    ofs << "    \"num_queries\": " << opt.num_queries << ",\n";
    ofs << "    \"recall_at_k\": " << avg_recall << ",\n";
    ofs << "    \"qps\": " << qps_search << ",\n";
    ofs << "    \"qps_search\": " << qps_search << ",\n";
    ofs << "    \"qps_total\": " << qps_total << ",\n";
    ofs << "    \"latency_us_p50\": " << p50 << ",\n";
    ofs << "    \"latency_us_p95\": " << p95 << ",\n";
    ofs << "    \"latency_us_p99\": " << p99 << ",\n";
    ofs << "    \"build_time_s\": " << build_s << ",\n";
    ofs << "    \"search_time_s\": " << search_s << ",\n";
    ofs << "    \"effective_search_time_s\": " << effective_search_s << ",\n";
    ofs << "    \"effective_qps\": " << effective_qps << ",\n";
    ofs << "    \"io\": {\n";
    ofs << "      \"num_reads\": " << num_reads << ",\n";
    ofs << "      \"bytes_read\": " << bytes_read << "\n";
    ofs << "    },\n";
    ofs << "    \"device_time_us\": " << device_time_us << "\n";
    ofs << "  }\n";
    ofs << "}\n";
}

static Options parse_args(int argc, char** argv) {
    Options opt;
    for (int i = 1; i < argc; ++i) {
        const char* a = argv[i];
        auto next = [&](std::size_t& out) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            out = static_cast<std::size_t>(std::stoull(argv[++i]));
        };
        auto next_u = [&](unsigned int& out) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            out = static_cast<unsigned int>(std::stoul(argv[++i]));
        };
        auto next_d = [&](double& out) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            out = std::stod(argv[++i]);
        };

        if (std::strcmp(a, "--num-base") == 0) {
            next(opt.num_base);
            opt.num_base_specified = true;
        } else if (std::strcmp(a, "--num-queries") == 0) {
            next(opt.num_queries);
        } else if (std::strcmp(a, "--dim") == 0) {
            next(opt.dim);
        } else if (std::strcmp(a, "--k") == 0) {
            next(opt.k);
        } else if (std::strcmp(a, "--ef-search") == 0) {
            next(opt.ef_search);
        } else if (std::strcmp(a, "--seed") == 0) {
            next_u(opt.seed);
        } else if (std::strcmp(a, "--mode") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.mode = argv[++i];
        } else if (std::strcmp(a, "--cache-capacity") == 0) {
            next(opt.cache_capacity);
        } else if (std::strcmp(a, "--cache-policy") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.cache_policy = argv[++i];
        } else if (std::strcmp(a, "--ssd-base-latency-us") == 0) {
            next_d(opt.ssd_base_read_latency_us);
        } else if (std::strcmp(a, "--ssd-internal-bw-GBps") == 0) {
            next_d(opt.ssd_internal_read_bandwidth_GBps);
        } else if (std::strcmp(a, "--ssd-num-channels") == 0) {
            next(opt.ssd_num_channels);
        } else if (std::strcmp(a, "--ssd-queue-depth") == 0) {
            next(opt.ssd_queue_depth_per_channel);
        } else if (std::strcmp(a, "--dataset-path") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.dataset_path = argv[++i];
        } else if (std::strcmp(a, "--dataset-name") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.dataset_name = argv[++i];
        } else if (std::strcmp(a, "--M") == 0) {
            next(opt.M);
        } else if (std::strcmp(a, "--ef-construction") == 0) {
            next(opt.ef_construction);
        } else if (std::strcmp(a, "--query-path") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.query_path = argv[++i];
        } else if (std::strcmp(a, "--groundtruth-path") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.groundtruth_path = argv[++i];
        } else if (std::strcmp(a, "--json-out") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.json_out = argv[++i];
        } else if (std::strcmp(a, "--per-query-out") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.per_query_out = argv[++i];
        } else if (std::strcmp(a, "--ann-ssd-mode") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.ann_ssd_mode = argv[++i];
        } else if (std::strcmp(a, "--ann-hw-level") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.ann_hw_level = argv[++i];
        } else if (std::strcmp(a, "--hnsw-build-threads") == 0) {
            next(opt.hnsw_build_threads);
        } else if (std::strcmp(a, "--ann-vectors-per-block") == 0) {
            next(opt.ann_vectors_per_block);
        } else if (std::strcmp(a, "--ann-max-steps") == 0) {
            next(opt.ann_max_steps);
        } else if (std::strcmp(a, "--ann-portal-degree") == 0) {
            next(opt.ann_portal_degree);
        } else if (std::strcmp(a, "--placement-mode") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.ann_placement_mode = argv[++i];
        } else if (std::strcmp(a, "--code-type") == 0) {
            if (i + 1 >= argc) {
                print_usage(argv[0]);
                std::exit(1);
            }
            opt.ann_code_type = argv[++i];
        } else if (std::strcmp(a, "--help") == 0 || std::strcmp(a, "-h") == 0) {
            print_usage(argv[0]);
            std::exit(0);
        } else {
            std::cerr << "Unknown argument: " << a << std::endl;
            print_usage(argv[0]);
            std::exit(1);
        }
    }
    return opt;
}

int main(int argc, char** argv) {
    Options opt = parse_args(argc, argv);

    std::cout << "[benchmark_recall] mode=" << opt.mode
              << ", num_base=" << opt.num_base
              << ", num_queries=" << opt.num_queries
              << ", dim=" << opt.dim
              << ", k=" << opt.k
              << ", ef_search=" << opt.ef_search
              << ", M=" << opt.M
              << ", ef_construction=" << opt.ef_construction
              << ", hnsw_build_threads=" << opt.hnsw_build_threads;
    if (opt.mode == "tiered") {
        std::cout << ", cache_capacity=" << opt.cache_capacity
                  << ", cache_policy=" << opt.cache_policy
                  << ", ssd_num_channels=" << opt.ssd_num_channels
                  << ", ssd_queue_depth=" << opt.ssd_queue_depth_per_channel
                  << ", ssd_base_read_latency_us=" << opt.ssd_base_read_latency_us
                  << ", ssd_internal_read_bandwidth_GBps=" << opt.ssd_internal_read_bandwidth_GBps;
    }
    std::cout << std::endl;

    // 1. Generate or load base dataset
    b2::Dataset base;
    if (!opt.dataset_path.empty()) {
        if (!base.load_from_file(opt.dataset_path)) {
            std::cerr << "Failed to load dataset from " << opt.dataset_path << std::endl;
            return 1;
        }
        if (opt.dim == 0) {
            opt.dim = base.dimension();
        }
        if (opt.dataset_name.empty()) {
            opt.dataset_name = opt.dataset_path;
        }
        if (!opt.num_base_specified || opt.num_base == 0 || opt.num_base > base.size()) {
            opt.num_base = base.size();
        }
    } else {
        base.generate_synthetic(opt.num_base, opt.dim, "gaussian");
        if (opt.dataset_name.empty()) {
            opt.dataset_name = "synthetic_gaussian";
        }
        if (opt.num_base == 0 || opt.num_base > base.size()) {
            opt.num_base = base.size();
        }
    }

    const std::size_t num_base_to_use = std::min<std::size_t>(opt.num_base, base.size());
    opt.num_base = num_base_to_use;
    std::vector<b2::VectorData> base_vecs;
    base_vecs.reserve(num_base_to_use);
    for (std::size_t i = 0; i < num_base_to_use; ++i) {
        base_vecs.push_back(base.get_vector_data(i));
    }

    std::vector<b2::VectorData> queries;
    std::vector<std::vector<b2::VectorID>> ground_truth;

    if (!opt.query_path.empty()) {
        b2::Dataset qds;
        if (!qds.load_from_file(opt.query_path)) {
            std::cerr << "Failed to load queries from " << opt.query_path << std::endl;
            return 1;
        }
        if (qds.dimension() != opt.dim) {
            std::cerr << "Query dimension mismatch: expected " << opt.dim
                      << ", got " << qds.dimension() << std::endl;
            return 1;
        }
        if (opt.num_queries == 0 || opt.num_queries > qds.size()) {
            opt.num_queries = qds.size();
        }
        queries.reserve(opt.num_queries);
        for (std::size_t i = 0; i < opt.num_queries; ++i) {
            queries.push_back(qds.get_vector_data(i));
        }

        if (!opt.groundtruth_path.empty()) {
            std::ifstream gin(opt.groundtruth_path, std::ios::binary);
            if (!gin) {
                std::cerr << "Failed to open groundtruth file " << opt.groundtruth_path << std::endl;
                return 1;
            }
            ground_truth.clear();
            ground_truth.reserve(opt.num_queries);
            for (std::size_t qi = 0; qi < opt.num_queries; ++qi) {
                std::int32_t gt_dim = 0;
                gin.read(reinterpret_cast<char*>(&gt_dim), sizeof(gt_dim));
                if (!gin) {
                    std::cerr << "Unexpected EOF while reading groundtruth at query " << qi << std::endl;
                    return 1;
                }
                if (gt_dim <= 0) {
                    std::cerr << "Invalid groundtruth dim " << gt_dim << " at query " << qi << std::endl;
                    return 1;
                }
                std::vector<std::int32_t> buf(static_cast<std::size_t>(gt_dim));
                gin.read(reinterpret_cast<char*>(buf.data()),
                         static_cast<std::streamsize>(gt_dim * sizeof(std::int32_t)));
                if (!gin) {
                    std::cerr << "Failed to read groundtruth ids at query " << qi << std::endl;
                    return 1;
                }
                std::vector<b2::VectorID> ids;
                ids.reserve(static_cast<std::size_t>(gt_dim));
                for (std::int32_t v : buf) {
                    if (v < 0) continue;
                    if (static_cast<std::size_t>(v) >= opt.num_base) continue;
                    ids.push_back(static_cast<b2::VectorID>(v));
                }
                ground_truth.push_back(std::move(ids));
            }
        } else {
            ground_truth = compute_ground_truth_from_base(base_vecs, queries, opt.k);
        }
    } else {
        // 2. Generate queries (independent synthetic set)
        queries.resize(opt.num_queries, b2::VectorData(opt.dim));
        {
            std::mt19937_64 rng(opt.seed);
            std::normal_distribution<float> dist(0.0f, 1.0f);
            for (std::size_t i = 0; i < opt.num_queries; ++i) {
                for (std::size_t d = 0; d < opt.dim; ++d) {
                    queries[i][d] = dist(rng);
                }
            }
        }

        // 3. Compute ground truth via brute-force
        ground_truth = compute_ground_truth_from_base(base_vecs, queries, opt.k);
    }

    // 4. ANN-in-SSD simulator mode: no explicit index build, use AnnInSsdModel
    if (opt.mode == "ann_ssd") {
        using namespace b2::simulator::ann_in_ssd;

        AnnInSsdConfig cfg;
        cfg.dataset_name = opt.dataset_name.empty() ? "synthetic_gaussian" : opt.dataset_name;
        cfg.dataset_path.clear();
        cfg.dimension = opt.dim;
        cfg.num_vectors = opt.num_base;

        cfg.placement_mode = opt.ann_placement_mode.empty() ? "hash_home" : opt.ann_placement_mode;
        cfg.vectors_per_block = opt.ann_vectors_per_block > 0 ? opt.ann_vectors_per_block : 128;
        cfg.portal_degree = opt.ann_portal_degree;
        cfg.neighbor_degree = 0;
        cfg.page_size_bytes = 0;
        cfg.code_type = opt.ann_code_type.empty() ? "raw" : opt.ann_code_type;

        cfg.hardware_level = opt.ann_hw_level.empty() ? "L0" : opt.ann_hw_level;
        cfg.num_channels = 0;
        cfg.queue_depth_per_channel = 0;
        cfg.base_read_latency_us = 0.0;
        cfg.internal_read_bandwidth_GBps = 0.0;
        cfg.controller_flops_GF = 0.0;
        cfg.per_block_unit_flops_GF = 0.0;

        cfg.k = opt.k;
        cfg.beam_width = 0;
        cfg.max_steps = opt.ann_max_steps;
        cfg.entry_block_strategy = "centroid_knn";
        cfg.termination = "fixed_steps";
        cfg.num_queries = opt.num_queries;
        cfg.concurrency = 1;
        cfg.workload_distribution = "uniform";
        cfg.seed = opt.seed;

        cfg.output_path.clear();
        cfg.record_per_query = false;
        cfg.record_per_block = false;
        cfg.simulation_mode = opt.ann_ssd_mode;

        std::vector<Query> sim_queries;
        sim_queries.resize(opt.num_queries);
        for (std::size_t i = 0; i < opt.num_queries; ++i) {
            sim_queries[i].id = static_cast<b2::VectorID>(i);
            sim_queries[i].values = queries[i];
            sim_queries[i].true_neighbors = ground_truth[i];
        }

        AnnInSsdModel model(cfg, base);
        auto results = model.search_batch(sim_queries);
        (void)results;
        const SimulationSummary& summary = model.summary();

        std::cout << "[ann_ssd] k=" << summary.k
                  << ", num_queries=" << summary.num_queries << std::endl;
        std::cout << "[ann_ssd] recall@" << summary.k << ": " << summary.recall_at_k << std::endl;
        std::cout << "[ann_ssd] QPS: " << summary.qps << std::endl;
        std::cout << "[ann_ssd] Latency us p50/p95/p99: "
                  << summary.latency_us_p50 << ", "
                  << summary.latency_us_p95 << ", "
                  << summary.latency_us_p99 << std::endl;
        std::cout << "[ann_ssd] Avg blocks/portal_steps/internal_reads/distances: "
                  << summary.avg_blocks_visited << " / "
                  << summary.avg_portal_steps << " / "
                  << summary.avg_internal_reads << " / "
                  << summary.avg_distances_computed << std::endl;
        std::cout << "[ann_ssd] Sim IO: num_reads=" << summary.io_stats.num_reads
                  << ", bytes_read=" << summary.io_stats.bytes_read << std::endl;
        std::cout << "[ann_ssd] Modeled SSD device time (us): "
                  << summary.device_time_us << std::endl;

        if (!opt.json_out.empty()) {
            model.write_json_log(opt.json_out);
        }

        return 0;
    }

    // 4. Build index (DRAM or tiered) and run queries
    std::vector<double> latencies_us;
    latencies_us.reserve(opt.num_queries);
    double recall_sum = 0.0;
    double build_s = 0.0;
    double search_s = 0.0;
    unsigned long long io_num_reads = 0;
    unsigned long long io_bytes_read = 0;
    double device_time_us = 0.0;

    std::vector<std::vector<b2::VectorID>> per_query_ids;
    const bool collect_neighbors = !opt.per_query_out.empty();
    if (collect_neighbors) {
        per_query_ids.resize(opt.num_queries);
    }

    b2::Timer total_timer;

    if (opt.mode == "tiered") {
        auto backing = std::make_shared<b2::MemoryBackend>();
        auto tiered = std::make_shared<b2::TieredBackend>(backing, opt.cache_capacity, opt.cache_policy);

        b2::simulator::SsdDeviceConfig dev_cfg;
        dev_cfg.num_channels = opt.ssd_num_channels;
        dev_cfg.queue_depth_per_channel = opt.ssd_queue_depth_per_channel;
        dev_cfg.base_read_latency_us = opt.ssd_base_read_latency_us;
        dev_cfg.internal_read_bandwidth_GBps = opt.ssd_internal_read_bandwidth_GBps;
        tiered->enable_device_model(dev_cfg);
        b2::TieredHNSW index(opt.dim, tiered, opt.M, opt.ef_construction, b2::DistanceMetric::L2);

        {
            b2::Timer t;
            if (opt.hnsw_build_threads <= 1) {
                index.build(base_vecs);
            } else {
                index.build_parallel(base_vecs, opt.hnsw_build_threads);
            }
            build_s = t.elapsed_s();
            std::cout << "Index build time (s): " << build_s << std::endl;
        }

        for (std::size_t i = 0; i < opt.num_queries; ++i) {
            b2::Timer qtimer;
            auto ids = index.search(queries[i].data(), opt.k, opt.ef_search);
            double q_s = qtimer.elapsed_s();
            double us = q_s * 1e6;
            latencies_us.push_back(us);
            recall_sum += b2::compute_recall_at_k(ground_truth[i], ids, opt.k);
            search_s += q_s;
            if (collect_neighbors) {
                per_query_ids[i] = std::move(ids);
            }
        }

        b2::IOStats s = tiered->get_stats();
        std::cout << "Tiered stats: num_reads=" << s.num_reads
                  << ", num_writes=" << s.num_writes
                  << ", bytes_read=" << s.bytes_read
                  << ", bytes_written=" << s.bytes_written << std::endl;
        std::cout << "Tiered cache: hits=" << tiered->cache_hits()
                  << ", misses=" << tiered->cache_misses() << std::endl;

        device_time_us = tiered->device_time_us();
        std::cout << "Tiered modeled SSD device time (us): " << device_time_us << std::endl;

        io_num_reads = static_cast<unsigned long long>(s.num_reads);
        io_bytes_read = static_cast<unsigned long long>(s.bytes_read);
    } else {
        b2::HNSW index(opt.dim, opt.M, opt.ef_construction, b2::DistanceMetric::L2);

        {
            b2::Timer t;
            if (opt.hnsw_build_threads <= 1) {
                index.build(base_vecs);
            } else {
                index.build_parallel(base_vecs, opt.hnsw_build_threads);
            }
            build_s = t.elapsed_s();
            std::cout << "Index build time (s): " << build_s << std::endl;
        }

        index.enable_search_stats(true);
        index.reset_search_stats();

        for (std::size_t i = 0; i < opt.num_queries; ++i) {
            b2::Timer qtimer;
            auto ids = index.search(queries[i].data(), opt.k, opt.ef_search);
            double q_s = qtimer.elapsed_s();
            double us = q_s * 1e6;
            latencies_us.push_back(us);
            recall_sum += b2::compute_recall_at_k(ground_truth[i], ids, opt.k);
            search_s += q_s;
            if (collect_neighbors) {
                per_query_ids[i] = std::move(ids);
            }
        }

        auto dist_count = index.search_distance_computations();
        std::cout << "HNSW search distance computations: " << dist_count << std::endl;
        if (search_s > 0.0 && opt.dim > 0 && dist_count > 0) {
            double flops_per_distance = 2.0 * static_cast<double>(opt.dim);
            double total_flops = flops_per_distance * static_cast<double>(dist_count);
            double gflops = (total_flops * 1e-9) / search_s;
            std::cout << "HNSW effective search GFLOP/s (2*dim flops per distance): "
                      << gflops << std::endl;
        }
    }

    double total_s = total_timer.elapsed_s();

    const double avg_recall = recall_sum / static_cast<double>(opt.num_queries);
    const double qps_total = static_cast<double>(opt.num_queries) / total_s;
    double qps_search = 0.0;
    double build_throughput = 0.0;

    if (search_s > 0.0) {
        qps_search = static_cast<double>(opt.num_queries) / search_s;
    }
    if (build_s > 0.0) {
        build_throughput = static_cast<double>(opt.num_base) / build_s;
    }

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

    std::cout << "Average recall@" << opt.k << ": " << avg_recall << std::endl;
    std::cout << "Total wall time (s, build+search): " << total_s << std::endl;
    std::cout << "Accumulated search time (s): " << search_s << std::endl;
    std::cout << "Total QPS (queries / total_time): " << qps_total << std::endl;
    std::cout << "Search-only QPS (queries / search_time): " << qps_search << std::endl;
    std::cout << "Build throughput (vectors/s): " << build_throughput << std::endl;
    std::cout << "Latency us p50/p95/p99: " << p50 << ", " << p95 << ", " << p99 << std::endl;

    if (collect_neighbors && !opt.per_query_out.empty()) {
        std::ofstream pout(opt.per_query_out);
        if (!pout) {
            std::cerr << "Failed to open per-query output file " << opt.per_query_out << std::endl;
        } else {
            for (const auto& nbrs : per_query_ids) {
                for (std::size_t j = 0; j < nbrs.size(); ++j) {
                    if (j > 0) {
                        pout << ' ';
                    }
                    pout << nbrs[j];
                }
                pout << '\n';
            }
        }
    }

    if (!opt.json_out.empty()) {
        write_json_log_baseline(opt, opt.mode, avg_recall, qps_total,
                                qps_search, p50, p95, p99, build_s, search_s,
                                io_num_reads, io_bytes_read, device_time_us);
    }

    return 0;
}
