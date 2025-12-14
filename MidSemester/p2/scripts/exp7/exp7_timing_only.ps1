# Experiment 7: TLB-Miss Impact (Timing-Only Version)
# Shows TLB effects through runtime measurements
# Points: 25 (20-23 achievable without hardware counters)

param(
    [int]$Repetitions = 5
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 7: TLB-Miss Impact"
Write-Host "Timing-Only Version (No Hardware Counters)"
Write-Host "========================================"
Write-Host ""

# Configuration
$KERNEL_PATH = "..\..\bin\tlb_miss_kernel.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp7_tlb_miss.csv"
$LOG_FILE = "$OUTPUT_DIR\exp7_tlb_miss.log"

# Test configuration (fast mode)
$TOTAL_SIZE_MB = 50  # Smaller working set
$PAGE_STRIDE_KB = 4
$ITERATIONS = 500  # Fewer iterations (2x faster)

Write-Host "Configuration:"
Write-Host "  Kernel: $KERNEL_PATH"
Write-Host "  Total Size: $TOTAL_SIZE_MB MB"
Write-Host "  Page Stride: $PAGE_STRIDE_KB KB"
Write-Host "  Iterations: $ITERATIONS"
Write-Host "  Repetitions: $Repetitions"
Write-Host ""

# Check for kernel
if (-not (Test-Path $KERNEL_PATH)) {
    Write-Host "Error: Kernel not found at $KERNEL_PATH" -ForegroundColor Red
    Write-Host "Build with:" -ForegroundColor Yellow
    Write-Host "  cd ..\..\src\build" -ForegroundColor Yellow
    Write-Host "  cmake --build . --config Release" -ForegroundColor Yellow
    exit 1
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠ WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Large page allocation will likely fail" -ForegroundColor Yellow
    Write-Host "The experiment will still run with standard pages only" -ForegroundColor Yellow
    Write-Host ""
}

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging
Start-Transcript -Path $LOG_FILE -Force

# Initialize CSV
"run,use_large_pages,runtime_ms,time_per_iter_us,pages_per_sec,bandwidth_gbps" |
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
    
    # Run with standard pages
    $output = & $KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 0 2>&1 | Out-String
    
    # Parse output
    if ($output -match 'Total Time:\s+([\d.]+)\s+seconds') {
        $total_time_s = [double]$matches[1]
        $runtime_ms = $total_time_s * 1000
    } else {
        $runtime_ms = 0
    }
    
    if ($output -match 'Time per Iteration:\s+([\d.]+)\s+.s') {
        $time_per_iter_us = [double]$matches[1]
    } else {
        $time_per_iter_us = 0
    }
    
    if ($output -match 'Pages per Second:\s+([\d.]+)') {
        $pages_per_sec = [double]$matches[1]
    } else {
        $pages_per_sec = 0
    }
    
    if ($output -match 'Bandwidth:\s+([\d.]+)\s+GB/s') {
        $bandwidth_gbps = [double]$matches[1]
    } else {
        $bandwidth_gbps = 0
    }
    
    # Save to CSV
    "$run,0,$runtime_ms,$time_per_iter_us,$pages_per_sec,$bandwidth_gbps" |
        Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
    
    Write-Host "  Runtime: ${runtime_ms} ms" -ForegroundColor Green
    Write-Host "  Time/iter: ${time_per_iter_us} µs" -ForegroundColor Green
    Write-Host ""
    
    Start-Sleep -Milliseconds 500
}

# Phase 2: Large Pages (2MB)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 2: Large Pages (2MB)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not $isAdmin) {
    Write-Host "⚠ Skipping large page tests (requires Administrator)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To test large pages:" -ForegroundColor Yellow
    Write-Host "1. Close this PowerShell window" -ForegroundColor Yellow
    Write-Host "2. Right-click PowerShell → Run as Administrator" -ForegroundColor Yellow
    Write-Host "3. Run this script again" -ForegroundColor Yellow
} else {
    for ($run = 1; $run -le $Repetitions; $run++) {
        $test_num++
        Write-Host "[$test_num/$total_tests] Run $run/$Repetitions - 2MB large pages"
        
        # Run with large pages
        $output = & $KERNEL_PATH $TOTAL_SIZE_MB $PAGE_STRIDE_KB $ITERATIONS 1 2>&1 | Out-String
        
        # Check if large pages actually worked
        if ($output -match 'Using Large Pages') {
            $actually_large = $true
        } else {
            $actually_large = $false
            Write-Host "  ⚠ Large page allocation failed, using standard pages" -ForegroundColor Yellow
        }
        
        # Parse output
        if ($output -match 'Total Time:\s+([\d.]+)\s+seconds') {
            $total_time_s = [double]$matches[1]
            $runtime_ms = $total_time_s * 1000
        } else {
            $runtime_ms = 0
        }
        
        if ($output -match 'Time per Iteration:\s+([\d.]+)\s+.s') {
            $time_per_iter_us = [double]$matches[1]
        } else {
            $time_per_iter_us = 0
        }
        
        if ($output -match 'Pages per Second:\s+([\d.]+)') {
            $pages_per_sec = [double]$matches[1]
        } else {
            $pages_per_sec = 0
        }
        
        if ($output -match 'Bandwidth:\s+([\d.]+)\s+GB/s') {
            $bandwidth_gbps = [double]$matches[1]
        } else {
            $bandwidth_gbps = 0
        }
        
        # Save to CSV
        "$run,1,$runtime_ms,$time_per_iter_us,$pages_per_sec,$bandwidth_gbps" |
            Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
        
        Write-Host "  Runtime: ${runtime_ms} ms" -ForegroundColor Green
        Write-Host "  Time/iter: ${time_per_iter_us} µs" -ForegroundColor Green
        Write-Host ""
        
        Start-Sleep -Milliseconds 500
    }
}

Stop-Transcript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Experiment 7 Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Analysis will be done by separate script
Write-Host "Run analysis: cd ..\..\analysis; python analyze_exp7.py"

Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review runtime differences between page sizes"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp7.py"
Write-Host "3. Calculate DTLB reach: 64 entries × 4KB = 256KB vs 64 × 2MB = 128MB"
Write-Host "4. Explain performance differences using TLB theory"
Write-Host ""
Write-Host "Note: This timing-based approach demonstrates TLB effects without"
Write-Host "      requiring hardware counters. Performance improvement with large"
Write-Host "      pages proves the TLB-miss impact."
Write-Host ""
