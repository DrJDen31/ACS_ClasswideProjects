# Experiment 0: hnswlib DRAM Upper-Bound Baseline

## What and why

- **What:** Use the external `hnswlib` library to measure a _gold-standard_ DRAM-only HNSW baseline on SIFT subsets and full SIFT1M.
- **Why:** This gives an **engineering upper bound** for DRAM HNSW performance (build time, search QPS, recall) so we can interpret how far the in-tree C++ HNSW (Experiment 1) and the tiered / ANN-in-SSD designs are from an optimized library.

This experiment runs three representative configurations:

- **SIFT20k, ef_search=256** – fast, high-recall subset baseline.
- **SIFT20k, ef_search=512** – slightly higher search cost at the same recall.
- **SIFT1M full, ef_search=512** – realistic large-scale baseline.

All results are logged as JSON in `results/raw/` and summarized in `CONCLUSIONS.md`.

## How to run (Windows + WSL)

### 1. Ensure dependencies

- **WSL** with Ubuntu is installed (already confirmed).
- **Python 3** and **pip** available inside WSL.
- `hnswlib` installed in WSL (one-time):

```powershell
wsl python3 -m pip install --user hnswlib
```

- SIFT1M dataset present under the project root:
  - `data/SIFT1M/sift/sift_base.fvecs`
  - `data/SIFT1M/sift/sift_query.fvecs`
  - `data/SIFT1M/sift/sift_groundtruth.ivecs`

### 2. Run the experiment

From a PowerShell prompt in the project root (`TrackB/`):

```powershell
wsl bash -lc 'cd /mnt/c/Users/jaden/OneDrive/Documents/RPI/Fall2025/AdvancedComputerSystems/Projects/TrackB/experiments/Experiment0_HNSWLIB_Baseline && ./scripts/experiment0.sh'
```

This script:

- Changes into the Experiment 0 directory.
- Calls `scripts/run_experiment0.py`, which in turn runs:
  - `scripts/compare_hnswlib_sift.py` on SIFT20k with `ef_search=256`.
  - `scripts/compare_hnswlib_sift.py` on SIFT20k with `ef_search=512`.
  - `scripts/compare_hnswlib_sift.py` on full SIFT1M with `ef_search=512`.
- Captures and parses the printed metrics into JSON files under `results/raw/`.
- Prints a one-line summary table at the end.

## Scripts and configuration

- **Core runner:** `scripts/run_experiment0.py`

  - Locates the project root and SIFT1M data.
  - Defines the three runs:
    - `sift20k_M24_efc300_efs256` – `num_base=20,000`, `num_queries=2,000`, `M=24`, `ef_construction=300`, `ef_search=256`.
    - `sift20k_M24_efc300_efs512` – same as above with `ef_search=512`.
    - `sift1m_M24_efc300_efs512` – `num_base=1,000,000`, `num_queries=10,000`, `M=24`, `ef_construction=300`, `ef_search=512`.
  - For **SIFT20k** runs, it **omits** `--groundtruth`, letting `compare_hnswlib_sift.py` compute brute-force ground truth on the 20k base for accurate recall.
  - For **SIFT1M**, it passes the official 1M `sift_groundtruth.ivecs` file to avoid an expensive brute-force pass.
  - Parses the printed metrics from `compare_hnswlib_sift.py` and writes compact JSON files to `results/raw/`.

- **Shell wrapper:** `scripts/experiment0.sh`

  - Thin wrapper to call `run_experiment0.py` from a bash shell.

- **Underlying tool:** `scripts/compare_hnswlib_sift.py`
  - Loads SIFT base, queries, and (optionally) ground truth.
  - Builds an `hnswlib.Index` with the specified `M` and `ef_construction`.
  - Runs `knn_query` with the given `ef_search` and `k`.
  - Computes recall@k, build time, search time, and both total and search-only QPS.

## Outputs

The main outputs of this experiment are JSON summaries in `results/raw/`:

- `hnswlib_sift20k_M24_efc300_efs256.json`
- `hnswlib_sift20k_M24_efc300_efs512.json`
- `hnswlib_sift1m_M24_efc300_efs512.json`

Each has the form:

```json
{
  "name": "sift1m_M24_efc300_efs512",
  "config": {
    "dataset_name": "SIFT1M",
    "num_base": 1000000,
    "num_queries": 10000,
    "dim": 128,
    "k": 10,
    "M": 24,
    "ef_construction": 300,
    "ef_search": 512,
    ...
  },
  "aggregate": {
    "recall_at_k": 0.99939,
    "build_time_s": 191.5,
    "search_time_s": 3.59,
    "total_qps": 51.3,
    "search_qps": 2784.6
  }
}
```

Refer to `CONCLUSIONS.md` in this directory for a narrative summary comparing these hnswlib baselines against the in-tree HNSW DRAM baseline from Experiment 1.
