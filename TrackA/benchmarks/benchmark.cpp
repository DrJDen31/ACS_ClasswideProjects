#include "workloads.hpp"
#include "coarse_hash_table.hpp"
#include "fine_hash_table.hpp"
#include <iostream>
#include <iomanip>
#include <string>
#include <cstring>

using namespace a4;

void print_usage(const char* prog_name) {
    std::cout << "Usage: " << prog_name << " [options]\n"
              << "Options:\n"
              << "  --strategy <coarse|fine>    Synchronization strategy\n"
              << "  --workload <lookup|insert|mixed>  Workload type\n"
              << "  --threads <N>               Number of threads\n"
              << "  --size <N>                  Dataset size\n"
              << "  --operations <N>            Total operations (default: size * 10)\n"
              << "  --seed <N>                  Random seed (default: 12345)\n"
              << "  --help                      Show this help\n";
}

int main(int argc, char* argv[]) {
    // Default parameters
    std::string strategy = "coarse";
    std::string workload = "lookup";
    size_t num_threads = 1;
    size_t dataset_size = 10000;
    size_t num_operations = 0;  // Will be set to dataset_size * 10 if not specified
    uint64_t seed = 12345;
    
    // Parse command line arguments
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--strategy") == 0 && i + 1 < argc) {
            strategy = argv[++i];
        } else if (strcmp(argv[i], "--workload") == 0 && i + 1 < argc) {
            workload = argv[++i];
        } else if (strcmp(argv[i], "--threads") == 0 && i + 1 < argc) {
            num_threads = std::stoull(argv[++i]);
        } else if (strcmp(argv[i], "--size") == 0 && i + 1 < argc) {
            dataset_size = std::stoull(argv[++i]);
        } else if (strcmp(argv[i], "--operations") == 0 && i + 1 < argc) {
            num_operations = std::stoull(argv[++i]);
        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            seed = std::stoull(argv[++i]);
        } else if (strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            std::cerr << "Unknown option: " << argv[i] << std::endl;
            print_usage(argv[0]);
            return 1;
        }
    }
    
    // Set default operations if not specified
    if (num_operations == 0) {
        num_operations = dataset_size * 10;
    }
    
    // Create hash table based on strategy
    HashTable* table = nullptr;
    if (strategy == "coarse") {
        table = new CoarseHashTable();
    } else if (strategy == "fine") {
        table = new FineHashTable();
    } else {
        std::cerr << "Unknown strategy: " << strategy << std::endl;
        return 1;
    }
    
    // Determine workload type
    WorkloadType wl_type;
    if (workload == "lookup") {
        wl_type = WorkloadType::LOOKUP_ONLY;
    } else if (workload == "insert") {
        wl_type = WorkloadType::INSERT_ONLY;
    } else if (workload == "mixed") {
        wl_type = WorkloadType::MIXED_70_30;
    } else {
        std::cerr << "Unknown workload: " << workload << std::endl;
        delete table;
        return 1;
    }
    
    // Create workload configuration
    WorkloadConfig config(wl_type, dataset_size, num_operations, num_threads, seed);
    
    // Print configuration
    std::cout << "Benchmark Configuration:" << std::endl;
    std::cout << "  Strategy:     " << strategy << std::endl;
    std::cout << "  Workload:     " << workload << std::endl;
    std::cout << "  Threads:      " << num_threads << std::endl;
    std::cout << "  Dataset Size: " << dataset_size << std::endl;
    std::cout << "  Operations:   " << num_operations << std::endl;
    std::cout << "  Seed:         " << seed << std::endl;
    std::cout << std::endl;
    
    // Run benchmark
    std::cout << "Running benchmark..." << std::flush;
    double throughput = run_workload(table, config);
    std::cout << " Done!" << std::endl;
    
    // Print results
    std::cout << std::endl;
    std::cout << "Results:" << std::endl;
    std::cout << "  Throughput:   " << std::fixed << std::setprecision(2) 
              << throughput << " ops/sec" << std::endl;
    std::cout << "  Throughput:   " << std::fixed << std::setprecision(4)
              << (throughput / 1e6) << " Mops/sec" << std::endl;
    std::cout << "  Final Size:   " << table->size() << std::endl;
    
    // Output in CSV format for easy parsing
    std::cout << std::endl;
    std::cout << "CSV: " << strategy << "," << workload << "," 
              << num_threads << "," << dataset_size << "," 
              << num_operations << "," << std::fixed << std::setprecision(2)
              << throughput << std::endl;
    
    delete table;
    return 0;
}
