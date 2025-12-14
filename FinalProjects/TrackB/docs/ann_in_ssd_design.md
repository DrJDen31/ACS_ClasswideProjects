# ANN-in-SSD Graph-in-Flash Design

## 1. Goals and Scope

This document specifies the design of the **ANN-in-SSD** simulator used in B2. The goal is to model a future SSD-like device that:

- Embeds a **graph-based ANN index directly into flash pages** ("graph-in-flash").
- Requires **no host DRAM** for the index itself (only small controller DRAM), though the simulator is free to use DRAM internally.
- Exposes many **configurable knobs** (geometry, graph parameters, hardware levels, workload, and logging).
- Outputs **rich JSON logs** for analysis and plotting.

The simulator is not required to be bit-accurate to hardware; it should approximate **latency, throughput, and resource usage** (I/O, compute) under different assumptions and algorithms.

Default benchmark standards:

- Vector dimension: **d = 128** (SIFT-like), with support for other dims.
- Primary quality metric: **recall@10**.
- Workloads emphasize **high concurrency** to match AIML/LLM serving scenarios.

---

## 2. Flash Block / Page Format

Each **4 KB flash page** is treated as a logical **block** that acts both as:

- A **bucket of vectors** (local neighborhood in embedding space).
- A **node in a small-world graph** (connected to other blocks via portal edges and per-vector neighbors).

### 2.1 Block Layout (Conceptual)

A 4 KB block is split into a fixed-size **header** and an **entry array**:

- **Header (128–512 B)**

  - `uint16 dim` – logical vector dimension.
  - `uint8 metric` – distance metric (L2 / inner product / cosine).
  - `uint8 code_type` – representation (e.g., PQ code, fp16, int8).
  - `uint16 K` – number of vectors in this block (or max capacity).
  - `uint8 num_portals = P` – number of portal neighbors in block graph.
  - `uint32 portal_neighbors[P]` – block IDs for long-range / inter-region edges.
  - `Centroid / BlockSummary` – compressed centroid or code summarizing this block’s region.

- **Entry array (~3.5 KB)**
  - `Entry i` contains:
    - `VectorCode` – compressed vector representation.
    - `neighbor_block_ids[M]` – up to `M` neighboring blocks that host nearby vectors.

Configurable parameters (knobs):

- `page_size_bytes` (default 4096).
- `vectors_per_block = K` (e.g., 64–150).
- `portal_degree = P` (e.g., 4–8).
- `neighbor_degree = M` (e.g., 1–4).
- `code_type` and `code_size_bytes`.

The simulator does **not** have to pack bytes exactly; it only needs to:

- Respect the capacity constraint (`K * code_size` + metadata ≤ `page_size_bytes`).
- Track `K`, `P`, and `M` for cost modeling and logging.

### 2.2 Placement Policies

Two main policies are supported:

- **Hash-based home placement (default)**

  - `block_id = hash(vector_id) % num_blocks`.
  - Ensures balanced distribution and simple addressing.
  - No DRAM-resident posting lists.

- **Locality-aware placement (optional)**
  - Vectors are first clustered (e.g., by k-means or graph-based clustering) and then assigned to blocks.
  - Blocks then represent tighter local neighborhoods.

The simulator will expose a `placement_mode` config knob with at least:

- `"hash_home"` – default, simple and scalable.
- `"locality_aware"` – enables an offline cluster-and-pack phase.

---

## 3. SSD Controller Metadata (DRAM-Resident)

The **controller** maintains a small amount of DRAM-resident metadata to navigate the graph and schedule work. In the simulator, these are regular in-memory data structures.

Core structures:

- `BlockDirectory[b]` – maps `block_id` → physical/logical address.
- `BlockCentroids[b]` – centroid or coarse code per block (16–32B each).
- `BlockGraph[b].portals` – portal neighbor lists for block-level graph.
- `CollectionMetadata` – global parameters (dim, metric, code_type, K, P, M, dataset size).
- `HardwareConfig` – parameters describing L0–L3 (latency, bandwidth, compute rates, channels, queue depths).
- `QueryState` / `QueryBuffers` – per-query structures for beam search, candidate queues, partial results.

We do **not** enforce a strict DRAM cap; instead, we track **metadata size** in bytes and log it as a metric.

---

## 4. Query Execution Model (ANN_SEARCH)

Query execution is modeled as a **graph search** over blocks and vectors, with cost accounting for:

