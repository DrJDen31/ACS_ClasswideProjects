# Experiment 1 Conclusions: DRAM Baseline

## What this experiment measured

- **Goal:** Characterize a DRAM-only HNSW baseline over both synthetic and real (SIFT1M) datasets.
- **Metrics:** recall@k (k=10), QPS, latency percentiles (p50/p95/p99), and build time.
- **Purpose:** Provide a trustworthy DRAM reference to compare against tiered and ANN-in-SSD designs in later experiments.

## Synthetic Gaussian (10k base, 1k queries) – ef_search sweep

**Configuration:**

- Dataset: synthetic Gaussian, `NUM_BASE = 10,000`, `NUM_QUERIES = 1,000`, `DIM = 128`.
- HNSW: `M = 16`, `ef_construction = 200`, `ef_search ∈ {16, 32, 64, 128, 256}`.
- Mode: `mode = dram` (pure DRAM, no I/O stats).

\*\*Observed trends (from JSON logs + `analyze_experiment1.py`):

- **Recall vs ef_search** (approximate):

  - `ef_search = 16` → recall@10 ≈ 0.80
  - `ef_search = 32` → recall@10 ≈ 0.89
  - `ef_search = 64` → recall@10 ≈ 0.95
  - `ef_search = 128` → recall@10 ≈ 0.99
  - `ef_search = 256` → recall@10 ≈ 0.997

- **Latency behavior:**

  - p50 latency grows from tens of microseconds at low `ef_search` to a few hundred microseconds at `ef_search = 256`.
  - p95/p99 latencies follow the same pattern (sub-millisecond at low ef_search, approaching ~1.5 ms at ef_search = 256).

- **Throughput behavior:**
  - Total QPS (build + search time amortized) stays in the ~140–150 QPS range because build dominates wall time for this small synthetic run.
  - **Search-only QPS**, which is reported by `benchmark_recall` but not plotted here, is in the **thousands to tens of thousands of queries/s** for this tiny synthetic problem.

**Takeaways for later experiments:**

- HNSW behaves as expected: **increasing ef_search monotonically improves recall** while raising per-query latency and reducing effective per-query throughput.
- For small synthetic datasets, build time dominates total wall-clock time, so **QPS measured over build+search is not a meaningful steady-state metric**. Later experiments should either:
  - focus on **search-only QPS**, or
  - interpret total QPS as a build+search “batch throughput” metric, not a production steady state.

## SIFT1M DRAM Baseline (1M base, 10k queries)

**Configuration used for the final baseline run:**

- Dataset: SIFT1M (`sift_base.fvecs`, `sift_query.fvecs`, `sift_groundtruth.ivecs`).
- `num_base = 1,000,000`, `num_queries = 10,000`, `dim = 128`, `k = 10`.
- HNSW: `M = 24`, `ef_construction = 300`, `ef_search = 512`, `hnsw_build_threads = 4`.
- Mode: `mode = dram`.
- JSON log: `results/raw/dram_sift1m_M24_efc300_efs512_nb1e6_q1e4_t4.json`.

**Key results from this run:**

- `recall@10 ≈ 0.99938` (essentially perfect recall).
- Build time ≈ 921.6 s (≈ 15.4 minutes) for 1M base vectors with 4 build threads.
- Search-only QPS ≈ 364 queries/s for 10k queries.
- Latency percentiles:
  - p50 ≈ 2.76 ms
  - p95 ≈ 4.00 ms
  - p99 ≈ 5.03 ms

**Relation to hnswlib “gold-standard” baseline:**

- Separate runs using `scripts/compare_hnswlib_sift.py` on the same machine and parameters show:
  - hnswlib achieves similar recall@10 (≈ 0.9993–0.9994) but with **substantially faster build and search**.
  - Roughly:
    - **Build:** your in-tree HNSW is ≈3× slower than hnswlib on full SIFT1M.
    - **Search:** your in-tree HNSW is ≈7× slower in search-only QPS at comparable recall.
- For all subsequent experiments (tiered and ANN-in-SSD), you treat **hnswlib as a DRAM upper bound** and your in-tree HNSW as the integrated baseline that can participate in tiering and SSD simulations.

**On the earlier low-recall SIFT1M run:**

- The file `results/raw/dram_sift1m_ef256_q200.json` corresponds to an **earlier, under-tuned run**:
  - recall@10 ≈ 0.14 and an anomalously large build time.
- This run is **superseded** by the tuned configuration above and is kept only as a record of early misconfiguration. It should not be used as the primary DRAM baseline in the report.

## Experiment 1: Overall conclusions

1. **HNSW DRAM behaves as expected across ef_search.**

   - On synthetic Gaussian data, recall rises smoothly from ≈0.8 → ≈0.997 as ef_search increases from 16 → 256, with corresponding increases in latency.
   - This validates both your HNSW implementation and the JSON logging / analysis pipeline.

2. **The tuned SIFT1M DRAM configuration delivers near-perfect recall.**

   - With `M = 24`, `ef_construction = 300`, `ef_search = 512`, your in-tree HNSW reaches ≈0.9994 recall@10 on full SIFT1M.
   - Latencies are in the low-millisecond range for this workload, and search-only QPS ≈ 360 queries/s is a reasonable baseline for later comparisons.

3. **Your in-tree HNSW is slower than hnswlib but adequate as a baseline.**

   - Even though it is ≈3× slower to build and ≈7× slower to search than hnswlib at similar recall, it provides a **self-contained, instrumented baseline** for DRAM and for integrating with tiered storage and ANN-in-SSD simulations.
   - This is acceptable for the project’s goals, as long as you clearly treat hnswlib as the engineering upper bound.

4. **This experiment establishes the DRAM reference points needed for later work.**
   - The synthetic sweep gives you a clean recall–ef_search–latency relationship.
   - The SIFT1M baseline provides a realistic DRAM point for a 1M-vector workload.
   - Together, they form the DRAM reference curves against which you can compare:
     - Tiered DRAM+SSD HNSW (Experiments 2, 9).
     - ANN-in-SSD designs and hardware levels (Experiments 9, 10, 11).
