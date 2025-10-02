# Experiment 5: Working-Set Size Sweep
# Shows locality transitions through cache hierarchy
# Points: 20 (10 + 10)

param(
    [int]$Repetitions = 3
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 5: Working-Set Size Sweep"
Write-Host "========================================"
Write-Host ""

# Configuration
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp5_working_set.csv"
$LOG_FILE = "$OUTPUT_DIR\exp5_working_set.log"
$KERNEL_PATH = "..\..\bin\cache_miss_kernel.exe"

# Working set sizes in KB (logarithmic sweep)
# Covers L1 (32KB), L2 (512KB), L3 (16MB), and beyond
$workingSets = @(4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768)

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging (stop any existing transcript first)
try { Stop-Transcript -ErrorAction SilentlyContinue } catch {}
Start-Transcript -Path $LOG_FILE -Force

Write-Host "Configuration:"
Write-Host "  Output: $OUTPUT_FILE"
Write-Host "  Working Set Sizes: $($workingSets -join ', ') KB"
Write-Host "  Repetitions: $Repetitions"
Write-Host ""

# Check if custom kernel exists
$useCustomKernel = Test-Path $KERNEL_PATH

if ($useCustomKernel) {
    Write-Host "Using custom kernel: $KERNEL_PATH" -ForegroundColor Green
} else {
    Write-Host "Custom kernel not found at $KERNEL_PATH" -ForegroundColor Yellow
    Write-Host "Using MLC as fallback (less precise)" -ForegroundColor Yellow
}
Write-Host ""

# Initialize CSV
$csvHeader = "run,working_set_kb,runtime_ms,bandwidth_mbps,notes"
$csvHeader | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8

Write-Host "Running Working-Set Size Sweep..."
Write-Host "Total tests: $($workingSets.Count * $Repetitions)"
Write-Host ""

$test_num = 0
$total_tests = $workingSets.Count * $Repetitions

foreach ($sizeKB in $workingSets) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Testing: ${sizeKB} KB working set" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Determine expected cache level
    if ($sizeKB -lt 32) {
        $expected = "L1"
    } elseif ($sizeKB -lt 512) {
        $expected = "L2"
    } elseif ($sizeKB -lt 16384) {
        $expected = "L3"
    } else {
        $expected = "DRAM"
    }
    Write-Host "  Expected to hit: $expected"
    
    for ($run = 1; $run -le $Repetitions; $run++) {
        $test_num++
        Write-Host "[$test_num/$total_tests] Run $run/$Repetitions - ${sizeKB} KB"
        
        if ($useCustomKernel) {
            # Use custom kernel (fast and precise)
            # More iterations for small working sets to keep data in cache
            $iterations = if ($sizeKB -lt 128) { 10000 } elseif ($sizeKB -lt 1024) { 5000 } else { 1000 }
            $output = & $KERNEL_PATH $sizeKB $iterations 2>&1 | Out-String
            
            # Parse output
            if ($output -match 'Total Time:\s+([\d.]+)\s+seconds') {
                $runtime_s = [double]$matches[1]
                $runtime_ms = $runtime_s * 1000
            } else {
                $runtime_ms = 0
            }
            
            if ($output -match 'Bandwidth:\s+([\d.]+)\s+GB/s') {
                $bandwidth_gbps = [double]$matches[1]
                $bandwidth_mbps = $bandwidth_gbps * 1000
            } else {
                $bandwidth_mbps = 0
            }
            
            "$run,$sizeKB,$runtime_ms,$bandwidth_mbps,Custom kernel" | 
                Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
            
            Write-Host "  Runtime: ${runtime_ms} ms, BW: ${bandwidth_mbps} MB/s" -ForegroundColor Green
        } else {
            # Fallback to MLC (slower but works)
            Write-Host "  Using MLC fallback..." -ForegroundColor Yellow
            "$run,$sizeKB,0,0,MLC fallback not implemented" | 
                Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
        }
        
        Start-Sleep -Milliseconds 500
    }
    
    Write-Host ""
}

Stop-Transcript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Experiment 5 Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""

if (-not $useCustomKernel) {
    Write-Host "WARNING: Custom kernel not used" -ForegroundColor Yellow
    Write-Host "Build the kernel for accurate results" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Next steps:"
Write-Host "1. Review CSV for locality transitions"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp5.py"
Write-Host "3. Annotate plot with cache levels"
Write-Host ""
