#!/usr/bin/env python3
"""
Focused benchmark runner for Project A4
Optimized to skip slow configurations and complete faster
"""

import subprocess
import csv
import os
import sys
from pathlib import Path
import time
from datetime import datetime

# Optimized configuration
STRATEGIES = ['coarse', 'fine']
WORKLOADS = ['lookup', 'insert', 'mixed']
THREAD_COUNTS = [1, 2, 4, 8, 16]
REPETITIONS = 5

# Smart dataset sizing: skip 1M for coarse-grained as it times out
DATASET_CONFIG = {
    'coarse': [10000, 100000],  # Skip 1M - too slow
    'fine': [10000, 100000, 1000000]  # Include all sizes
}

# Paths
SCRIPT_DIR = Path(__file__).parent.absolute()
BENCHMARK_BIN = SCRIPT_DIR / '../benchmarks/benchmark'
RESULTS_DIR = SCRIPT_DIR / '../results/raw'

def run_single_benchmark(strategy, workload, threads, size, rep):
    """Run a single benchmark configuration"""
    cmd = [
        str(BENCHMARK_BIN),
        '--strategy', strategy,
        '--workload', workload,
        '--threads', str(threads),
        '--size', str(size),
        '--seed', str(12345 + rep)
    ]
    
    try:
        # Longer timeout for large datasets
        timeout = 120 if size == 1000000 else 60
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=BENCHMARK_BIN.parent
        )
        
        if result.returncode != 0:
            print(f"    ERROR: {result.stderr[:100]}")
            return None
        
        # Parse CSV output line
        for line in result.stdout.split('\n'):
            if line.startswith('CSV:'):
                parts = line.split('CSV:')[1].strip().split(',')
                throughput = float(parts[5])
                return throughput
        
        return None
        
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT")
        return None
    except Exception as e:
        print(f"    EXCEPTION: {str(e)[:100]}")
        return None

def main():
    print("="*70)
    print("Project A4 - Focused Benchmark Suite")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Optimizations:")
    print("  - Skipping 1M keys for coarse-grained (too slow)")
    print("  - 5 repetitions for better statistics")
    print("  - Increased timeout for large datasets")
    print()
    
    # Check if benchmark binary exists
    if not BENCHMARK_BIN.exists():
        print(f"ERROR: Benchmark binary not found at {BENCHMARK_BIN}")
        sys.exit(1)
    
    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Calculate total runs
    total_runs = 0
    for strategy in STRATEGIES:
        total_runs += len(WORKLOADS) * len(THREAD_COUNTS) * len(DATASET_CONFIG[strategy]) * REPETITIONS
    
    print(f"Total configurations: {total_runs}")
    print()
    
    # Open CSV file for writing
    csv_file = RESULTS_DIR / f'focused_benchmark_{int(time.time())}.csv'
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['strategy', 'workload', 'threads', 'dataset_size', 'repetition', 'throughput_ops_sec'])
        
        run_count = 0
        failed_count = 0
        start_time = time.time()
        
        for strategy in STRATEGIES:
            dataset_sizes = DATASET_CONFIG[strategy]
            
            for workload in WORKLOADS:
                for threads in THREAD_COUNTS:
                    for size in dataset_sizes:
                        for rep in range(1, REPETITIONS + 1):
                            run_count += 1
                            
                            # Progress with ETA
                            elapsed = time.time() - start_time
                            if run_count > 1:
                                avg_time = elapsed / (run_count - 1)
                                eta_seconds = avg_time * (total_runs - run_count)
                                eta_min = int(eta_seconds / 60)
                                eta_str = f"ETA: {eta_min}m"
                            else:
                                eta_str = "ETA: calculating..."
                            
                            print(f"[{run_count}/{total_runs}] {strategy:6s} {workload:6s} "
                                  f"t={threads:2d} n={size:7d} rep={rep} ({eta_str})", end=' ... ')
                            sys.stdout.flush()
                            
                            throughput = run_single_benchmark(strategy, workload, threads, size, rep)
                            
                            if throughput is not None:
                                writer.writerow([strategy, workload, threads, size, rep, throughput])
                                print(f"✓ {throughput/1e6:.2f} Mops/sec")
                            else:
                                failed_count += 1
                                writer.writerow([strategy, workload, threads, size, rep, 'FAILED'])
                                print("✗ FAILED")
                            
                            # Flush after each run
                            f.flush()
    
    elapsed_total = time.time() - start_time
    print()
    print("="*70)
    print(f"Benchmark suite complete!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {int(elapsed_total/60)}m {int(elapsed_total%60)}s")
    print(f"Successful runs: {run_count - failed_count}/{total_runs}")
    print(f"Failed runs: {failed_count}")
    print(f"Results saved to: {csv_file}")
    print("="*70)

if __name__ == '__main__':
    main()
