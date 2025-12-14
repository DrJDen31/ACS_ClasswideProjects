# Project A4 – Quick Start

This guide explains how to **build the code**, **use the existing benchmark data**, and (optionally) **re-run the experiments and regenerate all plots** for Project A4. All commands below assume you start from the `TrackA` repository root.

---

## 1. Environment Setup

### 1.1 Toolchain

- **OS**: Linux or WSL2 on Windows (the project was developed under WSL2).
- **Compiler**: `g++` with C++17 support (for example GCC 9.4+).
- **Python**: 3.8+ with the following packages:

```bash
python -m pip install --user numpy pandas matplotlib
```

Optional but useful for deeper performance analysis:

- Linux `perf` tools (for hardware performance counters).

---

## 2. Building the Code

All builds are driven by simple Makefiles.

### 2.1 Build Benchmarks

From the repository root:

```bash
cd benchmarks
make
```

This produces the `benchmark` executable in `benchmarks/`.

### 2.2 (Optional) Build Tests

```bash
cd tests
make
```

You can then run:

```bash
./test_correctness
./stress_test 8
```

These validate basic correctness and exercise multi-threaded workloads.

---

## 3. Using the Existing Results

The repository already includes a **complete dataset** (675 measurements across 5 dataset sizes) and the corresponding analysis tables. If you only need to regenerate the analysis and plots from the existing CSV files, run:

```bash
cd scripts
python final_merge_all.py
```

This script:

- Merges all raw result files in `results/raw/` into `final_complete_results.csv`.
- Re-runs `analyze_results.py` to produce:
  - `results/analysis/statistics.csv`
  - `results/analysis/speedup.csv`
- Regenerates all plots in `results/analysis/plots/`.

After this step you have a fully consistent set of tables and figures that match the report.

---

## 4. Re-running Benchmarks (Optional and Time-Consuming)

Re-running the full benchmark grid takes on the order of **9–10 hours** on the reference machine.

The high-level workflow is:

1. Run the focused baseline grid (10K, 100K, 1M keys).
2. Retry any failed or timed-out baseline runs with a longer timeout.
3. Add intermediate dataset sizes (50K and 500K keys).
4. Retry any failed intermediate runs.
5. Merge everything and regenerate analysis and plots.

The scripts involved are:

- `run_focused_benchmarks.py` – Focused grid with 10K, 100K, and (for fine-grained) 1M keys.
- `retry_failed_benchmarks.py` – Retries the small set of slow/failed baseline configurations.
- `run_intermediate_sizes.py` – Adds 50K and 500K keys to fill in cache hierarchy gaps.
- `retry_intermediate_failures.py` – Retries any failed intermediate configurations.
- `final_merge_all.py` – Produces `final_complete_results.csv`, re-runs analysis, and regenerates all plots.

Because these scripts refer to specific CSV filenames already present in `results/raw/`, the repository is **self-contained**: you can either reuse the existing CSVs or replace them with new runs if you wish (adjusting script constants as needed).

---

## 5. Regenerating Plots Only

If you already have `final_complete_results.csv` (either the version in the repo or a newly generated one) and only want to rebuild the figures, you can call the plotting script directly:

```bash
cd scripts
python generate_plots.py ../results/raw/final_complete_results.csv ../results/analysis/plots
```

This produces all PNGs used in the report, including:

- `throughput_vs_threads.png`
- `speedup.png`
- `parallel_efficiency.png`
- `workload_comparison.png`
- `dataset_size_sensitivity.png`
- `workload_strategy_dataset_sweep.png`
- `workload_strategy_dataset_sweep_split.png`
- `strategy_comparison_threads_100000.png`
- `strategy_comparison_threads_500000.png`

These filenames are referenced from `report/A4-Report.tex`.

---

## 6. File Map

For quick reference:

- **Implementations**: `src/`
- **Benchmarks**: `benchmarks/benchmark` and `benchmarks/workloads.cpp`
- **Raw results**: `results/raw/*.csv`
- **Aggregates**: `results/analysis/statistics.csv`, `results/analysis/speedup.csv`
- **Plots**: `results/analysis/plots/*.png`
- **Docs and analysis notes**: `docs/*.md`
- **Final report source**: `report/A4-Report.tex` (compiled as `report/ACS_Final_Track_A_Report.pdf`)
