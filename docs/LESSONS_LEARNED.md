# Lessons Learned — RMBS RWA Pipeline Build

A record of issues encountered, root causes, and solutions. Reference this when:
- Preparing for data engineering interviews
- Working on future ETL/warehouse projects
- Troubleshooting similar pipelines

---

## 1. Schema Drift in Multi-Period Loads

**Issue:** Loading 6 AVON2 tapes failed with schema mismatch errors. AR167 changed from TIMESTAMP to DATE between monthly tapes.

**Root cause:** Excel stores dates differently depending on cell formatting. The `bq load --autodetect` command inferred different types from different files.

**Solution:**
```python
# Keep only AR columns (ignore non-standard columns that vary)
ar_cols = [c for c in df.columns if c.startswith("AR")]
df = df[ar_cols].copy()
```

**Lesson:** When loading multiple files to the same table, standardize columns BEFORE loading. Don't rely on autodetect for append operations.

---

## 2. Description Row Included as Data

**Issue:** First data row contained "AR1 Pool Cut-off Date" text instead of actual dates, corrupting the staging table.

**Root cause:** Some Excel tapes have a description row below the header (row 1 = AR codes, row 2 = descriptions, row 3+ = data).

**Solution:**
```python
# Detect description rows by keyword presence
desc_keywords = sum(1 for v in first_row if isinstance(v, str) and
                   any(kw in v for kw in ["Pool", "Identifier", "Date", "Loan"]))
if desc_keywords > 5:
    df = df.iloc[1:].reset_index(drop=True)  # Skip row
```

**Lesson:** Always inspect the first few rows of source data. Don't assume row 1 after headers is always data.

---

## 3. Windows Line Endings Breaking BigQuery CSV Parsing

**Issue:** BigQuery `bq load` created columns named `string_field_0`, `string_field_1` instead of recognizing headers.

**Root cause:** Windows CRLF (`\r\n`) line endings confused BigQuery's CSV parser. It couldn't find the header row.

**Solution:**
```python
df.to_csv(csv_path, index=False, lineterminator='\n')  # Force Unix LF
```

**Lesson:** When generating CSV files on Windows for cloud ingestion, explicitly set Unix line endings.

---

## 4. Dimension Table Duplication (dim_loan)

**Issue:** `dim_loan` showed 49,297 rows for AVON2 instead of ~8,200 unique loans. Pool metrics were 6x inflated.

**Root cause:** The conform view selected from staging (which has all periods), without deduplicating to one row per loan.

**Solution:**
```sql
-- Add to conform view
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY DealID, LoanID 
  ORDER BY CutoffDate DESC
) = 1
```

**Lesson:** Dimension tables must be deduplicated. Use `ROW_NUMBER()` with `QUALIFY` or a subquery to pick one row per entity (typically most recent).

---

## 5. Power BI Relationship Keys After Adding Time Series

**Issue:** Power BI refresh failed with "duplicate value 'AVON2' not allowed for primary key" on pool_summary.

**Root cause:** The model was built with single-period data where DealID was unique per table. Adding 13 periods made DealID non-unique.

**Solution:** Create a proper star schema:
- `dim_deal` — one row per deal (DealID = primary key)
- `pool_summary` / fact tables — many rows per deal (join to dim_deal on DealID)
- Relationships: `dim_deal.DealID` (one) → `pool_summary.DealID` (many)

**Lesson:** Design the data model for the FINAL state (multi-period, multi-deal) from the start. A star schema with dedicated dimension tables scales; using fact-table columns as keys does not.

---

## 6. BigQuery SSL Certificate Error (AVG Antivirus)

**Issue:** `bq` CLI failed with SSL certificate verification errors.

**Root cause:** AVG antivirus performs TLS interception, presenting its own certificate instead of Google's. The `bq` CLI rejected it.

**Solution:**
```bash
# Point gcloud at a CA bundle that includes AVG's root
set REQUESTS_CA_BUNDLE=C:\path\to\ca-bundle-with-avg.crt
```

**Lesson:** Enterprise antivirus/firewalls often intercept HTTPS. When CLI tools fail with SSL errors, check if a proxy or AV is injecting certificates.

---

## 7. OLE DB/ODBC Errors in Power BI (0x80040E4E)

**Issue:** Power BI showed "OLE DB or ODBC error: Exception from HRESULT: 0x80040E4E" for multiple tables.

**Root cause:** This error code means "data integrity violation" — typically a primary key or relationship constraint failed. One failing table cascades to others.

**Solution:** Fix the upstream constraint error (duplicate key in pool_summary). The OLE DB errors on other tables were side effects.

**Lesson:** When Power BI shows multiple OLE DB errors, find the FIRST table that failed with a specific message (like "duplicate value"). Fix that one; the others are cascade failures.

---

## 8. Mixing Loan-Level Data (LLD) and Investor Report (IR) Metrics

**Issue:** Tried to calculate CPR from loan tape, but CPR requires month-over-month balance comparison that isn't possible from a single tape.

**Root cause:** CPR (Constant Prepayment Rate) is calculated by the servicer using internal data and reported in the Investor Report PDF. It's not derivable from the loan tape alone.

**Solution:** Create `investor_report_metrics.csv` to capture IR-sourced metrics (CPR, CE, Factor) separately from tape-derived metrics.

**Lesson:** Know which metrics come from which source:
- **Loan tape (LLD):** Balance, LTV, arrears, loan count — calculable
- **Investor report (IR):** CPR, CDR, CE, Factor — must be extracted from PDF

---

## 9. Non-Unique Columns Set as Relationship Keys

**Issue:** `strat_delinquency.ArrearsBalance` was used as a relationship key, but the same balance value appeared in multiple rows.

**Root cause:** During initial model setup, wrong columns were chosen as keys. ArrearsBalance is a measure, not an identifier.

**Solution:** Only use true identifiers as keys:
- Good keys: DealID, LoanID, CutoffDate, TrancheID
- Bad keys: ArrearsBalance, CurrentBalance, LTV (these are measures that repeat)

**Lesson:** Relationship keys must be semantically unique identifiers, not metric values.

---

## 10. Forgetting to Rebuild Dependent Views

**Issue:** After fixing conform views, pool_summary still showed wrong numbers.

**Root cause:** BigQuery views don't auto-refresh. The conform view was fixed, but pool_summary (which depends on it) wasn't re-run.

**Solution:** Rebuild views in dependency order:
1. Conform views (read staging)
2. dim_loan, fact_loan_period (UNION conform views)
3. pool_summary, strat_* (aggregate from #2)

**Lesson:** Maintain a clear view dependency graph. After any change, rebuild downstream views in order.

---

## Summary: Data Engineering Principles Reinforced

| Principle | Example from this project |
|-----------|--------------------------|
| **Fail loudly** | Deal resolver refuses to guess when multiple files match |
| **Idempotent loads** | `--replace` flag ensures same result on re-run |
| **Schema-on-read risks** | Autodetect inferred wrong types across files |
| **Star schema scalability** | dim_deal table enables 100+ deal scaling |
| **Source lineage** | LLD vs IR metrics have different extraction paths |
| **Defensive parsing** | Skip description rows, handle Windows line endings |
| **Dependency ordering** | Rebuild views in correct sequence |

---

*Last updated: 2026-06-22*
