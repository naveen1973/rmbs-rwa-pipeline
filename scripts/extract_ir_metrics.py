#!/usr/bin/env python3
"""
Extract metrics from Investor Report PDFs.

Usage:
    python scripts/extract_ir_metrics.py --deal AVON2
    python scripts/extract_ir_metrics.py --deal AVON2 --load-bq
    python scripts/extract_ir_metrics.py --all
"""

import argparse
import re
import os
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd

# Deal configurations - map deal names to folder paths and patterns
DEAL_CONFIG = {
    "AVON2": {
        "folder": r"C:\Users\Naveen\OneDrive - Learn Data Insights\Desktop\DATA\Projects\RMBS Dashboard\Issuers\Avon Finance No 2 Plc",
        "ir_pattern": r"Avon 2.*IR.*\.pdf|Avon 2.*Monthly.*Report.*\.pdf",
        "original_class_a": 666_345_000,
        "subordination": 146_270_000,  # B + C + D + E + F + Z
    },
    "BLETCHLEY": {
        "folder": r"C:\Users\Naveen\OneDrive - Learn Data Insights\Desktop\DATA\Projects\RMBS Dashboard\Issuers\Bletchley Park Funding 2024-1 PLC 1",
        "ir_pattern": r"Bletchley.*IR.*\.pdf",
        "original_class_a": 207_150_000,  # From IR
        "subordination": 37_393_000,  # B + C + D + E + X1 + X2 at closing
        "note_table_page": 4,  # Principal distributions on page 4
    },
}

OUTPUT_CSV = Path(__file__).parent.parent / "config" / "investor_report_metrics.csv"


def parse_number(text: str) -> float:
    """Parse a number from text, handling commas and percentages."""
    if not text or text.strip() in ('', 'N/A', 'null', '-'):
        return None
    text = text.strip().replace(',', '').replace('%', '').replace('£', '').replace('GBP', '')
    try:
        return float(text)
    except ValueError:
        return None


def extract_date_from_filename(filename: str) -> str:
    """Extract date from IR filename."""
    # Pattern: 20201130, 20210228, etc.
    match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    # Pattern: Dec 2021, Mar 2022, etc.
    month_map = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                 'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
    match = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(\d{4})', filename.lower())
    if match:
        month = month_map[match.group(1)]
        year = match.group(2)
        # Assume end of month for report date
        if month in ('01', '03', '05', '07', '08', '10', '12'):
            day = '31'
        elif month == '02':
            day = '28'
        else:
            day = '30'
        return f"{year}-{month}-{day}"

    return None


