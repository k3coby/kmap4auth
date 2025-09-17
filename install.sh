#!/usr/bin/env bash
set -euo pipefail
echo "[install] Checking Python..."
python3 -V || { echo "Python3 not found"; exit 1; }
echo "[install] No external dependencies required."

