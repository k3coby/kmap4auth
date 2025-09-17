#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Table 9 (2FA vs Kmap2FA factor sets):"
python3 artifact/kmap_simplify.py artifact/data.csv artifact/data_with_kmap.csv --output-delim same >/dev/null
python3 artifact/factor_analyzer.py artifact/data_with_kmap.csv 2FA Kmap2FA
