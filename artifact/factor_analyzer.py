#!/usr/bin/env python3
"""
Analyze access by factor sets for two columns.

For each set S (e.g., {A}, {A, E}), counts rows accessible assuming a user can
present all factors in S simultaneously (term ⊆ S).

Sections:
- Factors: woReset — sets with P (but not K), using only the first column.
- Factors: woReset: wReset — two columns; shows only sets where count1 ≤ count2.

Usage: python factor_analyzer.py INPUT.csv COL1 COL2
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Set, Tuple


BRACKET_RE = re.compile(r"\[\s*([A-Z]+)\s*\]")


def detect_dialect(path: Path) -> csv.Dialect:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
    try:
        return csv.Sniffer().sniff(sample)
    except Exception:
        if "\t" in sample and "," not in sample:
            return csv.excel_tab
        return csv.excel


def parse_terms(expr: str | None) -> Set[FrozenSet[str]]:
    if not expr:
        return set()
    expr = expr.strip()
    if not expr or expr == "-":
        return set()
    terms: Set[FrozenSet[str]] = set()
    for grp in BRACKET_RE.findall(expr):
        factors = tuple(ch for ch in grp if ch.isalpha())
        if not factors:
            continue
        terms.add(frozenset(factors))
    return terms


def extract_singletons(terms: Set[FrozenSet[str]]) -> Set[str]:
    return {next(iter(t)) for t in terms if len(t) == 1}


def fmt_combo(combo: Iterable[str]) -> str:
    items = ", ".join(sorted(combo))
    return "{" + items + "}"


def count_access_by_set(input_path: Path, col1: str, col2: str) -> None:
    dialect = detect_dialect(input_path)
    rows_terms_1: List[Set[FrozenSet[str]]] = []
    rows_terms_2: List[Set[FrozenSet[str]]] = []
    all_factors_1: Set[str] = set()
    all_factors_2: Set[str] = set()

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f, dialect=dialect)
        for col in (col1, col2):
            if not rdr.fieldnames or col not in rdr.fieldnames:
                raise SystemExit(f"Missing required column: {col}")

        for row in rdr:
            t1 = parse_terms(row.get(col1))
            t2 = parse_terms(row.get(col2))
            rows_terms_1.append(t1)
            rows_terms_2.append(t2)
            for T in t1:
                all_factors_1.update(T)
            for T in t2:
                all_factors_2.update(T)

    # Generate all non-empty OR combinations from single factors observed in 1FA or Kmap1FA
    combos: List[FrozenSet[str]] = []
    pool = sorted(all_factors_1.union(all_factors_2))
    for r in range(1, len(pool) + 1):
        for comb in combinations(pool, r):
            combos.append(frozenset(comb))

    # Count for 1FA and Kmap1FA
    counts_1: Dict[FrozenSet[str], int] = {c: 0 for c in combos}
    counts_2: Dict[FrozenSet[str], int] = {c: 0 for c in combos}

    for c in combos:
        # Access if any term is a subset of the factor set
        for t1, t2 in zip(rows_terms_1, rows_terms_2):
            if t1 and any(term.issubset(c) for term in t1):
                counts_1[c] += 1
            if t2 and any(term.issubset(c) for term in t2):
                counts_2[c] += 1

    # Extra top section: only woReset (col1) for sets containing P but not K
    # Denominator: total number of rows where COL2 has any terms (>0),
    # same as the two-column section below
    denom_wo = sum(1 for t2 in rows_terms_2 if t2)
    def fmt_one(count: int) -> str:
        if denom_wo <= 0:
            return f"0.0% ({count})"
        return f"{(count/denom_wo)*100.0:.1f}% ({count})"

    p_no_k_sets = [k for k in combos if ('P' in k) and ('K' not in k) and (counts_1[k] > 0)]
    print("Factors: woReset")
    for c in sorted(p_no_k_sets, key=lambda x: fmt_combo(x)):
        print(f"{fmt_combo(c)}: {fmt_one(counts_1[c])}")

    # Divider before the two-column section
    print("=======")
    # Print only combos where the first count is <= the second count
    print("Factors: woReset: wReset")
    selected = []
    for k in combos:
        if (counts_1[k] <= counts_2[k]) and (counts_1[k] > 0 or counts_2[k] > 0):
            selected.append(k)

    # Determine denominator for percentage: total number of rows where COL2 has any terms (>0)
    # i.e., count of rows with a non-empty expression in the second column
    denom = sum(1 for t2 in rows_terms_2 if t2)
    def fmt(count: int) -> str:
        if denom <= 0:
            return f"0.0% ({count})"
        pct = (count / denom) * 100.0
        return f"{pct:.1f}% ({count})"

    for c in sorted(selected, key=lambda x: fmt_combo(x)):
        left = fmt(counts_1[c])
        right = fmt(counts_2[c])
        print(f"{fmt_combo(c)}: {left}; {right}")


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Count access by factor sets (term ⊆ set) for any two columns")
    ap.add_argument("input", type=Path, help="Path to CSV file")
    ap.add_argument("col1", type=str, help="First column name (e.g., 1FA)")
    ap.add_argument("col2", type=str, help="Second column name (e.g., Kmap1FA)")
    args = ap.parse_args(argv)
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1
    try:
        count_access_by_set(args.input, args.col1, args.col2)
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
