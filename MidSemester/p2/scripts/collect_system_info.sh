#!/bin/bash
# System Information Collection Script (Linux/WSL)
# This script collects detailed system information to populate SYSTEM_CONFIG.md

OUTPUT_FILE="../SYSTEM_CONFIG_AUTO.md"

echo "========================================"
echo "Collecting System Information"
echo "========================================"
echo ""

# Start the output file
cat > "$OUTPUT_FILE" << EOF
# System Configuration (Auto-Generated)

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')

## Hardware Specifications

EOF

# CPU Information
echo "Collecting CPU information..."
echo "### CPU" >> "$OUTPUT_FILE"

if command -v lscpu &> /dev/null; then
    MODEL=$(lscpu | grep "Model name" | cut -d':' -f2 | xargs)
    ARCH=$(lscpu | grep "Architecture" | cut -d':' -f2 | xargs)
    CORES=$(lscpu | grep "^CPU(s):" | cut -d':' -f2 | xargs)
    THREADS=$(lscpu | grep "^Thread(s) per core" | cut -d':' -f2 | xargs)
    CORES_PER_SOCKET=$(lscpu | grep "Core(s) per socket" | cut -d':' -f2 | xargs)
    SOCKETS=$(lscpu | grep "Socket(s)" | cut -d':' -f2 | xargs)
    MAX_MHZ=$(lscpu | grep "CPU max MHz" | cut -d':' -f2 | xargs)
    MIN_MHZ=$(lscpu | grep "CPU min MHz" | cut -d':' -f2 | xargs)
    
    PHYSICAL_CORES=$((CORES_PER_SOCKET * SOCKETS))
    LOGICAL_CORES=$CORES
    
    cat >> "$OUTPUT_FILE" << EOF
- **Model:** $MODEL
- **Architecture:** $ARCH
- **Base Frequency:** ${MIN_MHZ:-N/A} MHz
- **Max Frequency:** ${MAX_MHZ:-N/A} MHz
- **Cores:** $PHYSICAL_CORES physical cores
- **Threads:** $LOGICAL_CORES logical processors
- **SMT/Hyperthreading:** $([ $LOGICAL_CORES -gt $PHYSICAL_CORES ] && echo "Enabled ($THREADS threads per core)" || echo "Disabled")

EOF
fi

# Cache Information
echo "Collecting cache information..."
echo "### Cache Hierarchy" >> "$OUTPUT_FILE"

if command -v lscpu &> /dev/null; then
    L1D=$(lscpu | grep "L1d cache" | cut -d':' -f2 | xargs)
    L1I=$(lscpu | grep "L1i cache" | cut -d':' -f2 | xargs)
    L2=$(lscpu | grep "L2 cache" | cut -d':' -f2 | xargs)
    L3=$(lscpu | grep "L3 cache" | cut -d':' -f2 | xargs)
    
    cat >> "$OUTPUT_FILE" << EOF
- **L1 Data Cache:** ${L1D:-N/A}
- **L1 Instruction Cache:** ${L1I:-N/A}
- **L2 Cache:** ${L2:-N/A}
- **L3 Cache:** ${L3:-N/A}
- **Cache Line Size:** $(getconf LEVEL1_DCACHE_LINESIZE 2>/dev/null || echo "64") bytes

EOF
fi

# Memory Information
echo "Collecting memory information..."
echo "### Memory" >> "$OUTPUT_FILE"

if [ -f /proc/meminfo ]; then
    TOTAL_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_GB=$(echo "scale=2; $TOTAL_KB/1024/1024" | bc)
    echo "- **Total RAM:** $TOTAL_GB GB" >> "$OUTPUT_FILE"
fi

if command -v numactl &> /dev/null; then
    NUMA_NODES=$(numactl --hardware 2>/dev/null | grep "available:" | awk '{print $2}')
    echo "- **NUMA Nodes:** ${NUMA_NODES:-1}" >> "$OUTPUT_FILE"
fi

echo "" >> "$OUTPUT_FILE"

# Operating System
echo "Collecting OS information..."
cat >> "$OUTPUT_FILE" << EOF

---

## Software Environment

### Operating System
- **OS:** $([ -f /etc/os-release ] && grep PRETTY_NAME /etc/os-release | cut -d'"' -f2 || uname -s)
- **Kernel Version:** $(uname -r)
- **Architecture:** $(uname -m)

### Tools & Versions
EOF

# Check tools
[ -f "../tools/mlc" ] && echo "- **Intel MLC:** Found" >> "$OUTPUT_FILE" || echo "- **Intel MLC:** Not found" >> "$OUTPUT_FILE"
command -v perf &> /dev/null && echo "- **perf:** $(perf --version 2>&1)" >> "$OUTPUT_FILE" || echo "- **perf:** Not found" >> "$OUTPUT_FILE"
command -v gcc &> /dev/null && echo "- **GCC:** $(gcc --version | head -n1)" >> "$OUTPUT_FILE"
command -v python3 &> /dev/null && echo "- **Python:** $(python3 --version)" >> "$OUTPUT_FILE"

# Experimental Configuration
cat >> "$OUTPUT_FILE" << EOF

---

## Experimental Configuration

### CPU Frequency Management
EOF

if [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
    GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    echo "- **Governor:** $GOV" >> "$OUTPUT_FILE"
fi

# Performance counters
if [ -f "/proc/sys/kernel/perf_event_paranoid" ]; then
    PARANOID=$(cat /proc/sys/kernel/perf_event_paranoid)
    echo "- **perf_event_paranoid:** $PARANOID" >> "$OUTPUT_FILE"
fi

echo "" >> "$OUTPUT_FILE"
echo "System information collected successfully!"
echo "Output: $OUTPUT_FILE"
