#include "tiered_hnsw.hpp"

#include "../core/vector.hpp"
#include "../ann/hnsw.hpp"
#include "../storage/tiered_backend.hpp"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <limits>
#include <queue>
#include <random>
#include <unordered_set>
#include <thread>
#include <atomic>

#include <iostream>
#include "../utils/timer.hpp"

namespace b2 {

namespace {

using DistId = std::pair<float, VectorID>; // (distance, id)

struct DistIdMin {
    bool operator()(const DistId& a, const DistId& b) const {
        return a.first > b.first; // smaller distance = higher priority
    }
};

} // namespace

TieredHNSW::TieredHNSW(std::size_t dim,
                       std::shared_ptr<StorageBackend> storage,
                       std::size_t M,
                       std::size_t ef_construction,
                       DistanceMetric metric)
    : dim_(dim),
      M_(M),
      ef_construction_(ef_construction),
      metric_(metric),
      storage_(std::move(storage)),
      nodes_(),
      entry_point_(std::numeric_limits<VectorID>::max()),
      max_layer_(0),
      num_vectors_(0) {}

void TieredHNSW::reset_for_build(const std::vector<VectorData>& data) {
    nodes_.clear();
    nodes_.resize(data.size());
    entry_point_ = std::numeric_limits<VectorID>::max();
    max_layer_ = 0;
    num_vectors_ = data.size();
    vectors_ = data;

    node_mutexes_.reset();
    if (!nodes_.empty()) {
        node_mutexes_ = std::make_unique<std::mutex[]>(nodes_.size());
    }
}

std::size_t TieredHNSW::assign_layer() {
    static thread_local std::mt19937_64 rng(42);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);

    std::size_t level = 0;
    const float p = 1.0f / 2.0f;
    while (dist(rng) < p) {
        ++level;
    }
    return level;
}

bool TieredHNSW::load_vector(VectorID id, VectorData& out) const {
    if (storage_) {
        if (storage_->read_node(id, out)) {
            return true;
        }
    }

    const std::size_t idx = static_cast<std::size_t>(id);
    if (!vectors_.empty() && idx < vectors_.size()) {
        out = vectors_[idx];
        return true;
    }

    return false;
}

std::vector<VectorID> TieredHNSW::select_neighbors_heuristic(
    const std::vector<std::pair<VectorID, float>>& candidates,
    std::size_t M,
    const VectorData& query) {
    (void)query; // currently unused; kept for potential future refinements

    std::vector<VectorID> result;
    if (candidates.empty() || M == 0) {
        return result;
    }

    std::vector<std::pair<VectorID, float>> sorted = candidates;
    std::sort(sorted.begin(), sorted.end(),
              [](const std::pair<VectorID, float>& a, const std::pair<VectorID, float>& b) {
                  return a.second < b.second;
              });

    const std::size_t max_keep = std::min<std::size_t>(M, sorted.size());
    result.reserve(max_keep);

    std::unordered_map<VectorID, VectorData> cache;
    cache.reserve(sorted.size());

    auto get_vec = [&](VectorID vid) -> const VectorData& {
        auto it = cache.find(vid);
        if (it != cache.end()) {
            return it->second;
        }
        VectorData v;
        if (!load_vector(vid, v)) {
            v.assign(dim_, 0.0f);
        }
        auto inserted = cache.emplace(vid, std::move(v));
        return inserted.first->second;
    };

    for (const auto& cand : sorted) {
        const VectorID cid = cand.first;
        const float dist_q_c = cand.second;

        bool good = true;
        const VectorData& cv = get_vec(cid);
        for (VectorID sid : result) {
            const VectorData& sv = get_vec(sid);
            float dist_s_c = compute_distance(sv.data(), cv.data(), dim_, metric_);
            if (dist_s_c < dist_q_c) {
                good = false;
                break;
            }
        }

        if (good) {
            result.push_back(cid);
            if (result.size() >= max_keep) {
                break;
            }
        }
    }

    if (result.size() < max_keep) {
        for (const auto& cand : sorted) {
            if (result.size() >= max_keep) {
                break;
            }
            VectorID cid = cand.first;
            if (std::find(result.begin(), result.end(), cid) == result.end()) {
                result.push_back(cid);
            }
        }
    }

    return result;
}

