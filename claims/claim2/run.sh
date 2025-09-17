#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Table 3 (Reset1FA sufficiency):"
python3 artifact/access_analyzer.py -s artifact/data.csv Reset1FA
echo "Table 3 (Reset1FA necessity):"
python3 artifact/access_analyzer.py -n artifact/data.csv Reset1FA
