#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Table 2 (1FA sufficiency):"
python3 artifact/access_analyzer.py -s artifact/data.csv 1FA
echo "Table 2 (1FA necessity):"
python3 artifact/access_analyzer.py -n artifact/data.csv 1FA