void TieredHNSW::build(const std::vector<VectorData>& data) {
    b2::Timer total_timer;
    if (storage_) {
        storage_->reset_stats();
    }

    vectors_ = data;

    HNSW hnsw(dim_, M_, ef_construction_, metric_);
    b2::Timer hnsw_timer;
    hnsw.build(data);
    double hnsw_elapsed = hnsw_timer.elapsed_s();
    std::cout << "[TieredHNSW::build] inner HNSW::build time for "
              << data.size() << " vectors: "
              << hnsw_elapsed << " s" << std::endl;

    std::vector<std::vector<std::vector<VectorID>>> neighbors;
    VectorID entry_point = std::numeric_limits<VectorID>::max();
    std::size_t max_layer = 0;
    hnsw.export_graph(neighbors, entry_point, max_layer);

    nodes_.clear();
    nodes_.resize(neighbors.size());
    for (std::size_t i = 0; i < neighbors.size(); ++i) {
        nodes_[i].id = static_cast<VectorID>(i);
        nodes_[i].neighbors = std::move(neighbors[i]);
    }

    entry_point_ = entry_point;
    max_layer_ = max_layer;
    num_vectors_ = data.size();

    node_mutexes_.reset();
    if (!nodes_.empty()) {
        node_mutexes_ = std::make_unique<std::mutex[]>(nodes_.size());
    }

    if (storage_) {
        for (std::size_t i = 0; i < data.size(); ++i) {
            storage_->write_node(static_cast<VectorID>(i), data[i]);
        }
    }

    double total_elapsed = total_timer.elapsed_s();
    std::cout << "[TieredHNSW::build] total TieredHNSW::build time for "
              << data.size() << " vectors: "
              << total_elapsed << " s" << std::endl;
}

void TieredHNSW::build_parallel(const std::vector<VectorData>& data,
                                std::size_t num_threads) {
    if (num_threads <= 1) {
        build(data);
        return;
    }

    b2::Timer total_timer;

    if (storage_) {
        storage_->reset_stats();
    }

    vectors_ = data;

    HNSW hnsw(dim_, M_, ef_construction_, metric_);
    b2::Timer hnsw_timer;
    hnsw.build_parallel(data, num_threads);
    double hnsw_elapsed = hnsw_timer.elapsed_s();
    std::cout << "[TieredHNSW::build_parallel] inner HNSW::build_parallel time for "
              << data.size() << " vectors with "
              << num_threads << " threads: "
              << hnsw_elapsed << " s" << std::endl;

    std::vector<std::vector<std::vector<VectorID>>> neighbors;
    VectorID entry_point = std::numeric_limits<VectorID>::max();
    std::size_t max_layer = 0;
    hnsw.export_graph(neighbors, entry_point, max_layer);

    nodes_.clear();
    nodes_.resize(neighbors.size());
    for (std::size_t i = 0; i < neighbors.size(); ++i) {
        nodes_[i].id = static_cast<VectorID>(i);
        nodes_[i].neighbors = std::move(neighbors[i]);
    }

    entry_point_ = entry_point;
    max_layer_ = max_layer;
    num_vectors_ = data.size();

    node_mutexes_.reset();
    if (!nodes_.empty()) {
        node_mutexes_ = std::make_unique<std::mutex[]>(nodes_.size());
    }

    if (storage_) {
        for (std::size_t i = 0; i < data.size(); ++i) {
            storage_->write_node(static_cast<VectorID>(i), data[i]);
        }
    }

    double total_elapsed = total_timer.elapsed_s();
    std::cout << "[TieredHNSW::build_parallel] total TieredHNSW::build_parallel time for "
              << data.size() << " vectors with "
              << num_threads << " threads: "
              << total_elapsed << " s" << std::endl;
}

