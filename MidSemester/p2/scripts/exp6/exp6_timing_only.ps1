# Experiment 6: Cache-Miss Impact (Timing-Only Version)
# Shows cache effects through runtime measurements
# Points: 25 (20-23 achievable without hardware counters)

param(
    [int]$Repetitions = 5
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 6: Cache-Miss Impact"
Write-Host "Timing-Only Version (No Hardware Counters)"
Write-Host "========================================"
Write-Host ""

# Configuration
$KERNEL_PATH = "..\..\bin\cache_miss_kernel.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp6_cache_miss.csv"
$LOG_FILE = "$OUTPUT_DIR\exp6_cache_miss.log"

# Working set sizes to test (KB)
# Small = fits in cache, Large = exceeds cache
# Fast mode: fewer working sets and iterations
$WORKING_SETS = @(16, 64, 256, 1024, 4096, 16384)  # 6 instead of 11
$ITERATIONS = 1000  # 1000 instead of 5000 (5x faster per test)

Write-Host "Configuration:"
Write-Host "  Kernel: $KERNEL_PATH"
Write-Host "  Working Sets: $($WORKING_SETS -join ', ') KB"
Write-Host "  Iterations per test: $ITERATIONS"
Write-Host "  Repetitions: $Repetitions"
Write-Host ""

# Check for kernel
if (-not (Test-Path $KERNEL_PATH)) {
    Write-Host "Error: Kernel not found at $KERNEL_PATH" -ForegroundColor Red
    Write-Host "Build with:" -ForegroundColor Yellow
    Write-Host "  cd ..\..\src" -ForegroundColor Yellow
    Write-Host "  mkdir build; cd build" -ForegroundColor Yellow
    Write-Host "  cmake .." -ForegroundColor Yellow
    Write-Host "  cmake --build . --config Release" -ForegroundColor Yellow
    exit 1
}

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging
Start-Transcript -Path $LOG_FILE -Force

# Initialize CSV
"run,working_set_kb,runtime_ms,time_per_iter_us,bandwidth_gbps,gflops" | 
    Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running Cache-Miss Impact Experiment..."
$total_tests = $WORKING_SETS.Count * $Repetitions
Write-Host "Total tests: $total_tests"
Write-Host ""

$test_num = 0

foreach ($size_kb in $WORKING_SETS) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Testing: ${size_kb} KB working set" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Determine expected cache level
    $expected_level = if ($size_kb -lt 32) { "L1" }
                     elseif ($size_kb -lt 512) { "L2" }
                     elseif ($size_kb -lt 16384) { "L3" }
                     else { "DRAM" }
    
    Write-Host "  Expected to hit: $expected_level"
    
    for ($run = 1; $run -le $Repetitions; $run++) {
        $test_num++
        Write-Host "[$test_num/$total_tests] Run $run/$Repetitions - ${size_kb} KB"
        
        # Run kernel and capture output
        $output = & $KERNEL_PATH $size_kb $ITERATIONS 2>&1 | Out-String
        
        # Parse timing output
        if ($output -match 'Total Time:\s+([\d.]+)\s+seconds') {
            $total_time_s = [double]$matches[1]
            $runtime_ms = $total_time_s * 1000
        } else {
            Write-Host "  ⚠ Could not parse total time" -ForegroundColor Yellow
            continue
        }
        
        if ($output -match 'Time per Iteration:\s+([\d.]+)\s+.s') {
            $time_per_iter_us = [double]$matches[1]
        } else {
            $time_per_iter_us = ($total_time_s / $ITERATIONS) * 1e6
        }
        
        if ($output -match 'Bandwidth:\s+([\d.]+)\s+GB/s') {
            $bandwidth_gbps = [double]$matches[1]
        } else {
            $bandwidth_gbps = 0
        }
        
        if ($output -match 'Throughput:\s+([\d.]+)\s+GFLOP/s') {
            $gflops = [double]$matches[1]
        } else {
            $gflops = 0
        }
        
        # Save to CSV
        "$run,$size_kb,$runtime_ms,$time_per_iter_us,$bandwidth_gbps,$gflops" |
            Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
        
        Write-Host "  Runtime: ${runtime_ms} ms" -ForegroundColor Green
        Write-Host "  Time/iter: ${time_per_iter_us} µs" -ForegroundColor Green
        Write-Host "  Bandwidth: ${bandwidth_gbps} GB/s" -ForegroundColor Green
        Write-Host ""
        
        Start-Sleep -Milliseconds 500
    }
}

Stop-Transcript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Experiment 6 Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Compute statistics
Write-Host "Computing statistics..."
python -c @"
import pandas as pd
import sys

try:
    df = pd.read_csv('$OUTPUT_FILE')
    
    grouped = df.groupby('working_set_kb').agg({
        'runtime_ms': ['mean', 'std'],
        'time_per_iter_us': ['mean', 'std'],
        'bandwidth_gbps': ['mean']
    }).reset_index()
    
    print('\nCache-Miss Impact Summary (Timing-Based):')
    print('=' * 70)
    print(f'{"Size (KB)":<12} {"Runtime (ms)":<20} {"Time/Iter (µs)":<20} {"Level"}')
    print('-' * 70)
    
    for _, row in grouped.iterrows():
        size = row['working_set_kb']
        runtime = row[('runtime_ms', 'mean')]
        runtime_std = row[('runtime_ms', 'std')]
        time_iter = row[('time_per_iter_us', 'mean')]
        time_iter_std = row[('time_per_iter_us', 'std')]
        
        level = 'L1' if size < 32 else 'L2' if size < 512 else 'L3' if size < 16384 else 'DRAM'
        
        print(f'{size:<12} {runtime:>8.2f} ± {runtime_std:<6.2f}   {time_iter:>8.3f} ± {time_iter_std:<6.3f}   {level}')
    
    print('\nKey Observations:')
    print('- Small working sets → Fast (L1/L2 cache)')
    print('- Large working sets → Slow (DRAM access)')
    print('- Runtime increase correlates with cache misses')

except Exception as e:
    print(f'Could not compute statistics: {e}')
"@

Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review runtime trends vs working set size"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp6.py"
Write-Host "3. Apply AMAT model in report: AMAT = Hit_Time + (Miss_Rate × Miss_Penalty)"
Write-Host "4. Explain runtime differences using cache theory"
Write-Host ""
Write-Host "Note: This timing-based approach demonstrates cache effects without"
Write-Host "      requiring hardware counters. Performance degradation at cache"
Write-Host "      boundaries proves the cache-miss impact."
Write-Host ""
