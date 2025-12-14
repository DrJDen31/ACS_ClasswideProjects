# Project A4 – Final Results Summary

**Completion date**: November 11, 2025, 8:30 PM  
**Status**: Benchmarking and primary analysis complete

This document summarizes the main empirical findings from the Project A4 experiments. Detailed interpretation and writing guidance are provided separately in `REPORT_INSIGHTS.md`.

---

## 1. Experimental Configuration

### 1.1 Data Structure and Strategies

We evaluate a separate-chaining hash table with 1024 buckets under two synchronization strategies:

- **Coarse-grained locking**  
  Single global `std::mutex` protecting the entire table.

- **Fine-grained locking (lock striping)**  
  One `std::mutex` per bucket. Operations contend only on the bucket they touch, assuming a uniform hash.

Both implementations share a common `HashTable` interface and are exercised by the same benchmark driver.

### 1.2 Workloads and Parameters

The benchmark explores the following dimensions:

- **Strategies**: `coarse`, `fine`
- **Workloads**:
  - `lookup` (read-only)
  - `insert` (write-heavy)
  - `mixed` (70% lookups / 30% inserts)
- **Thread counts**: 1, 2, 4, 8, 16
- **Dataset sizes (keys)**: 10K, 50K, 100K, 500K, 1M (not all scripts exercise all sizes for all strategies, but the final merged dataset does)
- **Repetitions**: 5 independent trials per configuration

The reference machine is an AMD Ryzen 9 5900HS (8 cores / 16 threads, 4 MB L2, 16 MB shared LLC), running Linux under WSL2 with `g++` 9.4 and Python 3.12.

---

## 2. Throughput at 100K Keys (Representative Case)

The 100K-key dataset sits in the shared last-level cache and serves as a representative configuration for comparing strategies.

### 2.1 Lookup Workload (100K keys)

Throughput in millions of operations per second (Mops/sec):

| Threads | Coarse (Mops/sec) | Fine (Mops/sec) | Fine / Coarse |
| ------- | ----------------- | --------------- | ------------- |
| 1       | 1.58              | 1.62            | 1.03×         |
| 2       | 0.72              | 2.63            | 3.65×         |
| 4       | 0.43              | 5.29            | 12.3×         |
| 8       | 0.28              | 8.39            | 30.0×         |
| 16      | 0.21              | 10.38           | 49.4×         |

### 2.2 Insert Workload (100K keys)

| Threads | Coarse (Mops/sec) | Fine (Mops/sec) | Fine / Coarse |
| ------- | ----------------- | --------------- | ------------- |
| 1       | 1.30              | 1.55            | 1.19×         |
| 2       | 0.36              | 2.11            | 5.86×         |
| 4       | 0.33              | 3.89            | 11.8×         |
| 8       | 0.23              | 7.01            | 30.5×         |
| 16      | 0.20              | 9.39            | 47.0×         |

### 2.3 Mixed Workload (70% lookup / 30% insert, 100K keys)

| Threads | Coarse (Mops/sec) | Fine (Mops/sec) | Fine / Coarse |
| ------- | ----------------- | --------------- | ------------- |
| 1       | 1.49              | 1.41            | 0.95×         |
| 2       | 0.69              | 2.65            | 3.84×         |
| 4       | 0.36              | 4.30            | 11.9×         |
| 8       | 0.23              | 7.47            | 32.5×         |
| 16      | 0.21              | 9.94            | 47.3×         |

**Key observation:** At 100K keys and 16 threads, the fine-grained implementation is roughly **30–50× faster** than coarse-grained across all workloads.

---

## 3. Speedup and Parallel Efficiency

Speedup is defined relative to the single-threaded throughput of the same strategy, workload, and dataset size. Parallel efficiency is `speedup / threads`.

### 3.1 Coarse-Grained Locking: Negative Scaling

For 100K-key lookup workload:

| Threads | Speedup | Efficiency |
| ------- | ------- | ---------- |
| 1       | 1.00×   | 100.0%     |
| 2       | 0.46×   | 22.8%      |
| 4       | 0.27×   | 6.9%       |
| 8       | 0.17×   | 2.2%       |
| 16      | 0.13×   | 0.8%       |

Throughput **decreases** as threads are added. The coarse-grained design is dominated by lock contention, context switching, and cache-line bouncing on the global mutex. Adding threads makes performance substantially worse than running single-threaded.

### 3.2 Fine-Grained Locking: Reasonable Scaling

For the same 100K-key lookup workload:

| Threads | Speedup | Efficiency |
| ------- | ------- | ---------- |
| 1       | 1.00×   | 100.0%     |
| 2       | 1.62×   | 81.1%      |
| 4       | 3.27×   | 81.7%      |
| 8       | 5.18×   | 64.8%      |
| 16      | 6.41×   | 40.1%      |

Fine-grained locking tracks close to ideal up to 4–8 threads, and still achieves meaningful speedup at 16 threads despite coherence and SMT overheads.

---

## 4. Dataset-Size Sensitivity and Cache Effects

At a fixed thread count, throughput drops sharply as the working set outgrows the caches. Both strategies experience these effects, but fine-grained locking maintains much higher absolute throughput.

Representative 1-thread behavior for coarse-grained locking:

| Dataset Size | Approx. Working Set | Throughput (Mops/sec) | Relative to 10K     |
| ------------ | ------------------- | --------------------- | ------------------- |
| 10K keys     | ~480 KB (L2)        | 18.2                  | 1.0×                |
| 100K keys    | ~4.8 MB (LLC)       | 1.6                   | 0.09× (≈11× slower) |
| 1M keys      | ~48 MB (DRAM)       | ~0.3                  | 0.02× (≈60× slower) |

