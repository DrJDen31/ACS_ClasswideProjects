# Experiment 6: Cache-Miss Impact (Windows/PCM Version)
# Correlates cache miss rate with kernel performance
# Points: 25 (10 + 10 + 5)
# Requires: Intel PCM

param(
    [int]$Repetitions = 5
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Experiment 6: Cache-Miss Impact (PCM)"
Write-Host "========================================"
Write-Host ""

# Configuration
$PCM_PATH = "C:\PCM\pcm-202509\build\bin\Release\pcm.exe"
$KERNEL_PATH = "..\..\bin\cache_miss_kernel.exe"
$OUTPUT_DIR = "..\..\data\raw"
$OUTPUT_FILE = "$OUTPUT_DIR\exp6_cache_miss.csv"
$LOG_FILE = "$OUTPUT_DIR\exp6_cache_miss.log"

# Working set sizes to test (KB)
$WORKING_SETS = @(16, 64, 256, 1024, 4096, 16384, 32768)
$ITERATIONS = 10000

Write-Host "Configuration:"
Write-Host "  PCM: $PCM_PATH"
Write-Host "  Kernel: $KERNEL_PATH"
Write-Host "  Working Sets: $($WORKING_SETS -join ', ') KB"
Write-Host "  Iterations per test: $ITERATIONS"
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

# Create output directory
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Start logging
Start-Transcript -Path $LOG_FILE -Force

# Initialize CSV
"run,working_set_kb,runtime_ms,l2_misses,l3_misses,l2_hit_ratio,l3_hit_ratio,instructions,cycles,ipc" | 
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
    
    for ($run = 1; $run -le $Repetitions; $run++) {
        $test_num++
        Write-Host "[$test_num/$total_tests] Run $run/$Repetitions - ${size_kb} KB"
        
        # Run kernel with PCM monitoring
        # Note: PCM requires administrator privileges
        $pcm_output = & $PCM_PATH -r -- $KERNEL_PATH $size_kb $ITERATIONS 2>&1 | Out-String
        
        # Parse kernel output
        if ($pcm_output -match 'Total Time:\s+([\d.]+)') {
            $runtime_s = [double]$matches[1]
            $runtime_ms = $runtime_s * 1000
        } else {
            $runtime_ms = 0
            Write-Host "  ⚠ Could not parse runtime" -ForegroundColor Yellow
        }
        
        # Parse PCM output
        # PCM provides L2/L3 cache statistics
        $l2_misses = 0
        $l3_misses = 0
        $l2_hit_ratio = 0
        $l3_hit_ratio = 0
        $instructions = 0
        $cycles = 0
        $ipc = 0
        
        # Try to extract metrics from PCM output
        if ($pcm_output -match 'L2 MPI:\s+([\d.]+)') {
            $l2_misses = [double]$matches[1]
        }
        if ($pcm_output -match 'L3 MPI:\s+([\d.]+)') {
            $l3_misses = [double]$matches[1]
        }
        if ($pcm_output -match 'L2 hit ratio:\s+([\d.]+)') {
            $l2_hit_ratio = [double]$matches[1]
        }
        if ($pcm_output -match 'L3 hit ratio:\s+([\d.]+)') {
            $l3_hit_ratio = [double]$matches[1]
        }
        if ($pcm_output -match 'Instructions retired:\s+([\d,]+)') {
            $instructions = $matches[1] -replace ',',''
        }
        if ($pcm_output -match 'Cycles:\s+([\d,]+)') {
            $cycles = $matches[1] -replace ',',''
        }
        if ($pcm_output -match 'IPC:\s+([\d.]+)') {
            $ipc = [double]$matches[1]
        }
        
        # Save to CSV
        "$run,$size_kb,$runtime_ms,$l2_misses,$l3_misses,$l2_hit_ratio,$l3_hit_ratio,$instructions,$cycles,$ipc" |
            Out-File -FilePath $OUTPUT_FILE -Append -Encoding UTF8
        
        Write-Host "  Runtime: ${runtime_ms} ms" -ForegroundColor Green
        Write-Host "  L2 Hit Ratio: ${l2_hit_ratio}%" -ForegroundColor Green
        Write-Host "  L3 Hit Ratio: ${l3_hit_ratio}%" -ForegroundColor Green
        Write-Host "  IPC: ${ipc}" -ForegroundColor Green
        Write-Host ""
        
        Start-Sleep -Milliseconds 1000
    }
}

Stop-Transcript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Experiment 6 Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output file: $OUTPUT_FILE"
Write-Host "Log file: $LOG_FILE"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review CSV for cache miss correlation"
Write-Host "2. Run: cd ..\..\analysis; python analyze_exp6.py"
Write-Host "3. Apply AMAT model to explain results"
Write-Host ""
Write-Host "Note: If PCM data is incomplete, you may need to:"
Write-Host "  - Run PowerShell as Administrator"
Write-Host "  - Install Intel PCM driver"
Write-Host "  - Use alternative PCM tools (pcm-memory.exe, pcm-core.exe)"
Write-Host ""