- Block reads (internal flash reads).
- Vector decode + distance computations.
- Controller scheduling and merging.

### 4.1 High-Level Flow

1. **Host issues ANN_SEARCH**

   - Inputs: query vector `q`, desired `k`, optional hints (e.g., entry points).
   - In practice, this could correspond to a custom NVMe command; in the simulator we just call an API.

2. **Initialization**

   - Controller normalizes or preprocesses `q` as needed.
   - Controller chooses **entry blocks**:
     - Fixed set of well-distributed portals, or
     - Top few centroids closest to `q`.

3. **Beam / Greedy Graph Search**

   - Maintain a **frontier** of candidate blocks and best-so-far results.
   - At each step:
     - Pop one or more blocks from the frontier (depending on beam width and hardware level).
     - Dispatch work to flash channels (modeled, not physically executed).

4. **Block Processing (per block)**

   - Read block header + entries (modeled as internal flash read).
   - Decode `VectorCodes` and compute distances to `q`.
   - Update local top-k candidates.
   - Use:
     - `portal_neighbors` to propose **long-range jumps**.
     - `neighbor_block_ids` of promising entries for **local refinement**.

5. **Frontier / Result Update**

   - Merge new candidates into the global top-k heap.
   - Add new blocks to frontier if they may improve the result.
   - Terminate when:
     - Max steps or visited-block budget is reached, or
     - No frontier block can significantly improve the current top-k (heuristic).

6. **Return Results**
   - Final top-k IDs + scores.
   - Per-query stats (blocks visited, portals traversed, estimated latency, etc.).

### 4.2 Search Knobs

Search-related config options:

- `k` – number of neighbors (default 10).
- `beam_width` – number of blocks considered per step.
- `max_steps` – upper bound on search iterations.
- `entry_block_strategy` – how to choose starting blocks.
- `termination_heuristic` – simple or advanced early-stop logic.
- `concurrency` – number of concurrent queries.

---

## 5. Construction / Initialization

Construction can use DRAM freely (offline), then serialize into block structures for simulation.

### 5.1 Phase 0 – Bulk Placement

- Assign each vector a **home block** using:
  - Hash-based placement, or
  - Locality-aware clustering.
- Pack `VectorCodes` into blocks while respecting capacity `K`.

### 5.2 Phase 1 – Block Summaries

- Compute centroids or coarse codes per block.
- Store summaries in both:
  - Block headers.
  - Controller’s `BlockCentroids` array.

### 5.3 Phase 2 – Block Graph (Portal Neighbors)

- Build a graph over **block centroids**:
  - HNSW-like or k-NN graph construction on centroids in DRAM.
  - Sparsify to `P` portal neighbors per block.
- Write portal neighbors into block headers and `BlockGraph`.

### 5.4 Phase 3 – Per-Vector Neighbor Edges (Optional)

- For each vector, search within a limited radius (nearby centroids / blocks).
- Pick up to `M` neighbor blocks that contain close vectors.
- Store their `block_id`s in the entry metadata.

The simulator tracks build-time statistics (optional) but **focuses on search-time performance**.

---

## 6. Hardware Levels and Cost Model

We define four **hardware levels** (L0–L3) with increasing compute-in-SSD capability.

### 6.1 Common Device Parameters

Configurable knobs (device-level):

- `num_channels` – flash channels.
- `queue_depth_per_channel` – max outstanding commands.
- `base_read_latency_us` – fixed overhead per internal block read.
- `internal_read_bandwidth_GBps` – within-SSD bandwidth.
- `controller_flops_GF` – controller compute rate for distance ops.
- `per_block_unit_flops_GF` – compute per block-level unit (L2/L3).
- `pcie_bandwidth_GBps` – for comparison with DRAM/SSD profiles.

### 6.2 Levels

- **L0 – Controller-only**

  - All distance computation done on controller CPU (modeled GFLOP/s).
  - Block read cost: `T_read = base_read_latency + size / internal_read_bandwidth`.
  - Distance cost: `T_compute ≈ (#distances * dim * 2 flops) / controller_flops`.

- **L1 – Controller with SIMD / vector engine**

  - Higher `controller_flops` and/or vectorized distance primitives.
  - Same cost model, different parameters.

- **L2 – Per-Block Compute Units**

  - Each channel has lightweight compute near data.
  - For a block, most of `T_compute` is charged to `per_block_unit_flops_GF`.
  - Controller mostly merges top-k lists; its compute cost is reduced.

