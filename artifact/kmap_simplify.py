#!/usr/bin/env python3
"""
Karnaugh map minimization for access patterns

Ouput: Kmap1FA, Kmap2FA (both minimal covers)

Usage: python kmap_simplify.py INPUT.csv OUTPUT.csv [--output-delim same|comma|tab]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple
from itertools import product


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


def pick_output_dialect(input_dialect: csv.Dialect, choice: str) -> csv.Dialect:
    if choice == "same":
        return input_dialect
    if choice == "comma":
        return csv.excel
    if choice == "tab":
        return csv.excel_tab
    return input_dialect


def parse_expr_to_minterms(expr: str | None, variables: List[str]) -> Set[int]:
    """Parse expression into minterms (truth table indices where expression is true)"""
    if not expr or expr.strip() in ("", "-"):
        return set()

    minterms = set()
    terms = []

    # Extract terms like [ABC], [AB], etc.
    for match in BRACKET_RE.findall(expr):
        factors = [ch for ch in match if ch.isalpha()]
        terms.append(set(factors))

    if not terms:
        return set()

    # For each possible assignment of variables
    for assignment in product([0, 1], repeat=len(variables)):
        var_assignment = {variables[i]: assignment[i] for i in range(len(variables))}

        # Check if any term is satisfied (OR of terms)
        term_satisfied = False
        for term in terms:
            # Check if this term is satisfied (AND of factors in term)
            all_factors_true = True
            for factor in term:
                if factor not in var_assignment or var_assignment[factor] != 1:
                    all_factors_true = False
                    break
            if all_factors_true:
                term_satisfied = True
                break

        if term_satisfied:
            # Convert assignment to minterm number
            minterm = sum(assignment[i] * (2 ** (len(variables) - 1 - i)) for i in range(len(variables)))
            minterms.add(minterm)

    return minterms


def adjacent_cells(cell1: int, cell2: int) -> bool:
    """Check if two cells are adjacent in Karnaugh map (differ by exactly 1 bit)"""
    return bin(cell1 ^ cell2).count('1') == 1


def find_prime_implicants(minterms: Set[int]) -> List[Tuple[int, int]]:
    """Find all prime implicants using Quine-McCluskey algorithm"""
    if not minterms:
        return []

    # Combine adjacent groups
    prime_implicants = []
    current_level = {minterm: minterm for minterm in minterms}  # term -> original minterm mask

    while current_level:
        next_level = {}
        used = set()

        items = list(current_level.items())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                term1, mask1 = items[i]
                term2, mask2 = items[j]

                if adjacent_cells(term1, term2):
                    # Combine terms
                    diff_bit = term1 ^ term2
                    new_term = term1 & term2  # Common bits
                    new_mask = mask1 & mask2 & ~diff_bit  # Mask out differing bit

                    next_level[new_term] = new_mask
                    used.add(term1)
                    used.add(term2)

        # Unused terms are prime implicants
        for term, mask in current_level.items():
            if term not in used:
                prime_implicants.append((term, mask))

        current_level = next_level

    return prime_implicants


def implicant_to_expr(implicant: Tuple[int, int], variables: List[str]) -> str:
    """Convert prime implicant to Boolean expression"""
    term, mask = implicant
    factors = []

    for i in range(len(variables)):
        bit_pos = len(variables) - 1 - i
        if mask & (1 << bit_pos):  # This bit is relevant
            if term & (1 << bit_pos):  # Bit is 1
                factors.append(variables[i])

    if not factors:
        return ""
    return "[" + "".join(factors) + "]"


def get_covered_minterms(implicant: Tuple[int, int], num_vars: int) -> Set[int]:
    """Get all minterms covered by a prime implicant"""
    term, mask = implicant
    covered = set()

    # Generate all minterms that match this implicant
    # For each don't-care bit, try both 0 and 1
    dont_care_bits = []
    for i in range(num_vars):
        bit_pos = num_vars - 1 - i
        if not (mask & (1 << bit_pos)):  # This bit is don't-care
            dont_care_bits.append(bit_pos)

    # Generate all combinations of don't-care bits
    for dont_care_assignment in product([0, 1], repeat=len(dont_care_bits)):
        minterm = term
        for i, bit_value in enumerate(dont_care_assignment):
            if bit_value:
                minterm |= (1 << dont_care_bits[i])
        covered.add(minterm)

    return covered


def essential_prime_implicant_cover(prime_implicants: List[Tuple[int, int]], minterms: Set[int], num_vars: int) -> List[Tuple[int, int]]:
    """Select essential prime implicants and then apply Petrick's method for exact minimal cover."""
    if not prime_implicants or not minterms:
        return prime_implicants

    # Build coverage table: implicant -> set of covered minterms
    coverage = {}
    for pi in prime_implicants:
        coverage[pi] = get_covered_minterms(pi, num_vars) & minterms

    # Essential implicants: any minterm covered by exactly one implicant
    essential: List[Tuple[int, int]] = []
    covered_by_essential: Set[int] = set()
    for m in minterms:
        covering = [pi for pi, cov in coverage.items() if m in cov]
        if len(covering) == 1:
            epi = covering[0]
            if epi not in essential:
                essential.append(epi)
                covered_by_essential.update(coverage[epi])

    # Remaining minterms to cover
    remaining = minterms - covered_by_essential
    if not remaining:
        return essential

    # Indices for implicants to simplify set operations
    pi_list = list(prime_implicants)
    index_of: Dict[Tuple[int, int], int] = {pi: i for i, pi in enumerate(pi_list)}

    # Precompute literal counts per implicant (positive-only literals)
    literal_counts: List[int] = []
    for (_, mask) in pi_list:
        literal_counts.append(bin(mask).count("1"))

    # Build Petrick clauses: for each remaining minterm, list indices of implicants that cover it
    clauses: List[Set[int]] = []
    for m in remaining:
        idxs = {index_of[pi] for pi, cov in coverage.items() if m in cov}
        # Protect against uncovered minterms (shouldn't happen if prime implicants computed correctly)
        if not idxs:
            continue
        # Exclude implicants already chosen as essential (no need to include them again)
        idxs -= {index_of[epi] for epi in essential if epi in index_of}
        # If an essential implicant was the only cover, remaining would be empty; skip such clauses
        if idxs:
            clauses.append(idxs)

    # If no clauses remain, essentials already cover all remaining minterms
    if not clauses:
        return essential

    # Petrick's method: multiply sums (OR) into products (AND of implicants) and minimize

    # Products are represented as frozensets of implicant indices
    products: Set[frozenset[int]] = {frozenset()}

    def reduce_products(prods: Set[frozenset[int]]) -> Set[frozenset[int]]:
        # Remove any product that is a superset of another (absorption)
        minimal: List[frozenset[int]] = []
        for p in sorted(prods, key=lambda s: (len(s), sum(literal_counts[i] for i in s))):
            if any(p >= q for q in minimal):
                continue
            minimal.append(p)
        return set(minimal)

    for clause in clauses:
        new_products: Set[frozenset[int]] = set()
        for p in products:
            for idx in clause:
                new_products.add(p | {idx})
        products = reduce_products(new_products)
        if not products:
            # No possible cover
            return essential

    # Choose best products by (fewest implicants, then fewest total literals)
    def product_cost(p: frozenset[int]) -> tuple[int, int]:
        return (len(p), sum(literal_counts[i] for i in p))

    best_cost = min(product_cost(p) for p in products)
    best_products = [p for p in products if product_cost(p) == best_cost]

    # Pick one deterministically (smallest index tuple)
    chosen = min(best_products, key=lambda p: tuple(sorted(p)))

    selected = essential[:]
    selected.extend(pi_list[i] for i in sorted(chosen))
    return selected


