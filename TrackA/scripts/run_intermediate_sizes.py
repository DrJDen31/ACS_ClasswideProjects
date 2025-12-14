#!/usr/bin/env python3
"""
Add intermediate dataset sizes to fill gaps in cache hierarchy analysis
Adds 50K (L2/LLC boundary) and 500K (mid-LLC) to existing data
"""

import subprocess
import csv
import sys
from pathlib import Path
import time
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent.absolute()
BENCHMARK_BIN = SCRIPT_DIR / '../benchmarks/benchmark'
OUTPUT_FILE = SCRIPT_DIR / '../results/raw/intermediate_sizes_results.csv'

# New intermediate sizes to test
NEW_SIZES = [50000, 500000]  # 50K and 500K

# Test configurations
STRATEGIES = ['coarse', 'fine']
WORKLOADS = ['lookup', 'insert', 'mixed']
THREAD_COUNTS = [1, 2, 4, 8, 16]
REPETITIONS = 5

# Timeout (should be fast for these sizes)
TIMEOUT_SECONDS = 120

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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=BENCHMARK_BIN.parent
        )
        
        if result.returncode != 0:
            return None
        
        # Parse CSV output line
        for line in result.stdout.split('\n'):
            if line.startswith('CSV:'):
                parts = line.split('CSV:')[1].strip().split(',')
                throughput = float(parts[5])
                return throughput
        
        return None
        
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"    EXCEPTION: {str(e)[:100]}")
        return None

def main():
    print("="*70)
    print("Project A4 - Adding Intermediate Dataset Sizes")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"Adding dataset sizes: {', '.join(map(str, NEW_SIZES))} keys")
    print(f"Cache hierarchy coverage:")
    print(f"  10K   →  L2 cache (512 KB)")
    print(f"  50K   →  L2/LLC boundary (2.4 MB) [NEW]")
    print(f"  100K  →  LLC (4.8 MB)")
    print(f"  500K  →  Mid-LLC (24 MB) [NEW]")
    print(f"  1M    →  DRAM (48 MB)")
    print()
    
    # Check if benchmark binary exists
    if not BENCHMARK_BIN.exists():
        print(f"ERROR: Benchmark binary not found at {BENCHMARK_BIN}")
        sys.exit(1)
    
    # Calculate total configurations
    total_configs = len(STRATEGIES) * len(WORKLOADS) * len(THREAD_COUNTS) * len(NEW_SIZES) * REPETITIONS
    total_unique = len(STRATEGIES) * len(WORKLOADS) * len(THREAD_COUNTS) * len(NEW_SIZES)
    
    print(f"Total configurations: {total_unique}")
    print(f"Total measurements: {total_configs} ({REPETITIONS} reps each)")
    
    # Estimate time
    avg_time_per_config = 45  # 50K and 500K should be fast
    estimated_minutes = (total_configs * avg_time_per_config) / 60
    print(f"Estimated time: {estimated_minutes:.1f} minutes ({estimated_minutes/60:.1f} hours)")
    print()
    
    # Open CSV file for writing
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['strategy', 'workload', 'threads', 'dataset_size', 'repetition', 'throughput_ops_sec'])
        
        run_count = 0
        success_count = 0
        failed_count = 0
        start_time = time.time()
        
        for strategy in STRATEGIES:
            for workload in WORKLOADS:
                for threads in THREAD_COUNTS:
                    for size in NEW_SIZES:
                        for rep in range(1, REPETITIONS + 1):
                            run_count += 1
                            
                            # Progress with ETA
                            elapsed = time.time() - start_time
                            if run_count > 1:
                                avg_time = elapsed / (run_count - 1)
                                eta_seconds = avg_time * (total_configs - run_count)
                                eta_min = int(eta_seconds / 60)
                                eta_str = f"ETA: {eta_min}m"
                            else:
                                eta_str = "ETA: calculating..."
                            
                            print(f"[{run_count}/{total_configs}] {strategy:6s} {workload:6s} "
                                  f"t={threads:2d} n={size:6d} rep={rep} ({eta_str})", end=' ... ')
                            sys.stdout.flush()
                            
                            throughput = run_single_benchmark(strategy, workload, threads, size, rep)
                            
                            if throughput is not None:
                                writer.writerow([strategy, workload, threads, size, rep, throughput])
                                success_count += 1
                                print(f"✓ {throughput/1e6:.2f} Mops/sec")
                            else:
                                failed_count += 1
                                writer.writerow([strategy, workload, threads, size, rep, 'FAILED'])
                                print(f"✗ FAILED")
                            
                            # Flush after each run
                            f.flush()
    
    elapsed_total = time.time() - start_time
    print()
    print("="*70)
    print(f"Intermediate size benchmarks complete!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {int(elapsed_total/60)}m {int(elapsed_total%60)}s")
    print(f"Successful runs: {success_count}/{total_configs}")
    print(f"Failed runs: {failed_count}/{total_configs}")
    print(f"Success rate: {100*success_count/total_configs:.1f}%")
    print(f"Results saved to: {OUTPUT_FILE}")
    print("="*70)
    print()
    print("Next step: Run merge script to combine with existing data")
    print("  python3 merge_all_results.py")

if __name__ == '__main__':
    main()
