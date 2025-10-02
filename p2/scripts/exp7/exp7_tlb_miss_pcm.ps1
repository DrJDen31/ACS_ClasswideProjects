# Experiment 7: TLB-Miss Impact (Windows/PCM Version)
# Measures TLB miss effects and large page benefits
# Points: 25 (10 + 10 + 5)
# Requires: Intel PCM, Administrator privileges for large pages

param(
    [int]$Repetitions = 5
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 7: TLB-Miss Impact (PCM)"
Write-Host "========================================"
Write-Host ""

# Configuration
$PCM_PATH = "C:\PCM\pcm-202509\build\bin\Release\pcm.exe"
$KERNEL_PATH = "..\..\bin\tlb_miss_kernel.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp7_tlb_miss.csv"
$LOG_FILE = "$OUTPUT_DIR\exp7_tlb_miss.log"

# Test configuration
$TOTAL_SIZE_MB = 100
$PAGE_STRIDE_KB = 4
$ITERATIONS = 1000

Write-Host "Configuration:"
Write-Host "  PCM: $PCM_PATH"
Write-Host "  Kernel: $KERNEL_PATH"
Write-Host "  Total Size: $TOTAL_SIZE_MB MB"
Write-Host "  Page Stride: $PAGE_STRIDE_KB KB"
Write-Host "  Iterations: $ITERATIONS"
Write-Host "  Repetitions: $Repetitions"
Write-Host ""

# Check for PCM
if (-not (Test-Path $PCM_PATH)) {
    Write-Host "Error: PCM not found at $PCM_PATH" -ForegroundColor Red
    Write-Host "Please build PCM or update PCM_PATH" -ForegroundColor Red
    exit 1
}

# Check for kernel
if (-not (Test-Path $KERNEL_PATH)) {
    Write-Host "Error: Kernel not found at $KERNEL_PATH" -ForegroundColor Red
    Write-Host "Build with: cd ..\..\src\build; cmake --build . --config Release" -ForegroundColor Red
    exit 1
}

# Check if running as administrator (needed for large pages)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠ WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Large page allocation may fail without admin privileges" -ForegroundColor Yellow
    Write-Host "To enable large pages, restart PowerShell as Administrator" -ForegroundColor Yellow
    Write-Host ""
}

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging
Start-Transcript -Path $LOG_FILE -Force

# Initialize CSV
"run,use_large_pages,runtime_ms,dtlb_load_mpki,dtlb_store_mpki,itlb_mpki,l1_mpki,l2_mpki,l3_mpki,instructions,cycles,ipc" |
    Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running TLB-Miss Impact Experiment..."
Write-Host ""

# Phase 1: Standard 4KB Pages
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 1: Standard 4KB Pages" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$test_num = 0
$total_tests = $Repetitions * 2

for ($run = 1; $run -le $Repetitions; $run++) {
    $test_num++
    Write-Host "[$test_num/$total_tests] Run $run/$Repetitions - 4KB pages"
    
    # Run with standard pages (use_large_pages=0)
    $pcm_output = & $PCM_PATH -r -- $KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 0 2>&1 | Out-String
    
    # Parse kernel output
    if ($pcm_output -match 'Total Time:\s+([\d.]+)') {
        $runtime_s = [double]$matches[1]
        $runtime_ms = $runtime_s * 1000
    } else {
        $runtime_ms = 0
    }
    
    # Parse PCM output (if available)
    $dtlb_load_mpki = 0
    $dtlb_store_mpki = 0
    $itlb_mpki = 0
    $l1_mpki = 0
    $l2_mpki = 0
    $l3_mpki = 0
    $instructions = 0
    $cycles = 0
    $ipc = 0
    
    if ($pcm_output -match 'DTLB.*load.*MPKI:\s+([\d.]+)') {
        $dtlb_load_mpki = [double]$matches[1]
    }
    if ($pcm_output -match 'IPC:\s+([\d.]+)') {
        $ipc = [double]$matches[1]
    }
    
    # Save to CSV
    "$run,0,$runtime_ms,$dtlb_load_mpki,$dtlb_store_mpki,$itlb_mpki,$l1_mpki,$l2_mpki,$l3_mpki,$instructions,$cycles,$ipc" |
        Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
    
    Write-Host "  Runtime: ${runtime_ms} ms" -ForegroundColor Green
    Write-Host "  IPC: ${ipc}" -ForegroundColor Green
    Write-Host ""
    
    Start-Sleep -Milliseconds 1000
}