def minimize_karnaugh(minterms: Set[int], variables: List[str]) -> str:
    """Minimize Boolean function using Karnaugh map algorithm with minimal cover selection"""
    if not minterms:
        return ""

    num_vars = len(variables)
    if num_vars > 6:  # Practical limit for Karnaugh maps
        return ""

    # Find prime implicants
    prime_implicants = find_prime_implicants(minterms)

    if not prime_implicants:
        return ""

    # Apply essential prime implicant selection with Petrick's method for optimal minimal cover
    minimal_implicants = essential_prime_implicant_cover(prime_implicants, minterms, num_vars)

    # Convert to expressions
    terms = []
    for pi in minimal_implicants:
        expr = implicant_to_expr(pi, variables)
        if expr:
            terms.append(expr)

    terms.sort()
    return "".join(terms)


def extract_variables(expr: str | None) -> Set[str]:
    """Extract all variable names from expression"""
    if not expr:
        return set()

    variables = set()
    for match in BRACKET_RE.findall(expr):
        for ch in match:
            if ch.isalpha():
                variables.add(ch)
    return variables


def compute_kmap(base_expr: str | None, reset_expr: str | None) -> str:
    """Compute Karnaugh map minimization with minimal cover selection"""
    # Extract all variables
    all_vars = set()
    if base_expr:
        all_vars.update(extract_variables(base_expr))
    if reset_expr:
        all_vars.update(extract_variables(reset_expr))

    if not all_vars:
        return ""

    variables = sorted(list(all_vars))

    # Get minterms for base expression
    base_minterms = parse_expr_to_minterms(base_expr, variables)

    # Handle reset logic: if P is in base and we have reset terms,
    # replace P with reset terms
    if "P" in all_vars and reset_expr:
        reset_minterms = parse_expr_to_minterms(reset_expr, [v for v in variables if v != "P"])

        # Expand P terms with reset terms
        expanded_minterms = set()
        for minterm in base_minterms:
            # Check if this minterm has P=1
            p_index = variables.index("P") if "P" in variables else -1
            if p_index >= 0:
                p_bit = 1 << (len(variables) - 1 - p_index)
                if minterm & p_bit:  # P is in this minterm
                    # Replace with reset combinations
                    base_without_p = minterm & ~p_bit
                    for reset_term in reset_minterms:
                        # Shift reset term to account for P bit
                        shifted_reset = 0
                        reset_pos = 0
                        for i, var in enumerate(variables):
                            if var != "P":
                                bit_pos = len(variables) - 1 - i
                                reset_bit_pos = len([v for v in variables if v != "P"]) - 1 - reset_pos
                                if reset_term & (1 << reset_bit_pos):
                                    shifted_reset |= (1 << bit_pos)
                                reset_pos += 1
                        expanded_minterms.add(base_without_p | shifted_reset)
                else:
                    expanded_minterms.add(minterm)
            else:
                expanded_minterms.add(minterm)

        base_minterms = expanded_minterms

    return minimize_karnaugh(base_minterms, variables)