Fine-grained locking shows the same qualitative pattern but with higher absolute throughput and better scaling at larger sizes, because synchronization overhead becomes a smaller fraction of total time once the workload is DRAM-bound.

The full five-size dataset (10K, 50K, 100K, 500K, 1M) makes the cache transitions clearly visible in log–log plots.

---

## 5. Summary of Main Conclusions

1. **Synchronization strategy dominates scalability.**  
   Coarse-grained locking introduces a global serialization point and extremely poor scaling. Fine-grained locking, using per-bucket mutexes, enables the hash table to exploit multicore parallelism.

2. **Fine-grained locking delivers large throughput gains at high thread counts.**  
   For representative 100K-key workloads at 16 threads, fine-grained locking is roughly 30–50× faster than coarse-grained locking.

3. **Coarse-grained locking exhibits negative scaling.**  
   For coarse-grained locking, adding threads beyond one reduces throughput due to lock contention, context-switch overhead, and cache-line bouncing on the single mutex.

4. **Fine-grained locking achieves moderate to good efficiency.**  
   Fine-grained locking achieves 6–9× speedup at 16 threads (depending on dataset size), corresponding to 40–60% parallel efficiency given hardware limitations such as cache coherence and SMT.

5. **Cache hierarchy strongly influences absolute performance.**  
   Moving from L2-resident datasets to LLC and DRAM introduces 10×–60× slowdowns for both strategies. Fine-grained locking cannot eliminate the memory wall but preserves useful speedup in all regimes.

6. **The experimental dataset is statistically robust.**  
   Each configuration is measured across five repetitions, and medians are used for analysis. Variation across repetitions is modest, and the merged dataset is complete (no missing or failed entries) after retries.

---

## 6. Files and Reproduction

The following files capture the final numerical results and derived statistics:

- `results/raw/final_complete_results.csv` – All raw benchmark measurements.
- `results/analysis/statistics.csv` – Per-configuration statistics (medians, means, standard deviations, counts).
- `results/analysis/speedup.csv` – Speedup values and efficiencies relative to single-thread baselines.
- `results/analysis/plots/*.png` – Plots used in the report (throughput vs. threads, speedup, dataset-size sensitivity, workload comparison, and efficiency).

All of these can be regenerated from the raw results CSV via the Python scripts in `scripts/`, as described in `QUICKSTART.md`.

---

## 7. Effective Serial Fractions (Amdahl Fits)

To connect the measured speedups to Amdahl's Law, we can treat the fine-grained implementation as having
an "effective" serial fraction `s` and solve

\[
S(N) = \frac{1}{s + \frac{1-s}{N}}
\]

for `s` using the observed 16-thread speedup `S(16)` for each workload and dataset size. The table below
summarizes these fits for representative dataset sizes of 100K and 1M keys. All speedups are for the
fine-grained implementation at 16 threads.

| Dataset Size | Workload | `S(16)` (fine, from `speedup.csv`) | Effective serial fraction `s` |
| -----------: | :------- | ---------------------------------: | ----------------------------: |
|         100K | lookup   |                               6.41 |                        ≈ 0.10 |
|         100K | insert   |                               6.07 |                        ≈ 0.11 |
|         100K | mixed    |                               7.05 |                        ≈ 0.08 |
|           1M | lookup   |                               9.36 |                        ≈ 0.05 |
|           1M | insert   |                              12.07 |                        ≈ 0.02 |
|           1M | mixed    |                               7.40 |                        ≈ 0.08 |

These values show that the effective serial fraction for the fine-grained design is on the order of
10% for cache-resident datasets (100K keys), shrinking to only a few percent for large DRAM-resident
datasets (1M keys) where memory latency dominates. This is consistent with the visual Amdahl-law fits
overlaid on the speedup plots: the fine-grained curves track an Amdahl model with a modest serial
component, while the coarse-grained implementation falls far below any reasonable Amdahl prediction due
to lock contention and cache-line bouncing on the global mutex.

---

## 8. Perf-Stat Snapshot (WSL2)

To complement the timing-based measurements, we collected a small number of hardware performance
counters using `perf stat` under WSL2, focusing on a representative configuration:

- Strategy: `coarse` vs `fine`
- Workload: `lookup`
- Threads: 8
- Dataset size: 50K keys
- Operations: 500K per run

Because the WSL2 kernel used here does not expose last-level-cache miss events, the `LLC-load-misses`
and `LLC-store-misses` counters are reported as `<not supported>` and are omitted from the tables
below. The available counters (cycles and retired instructions) are still informative.

### 8.1 Raw Perf Counters

| Strategy |        Cycles | Instructions | Time elapsed (s) |
| :------- | ------------: | -----------: | ---------------: |
| Coarse   | 2,898,367,543 |  583,597,399 |           0.4595 |
| Fine     |   631,745,001 |  168,314,699 |           0.0722 |

### 8.2 Derived Per-Operation Metrics

Each run performs 500K lookups. Dividing the counters by the operation count yields:

| Strategy | Throughput (Mops/s) | Cycles/op | Instructions/op |
| :------- | ------------------: | --------: | --------------: |
| Coarse   |                1.26 |     5,800 |           1,167 |
| Fine     |                16.7 |     1,260 |             337 |

These snapshot measurements echo the broader results:

- Fine-grained locking achieves more than **13× higher throughput** than coarse-grained locking at this
  configuration.
- On a per-operation basis, the coarse-grained design uses roughly **4.6× more cycles** and **3.5× more
  instructions** than the fine-grained design, indicating that a large fraction of its work is spent on
  lock management, context switching, and kernel overhead rather than useful hash-table operations.
- The lack of LLC miss counters under WSL2 prevents a direct quantitative comparison of cache behavior,
  but the cycle and instruction counts already support the qualitative claim that the coarse-grained
  implementation wastes significant work under contention compared to the fine-grained design.