- **L3 – Fully Pipelined Multi-Channel Graph Search**
  - Multiple blocks processed in parallel per step.
  - Block reads and compute are overlapped; latency dominated by longest critical path.
  - Simulator models:
    - Channel utilization.
    - Effective per-query latency at given concurrency.

### 6.3 Per-Query Time Estimation

For each query, the simulator builds a **timeline** of events:

- Enqueue block reads to channels (respecting `queue_depth_per_channel`).
- For each block:
  - Add `T_read` and `T_compute` to the channel’s schedule.
- Controller merges candidate lists and manages the frontier.

The final **estimated latency** per query is the completion time of its last event. QPS at concurrency `C` is derived from aggregate simulated time.

---

## 7. Simulator Architecture

The ANN-in-SSD simulator will live in `src/simulator/ann_in_ssd_model.{hpp,cpp}` and integrate with the existing benchmarking harness.

### 7.1 Core Responsibilities

- Load or construct a graph-in-flash representation from an existing dataset.
- Simulate execution of **batched ANN_SEARCH queries** under a given hardware config.
- Track detailed **per-query and aggregate metrics**.
- Emit **JSON logs** usable by humans and scripts.

### 7.2 High-Level Components

- `AnnInSsdConfig` – configuration struct (mirrors JSON config).
- `AnnInSsdDevice` – encapsulates hardware parameters and channel state.
- `GraphInFlash` – block/entry representation, portal neighbors, per-vector neighbors.
- `QueryEngine` – executes graph search on top of `AnnInSsdDevice` and `GraphInFlash`.
- `StatsCollector` – records per-query and aggregate metrics, writes JSON.

---

## 8. Configuration Knobs (JSON)

Configs will live under `benchmarks/configs/`, e.g. `ann_in_ssd_l0.json`, `ann_in_ssd_l3.json`.

### 8.1 Top-Level Structure (Conceptual)

```jsonc
{
  "dataset": {
    "name": "SIFT1M",
    "path": "benchmarks/datasets/sift1m",
    "dimension": 128,
    "num_vectors": 1000000
  },
  "graph": {
    "placement_mode": "hash_home", // or "locality_aware"
    "vectors_per_block": 96, // K
    "portal_degree": 6, // P
    "neighbor_degree": 3, // M
    "code_type": "pq8x8", // example
    "page_size_bytes": 4096
  },
  "device": {
    "hardware_level": "L2", // L0, L1, L2, L3
    "num_channels": 8,
    "queue_depth_per_channel": 64,
    "base_read_latency_us": 2.0,
    "internal_read_bandwidth_GBps": 20.0,
    "controller_flops_GF": 50.0,
    "per_block_unit_flops_GF": 200.0
  },
  "search": {
    "k": 10,
    "beam_width": 8,
    "max_steps": 32,
    "entry_block_strategy": "centroid_knn", // or "fixed_portals"
    "termination": "simple" // placeholder
  },
  "workload": {
    "num_queries": 10000,
    "concurrency": 256,
    "distribution": "uniform", // or "zipfian", "bursty"
    "seed": 42
  },
  "logging": {
    "output_path": "results/raw/ann_in_ssd_l2.json",
    "record_per_query": true,
    "record_per_block": false
  }
}
```

Exact field names can be adjusted during implementation, but the structure should stay similar.

---

## 9. JSON Output Format and Metrics

The simulator will write **JSON logs** that are both human- and machine-readable.

### 9.1 Top-Level Layout

```jsonc
{
  "config": {
    /* echo of input config */
  },
  "aggregate": {
    "k": 10,
    "num_queries": 10000,
    "recall_at_k": 0.94,
    "qps": 50000.0,
    "latency_us_p50": 150.0,
    "latency_us_p95": 230.0,
    "latency_us_p99": 320.0,
    "avg_blocks_visited": 24.3,
    "avg_portal_steps": 7.1,
    "avg_internal_reads": 26.8,
    "avg_distances_computed": 4000.0,
    "metadata_bytes": 12345678,
    "estimated_energy_joules": 0.0 // optional
  },
  "per_query": [
    {
      "query_id": 0,
      "true_neighbors": [
        /* ids */
      ], // optional
      "found_neighbors": [
        /* ids */
      ],
      "found_scores": [
        /* distances */
      ],
      "blocks_visited": 22,
      "portal_steps": 6,
      "internal_reads": 24,
      "distances_computed": 3800,
      "estimated_latency_us": 140.5,
      "channel_utilization": [
        /* per-channel */
      ]
    }
    // ... more queries (or subset, depending on logging config)
  ]
}
```

