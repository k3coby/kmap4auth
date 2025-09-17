#!/usr/bin/env python3
"""
Analyze factor expressions in a CSV column.

Modes:
- Sufficiency (-s): count distinct patterns (canonicalized OR-of-ANDs).
- Necessity (-n): count combos C required across terms (every term ∩ C ≠ ∅).

Usage:
- python access_analyzer.py -s INPUT.csv COLUMN
- python access_analyzer.py -n INPUT.csv COLUMN
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import FrozenSet, Iterable, List, Set


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


def parse_expr(expr: str | None) -> Set[FrozenSet[str]]:
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


def format_expr(terms: Iterable[FrozenSet[str]]) -> str:
    parts: List[str] = []
    for t in terms:
        if not t:
            continue
        parts.append("[" + "".join(sorted(t)) + "]")
    parts.sort()
    return "".join(parts)


def format_set(s: Iterable[str]) -> str:
    return "".join(f"[{ch}]" for ch in sorted(s))


def run_sufficiency(path: Path, column: str) -> int:
    dialect = detect_dialect(path)
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f, dialect=dialect)
        if not rdr.fieldnames or column not in rdr.fieldnames:
            print(f"Input missing '{column}' column", file=sys.stderr)
            return 1
        for row in rdr:
            expr_raw = (row.get(column) or "").strip()
            terms = parse_expr(expr_raw)
            if not terms:
                continue
            canon = format_expr(terms)
            if canon:
                counts[canon] += 1
    for pattern, cnt in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{pattern}: {cnt}")
    return 0


def run_necessity(path: Path, column: str) -> int:
    dialect = detect_dialect(path)
    counts: Counter[str] = Counter()
    all_factors: Set[str] = set()
    rows_terms: List[Set[FrozenSet[str]]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f, dialect=dialect)
        if not rdr.fieldnames or column not in rdr.fieldnames:
            print(f"Input missing '{column}' column", file=sys.stderr)
            return 1
        for row in rdr:
            terms = parse_expr(row.get(column))
            if not terms:
                rows_terms.append(set())
                continue
            rows_terms.append(terms)
            for t in terms:
                all_factors.update(t)

    if not rows_terms or not all_factors:
        return 0

    combos: List[FrozenSet[str]] = []
    factors_sorted = sorted(all_factors)
    for r in range(1, len(factors_sorted) + 1):
        for comb in combinations(factors_sorted, r):
            combos.append(frozenset(comb))

    for C in combos:
        cnt = 0
        for terms in rows_terms:
            if not terms:
                continue
            if all((len(term.intersection(C)) > 0) for term in terms):
                cnt += 1
        if cnt > 0:
            counts[format_set(C)] = cnt

    for pattern, cnt in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{pattern}: {cnt}")
    return 0


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Access analyzer for sufficiency (-s) and necessity (-n)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("-s", "--sufficiency", action="store_true", help="Count supported patterns in column")
    mode.add_argument("-n", "--necessity", action="store_true", help="Count required combos in column")
    p.add_argument("input", type=Path, help="Input CSV path")
    p.add_argument("column", type=str, help="Column name to analyze (e.g., 1FA, 2FA)")
    args = p.parse_args(argv)

    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    if args.sufficiency:
        return run_sufficiency(args.input, args.column)
    else:
        return run_necessity(args.input, args.column)


if __name__ == "__main__":
    raise SystemExit(main())
