# Literature Review: ANN Search and Tiered Storage

## Key Papers

### 1. DiskANN (NIPS 2019, VLDB 2023)
- **Title**: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node
- **Key Contributions**:
  - Vamana graph for disk-based ANN
  - Beamwidth search for SSD optimization
  - Graph layout for sequential I/O
- **Notes**: [To be filled after reading]

### 2. SPANN (NIPS 2021)
- **Title**: Highly-efficient Billion-scale Approximate Nearest Neighbor Search
- **Key Contributions**:
  - Memory-disk hybrid architecture
  - Partitioning with posting lists
  - Distributed search coordination
- **Notes**: [To be filled]

### 3. HNSW (TPAMI 2018)
- **Title**: Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs
- **Key Contributions**:
  - Hierarchical graph structure
  - Greedy navigation algorithm
  - High recall with low search complexity
- **Notes**: [To be filled]

### 4. Vamana Graph (NeurIPS 2019)
- **Title**: [To be filled]
- **Notes**: Graph construction algorithm for DiskANN

### 5. FAISS
- **Library**: Meta AI's similarity search library
- **Techniques**: IVF, PQ, HNSW implementations
- **Notes**: [To be explored]

## Storage Technologies

### NVMe SSD Characteristics
- Gen3: ~500K IOPS, ~20μs latency
- Gen4: ~1M IOPS, ~10μs latency
- Gen5 (emerging): ~2M IOPS, ~5μs latency

### Computational Storage
- Near-data processing
- Push computation to storage device
- Reduce PCIe traffic

## Caching Strategies

### Traditional Policies
- LRU (Least Recently Used)
- LFU (Least Frequently Used)
- ARC (Adaptive Replacement Cache)

### Graph-Aware Policies
- Degree-based (cache high-degree nodes)
- Centrality-based
- Entry-layer always cached

## Questions to Investigate

1. What is the optimal cache size for different SSD characteristics?
2. How does graph locality affect I/O patterns?
3. Can prefetching overcome SSD latency?
4. What is the cost-performance Pareto frontier?

## To Read

- [ ] DiskANN NIPS 2019
- [ ] DiskANN VLDB 2023 (extended)
- [ ] SPANN NIPS 2021
- [ ] HNSW TPAMI 2018
- [ ] Vamana graph paper
- [ ] FAISS documentation
- [ ] Recent ANN benchmarks (ann-benchmarks.com)