def generate(input_path: Path, output_path: Path, *, output_delim: str = "same") -> None:
    in_dialect = detect_dialect(input_path)
    out_dialect = pick_output_dialect(in_dialect, output_delim)

    required = ["ID", "1FA", "2FA", "Reset1FA", "Reset2FA"]

    with input_path.open("r", encoding="utf-8-sig", newline="") as f_in, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in, dialect=in_dialect)
        if not reader.fieldnames:
            raise SystemExit("Input CSV has no header row.")
        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            raise SystemExit(f"Missing required columns: {', '.join(missing)}")

        # Build output header: original fields + ensure Kmap1FA, Kmap2FA appended
        fieldnames: List[str] = list(reader.fieldnames)
        for new_col in ("Kmap1FA", "Kmap2FA"):
            if new_col not in fieldnames:
                fieldnames.append(new_col)
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, dialect=out_dialect)
        writer.writeheader()

        for row in reader:
            row["Kmap1FA"] = compute_kmap(row.get("1FA"), row.get("Reset1FA"))
            row["Kmap2FA"] = compute_kmap(row.get("2FA"), row.get("Reset2FA"))
            writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Append K-map simplifications to a CSV")
    p.add_argument("input", type=Path, help="Path to input CSV")
    p.add_argument("output", type=Path, help="Path to output CSV (will not overwrite input)")
    p.add_argument(
        "--output-delim",
        choices=["same", "comma", "tab"],
        default="same",
        help="Delimiter for output (default: same as input)",
    )
    args = p.parse_args(argv)

    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1
    if args.input.resolve() == args.output.resolve():
        print("Output path must differ from input path.", file=sys.stderr)
        return 1

    try:
        generate(args.input, args.output, output_delim=args.output_delim)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
