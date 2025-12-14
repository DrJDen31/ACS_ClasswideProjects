#!/usr/bin/env python3
"""
Retry script for failed benchmark configurations
High timeout to ensure completion of slow 1M key benchmarks
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
EXISTING_RESULTS = SCRIPT_DIR / '../results/raw/focused_benchmark_1762902735.csv'
OUTPUT_FILE = SCRIPT_DIR / '../results/raw/retry_results.csv'

# Very high timeout for slow configs (10 minutes)
TIMEOUT_SECONDS = 600

def load_failed_configs():
    """Load configurations that failed in the original run"""
    failed = []
    
    with open(EXISTING_RESULTS, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['throughput_ops_sec'] == 'FAILED':
                failed.append({
                    'strategy': row['strategy'],
                    'workload': row['workload'],
                    'threads': int(row['threads']),
                    'size': int(row['dataset_size']),
                    'rep': int(row['repetition'])
                })
    
    return failed

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
    print("Project A4 - Retry Failed Benchmarks")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Timeout per config: {TIMEOUT_SECONDS} seconds ({TIMEOUT_SECONDS/60:.1f} minutes)")
    print()
    
    # Check if benchmark binary exists
    if not BENCHMARK_BIN.exists():
        print(f"ERROR: Benchmark binary not found at {BENCHMARK_BIN}")
        sys.exit(1)
    
    # Load failed configurations
    print("Loading failed configurations...")
    failed_configs = load_failed_configs()
    print(f"Found {len(failed_configs)} failed configurations to retry")
    print()
    
    # Estimate time
    avg_time_per_config = 180  # Conservative estimate: 3 minutes
    estimated_total = (len(failed_configs) * avg_time_per_config) / 60
    print(f"Estimated total time: {estimated_total:.1f} minutes ({estimated_total/60:.1f} hours)")
    print()
    
    # Open CSV file for writing
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['strategy', 'workload', 'threads', 'dataset_size', 'repetition', 'throughput_ops_sec'])
        
        run_count = 0
        success_count = 0
        failed_count = 0
        start_time = time.time()
        
        for config in failed_configs:
            run_count += 1
            
            # Progress with ETA
            elapsed = time.time() - start_time
            if run_count > 1:
                avg_time = elapsed / (run_count - 1)
                eta_seconds = avg_time * (len(failed_configs) - run_count)
                eta_min = int(eta_seconds / 60)
                eta_str = f"ETA: {eta_min}m"
            else:
                eta_str = "ETA: calculating..."
            
            print(f"[{run_count}/{len(failed_configs)}] {config['strategy']:6s} {config['workload']:6s} "
                  f"t={config['threads']:2d} n={config['size']:7d} rep={config['rep']} ({eta_str})", end=' ... ')
            sys.stdout.flush()
            
            throughput = run_single_benchmark(
                config['strategy'], config['workload'], 
                config['threads'], config['size'], config['rep']
            )
            
            if throughput is not None:
                writer.writerow([
                    config['strategy'], config['workload'], 
                    config['threads'], config['size'], config['rep'], 
                    throughput
                ])
                success_count += 1
                print(f"✓ {throughput/1e6:.2f} Mops/sec")
            else:
                failed_count += 1
                writer.writerow([
                    config['strategy'], config['workload'], 
                    config['threads'], config['size'], config['rep'], 
                    'FAILED'
                ])
                print(f"✗ STILL FAILED (timeout > {TIMEOUT_SECONDS}s)")
            
            # Flush after each run
            f.flush()
    
    elapsed_total = time.time() - start_time
    print()
    print("="*70)
    print(f"Retry benchmark complete!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {int(elapsed_total/60)}m {int(elapsed_total%60)}s")
    print(f"Successful runs: {success_count}/{len(failed_configs)}")
    print(f"Still failed: {failed_count}/{len(failed_configs)}")
    print(f"Success rate: {100*success_count/len(failed_configs):.1f}%")
    print(f"Retry results saved to: {OUTPUT_FILE}")
    print("="*70)
    print()
    print("Next step: Merge retry results with original data and re-analyze")

if __name__ == '__main__':
    main()
