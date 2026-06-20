# Work In Progress (WIP) Log

## Project goals (north star)
This is a portfolio piece to showcase three competencies. Every task should serve one of them:
1. **Securitisation knowledge** — UK RMBS data, prepayment/credit/loss metrics, capital structure, Basel 3.1 SEC-ERBA RWA.
2. **ETL pipeline engineering** — Python ingestion → BigQuery warehouse (staging→marts) → SQL transforms, with controls & lineage.
3. **Power BI dashboard depth** — star schema + DAX measures + build guide. (The HTML dashboard is a prototype of the PBI build.)


A running record of decisions, current state, and next steps. Newest entries at the top.

> **Step numbers** refer to `docs/pipeline_steps.md` (keyed to `docs/architecture.svg`).

---

## 2026-06-19 — Star schema + analytics marts complete

**Done**
- **`conform_avon_fact_loan_period`** view complete — dynamic fields (CurrentBalance, ArrearsBalance, AccountStatus, etc.)
  - Handled missing AR columns in Avon: AR123 (ForbearanceType), AR162 (EPC), AR173 (PerformanceArrangementDate) not present — commented as deal-specific gaps.
  - Fixed: AR109/AR110 divided by 100 (Avon stores rates as %), AR55 quarterly format parsed.
- **`docs/data_flow.svg`** created — visual diagram for GitHub.
- **`dim_loan.sql` + `fact_loan_period.sql`** — UNION ALL of conform views (star schema complete).
- **7 analytics marts** built:
  - `pool_summary` — aggregate metrics (8,246 loans, £839M, WA LTV 75.8%, WA Rate 2.64%)
  - `strat_ltv` — 30% of pool is 90%+ LTV
  - `strat_delinquency` — 87% current, 4.9% 3M+ arrears
  - `strat_region` — 40% South East + London concentration
  - `strat_seasoning` — 99.7% is 10yr+ vintage (pre-crisis)
  - `strat_occupancy` — 76% OO, 24% BTL
  - `strat_repayment` — 82% Interest-Only at 82% WA LTV (non-conforming signal)

**Key portfolio insights documented:** Classic non-conforming RMBS profile — high IO concentration, pre-crisis origination, elevated LTV in arrears buckets.

- **Controls** (`sql/controls/controls_reconciliation.sql`) — 5 checks (row count, balance, NULL keys, orphans, negative balance). All passed; 2 tiny negative balances flagged (overpayments, acceptable).

**Note for new programmes:** Run controls BEFORE analytics marts. Order: staging → conform → controls → analytics.

- **RWA engine (Step 5)** complete:
  - `src/rwa/sec_erba.py` — risk weight lookup (17 ratings × 2 seniorities × maturity interpolation)
  - `src/rwa/capital_structure.py` — Tranche + CapitalStructure classes
  - `src/rwa/rwa_calculator.py` — RWA = EAD × RW, Capital = RWA × 8%
  - `tests/test_rwa.py` — 24 unit tests, all passing
  - **Avon result:** £330M RWA, £26.4M capital (39.4% RWA density)

## 2026-06-20 — Multi-deal pipeline complete (Avon + Bletchley)

**Done**
- **Python loader** (`src/warehouse/load_bigquery.py`) — CLI with `--deal` and `--tape` filters, uses bq CLI for AVG SSL compatibility
- **Bletchley loaded** (1,079 loans, £233M, Aug 2024 tape)
- **Bletchley conform views** — handles different format (actual dates, decimal rates)
- **UNION views updated** — `dim_loan` + `fact_loan_period` now include both deals
- **Analytics marts** auto-refresh for both deals (no changes needed)

**Key format differences handled:**
- Avon: AR55 quarterly ("Q4-2006"), AR109 percent (2.64)
- Bletchley: AR55 actual date, AR109 decimal (0.0384)

**Portfolio now:** 9,325 loans, £1,072M across 2 deals

**Power BI connected** (same session)
- BigQuery connector configured (Import mode)
- Loaded: dim_loan, fact_loan_period, pool_summary
- Star schema relationships auto-detected
- Basic visuals: Balance by Deal, LoanCount card, Deal slicer, metrics table
- Saved: `powerbi/RMBS_BigQuery_Dashboard.pbix`
- **Fix applied:** Python loader now converts "ND" (No Data) → NULL at source

**Next steps**
1. GitHub page (separate focused session)
2. Phase 2: Add Canterbury
3. Phase 3: Hadrian + Stratton for automation GIF demo
2. Analytics marts (Step 4b): pool summary, stratifications, delinquency buckets
3. RWA engine (Step 5)

---

## 2026-06-18 — All ref_* tables done; first conform view complete (pair mode)