# Phase 2: Large Pages (2MB)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 2: Large Pages (2MB)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not $isAdmin) {
    Write-Host "⚠ Skipping large page tests (requires Administrator)" -ForegroundColor Yellow
    Write-Host "To test large pages, run this script as Administrator" -ForegroundColor Yellow
} else {
    for ($run = 1; $run -le $Repetitions; $run++) {
        $test_num++
        Write-Host "[$test_num/$total_tests] Run $run/$Repetitions - 2MB large pages"
        
        # Run with large pages (use_large_pages=1)
        $pcm_output = & $PCM_PATH -r -- $KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 1 2>&1 | Out-String
        
        # Parse kernel output
        if ($pcm_output -match 'Total Time:\s+([\d.]+)') {
            $runtime_s = [double]$matches[1]
            $runtime_ms = $runtime_s * 1000
        } else {
            $runtime_ms = 0
        }
        
        # Parse PCM output
        $dtlb_load_mpki = 0
        $ipc = 0
        
        if ($pcm_output -match 'DTLB.*load.*MPKI:\s+([\d.]+)') {
            $dtlb_load_mpki = [double]$matches[1]
        }
        if ($pcm_output -match 'IPC:\s+([\d.]+)') {
            $ipc = [double]$matches[1]
        }
        
        # Save to CSV
        "$run,1,$runtime_ms,$dtlb_load_mpki,$dtlb_store_mpki,$itlb_mpki,$l1_mpki,$l2_mpki,$l3_mpki,$instructions,$cycles,$ipc" |
            Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
        
        Write-Host "  Runtime: ${runtime_ms} ms" -ForegroundColor Green
        Write-Host "  IPC: ${ipc}" -ForegroundColor Green
        Write-Host ""
        
        Start-Sleep -Milliseconds 1000
    }
}

Stop-Transcript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Experiment 7 Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""

# Compute comparison
Write-Host "Computing statistics..."
python << 'EOF'
import pandas as pd
import sys

try:
    df = pd.read_csv("../../data/raw/exp7_tlb_miss.csv")
    
    grouped = df.groupby('use_large_pages').agg({
        'runtime_ms': ['mean', 'std'],
        'ipc': ['mean']
    }).reset_index()
    
    print("\nTLB-Miss Impact Summary:")
    print("=" * 60)
    
    for _, row in grouped.iterrows():
        page_type = "2MB Large Pages" if row['use_large_pages'] == 1 else "4KB Standard"
        runtime = row[('runtime_ms', 'mean')]
        runtime_std = row[('runtime_ms', 'std')]
        ipc = row[('ipc', 'mean')]
        
        print(f"{page_type}: {runtime:.2f} ± {runtime_std:.2f} ms, IPC: {ipc:.3f}")
    
    if len(grouped) == 2:
        std_runtime = grouped[grouped['use_large_pages']==0][('runtime_ms', 'mean')].values[0]
        large_runtime = grouped[grouped['use_large_pages']==1][('runtime_ms', 'mean')].values[0]
        speedup = (std_runtime / large_runtime - 1) * 100
        print(f"\nPerformance improvement: {speedup:+.1f}%")

except Exception as e:
    print(f"Could not compute statistics: {e}")
EOF

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review TLB miss rate differences"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp7.py"
Write-Host "3. Calculate DTLB reach for both page sizes"
Write-Host "4. Discuss performance impact"
Write-Host ""