void TieredHNSW::insert_node(VectorID id, const VectorData& vec) {
    const std::size_t level = assign_layer();

    if (nodes_.size() <= static_cast<std::size_t>(id)) {
        nodes_.resize(static_cast<std::size_t>(id) + 1);
    }
    Node& node = nodes_[static_cast<std::size_t>(id)];
    node.id = id;
    if (node.neighbors.size() < level + 1) {
        node.neighbors.resize(level + 1);
    }

    if (entry_point_ == std::numeric_limits<VectorID>::max()) {
        entry_point_ = id;
        max_layer_ = level;
        return;
    }

    VectorID ep = entry_point_;

    // Greedy search on upper layers (ef = 1)
    if (max_layer_ > level) {
        for (std::size_t l = max_layer_; l > level; --l) {
            auto res = search_layer(vec.data(), ep, 1, l);
            if (!res.empty()) {
                ep = res.front().first;
            }
        }
    }

    const std::size_t top_layer = std::min(max_layer_, level);
    for (int l = static_cast<int>(top_layer); l >= 0; --l) {
        auto candidates = search_layer(vec.data(), ep, ef_construction_, static_cast<std::size_t>(l));

        const std::size_t layer_M = (l == 0) ? (M_ * 2) : M_;
        std::vector<VectorID> neigh_ids =
            select_neighbors_heuristic(candidates, layer_M, vec);

        if (node.neighbors.size() <= static_cast<std::size_t>(l)) {
            node.neighbors.resize(static_cast<std::size_t>(l) + 1);
        }

        for (VectorID neighbor_id : neigh_ids) {
            node.neighbors[static_cast<std::size_t>(l)].push_back(neighbor_id);

            Node& nb_node = nodes_[static_cast<std::size_t>(neighbor_id)];
            if (nb_node.neighbors.size() <= static_cast<std::size_t>(l)) {
                nb_node.neighbors.resize(static_cast<std::size_t>(l) + 1);
            }
            auto& nb_list = nb_node.neighbors[static_cast<std::size_t>(l)];
            nb_list.push_back(id);

            const std::size_t nb_layer_M = (l == 0) ? (M_ * 2) : M_;
            if (nb_list.size() > nb_layer_M) {
                VectorData vref;
                if (!load_vector(neighbor_id, vref)) {
                    vref.assign(dim_, 0.0f);
                }

                std::vector<std::pair<VectorID, float>> cand_nb;
                cand_nb.reserve(nb_list.size());
                for (VectorID nid : nb_list) {
                    VectorData vv;
                    if (!load_vector(nid, vv)) {
                        vv.assign(dim_, 0.0f);
                    }
                    float d = compute_distance(vref.data(), vv.data(), dim_, metric_);
                    cand_nb.emplace_back(nid, d);
                }

                std::vector<VectorID> pruned =
                    select_neighbors_heuristic(cand_nb, nb_layer_M, vref);
                nb_list.assign(pruned.begin(), pruned.end());
            }
        }
    }

    if (level > max_layer_) {
        max_layer_ = level;
        entry_point_ = id;
    }
}

