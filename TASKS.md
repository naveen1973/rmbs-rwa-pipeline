# Task Checklist

Legend: [x] done · [~] in progress · [ ] to do

## 0 · Project setup
- [x] GitHub Pages landing page (docs/index.html) + setup guide
- [x] Profile Avon loan-level tape + redemptions log
- [x] Read investor report for structure & benchmark metrics
- [x] Scaffold GitHub-ready repo structure
- [x] Pipeline architecture diagram (docs/pipeline.md)
- [x] Architecture image for GitHub (docs/architecture.svg)
- [x] ADR 0001: ingestion trigger + transform location (docs/decisions/)
- [x] README / .gitignore / requirements.txt / deals.yml
- [x] WIP log + this task list
- [x] git init + push to GitHub (live: github.com/naveen1973/rmbs-rwa-pipeline)

## 1 · Ingestion (src/ingest)
- [x] Parse EDW AR-field tape, decode coded fields, derive metrics
- [x] Parse redemptions/defaults (Sales sheet) + loss severity
- [ ] Parse investor-report PDF into structured pool-summary table
- [~] Multi-deal loop driven by config/deals.yml (DealID on every row)
  - [x] Deal registry resolver `src/ingest/deals.py` + tests (resolve --deal -> tape path)
  - [ ] Wire `--deal` into prep_rmbs.main() + stamp DealID on output frames (parked)
- [ ] Input validation + row-count / balance reconciliation log

## 2-3 · Warehouse (src/warehouse, BigQuery)
- [x] config/settings.yml: project_id `rmbs-rwa-pipeline`, datasets, location EU
- [x] BigQuery project + datasets `rmbs_staging` & `rmbs_marts` (EU) created
- [x] Auth + connectivity from VS Code via `bq` CLI (AVG cert/lock fixes applied)
- [x] load_bigquery.py: CLI to upload LLD to BigQuery staging (--deal, --tape filters)
- [ ] Build `marts` dataset (facts: loans, exits, pool_history, delinquency; dims: deal, date)
- [ ] Incremental monthly append keyed by (deal, cutoff_date)
- [ ] (optional) GCS landing bucket for raw extracts

## 4 · BigQuery SQL transforms (sql/)  ← ELT: do the analytical work here (SQL showcase)
- [x] Extract BoE field dictionary (config/boe_rmbs_fields.csv, 233 fields)
- [x] Canonical schema accepted (docs/canonical_schema.md): dim_loan (static) + fact_loan_period (dynamic)
- [x] ref_* code-list seed tables (from BoE definitions) — 18/18 done (incl. ref_postcode_to_region)
- [x] conform_<deal> views: AR→canonical + decode + unit-normalise → dim_loan + fact_loan_period
  - [x] conform_avon_dim_loan (pair mode)
  - [x] conform_avon_fact_loan_period
  - [x] conform_bletchley_dim_loan
  - [x] conform_bletchley_fact_loan_period
- [x] Layered structure: staging → intermediate (views) → marts
- [x] dim_loan + fact_loan_period (UNION ALL of conform views)
- [x] Pool summary + weighted averages in SQL (pool_summary.sql)
- [x] Banding (LTV/seasoning) as SQL CASE in intermediate views
- [x] Stratification views — 6 complete:
  - [x] strat_ltv (LTV bands)
  - [x] strat_delinquency (arrears buckets)
  - [x] strat_region (ITL1 geographic)
  - [x] strat_seasoning (vintage)
  - [x] strat_occupancy (OO vs BTL)
  - [x] strat_repayment (IO vs Capital)
- [ ] Period-on-period CPR/CDR via window functions across cutoff dates
- [x] Controls: reconciliation & data-quality checks (sql/controls/controls_reconciliation.sql)
- [ ] Partition facts by cutoff_date, cluster by deal (cost/perf)

## 5 · RWA engine (src/rwa)  ← COMPLETE
- [x] Tranche attachment / detachment / thickness from capital structure
- [x] SEC-ERBA risk-weight table (Basel 3.1 / UK CRR) + maturity interpolation
- [x] Non-senior thickness adjustment, 15% floor, unrated -> 1250%
- [x] RWA + 8% capital per tranche and per deal
- [x] Unit tests (tests/test_rwa.py) — 24/24 passing
- [ ] Period-on-period RWA movement walk + auto commentary
- [ ] SEC-SA comparison (secondary)

## 6 · Consumers
- [x] HTML preview: Pool / Prepayment / Delinquency / Loss / Stress pages
- [ ] HTML preview: RWA & Capital page
- [ ] HTML preview: Portfolio (multi-deal) page
- [x] Power BI: star-schema CSVs + ~50 DAX measures + build guide
- [x] Power BI: connected to BigQuery (native connector), basic dashboard saved

## 7 · Governance
- [ ] docs/methodology_rwa.md (SEC-ERBA methodology & assumptions)
- [ ] docs/data_lineage.md (source -> field -> output traceability)
- [ ] Logging across pipeline stages
