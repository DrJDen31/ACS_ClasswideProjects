# System Information Collection Script (Windows)
# This script collects detailed system information to populate SYSTEM_CONFIG.md

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Collecting System Information" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$outputFile = "..\SYSTEM_CONFIG_AUTO.md"

$content = @"
# System Configuration (Auto-Generated)

**Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Hardware Specifications

"@

# CPU Information
Write-Host "Collecting CPU information..." -ForegroundColor Yellow
$cpu = Get-WmiObject Win32_Processor

$content += @"
### CPU
- **Model:** $($cpu.Name)
- **Manufacturer:** $($cpu.Manufacturer)
- **Architecture:** $($cpu.Architecture) ($(if ($cpu.AddressWidth -eq 64) {"x86_64"} else {"x86"}))
- **Max Clock Speed:** $($cpu.MaxClockSpeed) MHz ($([math]::Round($cpu.MaxClockSpeed/1000, 2)) GHz)
- **Current Clock Speed:** $($cpu.CurrentClockSpeed) MHz
- **Cores:** $($cpu.NumberOfCores) physical cores
- **Threads:** $($cpu.NumberOfLogicalProcessors) logical processors
- **SMT/Hyperthreading:** $(if ($cpu.NumberOfLogicalProcessors -gt $cpu.NumberOfCores) {"Enabled"} else {"Disabled"})

"@

# Cache Information
Write-Host "Collecting cache information..." -ForegroundColor Yellow
$content += @"
### Cache Hierarchy
- **L2 Cache:** $($cpu.L2CacheSize) KB $(if ($cpu.L2CacheSize -gt 0) {"(~$([math]::Round($cpu.L2CacheSize / $cpu.NumberOfCores, 0)) KB per core)"} )
- **L3 Cache:** $($cpu.L3CacheSize) KB $(if ($cpu.L3CacheSize -gt 0) {"($([math]::Round($cpu.L3CacheSize / 1024, 2)) MB total)"} )
- **Cache Line Size:** 64 bytes (typical)

"@

# Detailed cache from WMI (if available)
$caches = Get-WmiObject Win32_CacheMemory
if ($caches) {
    $content += "`n**Detailed Cache Information:**`n"
    foreach ($cache in $caches) {
        $level = $cache.Level
        $size = $cache.InstalledSize
        $content += "- Level $level Cache: $size KB`n"
    }
    $content += "`n"
}

# Memory Information
Write-Host "Collecting memory information..." -ForegroundColor Yellow
$memory = Get-WmiObject Win32_PhysicalMemory
$totalMemoryGB = ($memory | Measure-Object -Property Capacity -Sum).Sum / 1GB

$content += @"
### Memory
- **Total RAM:** $([math]::Round($totalMemoryGB, 2)) GB
- **Number of Modules:** $($memory.Count)

"@

# Memory details
$content += "`n**Memory Modules:**`n"
foreach ($mem in $memory) {
    $capacityGB = $mem.Capacity / 1GB
    $speed = $mem.Speed
    $type = $mem.SMBIOSMemoryType
    $manufacturer = $mem.Manufacturer
    $content += "- $capacityGB GB @ $speed MHz (Type: $type, $manufacturer)`n"
}

# Try to determine memory type
$memType = "Unknown"
if ($memory[0].SMBIOSMemoryType) {
    $typeCode = $memory[0].SMBIOSMemoryType
    switch ($typeCode) {
        20 { $memType = "DDR" }
        21 { $memType = "DDR2" }
        24 { $memType = "DDR3" }
        26 { $memType = "DDR4" }
        34 { $memType = "DDR5" }
    }
}

$content += @"

- **Memory Type:** $memType
- **Channels:** $(if ($memory.Count -eq 2) {"Dual Channel"} elseif ($memory.Count -eq 4) {"Quad Channel"} else {"Single Channel or Unknown"})
- **NUMA Nodes:** 1 (typical for consumer systems)

"@

# TLB Information (not readily available on Windows)
$content += @"
### TLB Configuration
- **L1 DTLB:** [Manual verification required - check CPU specifications]
- **L2 DTLB:** [Manual verification required - check CPU specifications]
- **Huge Page Support:** Windows Large Pages (2MB equivalent)

"@

# Operating System Information
Write-Host "Collecting OS information..." -ForegroundColor Yellow
$os = Get-WmiObject Win32_OperatingSystem
$content += @"

---

## Software Environment

### Operating System
- **OS:** $($os.Caption)
- **Version:** $($os.Version)
- **Build:** $($os.BuildNumber)
- **Architecture:** $($os.OSArchitecture)

"@

# Check for WSL
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    $content += "- **WSL:** Installed`n"
    try {
        $wslDistros = wsl --list --quiet 2>&1
        $content += "- **WSL Distributions:** $($wslDistros -join ', ')`n"
    } catch {
        $content += "- **WSL Distributions:** Unable to enumerate`n"
    }
} else {
    $content += "- **WSL:** Not installed`n"
}

# Tool versions
Write-Host "Collecting tool versions..." -ForegroundColor Yellow
$content += @"

### Tools & Versions

"@

# Check for Intel MLC
if (Test-Path "..\tools\mlc.exe") {
    $content += "- **Intel MLC:** Found in tools directory`n"
} else {
    $content += "- **Intel MLC:** Not found - needs to be downloaded`n"
}

# Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version 2>&1
    $content += "- **Python:** $pythonVersion`n"
} else {
    $content += "- **Python:** Not found`n"
}

# CMake
if (Get-Command cmake -ErrorAction SilentlyContinue) {
    $cmakeVersion = (cmake --version 2>&1 | Select-Object -First 1)
    $content += "- **CMake:** $cmakeVersion`n"
} else {
    $content += "- **CMake:** Not found`n"
}

# Compiler
if (Get-Command gcc -ErrorAction SilentlyContinue) {
    $gccVersion = (gcc --version 2>&1 | Select-Object -First 1)
    $content += "- **GCC:** $gccVersion`n"
} elseif (Get-Command cl -ErrorAction SilentlyContinue) {
    $content += "- **Compiler:** MSVC (Visual Studio)`n"
} else {
    $content += "- **Compiler:** Not found`n"
}

# Power configuration
Write-Host "Collecting power configuration..." -ForegroundColor Yellow
$content += @"

---

## Experimental Configuration

### CPU Frequency Management

"@

$activePlan = powercfg /getactivescheme
if ($activePlan -match "High performance") {
    $content += "- **Power Plan:** High Performance (Good for experiments)`n"
} else {
    $content += "- **Power Plan:** $activePlan`n"
    $content += "- **Note:** Recommend switching to High Performance`n"
}

$content += @"
- **Frequency Scaling:** Active (Windows does not expose direct control)
- **Recommendation:** Set power plan to High Performance for consistent results

### Windows-Specific Notes
- Windows does not provide the same level of CPU frequency control as Linux
- Consider using WSL for experiments requiring fine-grained control
- Large Pages can be enabled via Local Security Policy

"@

# Theoretical calculations
Write-Host "Calculating theoretical limits..." -ForegroundColor Yellow

# Memory bandwidth calculation (rough estimate)
$memSpeed = $memory[0].Speed
$channels = if ($memory.Count -ge 2) {2} else {1}  # Conservative estimate
$busWidth = 64  # bits per channel
$bytesPerTransfer = ($busWidth * $channels) / 8
$transfersPerSec = $memSpeed * 1000000
$bandwidthMBps = ($bytesPerTransfer * $transfersPerSec) / (1024 * 1024)
$bandwidthGBps = $bandwidthMBps / 1024

$content += @"

---

## Theoretical Limits

### Memory Bandwidth
- **Memory Speed:** $memSpeed MHz
- **Estimated Channels:** $channels
- **Bus Width per Channel:** 64 bits (8 bytes)
- **Theoretical Peak Bandwidth:** $([math]::Round($bandwidthGBps, 2)) GB/s
  - Calculation: $channels channels × $memSpeed MHz × 8 bytes / 1024^3
- **Note:** Actual bandwidth will be lower due to protocol overhead and inefficiencies

### Expected Latencies (Typical Values)
These are estimates - actual measurements may vary:
- **L1 Cache:** ~1-2 ns (3-6 cycles @ $($cpu.MaxClockSpeed) MHz)
- **L2 Cache:** ~3-5 ns (10-15 cycles)
- **L3 Cache:** ~10-20 ns (30-60 cycles)
- **DRAM:** ~50-100 ns (150-300 cycles)

**Note:** These are typical values. Your actual measurements may differ based on CPU architecture and memory configuration.

"@

# Recommendations
$content += @"

---

## Recommendations for Project 2

1. **For Maximum Accuracy:**
   - Use WSL or Linux VM for experiments requiring perf
   - Set power plan to High Performance
   - Close all unnecessary applications during measurements
   - Run experiments during low system activity

2. **Tool Setup:**
   - Download Intel MLC and place in p2/tools/
   - Install Python packages: ``pip install numpy matplotlib pandas``
   - Set up WSL for Linux-specific experiments (Exp 6 & 7)

3. **Measurement Best Practices:**
   - Always run warm-up iterations before measurement
   - Repeat each test at least 3 times
   - Calculate and report standard deviation
   - Document any anomalies or unusual observations

4. **Windows Limitations:**
   - Limited CPU frequency control compared to Linux
   - No direct access to performance counters without special drivers
   - Consider dual-boot or VM for experiments 6 & 7 (cache/TLB profiling)

---

## Additional Commands for Manual Verification

Run these commands to verify or supplement the information above:

**PowerShell:**
``````powershell
# Detailed CPU info
Get-WmiObject Win32_Processor | Format-List *

# Memory configuration
Get-WmiObject Win32_PhysicalMemory | Format-List *

# Cache details
Get-WmiObject Win32_CacheMemory | Format-List *
``````

**WSL/Linux (if available):**
``````bash
# Complete system info
lscpu
lscpu -C  # Cache details

# Memory info
free -h
lsmem

# Performance counter access
cat /proc/sys/kernel/perf_event_paranoid
``````

---

**End of auto-generated system configuration**
"@

# Write to file
$content | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "System information collected!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Output file: $outputFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Review the generated file"
Write-Host "2. Copy relevant sections to SYSTEM_CONFIG.md"
Write-Host "3. Add manual measurements where needed"
Write-Host "4. Look up CPU-specific details (TLB sizes, etc.) from manufacturer specs"
Write-Host ""
