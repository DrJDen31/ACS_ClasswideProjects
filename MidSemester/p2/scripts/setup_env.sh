#!/bin/bash
# Project 2 Environment Setup Script (Linux/WSL)
# This script checks for required tools and configures the system

set -e  # Exit on error

echo "========================================"
echo "Project 2 Environment Setup"
echo "========================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any issues found
ISSUES=0

# Function to check command existence
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 found: $(command -v $1)"
        if [ "$2" != "" ]; then
            echo "  Version: $($1 $2 2>&1 | head -n1)"
        fi
        return 0
    else
        echo -e "${RED}✗${NC} $1 not found"
        ISSUES=$((ISSUES + 1))
        return 1
    fi
}

# Function to print section header
section() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

# Check system information
section "System Information"
echo "Hostname: $(hostname)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "OS: $PRETTY_NAME"
fi

# Check CPU information
section "CPU Information"
if command -v lscpu &> /dev/null; then
    lscpu | grep -E "Model name|Architecture|CPU\(s\)|Thread|Core|Socket|L[123]|Cache"
else
    echo -e "${YELLOW}⚠${NC} lscpu not available, trying /proc/cpuinfo"
    cat /proc/cpuinfo | grep -E "model name|cpu cores|siblings" | head -n 3
fi

# Check cache information
section "Cache Hierarchy"
if command -v lscpu &> /dev/null; then
    lscpu -C 2>/dev/null || echo "Cache info not available via lscpu -C"
fi
getconf -a | grep CACHE 2>/dev/null || echo "Cache info not available via getconf"

# Check memory information
section "Memory Configuration"
if command -v free &> /dev/null; then
    free -h
fi
if command -v lsmem &> /dev/null; then
    lsmem | grep -E "Memory block|Total online"
fi

# Check NUMA configuration
section "NUMA Configuration"
if command -v numactl &> /dev/null; then
    numactl --hardware
else
    echo -e "${YELLOW}⚠${NC} numactl not installed"
    echo "  Install with: sudo apt-get install numactl"
fi

# Check required tools
section "Tool Availability"

# Check for Intel MLC
echo ""
echo "Checking for Intel MLC..."
MLC_PATH="../tools/mlc"
if [ -f "$MLC_PATH" ]; then
    echo -e "${GREEN}✓${NC} Intel MLC found at $MLC_PATH"
    if [ -x "$MLC_PATH" ]; then
        echo "  Executable: Yes"
    else
        echo -e "${YELLOW}⚠${NC} MLC not executable. Run: chmod +x $MLC_PATH"
    fi
else
    echo -e "${RED}✗${NC} Intel MLC not found at $MLC_PATH"
    echo "  Download from: https://www.intel.com/content/www/us/en/download/736633/intel-memory-latency-checker-intel-mlc.html"
    echo "  Place the binary in: p2/tools/"
    ISSUES=$((ISSUES + 1))
fi

# Check for perf
echo ""
check_command "perf" "--version"
if [ $? -ne 0 ]; then
    echo "  Install with: sudo apt-get install linux-tools-common linux-tools-generic linux-tools-\$(uname -r)"
fi

# Check for Python
echo ""
check_command "python3" "--version"

# Check Python packages
echo ""
echo "Checking Python packages..."
for pkg in numpy matplotlib pandas; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $pkg installed"
    else
        echo -e "${RED}✗${NC} $pkg not installed"
        echo "  Install with: pip3 install $pkg"
        ISSUES=$((ISSUES + 1))
    fi
done

# Check for build tools
echo ""
check_command "gcc" "--version"
check_command "g++" "--version"
check_command "cmake" "--version"

# Check CPU frequency scaling
section "CPU Frequency Configuration"
SCALING_GOVERNOR="/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
if [ -f "$SCALING_GOVERNOR" ]; then
    CURRENT_GOV=$(cat $SCALING_GOVERNOR)
    echo "Current governor: $CURRENT_GOV"
    if [ "$CURRENT_GOV" = "performance" ]; then
        echo -e "${GREEN}✓${NC} CPU governor set to performance"
    else
        echo -e "${YELLOW}⚠${NC} CPU governor is NOT set to performance"
        echo "  Recommended: Set to performance mode for consistent results"
        echo "  Run: echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    fi
    
    # Check if we can read current frequency
    FREQ_FILE="/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
    if [ -f "$FREQ_FILE" ]; then
        FREQ=$(cat $FREQ_FILE)
        FREQ_MHZ=$((FREQ / 1000))
        echo "Current CPU frequency: ${FREQ_MHZ} MHz"
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot access CPU frequency scaling information"
    echo "  May need root access or running on Windows"
fi

# Check huge pages
section "Huge Pages Configuration"
if [ -f /proc/meminfo ]; then
    echo "Huge page info:"
    grep -i huge /proc/meminfo
    
    HUGEPAGES=$(grep HugePages_Total /proc/meminfo | awk '{print $2}')
    if [ "$HUGEPAGES" = "0" ] || [ -z "$HUGEPAGES" ]; then
        echo -e "${YELLOW}⚠${NC} No huge pages allocated"
        echo "  For Experiment 7, you may want to allocate huge pages"
        echo "  Run: echo 512 | sudo tee /proc/sys/vm/nr_hugepages"
    fi
else
    echo "Cannot read /proc/meminfo"
fi

# Check perf access
section "Performance Counter Access"
PARANOID="/proc/sys/kernel/perf_event_paranoid"
if [ -f "$PARANOID" ]; then
    PARANOID_LEVEL=$(cat $PARANOID)
    echo "perf_event_paranoid: $PARANOID_LEVEL"
    if [ "$PARANOID_LEVEL" -le 1 ]; then
        echo -e "${GREEN}✓${NC} Performance counters accessible"
    else
        echo -e "${YELLOW}⚠${NC} Performance counter access restricted"
        echo "  Current level: $PARANOID_LEVEL"
        echo "  For full access, run: echo 1 | sudo tee /proc/sys/kernel/perf_event_paranoid"
        echo "  (Or run perf commands with sudo)"
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot check perf_event_paranoid"
fi

# Summary
section "Setup Summary"
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo "System is ready for Project 2 experiments."
else
    echo -e "${YELLOW}⚠ Found $ISSUES issue(s)${NC}"
    echo "Please address the issues above before running experiments."
fi

echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo "1. Review and complete SYSTEM_CONFIG.md with your system details"
echo "2. Download Intel MLC if not present (place in p2/tools/)"
echo "3. Set CPU governor to performance mode (see above)"
echo "4. Run validation tests to ensure measurements are stable"
echo "5. Start with Experiment 1 (zero-queue baselines)"
echo ""