void TieredHNSW::insert_node_parallel(
    VectorID id,
    const VectorData& vec,
    std::vector<std::uint32_t>& visited,
    std::uint32_t& visited_epoch) {
    const std::size_t level = assign_layer();

    // nodes_ and node_mutexes_ are sized in reset_for_build; no further resize here.
    {
        std::lock_guard<std::mutex> lock(node_mutexes_[static_cast<std::size_t>(id)]);
        Node& node = nodes_[static_cast<std::size_t>(id)];
        node.id = id;
        if (node.neighbors.size() < level + 1) {
            node.neighbors.resize(level + 1);
        }
    }

    VectorID ep;
    std::size_t cur_max_layer;
    {
        std::lock_guard<std::mutex> lock(global_mutex_);
        ep = entry_point_;
        cur_max_layer = max_layer_;
    }

    if (ep == std::numeric_limits<VectorID>::max()) {
        ep = id;
        cur_max_layer = level;
        {
            std::lock_guard<std::mutex> lock(global_mutex_);
            entry_point_ = id;
            max_layer_ = level;
        }
        return;
    }

    // Greedy search on upper layers (ef = 1)
    if (cur_max_layer > level) {
        for (std::size_t l = cur_max_layer; l > level; --l) {
            auto res = search_layer_parallel(vec.data(), ep, 1, l,
                                             visited, visited_epoch);
            if (!res.empty()) {
                ep = res.front().first;
            }
        }
    }

    // Search and connect on layers [min(max_layer_, level) .. 0]
    const std::size_t top_layer = std::min(cur_max_layer, level);
    for (int l = static_cast<int>(top_layer); l >= 0; --l) {
        auto candidates = search_layer_parallel(
            vec.data(), ep, ef_construction_, static_cast<std::size_t>(l),
            visited, visited_epoch);

        const std::size_t layer_M = (l == 0) ? (M_ * 2) : M_;
        std::vector<VectorID> neigh_ids =
            select_neighbors_heuristic(candidates, layer_M, vec);

        // Update this node's neighbors at layer l under its mutex
        {
            std::lock_guard<std::mutex> lock(node_mutexes_[static_cast<std::size_t>(id)]);
            Node& node = nodes_[static_cast<std::size_t>(id)];
            if (node.neighbors.size() <= static_cast<std::size_t>(l)) {
                node.neighbors.resize(static_cast<std::size_t>(l) + 1);
            }
            auto& self_list = node.neighbors[static_cast<std::size_t>(l)];
            for (VectorID neighbor_id : neigh_ids) {
                self_list.push_back(neighbor_id);
            }
        }

        // Symmetric updates on neighbor nodes, one mutex at a time
        for (VectorID neighbor_id : neigh_ids) {
            std::lock_guard<std::mutex> lock_nb(
                node_mutexes_[static_cast<std::size_t>(neighbor_id)]);
            Node& nb_node = nodes_[static_cast<std::size_t>(neighbor_id)];
            if (nb_node.neighbors.size() <= static_cast<std::size_t>(l)) {
                nb_node.neighbors.resize(static_cast<std::size_t>(l) + 1);
            }
            auto& nb_list = nb_node.neighbors[static_cast<std::size_t>(l)];
            nb_list.push_back(id);

            const std::size_t nb_layer_M = (l == 0) ? (M_ * 2) : M_;
            if (nb_list.size() > nb_layer_M) {
                VectorData vref;
                if (!load_vector(neighbor_id, vref)) {
                    vref.assign(dim_, 0.0f);
                }

                std::vector<std::pair<VectorID, float>> cand_nb;
                cand_nb.reserve(nb_list.size());
                for (VectorID nid : nb_list) {
                    VectorData vv;
                    if (!load_vector(nid, vv)) {
                        vv.assign(dim_, 0.0f);
                    }
                    float d = compute_distance(vref.data(), vv.data(), dim_, metric_);
                    cand_nb.emplace_back(nid, d);
                }

                std::vector<VectorID> pruned =
                    select_neighbors_heuristic(cand_nb, nb_layer_M, vref);
                nb_list.assign(pruned.begin(), pruned.end());
            }
        }
    }

    // If this node has the highest layer so far, make it the new entry point
    if (level > cur_max_layer) {
        std::lock_guard<std::mutex> lock(global_mutex_);
        if (level > max_layer_) {
            max_layer_ = level;
            entry_point_ = id;
        }
    }
}

