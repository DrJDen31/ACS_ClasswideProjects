#!/usr/bin/env python3
"""
Final merge: original (375) + intermediate (300) + intermediate retry
Creates complete dataset with all 5 dataset sizes
"""

import pandas as pd
import subprocess
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.absolute()
ORIGINAL_RESULTS = SCRIPT_DIR / '../results/raw/complete_benchmark_results.csv'
INTERMEDIATE_RESULTS = SCRIPT_DIR / '../results/raw/intermediate_sizes_results.csv'
RETRY_RESULTS = SCRIPT_DIR / '../results/raw/intermediate_retry_results.csv'
FINAL_RESULTS = SCRIPT_DIR / '../results/raw/final_complete_results.csv'


def merge_results():
    """Merge all three result files"""
    print("=" * 70)
    print("Final Merge - All Benchmark Results")
    print("=" * 70)
    print()

    # Load original results (10K, 100K, 1M)
    print("Loading original results (10K, 100K, 1M)...")
    original_df = pd.read_csv(ORIGINAL_RESULTS)
    print(f"  Loaded: {len(original_df)} rows")
    original_failed = len(original_df[original_df['throughput_ops_sec'] == 'FAILED'])
    print(f"  Success: {len(original_df) - original_failed}/{len(original_df)}")

    # Load intermediate results (50K, 500K)
    print("\nLoading intermediate results (50K, 500K)...")
    intermediate_df = pd.read_csv(INTERMEDIATE_RESULTS)
    print(f"  Loaded: {len(intermediate_df)} rows")
    intermediate_failed_count = len(intermediate_df[intermediate_df['throughput_ops_sec'] == 'FAILED'])
    print(f"  Failed: {intermediate_failed_count}")

    # Load retry results (if exists)
    if RETRY_RESULTS.exists():
        print("\nLoading retry results...")
        retry_df = pd.read_csv(RETRY_RESULTS)
        print(f"  Loaded: {len(retry_df)} rows")

        # Create retry lookup
        def make_key(row):
            return f"{row['strategy']},{row['workload']},{row['threads']},{row['dataset_size']},{row['repetition']}"

        retry_lookup = {}
        for _, row in retry_df.iterrows():
            key = make_key(row)
            retry_lookup[key] = row['throughput_ops_sec']

        print("\nMerging intermediate + retry...")
        # Replace FAILEDs in intermediate with retry results
        replaced_count = 0
        still_failed_count = 0

        merged_intermediate = []
        for _, row in intermediate_df.iterrows():
            if row['throughput_ops_sec'] == 'FAILED':
                key = make_key(row)
                if key in retry_lookup:
                    retry_value = retry_lookup[key]
                    if retry_value != 'FAILED':
                        row['throughput_ops_sec'] = retry_value
                        replaced_count += 1
                    else:
                        still_failed_count += 1
            merged_intermediate.append(row)

        intermediate_df = pd.DataFrame(merged_intermediate)
        print(f"  Replaced {replaced_count} FAILEDs with successful retries")
        print(f"  Still failed: {still_failed_count}")
    else:
        print("\nNo retry results found (skipping retry merge)")

    # Combine original + intermediate
    print("\nCombining all datasets...")
    final_df = pd.concat([original_df, intermediate_df], ignore_index=True)

    # Sort by strategy, workload, threads, size, rep
    final_df = final_df.sort_values(['strategy', 'workload', 'threads', 'dataset_size', 'repetition'])

    # Save
    print(f"Saving final results to: {FINAL_RESULTS}")
    final_df.to_csv(FINAL_RESULTS, index=False)

    # Statistics
    total = len(final_df)
    failed = len(final_df[final_df['throughput_ops_sec'] == 'FAILED'])
    success = total - failed

    print()
    print("=" * 70)
    print("Final Merge Complete!")
    print("=" * 70)
    print(f"Total measurements: {total}")
    print(f"Successful: {success} ({100 * success / total:.1f}%)")
    print(f"Failed: {failed} ({100 * failed / total:.1f}%)")
    print()

    # Show dataset size breakdown
    print("Dataset sizes covered:")
    sizes = final_df['dataset_size'].unique()
    sizes = sorted([int(s) for s in sizes if s != 'FAILED'])
    for size in sizes:
        size_data = final_df[final_df['dataset_size'] == size]
        total_size = len(size_data)
        failed_size = len(size_data[size_data['throughput_ops_sec'] == 'FAILED'])
        success_size = total_size - failed_size
        print(f"  {size:7d} keys: {success_size:3d}/{total_size:3d} successful ({100 * success_size / total_size:.1f}%)")

    print()
    print(f"FINAL DATASET: {len(sizes)} dataset sizes with {success}/{total} measurements")
    print()

    return FINAL_RESULTS


def run_analysis(results_file):
    """Run analysis on final merged results"""
    print("=" * 70)
    print("Running Analysis on Complete Dataset")
    print("=" * 70)
    print()

    analyze_cmd = [
        'python3',
        str(SCRIPT_DIR / 'analyze_results.py'),
        str(results_file),
        str(SCRIPT_DIR / '../results/analysis'),
    ]

    subprocess.run(analyze_cmd, check=True)


def generate_plots(results_file):
    """Generate plots from final merged results"""
    print()
    print("=" * 70)
    print("Generating Plots with 5-Point Curves")
    print("=" * 70)
    print()

    plot_cmd = [
        'python3',
        str(SCRIPT_DIR / 'generate_plots.py'),
        str(results_file),
        # Standardized plot output directory to results/analysis/plots
        str(SCRIPT_DIR / '../results/analysis/plots'),
    ]

    subprocess.run(plot_cmd, check=True)


def main():
    # Merge all results
    merged_file = merge_results()

    # Re-run analysis
    run_analysis(merged_file)

    # Regenerate plots
    generate_plots(merged_file)

    print()
    print("=" * 70)
    print("🎉 ALL COMPLETE! 🎉")
    print("=" * 70)
    print()
    print("Dataset now includes 5 sizes:")
    print("  10K   → L2 cache")
    print("  50K   → L2/LLC boundary")
    print("  100K  → LLC")
    print("  500K  → Mid-LLC/DRAM")
    print("  1M    → DRAM-bound")
    print()
    print("All plots updated with smooth 5-point curves!")
    print("Ready for report writing! 📝")
    print("=" * 70)


if __name__ == '__main__':
    main()