def extract_cutoff_date(pdf) -> str:
    """Extract cutoff date from PDF content."""
    for page in pdf.pages[:3]:
        text = page.extract_text() or ''
        # Look for "Reporting Period End Date: DD-Mon-YYYY" or similar
        match = re.search(r'Reporting Period End Date[:\s]+(\d{1,2}[-/]\w+[-/]\d{4})', text)
        if match:
            date_str = match.group(1)
            try:
                for fmt in ['%d-%b-%Y', '%d/%b/%Y', '%d-%B-%Y']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            except:
                pass

        # Alternative pattern: DD-Mon-YYYY anywhere
        match = re.search(r'(\d{1,2})[-/](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-/](\d{4})', text, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            month_map = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                         'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
            return f"{year}-{month_map[month.lower()]}-{int(day):02d}"

    return None


def extract_note_balances(pdf) -> dict:
    """Extract note balances from the Note Details table."""
    balances = {}

    for page in pdf.pages[:10]:
        text = page.extract_text() or ''

        # Method 1: Look for "Class A" line with balance data (AVON2 format)
        # Must have XS (ISIN), GBP, but NOT "Notes" (which is header row)
        lines = text.split('\n')
        for line in lines:
            # AVON2: "Class A XS... 666,345,000.00 648,188,081.84 GBP..."
            if 'Class A' in line and 'XS' in line and 'Class B' not in line and 'GBP' in line and 'Notes' not in line:
                # Extract all numbers that look like balances (6+ digits with decimals)
                numbers = re.findall(r'([\d,]{3,}(?:,\d{3})*\.?\d*)', line)
                large_numbers = [parse_number(n) for n in numbers if parse_number(n) and parse_number(n) > 1_000_000]
                if len(large_numbers) >= 2:
                    # First is beginning balance, second is ending balance
                    balances['class_a'] = large_numbers[1]
                    break
                elif len(large_numbers) == 1:
                    balances['class_a'] = large_numbers[0]
                    break

        # Method 2: Look for Principal Distributions table (BLETCHLEY format)
        # Has columns: Original Balance, Beginning Balance, Principal Paid, Ending Balance, Ending Pool Factor
        if not balances.get('class_a'):
            if 'Principal' in text and 'Ending Balance' in text:
                for line in lines:
                    # Look for Class A row - must have 5 numbers (not "Notes" or "ISIN")
                    if line.strip().startswith('Class A') and 'Notes' not in line and 'XS' not in line:
                        numbers = re.findall(r'([\d,]+\.?\d*)', line)
                        # Format: Original, Beginning, Principal Paid, Ending, Factor
                        if len(numbers) == 5:
                            ending_bal = parse_number(numbers[3])
                            factor = parse_number(numbers[4])
                            if ending_bal and ending_bal > 1_000_000 and factor and factor < 2:
                                balances['class_a'] = ending_bal
                                balances['factor'] = factor
                                break

        # Method 3: Check tables if other methods didn't work
        if not balances.get('class_a'):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                header = table[0] if table else []
                if header and any('Ending Balance' in str(h) for h in header if h):
                    for row in table[1:]:
                        if row and len(row) >= 4:
                            cell0 = str(row[0]) if row[0] else ''
                            # Handle multi-line cells - Class A is first line
                            if 'Class A' in cell0.split('\n')[0] and 'Class B' not in cell0:
                                ending_col = row[3] if len(row) > 3 else None
                                if ending_col:
                                    # Get first value if multi-line
                                    val = str(ending_col).split('\n')[0]
                                    parsed = parse_number(val)
                                    if parsed and parsed > 1_000_000:
                                        balances['class_a'] = parsed
                                        break

        if balances.get('class_a'):
            break

    return balances


def extract_pool_metrics(pdf) -> dict:
    """Extract pool-level metrics from PDF."""
    metrics = {
        'pool_balance': None,
        'wa_ltv': None,
        'loan_count': None,
        'cpr_1m': None,
        'cpr_12m': None,
        'arrears_90plus_pct': None,
    }

    for page in pdf.pages:
        text = page.extract_text() or ''

        # Pool Balance
        match = re.search(r'Current Balance of Mortgage Loans[^\d]*([\d,]+\.?\d*)', text)
        if match and not metrics['pool_balance']:
            metrics['pool_balance'] = parse_number(match.group(1))

        # WA LTV
        match = re.search(r'Weighted Average Loan to Value[^\d]*([\d.]+)%?', text, re.IGNORECASE)
        if match and not metrics['wa_ltv']:
            metrics['wa_ltv'] = parse_number(match.group(1))

        # Loan Count
        match = re.search(r'Number of.*Mortgage Loans[^\d]*([\d,]+)', text)
        if match and not metrics['loan_count']:
            metrics['loan_count'] = parse_number(match.group(1))

        # CPR (Annualised)
        match = re.search(r'Annualised CPR[^\d]*([\d.]+)%?', text, re.IGNORECASE)
        if match and not metrics['cpr_12m']:
            metrics['cpr_12m'] = parse_number(match.group(1))

        # Monthly CPR
        match = re.search(r'Constant Principal Pre-?payment Rate[^\d]*([\d.]+)%?', text, re.IGNORECASE)
        if match and not metrics['cpr_1m']:
            metrics['cpr_1m'] = parse_number(match.group(1))

        # Arrears 90+ (> 3 months)
        # Look for "> 6.00 Months in Arrears" or "3.00+ Months in Arrears"
        match = re.search(r'>\s*6\.?\d*\s*Months in Arrears[^\d]*([\d,]+\.?\d*)[^\d]*([\d,]+)[^\d]*([\d.]+)%?', text)
        if match:
            # The percentage is typically the 3rd capture group
            pct = parse_number(match.group(3))
            if pct and not metrics['arrears_90plus_pct']:
                metrics['arrears_90plus_pct'] = pct

        # Alternative: sum up 3+ month arrears
        if not metrics['arrears_90plus_pct']:
            # Look for arrears breakdown table
            arrears_pattern = r'([345]\.?\d*|>\s*6).*Months in Arrears[^\d]*([\d,]+\.?\d*)[^\d]*([\d,]+)[^\d]*([\d.]+)%?'
            matches = re.findall(arrears_pattern, text)
            if matches:
                total_pct = sum(parse_number(m[3]) or 0 for m in matches)
                if total_pct > 0:
                    metrics['arrears_90plus_pct'] = total_pct

    return metrics


def calculate_ce(class_a_balance: float, subordination: float) -> float:
    """Calculate Credit Enhancement for Class A."""
    if not class_a_balance or not subordination:
        return None
    total_notes = class_a_balance + subordination
    return subordination / total_notes


def extract_ir_metrics(pdf_path: str, deal_config: dict) -> dict:
    """Extract all metrics from a single IR PDF."""
    print(f"  Processing: {Path(pdf_path).name}")

    with pdfplumber.open(pdf_path) as pdf:
        # Get dates
        filename = Path(pdf_path).name
        report_date = extract_date_from_filename(filename)
        cutoff_date = extract_cutoff_date(pdf) or report_date

        # Get note balances
        note_balances = extract_note_balances(pdf)
        class_a_balance = note_balances.get('class_a')

        # Calculate factor (use extracted factor if available, otherwise calculate)
        factor_class_a = note_balances.get('factor')
        if not factor_class_a and class_a_balance and deal_config.get('original_class_a'):
            factor_class_a = class_a_balance / deal_config['original_class_a']

        # Calculate CE
        ce_class_a = None
        if class_a_balance and deal_config.get('subordination'):
            ce_class_a = calculate_ce(class_a_balance, deal_config['subordination'])

        # Get pool metrics
        pool_metrics = extract_pool_metrics(pdf)

        return {
            'ReportDate': report_date,
            'CutoffDate': cutoff_date,
            'PoolBalance': pool_metrics['pool_balance'],
            'WA_LTV': pool_metrics['wa_ltv'],
            'CPR_1m': pool_metrics['cpr_1m'],
            'CPR_12m': pool_metrics['cpr_12m'],
            'Arrears_90Plus_Pct': pool_metrics['arrears_90plus_pct'],
            'CE_ClassA': round(ce_class_a, 4) if ce_class_a else None,
            'Factor_ClassA': round(factor_class_a, 4) if factor_class_a else None,
            'ClassA_Balance': class_a_balance,
        }


def process_deal(deal_id: str, load_bq: bool = False) -> pd.DataFrame:
    """Process all IR PDFs for a deal."""
    if deal_id not in DEAL_CONFIG:
        print(f"Error: Unknown deal '{deal_id}'. Available: {list(DEAL_CONFIG.keys())}")
        return None

    config = DEAL_CONFIG[deal_id]
    folder = Path(config['folder'])

    if not folder.exists():
        print(f"Error: Folder not found: {folder}")
        return None

    # Find all IR PDFs
    pattern = re.compile(config['ir_pattern'], re.IGNORECASE)
    pdf_files = [f for f in folder.glob("*.pdf") if pattern.search(f.name)]

    # Exclude rating reports
    pdf_files = [f for f in pdf_files if 'DBRS' not in f.name and 'rating' not in f.name.lower()]

    print(f"\nProcessing {deal_id}: Found {len(pdf_files)} IR PDFs")

    results = []
    for pdf_path in sorted(pdf_files):
        try:
            metrics = extract_ir_metrics(str(pdf_path), config)
            if metrics['CutoffDate']:
                metrics['DealID'] = deal_id
                results.append(metrics)
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")

    if not results:
        print(f"  No valid metrics extracted")
        return None

    df = pd.DataFrame(results)

    # Reorder columns
    cols = ['DealID', 'ReportDate', 'CutoffDate', 'CPR_1m', 'CPR_12m', 'PoolBalance',
            'WA_LTV', 'Arrears_90Plus_Pct', 'CE_ClassA', 'Factor_ClassA']
    df = df[[c for c in cols if c in df.columns]]

    # Sort by date
    df = df.sort_values('CutoffDate').drop_duplicates(subset=['DealID', 'CutoffDate'])

    print(f"\nExtracted {len(df)} periods for {deal_id}:")
    print(df.to_string(index=False))

    return df


def update_csv(new_data: pd.DataFrame, deal_id: str):
    """Update the investor_report_metrics.csv with new data."""
    csv_path = OUTPUT_CSV

    # Load existing data (handle malformed CSVs)
    existing = pd.DataFrame()
    if csv_path.exists():
        try:
            existing = pd.read_csv(csv_path, on_bad_lines='skip')
            # Remove old data for this deal
            existing = existing[existing['DealID'] != deal_id]
        except Exception as e:
            print(f"Warning: Could not read existing CSV: {e}")
            print("Starting fresh...")

    # Prepare new data with all expected columns
    all_cols = ['DealID', 'ReportDate', 'CutoffDate', 'CPR_1m', 'CPR_3m', 'CPR_12m',
                'CDR_1m', 'CDR_3m', 'CDR_Lifetime', 'PoolBalance', 'PoolFactor',
                'WA_LTV', 'WA_Coupon', 'Arrears_30_60_Pct', 'Arrears_60_90_Pct',
                'Arrears_90Plus_Pct', 'CE_ClassA', 'Factor_ClassA', 'LRF_Balance', 'Notes']

    for col in all_cols:
        if col not in new_data.columns:
            new_data[col] = None

    new_data['Notes'] = 'extracted by script'
    new_data = new_data[all_cols]

    # Combine and save
    combined = pd.concat([existing, new_data], ignore_index=True)
    combined = combined.sort_values(['DealID', 'CutoffDate'])
    combined.to_csv(csv_path, index=False)

    print(f"\nUpdated {csv_path}")
    print(f"Total rows: {len(combined)}")


def load_to_bigquery():
    """Load the CSV to BigQuery."""
    import subprocess
    csv_path = OUTPUT_CSV
    result = subprocess.run([
        'bq', 'load', '--replace', '--autodetect', '--source_format=CSV',
        'rmbs-rwa-pipeline:rmbs_marts.investor_report_metrics',
        str(csv_path)
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print("Loaded to BigQuery successfully")
    else:
        print(f"BigQuery load failed: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description='Extract metrics from IR PDFs')
    parser.add_argument('--deal', type=str, help='Deal ID (e.g., AVON2, BLETCHLEY)')
    parser.add_argument('--all', action='store_true', help='Process all deals')
    parser.add_argument('--load-bq', action='store_true', help='Load results to BigQuery')
    parser.add_argument('--list', action='store_true', help='List available deals')

    args = parser.parse_args()

    if args.list:
        print("Available deals:")
        for deal_id, config in DEAL_CONFIG.items():
            print(f"  {deal_id}: {config['folder']}")
        return

    deals_to_process = []
    if args.all:
        deals_to_process = list(DEAL_CONFIG.keys())
    elif args.deal:
        deals_to_process = [args.deal.upper()]
    else:
        parser.print_help()
        return

    for deal_id in deals_to_process:
        df = process_deal(deal_id)
        if df is not None and not df.empty:
            update_csv(df, deal_id)

    if args.load_bq:
        load_to_bigquery()


if __name__ == '__main__':
    main()