std::vector<std::pair<VectorID, float>> TieredHNSW::search_layer(
    const float* query,
    VectorID entry_point,
    std::size_t ef,
    std::size_t layer) {
    std::vector<std::pair<VectorID, float>> empty_result;
    if (num_vectors_ == 0 || entry_point == std::numeric_limits<VectorID>::max()) {
        return empty_result;
    }

    std::priority_queue<DistId, std::vector<DistId>, DistIdMin> candidate_queue;
    std::priority_queue<DistId> top_candidates;

    std::unordered_set<VectorID> visited;
    visited.reserve(num_vectors_);

    VectorData entry_vec;
    if (!load_vector(entry_point, entry_vec)) {
        return empty_result;
    }
    const float entry_dist = compute_distance(query, entry_vec.data(), dim_, metric_);
    candidate_queue.emplace(entry_dist, entry_point);
    top_candidates.emplace(entry_dist, entry_point);
    visited.insert(entry_point);

    while (!candidate_queue.empty()) {
        const DistId curr = candidate_queue.top();
        const float lower_bound = top_candidates.top().first;
        if (curr.first > lower_bound) {
            break;
        }
        candidate_queue.pop();
        const VectorID v = curr.second;

        const Node& node = nodes_[static_cast<std::size_t>(v)];
        if (layer >= node.neighbors.size()) {
            continue;
        }

        const auto& nbrs = node.neighbors[layer];
        for (VectorID nb : nbrs) {
            if (!visited.insert(nb).second) {
                continue;
            }
            VectorData nb_vec;
            if (!load_vector(nb, nb_vec)) {
                continue;
            }
            const float d = compute_distance(query, nb_vec.data(), dim_, metric_);

            if (top_candidates.size() < ef || d < top_candidates.top().first) {
                candidate_queue.emplace(d, nb);
                top_candidates.emplace(d, nb);
                if (top_candidates.size() > ef) {
                    top_candidates.pop();
                }
            }
        }
    }

    std::vector<std::pair<VectorID, float>> result;
    result.reserve(top_candidates.size());
    while (!top_candidates.empty()) {
        const DistId di = top_candidates.top();
        top_candidates.pop();
        result.emplace_back(di.second, di.first);
    }

    std::sort(result.begin(), result.end(),
              [](const std::pair<VectorID, float>& a, const std::pair<VectorID, float>& b) {
                  return a.second < b.second;
              });
    return result;
}

std::vector<std::pair<VectorID, float>> TieredHNSW::search_layer_parallel(
    const float* query,
    VectorID entry_point,
    std::size_t ef,
    std::size_t layer,
    std::vector<std::uint32_t>& visited,
    std::uint32_t& visited_epoch) {
    std::vector<std::pair<VectorID, float>> empty_result;
    if (num_vectors_ == 0 || entry_point == std::numeric_limits<VectorID>::max()) {
        return empty_result;
    }

    std::priority_queue<DistId, std::vector<DistId>, DistIdMin> candidate_queue;
    std::priority_queue<DistId> top_candidates;

    if (visited.size() < num_vectors_) {
        visited.assign(num_vectors_, 0);
    }
    ++visited_epoch;
    if (visited_epoch == 0) {
        std::fill(visited.begin(), visited.end(), 0);
        ++visited_epoch;
    }

    auto mark_visited = [&visited, &visited_epoch](VectorID id) {
        visited[static_cast<std::size_t>(id)] = visited_epoch;
    };
    auto is_visited = [&visited, &visited_epoch](VectorID id) {
        return visited[static_cast<std::size_t>(id)] == visited_epoch;
    };

    VectorData entry_vec;
    if (!load_vector(entry_point, entry_vec)) {
        return empty_result;
    }
    const float entry_dist = compute_distance(query, entry_vec.data(), dim_, metric_);
    candidate_queue.emplace(entry_dist, entry_point);
    top_candidates.emplace(entry_dist, entry_point);
    mark_visited(entry_point);

    while (!candidate_queue.empty()) {
        const DistId curr = candidate_queue.top();
        const float lower_bound = top_candidates.top().first;
        if (curr.first > lower_bound) {
            break;
        }
        candidate_queue.pop();
        const VectorID v = curr.second;

        const Node& node = nodes_[static_cast<std::size_t>(v)];
        if (layer >= node.neighbors.size()) {
            continue;
        }

        {
            std::lock_guard<std::mutex> lock(node_mutexes_[static_cast<std::size_t>(v)]);
            const auto& nbrs = node.neighbors[layer];
            for (VectorID nb : nbrs) {
                if (is_visited(nb)) {
                    continue;
                }
                mark_visited(nb);

                VectorData nb_vec;
                if (!load_vector(nb, nb_vec)) {
                    continue;
                }
                const float d = compute_distance(query, nb_vec.data(), dim_, metric_);

                if (top_candidates.size() < ef || d < top_candidates.top().first) {
                    candidate_queue.emplace(d, nb);
                    top_candidates.emplace(d, nb);
                    if (top_candidates.size() > ef) {
                        top_candidates.pop();
                    }
                }
            }
        }
    }

    std::vector<std::pair<VectorID, float>> result;
    result.reserve(top_candidates.size());
    while (!top_candidates.empty()) {
        const DistId di = top_candidates.top();
        top_candidates.pop();
        result.emplace_back(di.second, di.first);
    }

    std::sort(result.begin(), result.end(),
              [](const std::pair<VectorID, float>& a, const std::pair<VectorID, float>& b) {
                  return a.second < b.second;
              });
    return result;
}

