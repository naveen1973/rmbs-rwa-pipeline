#!/usr/bin/env python3
"""
Export SEC-ERBA RWA calculations to CSV for BigQuery.

Calculates Risk-Weighted Assets for each tranche using the
External Ratings-Based Approach (Basel 3.1 / UK CRR).

Usage:
    python scripts/export_rwa.py
    python scripts/export_rwa.py --load-bq
"""

import argparse
import csv
import subprocess
from pathlib import Path
from dataclasses import dataclass

# Output path
OUTPUT_CSV = Path(__file__).parent.parent / "config" / "tranche_rwa.csv"

# SEC-ERBA Risk Weight Table (Basel 3.1 / UK CRR Article 263)
# {rating: {seniority: {maturity_years: risk_weight}}}
SEC_ERBA_TABLE = {
    "AAA": {"senior": {1: 0.15, 5: 0.20}, "non-senior": {1: 0.15, 5: 0.30}},
    "AA+": {"senior": {1: 0.15, 5: 0.25}, "non-senior": {1: 0.15, 5: 0.40}},
    "AA":  {"senior": {1: 0.20, 5: 0.30}, "non-senior": {1: 0.25, 5: 0.50}},
    "AA-": {"senior": {1: 0.25, 5: 0.35}, "non-senior": {1: 0.30, 5: 0.55}},
    "A+":  {"senior": {1: 0.30, 5: 0.45}, "non-senior": {1: 0.40, 5: 0.65}},
    "A":   {"senior": {1: 0.35, 5: 0.55}, "non-senior": {1: 0.50, 5: 0.80}},
    "A-":  {"senior": {1: 0.45, 5: 0.70}, "non-senior": {1: 0.60, 5: 0.95}},
    "BBB+": {"senior": {1: 0.55, 5: 0.85}, "non-senior": {1: 0.75, 5: 1.15}},
    "BBB":  {"senior": {1: 0.70, 5: 1.05}, "non-senior": {1: 0.90, 5: 1.40}},
    "BBB-": {"senior": {1: 0.90, 5: 1.40}, "non-senior": {1: 1.20, 5: 1.85}},
    "BB+":  {"senior": {1: 1.20, 5: 1.85}, "non-senior": {1: 1.40, 5: 2.70}},
    "BB":   {"senior": {1: 1.40, 5: 2.50}, "non-senior": {1: 1.70, 5: 3.30}},
    "BB-":  {"senior": {1: 1.70, 5: 3.00}, "non-senior": {1: 2.20, 5: 4.20}},
    "B+":   {"senior": {1: 2.20, 5: 3.80}, "non-senior": {1: 3.30, 5: 5.80}},
    "B":    {"senior": {1: 2.80, 5: 4.60}, "non-senior": {1: 4.70, 5: 7.50}},
    "B-":   {"senior": {1: 3.80, 5: 6.20}, "non-senior": {1: 6.50, 5: 10.50}},
    "CCC+": {"senior": {1: 5.30, 5: 8.00}, "non-senior": {1: 9.00, 5: 13.50}},
    "CCC":  {"senior": {1: 7.00, 5: 10.50}, "non-senior": {1: 12.00, 5: 18.00}},
    "CCC-": {"senior": {1: 9.50, 5: 13.50}, "non-senior": {1: 12.50, 5: 12.50}},
    "NR":   {"senior": {1: 12.50, 5: 12.50}, "non-senior": {1: 12.50, 5: 12.50}},
}

# Deal configurations with ratings and WAL estimates
DEAL_CONFIG = {
    "AVON2": {
        "tranches": {
            "Class A": {"rating": "AAA", "seniority": "senior", "wal": 3.5},
            "Class B": {"rating": "AA", "seniority": "non-senior", "wal": 4.0},
            "Class C": {"rating": "A", "seniority": "non-senior", "wal": 4.5},
            "Class D": {"rating": "BBB", "seniority": "non-senior", "wal": 5.0},
            "Class E": {"rating": "BB", "seniority": "non-senior", "wal": 5.0},
            "Class F": {"rating": "B", "seniority": "non-senior", "wal": 5.0},
            "Class Z": {"rating": "NR", "seniority": "non-senior", "wal": 5.0},
        }
    },
    "BLETCHLEY": {
        "tranches": {
            "Class A": {"rating": "AAA", "seniority": "senior", "wal": 3.0},
            "Class B": {"rating": "AA", "seniority": "non-senior", "wal": 3.5},
            "Class C": {"rating": "A", "seniority": "non-senior", "wal": 4.0},
            "Class D": {"rating": "BBB", "seniority": "non-senior", "wal": 4.5},
            "Class E": {"rating": "BB", "seniority": "non-senior", "wal": 5.0},
            "Class X1": {"rating": "NR", "seniority": "non-senior", "wal": 2.0},
            "Class X2": {"rating": "NR", "seniority": "non-senior", "wal": 3.0},
        }
    },
}

CAPITAL_RATIO = 0.08  # Basel 8% capital requirement


def interpolate_rw(rw_1yr: float, rw_5yr: float, maturity: float) -> float:
    """Interpolate risk weight between 1yr and 5yr anchor points."""
    if maturity <= 1:
        return rw_1yr
    if maturity >= 5:
        return rw_5yr
    return rw_1yr + (rw_5yr - rw_1yr) * (maturity - 1) / 4