The **aggregate** section is what most plotting scripts will use. The **per_query** section allows fine-grained analysis when needed.

### 9.2 Metrics to Track (Non-Exhaustive)

Per query:

- `blocks_visited` – number of unique blocks touched.
- `portal_steps` – how many portal edges followed.
- `internal_reads` – number of internal block reads.
- `distances_computed` – total vector distance evaluations.
- `estimated_latency_us` – modeled end-to-end latency.
- `channel_utilization` – per-channel usage snapshot (optional).

Aggregate:

- Latency distribution (p50/p95/p99).
- QPS at specified concurrency.
- Average and distribution of `blocks_visited`, `portal_steps`, `internal_reads`.
- Metadata size and code footprint.

---

## 10. C++ API Sketch (ann_in_ssd_model)

This section sketches a possible API for `ann_in_ssd_model`. Exact naming is flexible, but the responsibilities should remain.

### 10.1 Core Types

- `struct AnnInSsdConfig` – holds config parameters, with a `load_from_json(path)` helper.
- `struct Query` – wraps a query vector and optional ground truth.
- `struct QueryResult` – top-k neighbors and stats for one query.
- `struct SimulationSummary` – aggregate metrics and config echo.

### 10.2 Class Interface

```cpp
namespace simulator {
namespace ann_in_ssd {

struct AnnInSsdConfig;
struct Query;
struct QueryResult;
struct SimulationSummary;

class AnnInSsdModel {
public:
    explicit AnnInSsdModel(const AnnInSsdConfig& config,
                           const core::Dataset& dataset);

    // Single-query search (mainly for testing / debugging)
    QueryResult search_one(const Query& q);

    // Batch search with modeled concurrency
    std::vector<QueryResult> search_batch(const std::vector<Query>& queries);

    // Summary statistics after running one or more batches
    const SimulationSummary& summary() const;

    // Write JSON log to file following the format in Section 9
    void write_json_log(const std::string& path) const;
};

} // namespace ann_in_ssd
} // namespace simulator
```

The benchmark harness can:

1. Build or load a `core::Dataset`.
2. Load `AnnInSsdConfig` from a JSON config file.
3. Construct `AnnInSsdModel`.
4. Generate a set of queries and ground-truth neighbors (for recall computation).
5. Call `search_batch` to run the simulation.
6. Call `write_json_log` to dump results.

This matches the desired workflow:

1. **Create config** (or a script that sweeps configs).
2. **Run simulator**, logging JSON.
3. **Analyze** manually or with scripts that plot and compare metrics.

---

## 11. Relationship to Other Paths

- The ANN-in-SSD simulator is a **separate device path** from:
  - DRAM-only HNSW baseline.
  - Tiered DRAM+SSD system.
- All three paths share:
  - Common datasets and workloads.
  - Common quality metrics (recall@k).
  - Comparable latency/QPS metrics.

This makes it possible to produce plots that directly compare:

- **DRAM-only** vs **Tiered DRAM+SSD** vs **ANN-in-SSD (L0–L3)**
- Under various hardware assumptions and algorithmic knobs.

## 12. Abstraction Level and Generality Notes

- **Abstraction level**: The simulator sits **above the FTL**. We treat `base_read_latency_us` (and any future write latency) as already incorporating mapping, garbage collection, and wear-leveling effects. We do not explicitly model mapping tables, erase blocks, GC, or write amplification.
- **Capacity partitioning**: Conceptually, the device can expose a total block budget where some fraction is reserved for the ANN region (graph-in-flash) and the remainder is available as traditional storage. In the simulator, this can be modeled with simple knobs such as `total_blocks` and `ann_blocks` and logged as an ANN-capacity fraction.
- **Background host I/O**: Traditional storage traffic can be approximated by injecting background read/write workloads that consume channel time and queue depth, without simulating full block-device semantics. This allows us to study contention between ANN_SEARCH commands and generic host I/O.
- **Out-of-scope (future work)**: A full, general-purpose SSD model with block-device API, detailed FTL, GC, and wear-leveling is intentionally out of scope for this project, but the current abstraction is compatible with adding such layers in future work and will be documented as such in the report.