std::vector<VectorID> TieredHNSW::search(const float* query,
                                         std::size_t k,
                                         std::size_t ef_search) {
    std::vector<VectorID> empty;
    if (num_vectors_ == 0 || entry_point_ == std::numeric_limits<VectorID>::max()) {
        return empty;
    }

    VectorID ep = entry_point_;

    for (int l = static_cast<int>(max_layer_); l > 0; --l) {
        auto res = search_layer(query, ep, 1, static_cast<std::size_t>(l));
        if (!res.empty()) {
            ep = res.front().first;
        }
    }

    auto res0 = search_layer(query, ep, ef_search, 0);
    if (res0.empty()) {
        return empty;
    }

    const std::size_t out_k = std::min<std::size_t>(k, res0.size());
    std::vector<VectorID> ids;
    ids.reserve(out_k);
    for (std::size_t i = 0; i < out_k; ++i) {
        ids.push_back(res0[i].first);
    }
    return ids;
}

bool TieredHNSW::save(const std::string& filepath) const {
    // For now, only persist the graph structure; vector data is assumed to be
    // managed by the underlying StorageBackend (e.g., file-backed).
    std::ofstream out(filepath, std::ios::binary);
    if (!out) {
        return false;
    }

    std::uint64_t dim = static_cast<std::uint64_t>(dim_);
    std::uint64_t M = static_cast<std::uint64_t>(M_);
    std::uint64_t efc = static_cast<std::uint64_t>(ef_construction_);
    std::int32_t metric_val = static_cast<std::int32_t>(metric_);
    std::uint64_t entry = static_cast<std::uint64_t>(entry_point_);
    std::uint64_t max_l = static_cast<std::uint64_t>(max_layer_);
    std::uint64_t nvec = static_cast<std::uint64_t>(num_vectors_);

    out.write(reinterpret_cast<const char*>(&dim), sizeof(dim));
    out.write(reinterpret_cast<const char*>(&M), sizeof(M));
    out.write(reinterpret_cast<const char*>(&efc), sizeof(efc));
    out.write(reinterpret_cast<const char*>(&metric_val), sizeof(metric_val));
    out.write(reinterpret_cast<const char*>(&entry), sizeof(entry));
    out.write(reinterpret_cast<const char*>(&max_l), sizeof(max_l));
    out.write(reinterpret_cast<const char*>(&nvec), sizeof(nvec));

    const std::uint64_t num_nodes = static_cast<std::uint64_t>(nodes_.size());
    out.write(reinterpret_cast<const char*>(&num_nodes), sizeof(num_nodes));
    for (const auto& n : nodes_) {
        std::uint64_t id_u64 = static_cast<std::uint64_t>(n.id);
        std::uint64_t num_layers = static_cast<std::uint64_t>(n.neighbors.size());
        out.write(reinterpret_cast<const char*>(&id_u64), sizeof(id_u64));
        out.write(reinterpret_cast<const char*>(&num_layers), sizeof(num_layers));
        for (const auto& layer_nbrs : n.neighbors) {
            std::uint64_t deg = static_cast<std::uint64_t>(layer_nbrs.size());
            out.write(reinterpret_cast<const char*>(&deg), sizeof(deg));
            for (VectorID nid : layer_nbrs) {
                std::uint64_t nid_u64 = static_cast<std::uint64_t>(nid);
                out.write(reinterpret_cast<const char*>(&nid_u64), sizeof(nid_u64));
            }
        }
    }

    return static_cast<bool>(out);
}

