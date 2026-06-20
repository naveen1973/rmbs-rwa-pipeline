"""
Demo script: Calculate SEC-ERBA RWA for Avon Finance No.2.

Run: python scripts/run_rwa.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rwa.capital_structure import create_avon_structure
from src.rwa.rwa_calculator import calculate_deal_rwa, print_rwa_report


def main():
    # Pool balance from BigQuery (Nov 2020)
    pool_balance = 839_448_270
    cutoff_date = "2020-11-30"

    # Create capital structure
    structure = create_avon_structure(pool_balance, cutoff_date)

    # Validate structure
    errors = structure.validate()
    if errors:
        print("Structure validation errors:")
        for e in errors:
            print(f"  - {e}")
        return

    # Calculate RWA
    result = calculate_deal_rwa(structure)

    # Print report
    print_rwa_report(result)

    # Summary
    summary = result.summary()
    print("Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