**Done**
- All **18 ref_* code-list tables** created in `rmbs_marts` (including `ref_postcode_to_region` for real-world postcode→ITL1 mapping).
- Loaded **Avon Nov 2020** tape to `rmbs_staging.loans_avon` (8,246 loans, £839m).
- **`conform_avon_dim_loan`** view complete — Naveen wrote in pair mode:
  - SELECT with decoded fields (EmploymentStatus, OccupancyType, Purpose, RepaymentMethod, PropertyType, etc.)
  - LEFT JOINs to ref_* tables
  - Unit normalisation (LTV already decimal in Avon, no division needed)
- Learned: each deal gets its own conform view to handle deal-specific quirks.

**Key insight documented (BUILD_NOTES):** `ref_postcode_to_region` — issuers send postcodes not ITL1 codes; use `REGEXP_EXTRACT(AR128, r'^([A-Z]{1,2})')` to extract postcode area. Real-world harmonisation knowledge.

**⏸ Paused at:** `conform_avon_dim_loan` done; `conform_avon_fact_loan_period` next.

**Next steps**
1. Create `conform_avon_fact_loan_period.sql` — dynamic fields (CurrentBalance, ArrearsBalance, AccountStatus, etc.)
2. Create `dim_loan.sql` + `fact_loan_period.sql` — UNION ALL of conform views
3. Analytics marts (Step 4b) + controls (4c)
4. RWA engine (Step 5)

---

## 2026-06-17 (addendum 2) — BigQuery live from VS Code; first ref_ tables built

**Done**
- BigQuery connected **from VS Code** via `bq` CLI. Created GCP project **`rmbs-rwa-pipeline`**
  (settings.yml updated) + datasets **`rmbs_staging`** and **`rmbs_marts`** (EU).
- Workflow: author `sql/*.sql` in repo → `bq query --use_legacy_sql=false < file.sql` → version-controlled SQL.
- Built **`ref_occupancy`** (AR130) and **`ref_account_status`** (AR166) tables in `rmbs_marts` — pair mode, Naveen wrote the SQL.
- **AVG fixes:** (1) TLS interception broke `bq` SSL → custom CA bundle (`core/custom_ca_certs_file`,
  see memory [[bq-ssl-avg-fix]]); (2) AVG locked files on save → added repo folder to AVG exceptions.

**⏸ Paused at:** building the ~17 `ref_*` code-list tables (2 of 17 done).
**Open decision:** pacing — Naveen likely agreed to **A) I bulk-generate the remaining ref_ tables, he reviews**,
then he writes the conform views + analytics himself (confirm tomorrow).

**Known issue:** `sql/marts/ref_occupancy.sql` *file* is ghost-locked (AVG handle) — the **table is fine in
BigQuery**; recreate the file after a **reboot** (content is in WIP/earlier messages).

**Next steps**
1. Reboot → recreate `sql/marts/ref_occupancy.sql` (ghost clears on reboot).
2. Generate remaining `ref_*` tables from `config/boe_rmbs_fields.csv` (List fields: AR21,27,58,59,60,69,70,84,107,108,123,128,131,137,162).
3. Conform views (Step 4a): AR→canonical + decode (JOIN ref_) + unit-normalise → `dim_loan` + `fact_loan_period`. ← Naveen writes.
4. Load a tape to `rmbs_staging` (Step 2) so conform has input; fix deals.yml folders + multi-period resolve.
5. Analytics marts (4b) + controls (4c); then RWA (Step 5); publish.

---

## 2026-06-17 (addendum) — five-format recon; harmonisation reframed; canonical schema next

**Done**
- Reconnaissance on all five programmes' tapes (Avon, Bletchley, Canterbury, Hadrian, Stratton).
  **Key finding:** they all use the **ESMA/BoE AR-field standard** (`AR1…AR236`). The differences
  are *packaging* not *vocabulary* — data-sheet name, AR-code subset, extra columns (Bletchley
  `EXTRA1–11`), naming quirks (Hadrian `AR162_`), file type (Stratton csv+xlsx), and intra-programme
  schema drift. Logged in BUILD_NOTES.
- Created `docs/pipeline_steps.md` — numbered step reference (Step 1–6) keyed to the SVG.

**Decisions / reframing**
- Harmonisation is **packaging-level**, so the conform logic is largely shared (`AR3→LoanID` everywhere).
  Onboarding a new programme = a tiny descriptor (sheet, header row, file type, gaps/extras) + the
  shared AR→canonical mapping written **once in SQL** (Step 4a). Scales cleanly to 50+.
