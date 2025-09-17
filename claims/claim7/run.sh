#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Table 8 (Kmap2FA sufficiency):"
python3 artifact/kmap_simplify.py artifact/data.csv artifact/data_with_kmap.csv --output-delim same >/dev/null
python3 artifact/access_analyzer.py -s artifact/data_with_kmap.csv Kmap2FA
