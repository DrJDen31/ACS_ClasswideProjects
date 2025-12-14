# Project A4 – Report Writing Insights

**Date**: November 12, 2025  
**Purpose**: Summarize the most important technical insights and provide guidance for writing the final report.

This document is not graded directly but is intended to make it straightforward to produce a clear, well-supported report based on the completed experiments.

---

## 1. Headline Result

The central finding of this project is that **synchronization strategy has a decisive impact on scalability** for concurrent hash tables:

- At 100K keys and 16 threads, the fine-grained implementation (per-bucket locks) achieves **roughly 49× higher throughput** than the coarse-grained implementation (single global lock).
- Coarse-grained locking **scales negatively**: adding threads beyond one reduces throughput.
- Fine-grained locking achieves **moderate to strong speedup**, depending on dataset size (about 6× at 100K keys and up to about 9× at 1M keys).

The report introduction should surface this contrast early and then explain how the design, methodology, and data support it.

---

## 2. Coarse-Grained Locking: Why It Fails to Scale

### 2.1 Observed Behavior

For typical workloads at 100K keys, coarse-grained locking shows the following pattern for throughput and speedup (lookup workload shown here as representative):

- Throughput decreases as the number of threads increases from 1 to 16.
- Speedup drops from 1.0× at 1 thread to about 0.13× at 16 threads (negative scaling).
- Parallel efficiency falls below 1% at 16 threads.

### 2.2 Root Causes

The report should explain that this behavior is not just a “less than ideal” scaling scenario; it is qualitatively worse than running sequentially. Key factors include:

- **Lock contention** – All operations must acquire the same global mutex, forcing serialization and long wait times when many threads are active.
- **Context-switch overhead** – Threads that block on the global mutex may be descheduled and later rescheduled, adding tens of microseconds per context switch when contention is high.
- **Cache-line bouncing** – The cache line containing the mutex is constantly invalidated and moved between cores, increasing latency and consuming coherence bandwidth.

Together, these effects make the coarse-grained implementation slower at 16 threads than at 1 thread for most workloads and dataset sizes.

---

## 3. Fine-Grained Locking: Why It Succeeds

### 3.1 Design

Fine-grained locking uses one mutex per bucket in a 1024-bucket table. With a uniform hash function, operations on different keys very rarely contend for the same lock.

### 3.2 Expected Parallelism

If we assume uniform hashing:

- Probability of two threads needing the same bucket at the same time is low (approximately `threads / buckets`, or 16 / 1024 ≈ 1.6% in the worst case).
- Most operations proceed in parallel on different buckets.

This design removes the single global bottleneck and exploits the independence of bucket operations.

### 3.3 Observed Scaling

The data show that fine-grained locking:

- Achieves near-linear scaling up to about 4 threads for many workloads and dataset sizes.
- Provides meaningful speedup at 8 and 16 threads, even when the working set exceeds the last-level cache.
- Delivers 30–50× higher throughput than coarse-grained locking at 16 threads in representative cases.

The remaining gap from ideal linear scaling is largely explained by cache coherence, SMT, and DRAM latency, rather than algorithmic limitations.

---

## 4. Dataset Size and Cache Hierarchy

### 4.1 Motivation for Five Dataset Sizes

The final dataset uses five sizes: 10K, 50K, 100K, 500K, and 1M keys. These were chosen to span the cache hierarchy on the reference system:

- 10K keys – comfortably fits in L2 cache.
- 50K keys – near the L2/LLC boundary.
- 100K keys – fits in the shared LLC.
- 500K keys – near the point where the working set exceeds LLC capacity.
- 1M keys – clearly DRAM-bound.

With these sizes, the report can demonstrate how both absolute throughput and parallel speedup change as the working set moves from L2, to LLC, to main memory.

### 4.2 Observed Performance Cliffs

The measurements show clear slowdowns as dataset size increases:

- Moving from L2-resident to LLC-resident datasets introduces about an order-of-magnitude slowdown for single-threaded throughput.
- Moving from LLC-resident to DRAM-resident datasets introduces an additional order-of-magnitude slowdown.

These effects apply to both synchronization strategies and should be explained as consequences of the underlying hardware latency and bandwidth differences, not of the lock design.

### 4.3 Interaction with Synchronization

Even though both strategies suffer from cache and memory effects, the fine-grained implementation retains two advantages:

- It avoids the serialization penalty of a single global lock, so additional threads can still overlap work even when memory is the bottleneck.
- As operations become more expensive (due to DRAM latency), the fixed cost of acquiring and releasing a per-bucket mutex becomes a smaller fraction of total work.

This explains why fine-grained locking can achieve higher speedup at 1M keys than at 10K keys, even though absolute throughput is much lower.

---

## 5. Workload Differences

The report should compare lookup-only, insert-only, and mixed (70/30) workloads.

### 5.1 Lookup (Read-Only)

- Typically scales well with fine-grained locking, because reads do not modify the structure and primarily generate shared cache-line traffic.
- With coarse-grained locking, lookup workloads still serialize on the global mutex and suffer from the same contention issues as writes.

### 5.2 Insert (Write-Heavy)

- Generates more cache coherence traffic because writes require exclusive ownership of cache lines.
- In the fine-grained implementation, inserts may sometimes scale nearly as well as lookups at large dataset sizes, as the cost of DRAM latency dominates.

### 5.3 Mixed (70% Lookup / 30% Insert)

