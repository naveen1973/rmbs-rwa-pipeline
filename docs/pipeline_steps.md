# Pipeline Steps — shared reference

The numbers below match the circled stages in **`docs/architecture.svg`**. Use them as shorthand
in conversation: "Step 4" always means the BigQuery SQL transforms, etc.

Legend: ✅ done · 🔄 in progress · ⏳ not started

| Step | Stage (SVG) | What happens | Components | Status |
|----:|---|---|---|---|
| **1** | Data Pre-processing | Read each issuer tape, locate the data sheet, flatten to a clean AR-headed table, tag DealID + period | `src/ingest/` (`prep_rmbs.py`, `deals.py`) | 🔄 |
| **2** | High-speed load | Push each deal's extracted table into the BigQuery **staging** dataset (one raw table per deal) | `src/warehouse/load_bigquery.py` | 🔄 (BigQuery + datasets live; loader TBD) |
| **3** | Staging → transform | Staging tables become available to SQL (the handoff into processing) | BigQuery `rmbs_staging` | ⏳ |
| **4** | BigQuery SQL transforms | Conform AR→canonical, UNION to `marts.loans`, then build analytics marts + controls | `sql/` (staging→marts) | 🔄 (ref_ tables started) |
| **5** | SEC-ERBA RWA engine | Tranche attachment/detachment, risk weights, RWA + capital, period movement | `src/rwa/` | ✅ |
| **6** | Data Consumers | Power BI model, HTML dashboard, reporting + commentary | `powerbi/`, `docs/`, `src/reporting/` | 🔄 |

---

## Detail per step

### Step 1 — Data Pre-processing (`src/ingest`)  🔄
Turn a raw issuer tape into a clean, loadable table.
- **1a · Resolve** the deal + its tape(s) from `config/deals.yml` — `resolve_deal` ✅ (6/6 tests green).
- **1b · Extract** (the only non-SQL bit): per-format descriptor (sheet name, header row, file type)
  → flatten the AR-coded data sheet to a flat CSV, tag `DealID` + `CutoffDate`. ⏳
- *Why thin:* BigQuery can't read `.xlsx`; this step exists only to make each tape loadable. The
  real harmonisation is done later in SQL (Step 4).

### Step 2 — High-speed load (`src/warehouse/load_bigquery.py`)  ⏳
Load each deal's extracted CSV into the BigQuery **staging** dataset — one raw, AR-columned table
per deal (e.g. `rmbs_staging.loans_avon`). For now, upload may be done via the BigQuery console UI.

### Step 3 — Staging → transform handoff  ⏳
No code of its own — it's the point where the raw staging tables are in BigQuery and ready for SQL.

### Step 4 — BigQuery SQL transforms (`sql/`)  ⏳  ← the SQL showcase
- **4a · Conform** — one view per deal mapping AR codes → the **canonical schema**, decoding coded
  fields, casting, then `UNION ALL` into `rmbs_marts.loans`. This is where the five formats become one.
- **4b · Analytics marts** — pool summary + weighted averages, stratifications (LTV/seasoning/region),
  delinquency buckets + arrears migration, period-on-period CPR/CDR (window functions).
- **4c · Controls** — reconciliation & data-quality checks (`sql/controls.sql`).

### Step 5 — SEC-ERBA RWA engine (`src/rwa`)  ✅
Attachment/detachment/thickness from the capital structure, SEC-ERBA risk weights, RWA + 8% capital
per tranche and per deal, and period-on-period movement. (Python — the numeric showcase.)

### Step 6 — Data Consumers  🔄
- HTML dashboard prototype: Pool / Prepayment / Delinquency / Loss / Stress pages ✅; RWA + Portfolio pages ⏳.
- Power BI: star-schema CSVs + ~50 DAX measures + build guide ✅; RWA measures/page + BigQuery connection ⏳.

---

## Cross-cutting (the governs bar in the SVG)
IAM · KMS · Cloud Logging · validation/controls · data lineage — applies across Steps 2–6.

## Where we are right now (2026-06-19)
**Step 4 complete**: Star schema, 7 analytics marts, controls — SQL showcase delivered.
**Step 5 complete**: SEC-ERBA RWA engine — Python showcase delivered (24 tests passing).

Avon result: £839M pool → £330M RWA → £26.4M capital (39.4% density).

Next: Connect to Power BI, push to GitHub. See `WIP.md` for live next-steps.