bool TieredHNSW::load(const std::string& filepath) {
    std::ifstream in(filepath, std::ios::binary);
    if (!in) {
        return false;
    }

    std::uint64_t dim = 0, M = 0, efc = 0, entry = 0, max_l = 0, nvec = 0;
    std::int32_t metric_val = 0;

    in.read(reinterpret_cast<char*>(&dim), sizeof(dim));
    in.read(reinterpret_cast<char*>(&M), sizeof(M));
    in.read(reinterpret_cast<char*>(&efc), sizeof(efc));
    in.read(reinterpret_cast<char*>(&metric_val), sizeof(metric_val));
    in.read(reinterpret_cast<char*>(&entry), sizeof(entry));
    in.read(reinterpret_cast<char*>(&max_l), sizeof(max_l));
    in.read(reinterpret_cast<char*>(&nvec), sizeof(nvec));
    if (!in) {
        return false;
    }

    dim_ = static_cast<std::size_t>(dim);
    M_ = static_cast<std::size_t>(M);
    ef_construction_ = static_cast<std::size_t>(efc);
    metric_ = static_cast<DistanceMetric>(metric_val);
    entry_point_ = static_cast<VectorID>(entry);
    max_layer_ = static_cast<std::size_t>(max_l);
    num_vectors_ = static_cast<std::size_t>(nvec);

    std::uint64_t num_nodes = 0;
    in.read(reinterpret_cast<char*>(&num_nodes), sizeof(num_nodes));
    if (!in) {
        return false;
    }

    nodes_.clear();
    nodes_.resize(static_cast<std::size_t>(num_nodes));
    for (auto& n : nodes_) {
        std::uint64_t id_u64 = 0;
        std::uint64_t num_layers = 0;
        in.read(reinterpret_cast<char*>(&id_u64), sizeof(id_u64));
        in.read(reinterpret_cast<char*>(&num_layers), sizeof(num_layers));
        if (!in) {
            return false;
        }
        n.id = static_cast<VectorID>(id_u64);
        n.neighbors.clear();
        n.neighbors.resize(static_cast<std::size_t>(num_layers));
        for (auto& layer_nbrs : n.neighbors) {
            std::uint64_t deg = 0;
            in.read(reinterpret_cast<char*>(&deg), sizeof(deg));
            if (!in) {
                return false;
            }
            layer_nbrs.resize(static_cast<std::size_t>(deg));
            for (std::uint64_t i = 0; i < deg; ++i) {
                std::uint64_t nid_u64 = 0;
                in.read(reinterpret_cast<char*>(&nid_u64), sizeof(nid_u64));
                if (!in) {
                    return false;
                }
                layer_nbrs[static_cast<std::size_t>(i)] = static_cast<VectorID>(nid_u64);
            }
        }
    }

    return true;
}

} // namespace b2
