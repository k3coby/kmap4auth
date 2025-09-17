#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Table 4 (2FA sufficiency):"
python3 artifact/access_analyzer.py -s artifact/data.csv 2FA
echo "Table 4 (2FA necessity):"
python3 artifact/access_analyzer.py -n artifact/data.csv 2FA