- Represents a more realistic workload for many applications.
- Shows intermediate behavior in terms of throughput and speedup, but still clearly favors fine-grained locking over coarse-grained locking.

The report can use the workload-comparison plot (e.g., at 8 or 16 threads and 100K or 500K keys) to show that fine-grained locking is consistently faster across all three workload types.

---

## 6. Parallel Efficiency and Amdahl’s Law

Parallel efficiency provides a compact way to discuss how close the implementation gets to ideal scaling.

- **Definition**: `efficiency = speedup / threads`.
- For fine-grained locking, efficiency is high (often above 70%) at low thread counts and remains in the 40–60% range at 16 threads for many dataset sizes.
- For coarse-grained locking, efficiency drops below 1% at high thread counts.

The report may briefly connect these observations to Amdahl’s Law:

- Coarse-grained locking effectively makes the “serial fraction” very large (because all operations pass through a single lock), so Amdahl’s Law predicts poor scaling.
- Fine-grained locking reduces the serial fraction and shifts the main limitations to hardware (cache coherence and memory latency), which is consistent with the observed efficiency plateau.

A precise derivation is not required, but acknowledging the relationship to Amdahl’s Law strengthens the theoretical grounding of the analysis.

---

## 7. Hardware Considerations

The behavior of the two synchronization strategies must be interpreted in the context of the underlying hardware:

- **CPU**: AMD Ryzen 9 5900HS, 8 physical cores, 16 logical threads (SMT), base 3.0 GHz, boost up to 4.6 GHz.
- **Caches**: 32 KB L1d per core, 512 KB L2 per core, 16 MB shared L3.
- **Memory**: LPDDR4x with significantly higher latency than cache (tens of nanoseconds for cache vs. ~100 ns for DRAM).

Key points for the report:

- SMT (hyper-threading) can improve throughput for memory-bound workloads by filling pipeline stalls, but cannot double performance.
- Cache coherence and cache capacity are fundamental limits on scalability for shared data structures.
- No synchronization strategy can avoid the basic costs of moving data between cores and main memory.

The report should briefly describe these hardware characteristics so that the scaling results are placed in proper context.

---

## 8. Structuring the Report

A reasonable outline for the final report is:

1. **Introduction**  
   - Motivate concurrent hash tables and synchronization design.  
   - State the main finding clearly (fine-grained vs. coarse-grained).

2. **Design and Implementation**  
   - Describe the data structure (1024 buckets, separate chaining).  
   - Explain the two synchronization strategies.  
   - Note any important implementation details relevant to correctness or performance.

3. **Experimental Methodology**  
   - Describe the benchmark harness, workloads, thread counts, dataset sizes, number of repetitions, and hardware.  
   - Briefly describe the analysis pipeline (CSV output, Python scripts for statistics and plotting).

4. **Results**  
   - Present throughput vs. threads plots for representative workloads and dataset sizes.  
   - Present speedup vs. threads with an ideal linear reference.  
   - Present dataset-size sensitivity and workload comparison plots.  
   - Use a few key tables to support the plots where precise numbers are important.

5. **Analysis and Discussion**  
   - Explain why coarse-grained locking fails to scale.  
   - Explain why fine-grained locking scales better but not perfectly.  
   - Relate the observations to cache hierarchy, coherence, SMT, and Amdahl’s Law.  
   - Discuss any surprising or non-obvious findings.

6. **Conclusion and Future Work**  
   - Restate the main conclusions.  
   - Suggest potential extensions such as reader–writer locks or lock-free designs.

---

## 9. Writing Style Guidelines

To keep the report professional and readable:

- Use **clear, direct sentences** and avoid unnecessary informal language.
- State quantitative results with approximate values where appropriate (for example, “about 49× higher throughput”).
- When making a claim, **refer to a specific figure or table** (for example, “Figure 3 shows that…”).
- Explain mechanisms, not just outcomes (for example, do not only say that coarse-grained locking scales poorly; explain why).
- Keep equations and formal models lightweight. A brief mention of Amdahl’s Law is sufficient; detailed derivations are not necessary.

---

## 10. Cross-Referencing Repository Artifacts

The report can and should refer to the concrete artifacts in the repository:

- **Code**: `src/*.hpp` and `src/*.cpp` for implementation details.
- **Benchmarks**: `benchmarks/benchmark` and `benchmarks/workloads.cpp` for workload definitions.
- **Results**: `results/raw/final_complete_results.csv` for the full dataset.
- **Derived tables**: `results/analysis/statistics.csv` and `results/analysis/speedup.csv` for summary metrics.
- **Plots**: `results/analysis/plots/*.png` for all figures.

By grounding the discussion in these artifacts, the report demonstrates reproducibility and makes it straightforward for a reader to verify claims.

---

## 11. Checklist Before Submission

Before finalizing the report, it is useful to confirm that:

- The main headline result (fine-grained vs. coarse-grained performance) is clearly stated in the introduction.
- At least one figure shows throughput vs. threads for both strategies on a representative dataset size.
- At least one figure shows speedup vs. threads with an ideal linear reference.
- At least one figure or table demonstrates the effect of dataset size (cache hierarchy) on throughput.
- The text explains why coarse-grained locking scales poorly and why fine-grained locking performs better.
- The hardware configuration and experimental methodology are described clearly enough that the experiments are reproducible.

If these items are satisfied, the report should adequately convey both the implementation work and the insights gained from the experiments.
