# Data Quality Report

Control checks run after each data load to validate integrity before analytics.

## Avon Finance No.2 — Nov 2020 Tape

**Load date:** 2026-06-19  
**Source:** EDW loan-level tape (8,246 loans)

### Reconciliation Checks

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Row count (staging → mart) | 8,246 | 8,246 | PASS |
| Total balance | £839,448,270 | £839,448,270 | PASS |
| NULL LoanID | 0 | 0 | PASS |
| NULL CurrentBalance | 0 | 0 | PASS |
| Orphan fact rows | 0 | 0 | PASS |
| Negative balance | 0 | 2 | FLAG |

### Flagged Items

| LoanID | CurrentBalance | Notes |
|--------|----------------|-------|
| 152129 | -£0.01 | Overpayment (rounding) |
| 191853 | -£0.03 | Overpayment (rounding) |

**Assessment:** Tiny negative balances from overpayments — acceptable in RMBS data. No action required.

### Pool Summary (validated)

| Metric | Value |
|--------|-------|
| Loan count | 8,246 |
| Total balance | £839.4M |
| WA interest rate | 2.64% |
| WA LTV | 75.8% |
| WA seasoning | 167 months |
| Loans in arrears | 972 (11.8%) |

---

*Controls query: `sql/controls/controls_reconciliation.sql`*
