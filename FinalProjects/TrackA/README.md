# Project A4 – Concurrent Hash Tables

The goal of the project is to quantify how **synchronization granularity** (a single global lock versus per-bucket locks) affects the scalability of a concurrent hash table on a modern multicore CPU.

---

## How to Reproduce Key Results

A detailed, step-by-step guide for building the code, running benchmarks, and regenerating analysis tables and plots is provided in `QUICKSTART.md`.

If you only need the final outcomes, consult:

- `report/ACS_Final_Track_A_Report.pdf` (compiled from `report/A4-Report.tex`) for the full narrative and figures.
- `docs/FINAL_RESULTS.md` and `docs/FINAL_COMPLETE_STATUS.md` for numerical summaries and a description of the experimental workflow.

---

## Hash Table Variants

- **Coarse-grained locking**  
  A single `std::mutex` protects the entire table. All operations serialize on this lock.

- **Fine-grained lock striping**  
  Each bucket in a 1024-bucket chained hash table has its own `std::mutex`. Operations contend only on the bucket they touch.

Both variants implement the same `HashTable` interface defined in `src/hash_table.hpp`.

---

## High-Level Findings

- At **100K keys** and **16 threads**, the fine-grained table achieves **up to ~49× higher throughput** than the coarse-grained table.
- The coarse-grained table exhibits **negative scaling**: throughput **decreases** as threads are added, due to lock contention, context switching, and cache-line bouncing.
- The fine-grained table scales well up to 8–16 threads, achieving **6–9× speedup** at 16 threads (depending on dataset size), and clearly exposes **cache-hierarchy effects** across datasets from 10K to 1M keys.

For a complete description of the design, methodology, and results, see `report/A4-Report.tex` (compiled as `report/ACS_Final_Track_A_Report.pdf`).

---

## Directory Layout

```text
TrackA/
├── report/                         # Report sources and compiled PDF
│   ├── A4-Report.tex               # Final LaTeX report
│   └── ACS_Final_Track_A_Report.pdf  # Compiled PDF
├── README.md                       # Project overview (this file)
├── QUICKSTART.md                   # Build, run, and reproduction instructions
├── docs/                           # Supporting documentation and analysis summaries
│   ├── FINAL_COMPLETE_STATUS.md
│   ├── FINAL_RESULTS.md
│   └── REPORT_INSIGHTS.md
├── src/                            # Hash table implementations
│   ├── common.hpp                  # Shared types, node layout, hash function
│   ├── hash_table.hpp              # Thread-safe HashTable interface
│   ├── coarse_hash_table.hpp
│   ├── coarse_hash_table.cpp
│   ├── fine_hash_table.hpp
│   └── fine_hash_table.cpp
├── benchmarks/                     # Benchmark driver and workloads
│   ├── benchmark.cpp               # CLI wrapper around run_workload()
│   ├── workloads.hpp
│   ├── workloads.cpp
│   └── Makefile
├── tests/                          # Correctness and stress tests
│   ├── correctness_test.cpp
│   ├── stress_test.cpp
│   └── Makefile
├── scripts/                        # Benchmark, merge, and plotting scripts
│   ├── run_focused_benchmarks.py       # Main benchmark driver (10K, 100K, 1M)
│   ├── retry_failed_benchmarks.py      # Retries slow/failed baseline configs
│   ├── run_intermediate_sizes.py       # Additional 50K and 500K dataset sizes
│   ├── retry_intermediate_failures.py  # Retries failed intermediate configs
│   ├── final_merge_all.py              # Produces final_complete_results.csv and regenerates analysis
│   ├── analyze_results.py              # Aggregates statistics and speedups
│   └── generate_plots.py               # Generates all figures used in the report
└── results/
    ├── raw/                            # Raw and merged CSV benchmark outputs
    └── analysis/                       # statistics.csv, speedup.csv, etc.
        └── plots/                      # Final PNG plots used in the report
```
