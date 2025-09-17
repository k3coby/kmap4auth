#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Table 5 (Reset2FA sufficiency):"
python3 artifact/access_analyzer.py -s artifact/data.csv Reset2FA
echo "Table 5 (Reset2FA necessity):"
python3 artifact/access_analyzer.py -n artifact/data.csv Reset2FA
