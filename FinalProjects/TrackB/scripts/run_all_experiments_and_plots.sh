#!/usr/bin/env bash
set -euo pipefail

# Run all experiments and then all analysis/plot scripts.
# Usage (from inside WSL):
#   cd "$(dirname "$0")/.."  # go to TrackB project root
#   ./scripts/run_all_experiments_and_plots.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Running all experiments ==="
"${SCRIPT_DIR}/run_all_experiments.sh"

echo
echo "=== Running all analysis/plot scripts ==="
"${SCRIPT_DIR}/run_all_plots.sh"

echo
echo "=== All experiments and analyses completed ==="
