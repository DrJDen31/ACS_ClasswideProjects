# Experiment 0 Conclusions: hnswlib DRAM Upper Bound

## What this experiment measured

- **Goal:** Quantify how much faster a highly optimized HNSW library (`hnswlib`) is compared to the in-tree C++ HNSW implementation used in Experiment 1.
- **Datasets:**
  - SIFT20k subset: `num_base = 20,000`, `num_queries = 2,000`, `dim = 128`, `k = 10`.
  - Full SIFT1M: `num_base = 1,000,000`, `num_queries = 10,000`, `dim = 128`, `k = 10`.
- **Parameters (all runs):**
  - `M = 24`, `ef_construction = 300`.
  - `ef_search ∈ {256, 512}` for SIFT20k; `ef_search = 512` for SIFT1M.

Results are logged as:

- `results/raw/hnswlib_sift20k_M24_efc300_efs256.json`
- `results/raw/hnswlib_sift20k_M24_efc300_efs512.json`
- `results/raw/hnswlib_sift1m_M24_efc300_efs512.json`

Each JSON file contains `recall_at_k`, build/search times, and both total and search-only QPS.

## SIFT20k subset (20k base, 2k queries)

**Configuration:**

- `num_base = 20,000`, `num_queries = 2,000`, `dim = 128`, `k = 10`.
- `M = 24`, `ef_construction = 300`.
- `ef_search = 256` and `512`.
- Ground truth computed by `compare_hnswlib_sift.py` via brute-force over the 20k base.

**Observed metrics (approximate):**

- `ef_search = 256` (`hnswlib_sift20k_M24_efc300_efs256.json`):

  - `recall@10 ≈ 0.99990` (essentially perfect).
  - `build_time_s ≈ 0.50 s`.
  - `search_time_s ≈ 0.043 s` for 2,000 queries.
  - `total_qps ≈ 3,710` (build+search time).
  - `search_qps ≈ 45,900` (search-only).

- `ef_search = 512` (`hnswlib_sift20k_M24_efc300_efs512.json`):
  - `recall@10 ≈ 0.99990` (no visible gain over 256 in this regime).
  - `build_time_s ≈ 0.46 s`.
  - `search_time_s ≈ 0.067 s`.
  - `total_qps ≈ 3,800`.
  - `search_qps ≈ 30,000`.

**Interpretation:**

- On this small subset, **hnswlib saturates recall** already at `ef_search = 256`, and pushing to 512 mostly increases search cost without improving recall.
- Even at `ef_search = 256`, search-only throughput is extremely high (tens of thousands of queries/s), and build time is well under a second.
- For later experiments, this tells us that **pure DRAM HNSW tuned with these parameters can essentially reach perfect recall on SIFT20k with negligible build and search cost**.

## Full SIFT1M (1M base, 10k queries)

**Configuration:**

- `num_base = 1,000,000`, `num_queries = 10,000`, `dim = 128`, `k = 10`.
- `M = 24`, `ef_construction = 300`, `ef_search = 512`.
- Ground truth loaded from `sift_groundtruth.ivecs` and filtered to the 1M subset.

**Observed metrics (from `hnswlib_sift1m_M24_efc300_efs512.json`):**

- `recall@10 ≈ 0.99933`.
- `build_time_s ≈ 191.5 s` (≈ 3.2 minutes).
- `search_time_s ≈ 3.59 s` for 10,000 queries.
- `total_qps ≈ 51.3` (queries per second over build+search time).
- `search_qps ≈ 2,785` (search-only queries per second).

## Comparison with in-tree DRAM HNSW baseline (Experiment 1)

From Experiment 1, the tuned **in-tree** C++ HNSW baseline on the same SIFT1M workload and parameters (`M=24`, `ef_construction=300`, `ef_search=512`, 4 build threads) achieved approximately:

- `recall@10 ≈ 0.99938` (essentially identical to hnswlib’s ≈0.99933).
- `build_time_s ≈ 921.6 s` (≈ 15.4 minutes).
- `search_time_s ≈ 27.5 s` for 10,000 queries.
- `effective_qps ≈ 364` (search-only qps from the C++ benchmark).

Juxtaposing the two:

- **Build time:**

  - hnswlib ≈ 191.5 s vs. in-tree HNSW ≈ 921.6 s.
  - hnswlib is roughly **4.8× faster** to build at comparable recall.

- **Search throughput:**

  - hnswlib search QPS ≈ 2,785 vs. in-tree search QPS ≈ 360.
  - hnswlib is roughly **7.5× faster** in search throughput at comparable recall.

- **Recall:**
  - Both achieve `recall@10 ≈ 0.9993–0.9994`; quality is essentially identical.

**Conclusion of this comparison:**

- `hnswlib` is significantly more optimized from an engineering standpoint (build and search speed) while matching recall.
- The in-tree HNSW baseline is slower but acceptable as a **research baseline**, especially since it is tightly integrated with the tiered and ANN-in-SSD simulators and has richer instrumentation (IOStats, modeled device time, etc.).

## Overall conclusions for Experiment 0

1. **hnswlib provides a clear DRAM upper bound.**

   - On SIFT20k and SIFT1M, hnswlib reaches essentially perfect recall with dramatically faster build and search times than the in-tree implementation.
   - For the remainder of the project, hnswlib should be treated as the **engineering/speed upper bound for DRAM HNSW**.

2. **The in-tree DRAM HNSW baseline is close in quality but slower in performance.**

   - At matched parameters, recall is effectively the same.
   - The extra factor of ~5× (build) and ~7–8× (search) in slow-down reflects implementation differences and additional instrumentation, not fundamental algorithmic gaps.

3. **Subsequent experiments should interpret results relative to both baselines.**

   - When comparing tiered DRAM+SSD and ANN-in-SSD designs, you should:
     - Use the **in-tree DRAM HNSW** as the _direct_ baseline (since it shares code paths and logging).
     - Use **hnswlib** as an aspirational “how fast could a very optimized DRAM HNSW be?” reference.

4. **SIFT20k results validate correctness and tuning at small scale.**
   - The near-perfect recall and tiny build/search times at SIFT20k confirm that the chosen HNSW parameters (`M=24`, `ef_construction=300`, `ef_search≥256`) are sufficient for high-quality results.
   - This supports using the same parameter set as a reasonable default when exploring tiered and ANN-in-SSD behavior.

These conclusions can be referenced directly in the final report when introducing hnswlib and justifying its role as the DRAM upper bound for the rest of the Track B Topic 2 experiments.
