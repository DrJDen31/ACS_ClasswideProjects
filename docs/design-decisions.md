# Design Decisions Log

Track key architectural and implementation choices for the tiered ANN system.

---

## Core Design Choices

### Distance Metric

- **Decision**: Support L2, inner product, and cosine similarity
- **Rationale**: Different applications prefer different metrics; flexibility is important
- **Implementation**: Function pointer or enum-based dispatch in hot path
- **Trade-offs**: Small overhead vs flexibility
- **Date**: [Initial setup]

### HNSW Parameters

- **Decision**: Default M=16, ef_construction=200
- **Rationale**: Standard values from HNSW paper; good balance of quality and speed
- **Trade-offs**: Can tune later based on experiments
- **Date**: [Initial setup]

### Node Serialization Format

- **Decision**: [To be decided]
- **Options**:
  1. Binary packed structs (fast, not portable)
  2. JSON (portable, slow, large)
  3. Custom binary format with versioning
  4. Protocol Buffers / FlatBuffers
- **Rationale**: [To be filled after analysis]
- **Date**: [TBD]

---

## Storage Layer Design

### Storage Interface Abstraction

- **Decision**: Abstract `StorageBackend` interface with multiple implementations
- **Rationale**:
  - Allows swapping DRAM, file, and tiered backends
  - Facilitates testing and comparison
  - Clean separation of concerns
- **Trade-offs**: Small virtual function overhead
- **Date**: [Initial setup]

### Batch I/O Interface

- **Decision**: Support both single and batch reads
- **Rationale**:
  - Single reads for simple implementation
  - Batch reads for I/O optimization (amortize syscall overhead)
- **Trade-offs**: More complex API
- **Date**: [Initial setup]

### Memory Backend

- **Decision**: [To be decided: hash map vs vector storage]
- **Options**:
  1. `std::unordered_map<VectorID, VectorData>` - flexible but overhead
  2. `std::vector<VectorData>` - assumes contiguous IDs, fast
- **Rationale**: [To be filled]
- **Date**: [TBD]

### File Backend I/O Method

- **Decision**: [To be decided: mmap vs direct I/O]
- **Options**:
  1. **mmap**: OS-managed paging, simple API
  2. **Direct I/O**: Explicit control, bypass page cache
  3. **Hybrid**: mmap with madvise hints
- **Rationale**: [To be filled after benchmarking]
- **Trade-offs**:
  - mmap: Easy but less control
  - Direct I/O: Complex but predictable
- **Date**: [TBD]

---

## Tiering Design

### Cache Eviction Policy

- **Decision**: Support multiple policies (LRU, LFU, ARC, custom)
- **Rationale**: No clear winner a priori; need experimental comparison
- **Implementation**: Strategy pattern with pluggable policies
- **Date**: [Initial setup]

### Admission Control Strategy

- **Decision**: [To be decided after profiling]
- **Options**:
  1. Top-K by degree (hub nodes)
  2. Entry layer always cached
  3. Random sampling
  4. Cluster-aware partitioning
  5. Learned admission policy
- **Rationale**: [To be filled after I/O profiling]
- **Date**: [TBD]

### Cache Coherency

- **Decision**: [To be decided]
- **Options**:
  1. Write-through (simple, no coherency issues for read-only index)
  2. Write-back (complex, better for index updates)
- **Rationale**: Since index is typically built once and queried many times, write-through is sufficient
- **Date**: [TBD]

---

## I/O Optimization Design

### Prefetching Strategy

- **Decision**: [To be decided after access pattern analysis]
- **Options**:
  1. One-hop prefetch (neighbors of current node)
  2. Two-hop prefetch (neighbors of neighbors)
  3. Trajectory-based prediction (ML model)
  4. Speculative prefetch based on search beam
- **Rationale**: [To be filled]
- **Trade-offs**: Accuracy vs overhead
- **Date**: [TBD]

### Graph Layout Optimization

- **Decision**: [To be decided]
- **Options**:
  1. Random layout (baseline)
  2. BFS ordering
  3. DFS ordering
  4. Graph partitioning (METIS)
  5. Cluster-aware placement