def get_risk_weight(rating: str, seniority: str, maturity: float) -> float:
    """Look up SEC-ERBA risk weight."""
    rating = rating or "NR"
    if rating not in SEC_ERBA_TABLE:
        rating = "NR"

    rw_table = SEC_ERBA_TABLE[rating][seniority]
    return interpolate_rw(rw_table[1], rw_table[5], maturity)


def fetch_tranche_balances():
    """Fetch current tranche balances from BigQuery."""
    import tempfile
    import os

    query = """SELECT DealID, TrancheID, CurrentBalance, Attachment, Detachment, CreditEnhancement, CutoffDate
FROM `rmbs-rwa-pipeline.rmbs_marts.dim_tranche`
ORDER BY DealID, Attachment DESC"""

    # Write query to temp file to avoid shell escaping issues
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(query)
        query_file = f.name

    try:
        cmd = f'bq query --use_legacy_sql=false --format=csv --quiet < "{query_file}"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    finally:
        os.unlink(query_file)

    if result.returncode != 0:
        print(f"Error fetching from BigQuery: {result.stderr}")
        return []

    output = result.stdout.strip()
    if not output:
        print("Empty result from BigQuery")
        return []

    lines = output.split('\n')
    if len(lines) < 2:
        print(f"Only {len(lines)} lines returned")
        return []

    reader = csv.DictReader(lines)
    return list(reader)


def calculate_rwa(tranches: list) -> list:
    """Calculate RWA for each tranche."""
    results = []

    for t in tranches:
        deal_id = t['DealID']
        tranche_id = t['TrancheID']
        balance = float(t['CurrentBalance'])
        attachment = float(t['Attachment'])
        detachment = float(t['Detachment'])
        cutoff_date = t['CutoffDate']

        # Get rating config
        config = DEAL_CONFIG.get(deal_id, {}).get("tranches", {}).get(tranche_id, {})
        rating = config.get("rating", "NR")
        seniority = config.get("seniority", "non-senior")
        wal = config.get("wal", 5.0)

        # Calculate thickness
        thickness = detachment - attachment

        # Get risk weight
        rw = get_risk_weight(rating, seniority, wal)

        # Calculate RWA and capital
        rwa = balance * rw
        capital = rwa * CAPITAL_RATIO

        results.append({
            "DealID": deal_id,
            "TrancheID": tranche_id,
            "CutoffDate": cutoff_date,
            "Rating": rating,
            "Seniority": seniority,
            "WAL": wal,
            "CurrentBalance": round(balance, 2),
            "Attachment": attachment,
            "Detachment": detachment,
            "Thickness": round(thickness, 4),
            "RiskWeight": round(rw, 4),
            "RiskWeight_Pct": round(rw * 100, 2),
            "RWA": round(rwa, 2),
            "Capital": round(capital, 2),
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Export SEC-ERBA RWA to CSV")
    parser.add_argument("--load-bq", action="store_true", help="Load to BigQuery after export")
    args = parser.parse_args()

    print("Fetching tranche balances from BigQuery...")
    tranches = fetch_tranche_balances()

    if not tranches:
        print("No tranches found in BigQuery")
        return

    print(f"Found {len(tranches)} tranches")

    print("Calculating SEC-ERBA RWA...")
    results = calculate_rwa(tranches)

    # Write CSV
    fieldnames = [
        "DealID", "TrancheID", "CutoffDate", "Rating", "Seniority", "WAL",
        "CurrentBalance", "Attachment", "Detachment", "Thickness",
        "RiskWeight", "RiskWeight_Pct", "RWA", "Capital"
    ]

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nWritten to {OUTPUT_CSV}")

    # Print summary
    print("\n=== RWA Summary ===")
    for deal_id in set(r['DealID'] for r in results):
        deal_results = [r for r in results if r['DealID'] == deal_id]
        total_balance = sum(r['CurrentBalance'] for r in deal_results)
        total_rwa = sum(r['RWA'] for r in deal_results)
        total_capital = sum(r['Capital'] for r in deal_results)
        avg_rw = total_rwa / total_balance if total_balance > 0 else 0

        print(f"\n{deal_id}:")
        print(f"  Total Balance: £{total_balance:,.0f}")
        print(f"  Total RWA:     £{total_rwa:,.0f}")
        print(f"  Total Capital: £{total_capital:,.0f}")
        print(f"  Avg RW:        {avg_rw*100:.1f}%")
        print(f"  RWA Density:   {(total_rwa/total_balance)*100:.1f}%")

    # Print tranche details
    print("\n=== Tranche Details ===")
    print(f"{'Deal':<12} {'Tranche':<10} {'Rating':<6} {'Balance':>14} {'RW%':>8} {'RWA':>14} {'Capital':>12}")
    print("-" * 80)
    for r in results:
        print(f"{r['DealID']:<12} {r['TrancheID']:<10} {r['Rating']:<6} "
              f"£{r['CurrentBalance']:>12,.0f} {r['RiskWeight_Pct']:>7.1f}% "
              f"£{r['RWA']:>12,.0f} £{r['Capital']:>10,.0f}")

    # Load to BigQuery if requested
    if args.load_bq:
        print("\nLoading to BigQuery...")
        result = subprocess.run(
            f'bq load --replace --autodetect --source_format=CSV "rmbs-rwa-pipeline:rmbs_marts.tranche_rwa" "{OUTPUT_CSV}"',
            capture_output=True, text=True, shell=True
        )

        if result.returncode == 0:
            print("Loaded to rmbs_marts.tranche_rwa")
        else:
            print(f"Error loading to BigQuery: {result.stderr}")


if __name__ == "__main__":
    main()