- **Power Query is NOT the harmonisation layer** (job-winning narrative — see memory + BUILD_NOTES).
- SQL = hands-on **learning exercise**, pair mode (Naveen writes, I scaffold/explain), like resolve_deal.

**Folder renames noted** (deals.yml `folder:` fields now stale — to fix): Avon→`Avon Finance No 2 Plc`,
Bletchley→`Bletchley Park Funding 2024-1 PLC 1`, Canterbury→`Canterbury Finance No 3`,
Hadrian→`Hadrian Funding 2025-1 PLC`. Also: 3 monthly tapes per folder → resolver's "exactly one"
rule must become "list periods". No manual file-splitting (Step 1b extract handles one source file).

**Update — canonical schema done (BoE-aligned).** Naveen provided the official BoE RMBS template;
extracted its 233-field dictionary to `config/boe_rmbs_fields.csv`. Canonical schema v2 written
(`docs/canonical_schema.md`): two-table star `dim_loan` (static) + `fact_loan_period` (dynamic),
curated ~58 mandatory fields, official names, `ref_*` code-list seed tables. Units = decimal per BoE
spec (Avon stores percents → conform normalises).

**Next steps**
1. ✅ Canonical schema v2 **accepted** (2026-06-17). Field set signed off.
2. Build `ref_*` code-list seed tables from the BoE definitions — **first SQL, pair mode**.
   Needs BigQuery: resume the Sandbox setup (interrupted earlier) so the SQL is runnable.
3. Pair-write the conform SQL (Step 4a): AR→canonical + decode + unit-normalise → `dim_loan` + `fact_loan_period`.
4. Stand up BigQuery Sandbox + load staging (Steps 2–3); fix deals.yml folders + multi-period resolve.
5. Analytics marts + controls (Step 4b/4c); then RWA (Step 5); publish.

---

## 2026-06-17 — resolver done; pivot to SQL-first

**Done**
- Finished `resolve_deal` in `src/ingest/deals.py`; all 6 tests in `tests/test_deals.py` green.
- Verified end-to-end against the real Avon tape — the 0/1/many guard caught **3** files matching
  `*Data_Tape*.xlsx`, so tightened `config/deals.yml` tape_pattern to `*Data_Tape*_20[0-9][0-9].xlsx`
  (combined workbook only). Logged the story in BUILD_NOTES.

**Decisions (priorities reset)**
- **SQL first, then publish.** SQL skills sit inside goal 2 (ETL) — prioritise the BigQuery SQL transforms.
- **No DuckDB** (keep the warehouse = BigQuery decision clean). Run SQL on **BigQuery itself**: stand up
  the free BigQuery Sandbox, upload the curated CSVs via the console UI (no Python), write/run pure SQL there.
- `--deal` wiring into prep_rmbs + DealID stamping = **parked** (multi-deal plumbing, not SQL/publish).

**Next steps**
1. Scaffold `sql/` layered structure (staging → intermediate → marts) + `sql/controls.sql`.
2. Build the SQL showcase against the CSVs (Naveen on the pen): pool summary, banding, stratifications,
   delinquency + arrears migration (window funcs), period-on-period CPR/CDR.
3. `git init` + push + enable GitHub Pages.

---

## 2026-06-16 (session) — Architecture: ELT in BigQuery + local ingest

**Done**
- Scaffolded `src/ingest/deals.py` (registry resolver): `load_registry` + `find_deal` written;
  `resolve_deal` left as a guided stub for Naveen to implement (pair mode).
- Recorded **ADR 0001** (`docs/decisions/0001-ingestion-and-transformation.md`) — the 3 ingest
  options + the transform-location decision, so the choices are evidenced.
- Added `docs/architecture.svg` — GitHub-ready architecture image (reference cloud diagram
  mapped to this GCP/BigQuery pipeline, stages 1–6).

**Decisions**
- **Ingest = Option 1 (local CLI)** for now → zero standing cloud cost. Keep code import-friendly
  so a Cloud Function (Option 2) is a later wrapper, not a rewrite.
