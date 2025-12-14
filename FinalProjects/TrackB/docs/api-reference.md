# B2 API Reference

This document describes the public APIs for the three solutions in Track B Topic 2.

- **Solution 1** – DRAM-only baseline (HNSW in memory)
- **Solution 2** – Tiered DRAM+SSD system
- **Solution 3** – ANN-in-SSD simulator

The goal is that all three solutions share common configuration and logging paths so that a single set of scripts can launch and analyze runs across all of them.

---

## Common Types and Namespaces

- Namespace: `b2`
- Core types (from `src/core/`):
  - `VectorData`, `VectorID`
  - `DistanceMetric` and `compute_distance`
  - `Dataset`
- Storage layer abstractions (from `src/storage/`):
  - `StorageBackend` and `IOStats`

Details for each solution will be filled in as implementations solidify.

---

## Solution 1 – DRAM-Only Baseline

### Core Vector and Dataset APIs

- `vector.hpp`
  - Distance metric helpers used throughout the project.
- `dataset.hpp/cpp`
  - Dataset loading (e.g., `.fvecs` / `.bvecs`) and synthetic generation.

### ANN Index Interface

- `ann_index.hpp`
  - Abstract index interface used by Solution 1 and extended by other solutions.

### HNSW Baseline

- `hnsw.hpp/cpp`
  - DRAM-only HNSW implementation (graph build, search, save/load).

### Benchmarks and Drivers

- DRAM-only benchmark entrypoints (e.g., `benchmark_recall.cpp`, `benchmark_latency.cpp`).

---

## Solution 2 – Tiered DRAM+SSD

- Storage backends: `memory_backend`, `file_backend`, `tiered_backend`.
- Cache and admission policies.
- Tier-aware HNSW that uses `StorageBackend` instead of raw DRAM.

Details will be documented as the tiered implementation is built out.

---

## Solution 3 – ANN-in-SSD Simulator

- Simulator core: `ssd_simulator`, `ann_in_ssd_model`.
- Graph-in-flash representation and controller metadata.
- Configuration and logging schema as described in `ann_in_ssd_design.md`.

This section will be expanded once the simulator scaffolding and configuration path are implemented.
