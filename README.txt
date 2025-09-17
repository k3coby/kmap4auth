Artifact: Reproduction Package

Overview
- This artifact includes Python scripts that output results
  consistent with the tables in the paper. The mapping between commands and
  tables is encoded in `claims.txt`.

What's Included
- data.csv: input dataset for the scripts.
- claims.txt: consistency relations (which script maps to which table).
- access_analyzer.py, factor_analyzer.py, kmap_simplify.py: analysis scripts.
- colab_artifact.ipynb: a notebook for Google Colab (runs all claim
  commands and prints outputs for visual comparison to the paper's tables).
- tools/compare_tables.py: automated script to verify all tables match
  artifact outputs (eliminates need for manual comparison).

Quick Start (Local)
1) Install: from the repo root, run `./install.sh` (or see Colab below).
2) Run individual claims from repo root:
   - `./claims/claim1/run.sh`  # Table 2 (1FA sufficiency)
   - `./claims/claim2/run.sh`  # Table 3 (Reset1FA sufficiency)
   - `./claims/claim3/run.sh`  # Table 4 (2FA sufficiency)
   - `./claims/claim4/run.sh`  # Table 5 (Reset2FA sufficiency)
   - `./claims/claim5/run.sh`  # Table 6 (Kmap1FA)
   - `./claims/claim6/run.sh`  # Table 7 (1FA w/o reset vs 1FA w reset through Kmap)
   - `./claims/claim7/run.sh`  # Table 8 (Kmap2FA)
   - `./claims/claim8/run.sh`  # Table 9 (2FA w/o reset vs 2FA w reset through Kmap)

Quick Start (Google Colab)
- Open `artifact/colab_artifact.ipynb` in Colab and run all cells.

Quick Start (Automated Verification)
- From repo root, run: `python artifact/tools/compare_tables.py`
- This automatically verifies all paper tables match artifact outputs.
- Eliminates manual comparison; shows detailed per-table verification.

Directory Layout
- Root directory:
  - artifact/: data.csv, claims.txt, *.py, colab_artifact.ipynb, tools/
  - claims/: per-claim run.sh + claim.txt
  - claims/Tables/: LaTeX table files for automated verification
  - install.sh, license.txt, use.txt

System Requirements
- Python 3.8+; no external packages required.
- Tested on Ubuntu 22.04 and Google Colab (CPU).

Verification Methods
- **Individual Claims**: Run ./claims/claim*/run.sh and manually compare outputs to paper tables
- **Notebook**: Use colab_artifact.ipynb for visual comparison of all tables
- **Automated**: Use tools/compare_tables.py for automatic verification

Notes
- For manual verification, compare printed outputs to paper tables using `claims.txt` mapping.