- **Transform = ELT in BigQuery SQL** (showcases SQL, goal #2). Shrink Python to extract+decode;
  move banding / weighted averages / pool history / delinquency / stratifications / CPR-CDR
  movement into layered SQL (`staging → intermediate → marts`) + a `controls` reconciliation suite.
- **Power Query stays thin** (connect + types only); **DAX** = slicer-reactive measures only.
- Cost: BigQuery free tier (10 GB storage / 1 TB queries pm) → effectively £0; use views,
  materialise only small marts, partition by `cutoff_date`, cluster by `deal`.

**Also done this session**
- Wrote contract tests `tests/test_deals.py` + root `conftest.py` (puts repo root on import path).
  Current state: `find_deal` 2 tests PASS; `resolve_deal` 4 tests FAIL (NotImplementedError) — by design,
  they're the target to code against. Installed `pytest` globally (no venv yet).
- Embedded `docs/architecture.svg` in README; created `docs/BUILD_NOTES.md` (GitHub-facing journal).

**⏸ Paused at:** implementing `resolve_deal` in `src/ingest/deals.py`, pair mode, one step at a time.
Gave a 6-step walkthrough (Step 1 = `registry = registry or load_registry()` at top of the function
body, replacing the `raise NotImplementedError`). Naveen is about to write Step 1; Steps 2–6 = find the
deal, status guard, build folder path, glob the tape pattern, guard 0/1/many matches + return tuple.

**Next steps**
1. Finish `resolve_deal` (Steps 1–6) → `python -m pytest tests/test_deals.py -v` all 6 green →
   smoke-test `resolve_deal('AVON2')` against the real OneDrive tape.
2. Wire `--deal` into `prep_rmbs.main()` + stamp `DealID` on output frames (pair).
3. Build `src/warehouse/load_bigquery.py` (Cloud-Function-ready shape).
4. Layered SQL transforms under `sql/` + `sql/controls.sql`.

---

## 2026-06-14 (addendum) — Warehouse = BigQuery

Switched warehouse from DuckDB to **BigQuery** at Naveen's request (already on his CV;
better cloud-architecture fit and stronger JD evidence for data warehousing/ETL).
- GCS = landing bucket (reference "COS Bucket"); BigQuery = "Secure Database".
- Datasets: `rmbs_staging` (raw) + `rmbs_marts` (curated). Region: EU.
- A BigQuery connector is available in this workspace; once Naveen sets project_id and
  authenticates, the loads/queries can run directly against his BigQuery.
- Next: build `src/warehouse/load_bigquery.py` and BigQuery SQL transforms.

## 2026-06-14 — Repo scaffold + architecture

**Done**
- Agreed to evolve the single-deal RMBS dashboard into a realistic, GitHub-ready
  **RMBS RWA pipeline** that doubles as a learning project for an RWA Reporting role.
- Scaffolded repo structure (`src/{ingest,warehouse,transform,rwa,reporting}`, `sql`,
  `docs`, `powerbi`, `tests`, `config`, `data`).
- Migrated existing assets in: `prep_rmbs.py` (ingest), DAX measures + build guide
  (powerbi), HTML preview (docs), curated CSVs (data).
- Wrote architecture flow (`docs/pipeline.md`) mapping the reference cloud diagram to
  pipeline stages 1–6 + controls.
- Authored README, .gitignore, requirements.txt, deals.yml registry, this WIP, TASKS.md.

**Decisions**
- Warehouse = **BigQuery** (Google Cloud) — see addendum above. GCS landing + BigQuery datasets.
- Working mode = **pair** (I scaffold, you complete key parts) — confirm or change.
- Lead RWA approach = **SEC-ERBA** (ratings-based), SEC-SA as a later comparison.
- UK RMBS only; EDW AR-field tape format is the standard.

**Current state**
- Avon Finance No.2 fully processed (8,312 loans, £846.6m, WA LTV 75.8%, verified vs IR).
- Other 4 deals registered, folders empty (awaiting tapes).
- RWA engine **not yet built** — next major task.

**Next steps**
1. Build `src/warehouse/load_duckdb.py` (CSVs → staging → marts).
2. Build `src/rwa/sec_erba.py` (SEC-ERBA risk weights, RWA, capital) + tests.
3. Add RWA page to the HTML preview + RWA DAX measures.
4. SQL transform scripts (`sql/transform`, `sql/controls`).
5. Controls & data-lineage doc (`docs/data_lineage.md`, `docs/methodology_rwa.md`).
6. Generalise to multi-deal (Deals dimension keyed by DealID).
7. Initialise git + push to GitHub.

---

## How to use this file
Add a dated entry each working session: what was **Done**, any **Decisions**, the
**Current state**, and the **Next steps**. Keep it short — it's the project memory.

## 2026-06-16 — GitHub Pages ready

- Set `config/deals.yml` `data_root` to the absolute OneDrive Issuers path (survives the folder rename).
- Added `docs/index.html` (Pages landing page → links to the live dashboard) + `docs/.nojekyll`.
- Added `docs/GITHUB_SETUP.md` (push + enable Pages, via gh CLI or manual).
- Next session (in VS Code): wire `prep_rmbs` to resolve `--deal` from deals.yml/data_root,
  then build `src/warehouse/load_bigquery.py` and `src/rwa/sec_erba.py`.
