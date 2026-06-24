# RMBS RWA Pipeline — Build Summary

This document summarizes key decisions and work completed on the project.

---

## What Was Built

### 1. BigQuery Data Warehouse
- **Dataset:** `rmbs-rwa-pipeline.rmbs_marts`
- **Tables:** dim_deal, dim_tranche, dim_loan, pool_summary, fact_loan_period, investor_report_metrics, strat_* (stratifications), tranche_rwa
- **Deals loaded:** AVON2 (2020-2021), BLETCHLEY (2024)

### 2. SEC-ERBA RWA Engine
- Implements Basel 3.1 / UK CRR securitisation capital calculation
- Risk weights by rating, seniority, maturity (with interpolation)
- Script: `scripts/export_rwa.py`
- Full methodology: `docs/RWA_METHODOLOGY.md`

### 3. Power BI Dashboard
- **File:** `powerbi/RMBS_BigQuery_Dashboard.pbix`
- **Connection:** BigQuery native connector (Import mode)
- **Pages:**
  1. Pool Analysis — KPIs, Region/LTV bars, Occupancy donut, Capital Structure table
  2. Time Series — 6 performance charts (Balance, CPR, Arrears, CE, Factor, LTV)

---

## Key Technical Decisions

### Star Schema Design
- `dim_deal` is the central hub (1 side of all relationships)
- All other tables connect via `DealID` with *:1 cardinality
- Cross-filter direction: Single (not bidirectional)

### LASTDATE Pattern for KPIs
Problem: Simple `SUM(TotalBalance)` aggregates ALL periods = wrong.

Solution:
```dax
Pool Balance = CALCULATE(SUM(pool_summary[TotalBalance]), LASTDATE(pool_summary[CutoffDate]))
```
This returns only the latest period's value in the current filter context.

### DAX Measures Created
| Measure | Formula |
|---------|---------|
| Pool Balance | `CALCULATE(SUM([TotalBalance]), LASTDATE([CutoffDate]))` |
| Total Loans | `CALCULATE(SUM([LoanCount]), LASTDATE([CutoffDate]))` |
| WA LTV | `CALCULATE(AVERAGE([WA_LTV]), LASTDATE([CutoffDate]))` |
| WA Int Rate | `CALCULATE(AVERAGE([WA_InterestRate]), LASTDATE([CutoffDate]))` |
| Total RWA | `SUM(tranche_rwa[RWA])` |
| Capital Required | `SUM(tranche_rwa[Capital])` |
| Avg Risk Weight | `DIVIDE(SUM([RWA]), SUM([CurrentBalance]), 0)` |

### Capital Structure Table
- Turned off row subtotals (Factor and CreditEnhancement are non-additive)
- Shows: TrancheID, CurrentBalance, Factor, CreditEnhancement, Coupon

---

## Issues Solved

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Pool Balance showing £5bn | SUM aggregated all 6 periods | Use LASTDATE pattern |
| WA_LTV showing 0.03 | Measure used wrong column | Fixed column reference |
| BLETCHLEY CPR not showing | Wrong field extracted from IR | Changed to cpr_1m |
| BigQuery query empty | Backtick escaping on Windows | Used tempfile approach |
| Capital Structure totals wrong | Factor/CE are non-additive | Disabled subtotals |

---

## Pending Tasks

1. **Date slicer fix** — Use `pool_summary[CutoffDate]` directly (not hierarchy) so it shows only dates with data for selected programme

2. **Optional:** Add CC BY-NC-ND license to protect IP

---

## Private Assets (not in repo)

Saved locally at `C:\Users\Naveen\Documents\rmbs-private-assets\`:
- `RMBS_Dashboard_Preview.html` — interactive HTML dashboard
- `RMBS_Dashboard_Build_Guide.docx` — PL-300 course material

---

## References

- [RWA_METHODOLOGY.md](RWA_METHODOLOGY.md) — SEC-ERBA calculation details
- [powerbi/POWERBI_MODEL_GUIDE.md](powerbi/POWERBI_MODEL_GUIDE.md) — Star schema and DAX patterns
- [pipeline.md](pipeline.md) — Architecture overview
