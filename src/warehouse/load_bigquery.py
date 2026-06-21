#!/usr/bin/env python3
"""
BigQuery Loader
===============
CLI to load an RMBS loan-level tape into BigQuery staging.

Usage:
    python -m src.warehouse.load_bigquery --deal AVON2
    python -m src.warehouse.load_bigquery --deal BLETCHLEY

Flow:
    1. Resolve deal from config/deals.yml
    2. Read Excel tape (find the data sheet)
    3. Clean column names (AR codes only)
    4. Add DealID column
    5. Upload to BigQuery staging table (rmbs_staging.loans_<deal>)

The staging table is REPLACED on each load (full refresh per deal).
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.deals import DealError

# BigQuery settings
PROJECT_ID = "rmbs-rwa-pipeline"
DATASET_STAGING = "rmbs_staging"


def load_settings() -> dict:
    """Load config/settings.yml for BigQuery project/dataset info."""
    settings_path = Path(__file__).resolve().parents[2] / "config" / "settings.yml"
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_data_sheet(excel_path: Path) -> str:
    """Find the sheet containing AR-coded loan data."""
    xl = pd.ExcelFile(excel_path)

    # Common sheet names across programmes
    candidates = [
        "AF 2 Current",  # Avon
        "Loan Level Data",
        "LLD",
        "Pool Data",
        "Data",
        "BOE Template",
        "Sheet1",
    ]

    for name in candidates:
        if name in xl.sheet_names:
            return name

    # Fallback: find sheet with AR columns
    for name in xl.sheet_names:
        df = pd.read_excel(excel_path, sheet_name=name, nrows=5)
        ar_cols = [c for c in df.columns if str(c).startswith("AR")]
        if len(ar_cols) > 10:
            return name

    raise ValueError(f"No data sheet found in {excel_path}. Sheets: {xl.sheet_names}")


def clean_column_name(col: str) -> str:
    """Clean column name for BigQuery compatibility."""
    s = str(col).strip()
    # Remove everything after AR code (e.g., "AR3 Loan Identifier" -> "AR3")
    match = re.match(r"^(AR\d+)", s)
    if match:
        return match.group(1)
    # Replace invalid characters
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    # Remove leading digits
    s = re.sub(r"^(\d+)", r"_\1", s)
    return s


def extract_tape(tape_path: Path, deal_id: str) -> pd.DataFrame:
    """Extract loan-level data from Excel tape."""
    print(f"Reading tape: {tape_path.name}")

    sheet_name = find_data_sheet(tape_path)
    print(f"  Using sheet: {sheet_name}")

    # Read data (skip description row if present)
    df = pd.read_excel(tape_path, sheet_name=sheet_name)

    # Check if first row is descriptions (contains description keywords or long text)
    if df.shape[0] > 0:
        first_row = df.iloc[0]
        # Check for description keywords like "Pool", "Identifier", "Date"
        desc_keywords = sum(1 for v in first_row if isinstance(v, str) and
                           any(kw in v for kw in ["Pool", "Identifier", "Date", "Loan", "Balance"]))
        long_text_count = sum(1 for v in first_row if isinstance(v, str) and len(v) > 50)
        if desc_keywords > 5 or long_text_count > 5:
            print("  Skipping description row")
            df = df.iloc[1:].reset_index(drop=True)

    # Clean column names
    df.columns = [clean_column_name(c) for c in df.columns]

    # Keep only AR columns (drop non-standard columns that vary between tapes)
    ar_cols = [c for c in df.columns if c.startswith("AR")]
    df = df[ar_cols].copy()

    # Add DealID
    df.insert(0, "DealID", deal_id)

    # Remove completely empty rows
    df = df.dropna(how="all", subset=[c for c in df.columns if c != "DealID"])

    # Convert all columns to string, replace special values with NULL
    for col in df.columns:
        if col != "DealID":
            df[col] = (df[col].astype(str)
                       .replace("nan", None)
                       .replace("NaT", None)
                       .replace("ND", None))  # BoE "No Data" code → NULL

    print(f"  Extracted {len(df):,} loans, {len(df.columns)} columns")
    return df


def upload_to_bigquery(df: pd.DataFrame, deal_id: str, dry_run: bool = False, append: bool = False) -> None:
    """Upload DataFrame to BigQuery staging table via bq CLI."""
    import subprocess
    import tempfile

    table_name = f"loans_{deal_id.lower().replace('-', '_')}"
    table_ref = f"{PROJECT_ID}:{DATASET_STAGING}.{table_name}"

    if dry_run:
        print(f"[DRY RUN] Would upload {len(df):,} rows to {table_ref}")
        print(f"  Columns: {list(df.columns)[:10]}...")
        return

    # Export to temp CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        csv_path = f.name
        df.to_csv(f, index=False)

    mode = "Appending to" if append else "Replacing"
    print(f"{mode} {table_ref}...")

    # Use bq load command (works with AVG SSL)
    # For append mode, don't use autodetect - use existing table schema
    if append:
        cmd = f'bq load --source_format=CSV --skip_leading_rows=1 {table_ref} "{csv_path}"'
    else:
        cmd = f'bq load --source_format=CSV --replace --autodetect {table_ref} "{csv_path}"'

    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

    # Clean up temp file
    Path(csv_path).unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)

    print(f"  Loaded {len(df):,} rows to {table_ref}")


def resolve_tape_with_filter(deal_id: str, tape_filter: str | None = None):
    """Resolve deal and find tape, optionally filtered by substring."""
    from src.ingest.deals import load_registry, find_deal, DealError

    registry = load_registry()
    deal = find_deal(deal_id, registry)

    if deal["status"] != "active":
        raise DealError(f"Deal '{deal_id}' not active (status: {deal.get('status')})")

    folder = Path(registry["data_root"]) / deal["folder"]
    pattern = deal.get("tape_pattern", "*.xlsx")
    matches = list(folder.glob(pattern))

    if tape_filter:
        matches = [m for m in matches if tape_filter.lower() in m.name.lower()]

    if not matches:
        raise DealError(f"No tape matching filter '{tape_filter}' in {folder}")
    if len(matches) > 1:
        names = sorted([m.name for m in matches])
        raise DealError(
            f"Multiple tapes found. Use --tape to filter (e.g., --tape Nov):\n  " + "\n  ".join(names)
        )

    return deal, matches[0].resolve()


def main():
    parser = argparse.ArgumentParser(
        description="Load RMBS tape to BigQuery staging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--deal", "-d",
        required=True,
        help="Deal ID from config/deals.yml (e.g., AVON2, BLETCHLEY)",
    )
    parser.add_argument(
        "--tape", "-t",
        help="Filter tape filename (e.g., 'Nov' to match Nov_2020)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract data but don't upload to BigQuery",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing table instead of replacing",
    )
    args = parser.parse_args()

    try:
        deal, tape_path = resolve_tape_with_filter(args.deal, args.tape)
        print(f"Deal: {deal['name']} ({deal['id']})")
        print(f"Tape: {tape_path}")

        df = extract_tape(tape_path, deal["id"])
        upload_to_bigquery(df, deal["id"], dry_run=args.dry_run, append=args.append)

        print("Done.")

    except DealError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