- **Rationale**: [To be filled after experiments]
- **Date**: [TBD]

---

## Simulator Design

### SSD Latency Model

- **Decision**: [To be decided]
- **Options**:
  1. Fixed latency per I/O
  2. Latency = base + queue_delay + transfer_time
  3. CDF-based model from real device traces
- **Rationale**: [To be filled]
- **Date**: [TBD]

### Queue Depth Modeling

- **Decision**: [To be decided]
- **Options**:
  1. Infinite queue (ignore queuing)
  2. Fixed queue depth with blocking
  3. Realistic NVMe queue (submission + completion queues)
- **Rationale**: [To be filled]
- **Date**: [TBD]

---

## Alternative Approaches Considered

### Use Existing HNSW Library (hnswlib)

- **Decision**: Maintain an in-house HNSW implementation for integration and also use hnswlib as a gold-standard DRAM baseline.
- **Rationale**:
  - Learning exercise and tight integration with the custom storage/tiering/ANN-in-SSD layers
  - hnswlib provides a realistic, highly optimized HNSW implementation to calibrate expectations and decouple "implementation quality" from high-level algorithm/architecture choices
  - Comparing our HNSW against hnswlib on the same SIFT subsets highlights which gaps are due to code/engineering vs theory/strategy
  - After introducing a diversified neighbor-selection heuristic and parallel HNSW build, our in-house HNSW now essentially matches hnswlib's recall on a 20k SIFT subset (recall@10 ≈ 1.0 with `M=24`, `ef_construction=300`, `ef_search=512`) and nearly matches it on full SIFT1M (recall@10 ≈ 0.9993), at the cost of substantially higher build time (minutes vs sub-second at 20k, tens of minutes vs expected shorter times at 1M). hnswlib remains the speed/engineering reference, while our HNSW is the integrated baseline for tiered and ANN-in-SSD experiments.
- **Trade-offs**: More code to maintain in-tree, but clearer separation between project-specific innovations and the state of the art for DRAM HNSW
- **Date**: [Initial setup; updated after SIFT subset + hnswlib comparison and HNSW heuristic/parallel-build improvements]

### Graph Structure Choice

- **Decision**: HNSW over alternatives (NSG, Vamana)
- **Rationale**:
  - Well-studied
  - High recall baseline
  - Clear hierarchical structure for tiering
- **Alternative Considered**:
  - DiskANN's Vamana graph (more disk-friendly but more complex)
  - IVF-based methods (simpler but lower recall)
- **Date**: [Initial setup]

---

## Open Questions

### Technical

1. Should we implement index updates (insertions/deletions) or read-only?

   - **Leaning towards**: Read-only for simplicity (build once, query many)

2. Multi-threading: per-query parallelism or concurrent queries?

   - **Options**: Both eventually, start with concurrent queries

3. SIMD: Hand-written intrinsics or rely on compiler auto-vectorization?
   - **Leaning towards**: Hand-written for hot path (distance computation)

### Experimental

1. What cache sizes to evaluate? (10%, 25%, 50%, 75%?)
2. Which datasets are most representative? (SIFT1M for dev, Deep1B for scale?)
3. How many queries for statistically significant results? (10K? 100K?)

---

## Decisions to Be Made

Priority order for next steps:

1. **High Priority**:

   - [ ] Node serialization format
   - [ ] Memory vs file backend implementation approach
   - [ ] Cache policy to implement first

2. **Medium Priority**:

   - [ ] Admission control strategy
   - [ ] Prefetching approach
   - [ ] Graph layout method

3. **Low Priority (Phase 6)**:
   - [ ] Compression/quantization
   - [ ] Computational storage simulation details
   - [ ] Multi-threading strategy

---

## Lessons Learned (To Be Updated)

### What Worked Well

- [To be filled during implementation]

### What Didn't Work

- [To be filled during implementation]

### Unexpected Findings

- [To be filled during experiments]

---

## References for Design Choices

- HNSW paper: Malkov & Yashunin, TPAMI 2018
- DiskANN: Jayaram Subramanya et al., NIPS 2019
- SPANN: Chen et al., NIPS 2021
- Cache policies: [To be added]
