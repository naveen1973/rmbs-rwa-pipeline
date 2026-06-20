# Build Notes — RMBS RWA Pipeline

A plain-English journal of *what I decided and why*, written so it can be quoted directly
into GitHub (README sections, commit messages, the repo wiki, or a LinkedIn write-up).

- **WIP.md** = terse internal session log (Done / Decisions / Next).
- **docs/decisions/** = formal ADRs (one decision, alternatives weighed).
- **This file** = the narrative — the story a reader follows to understand the choices.

New entries are appended at the **bottom** (chronological).

---

## The goal

This is a portfolio piece built to evidence three competencies at once: (1) **securitisation
knowledge** — UK RMBS data, prepayment/credit/loss metrics, the capital structure, and
Basel 3.1 SEC-ERBA regulatory capital; (2) **ETL pipeline engineering** — a real
source-to-warehouse pipeline; and (3) **Power BI depth** — a properly modelled star schema
with DAX. The interactive HTML dashboard is a working *prototype* of the Power BI build,
made first so the layout and metrics could be agreed before assembling them in Power BI.

## Why BigQuery (not DuckDB)

The warehouse was switched from DuckDB to **BigQuery**. Reasoning: it's already on my CV,
it's a stronger cloud-architecture story for a data-warehousing/ETL role, and it lets the
project mirror a real reference cloud architecture (landing storage → warehouse →
processing → consumers). Datasets: `rmbs_staging` (raw) and `rmbs_marts` (curated), EU region.

## Why a deal registry (config-driven ingestion)

Rather than hard-coding one tape's filename, the pipeline reads `config/deals.yml` — a
registry of deals, each with a folder and a filename *pattern* (e.g. `*Data_Tape*.xlsx`).
A resolver (`src/ingest/deals.py`) turns a short id like `AVON2` into the absolute tape path
by globbing that pattern, and fails loudly if a deal is still awaiting data or the file is
missing. This is what makes the pipeline multi-deal instead of single-file, and it's the
same lookup the warehouse loader and RWA engine will reuse.

## Where transformation happens — ELT in BigQuery, not Power Query

A deliberate architecture choice (see ADR 0001). The pipeline follows an **ELT** pattern:
Python is kept thin (extract the messy multi-sheet `.xlsx`, decode the European DataWarehouse
coded fields, type it), and **all the analytical work is done in BigQuery SQL** — banding,
weighted averages, pool history, delinquency buckets, stratifications, and period-on-period
CPR/CDR using window functions. Power Query stays a thin connector (no business logic), and
DAX is reserved for slicer-reactive measures.

Why not transform in Power Query? Three reasons: (1) **single source of truth** — both the
Power BI model and the HTML dashboard read the *same* curated marts, so they can't drift;
(2) **updates don't require opening the .pbix** — a logic change is one version-controlled
`.sql` file, and the end-user just clicks Refresh; (3) it **showcases SQL** (a core goal) and
keeps the heavy lifting server-side. It's also the cheapest option.

## How a new tape gets loaded — local CLI now, zero cloud cost

Three ingestion designs were weighed (ADR 0001): a local CLI command, an
upload-to-Cloud-Storage trigger that auto-runs a Cloud Function, or manual upload through the
BigQuery console. I chose the **local CLI** for now — it has *zero standing cloud cost*, needs
no infrastructure, and demonstrates the ETL engineering cleanly. The code is kept
import-friendly so the Cloud Function version is a later *wrapper*, not a rewrite. BigQuery's
free tier (10 GB storage, 1 TB queries/month) comfortably covers this data, so running cost is
effectively £0.

## The architecture diagram

Re-drew the reference cloud architecture as `docs/architecture.svg`, mapped onto this stack
(prep_rmbs → BigQuery staging+marts → SQL transforms + SEC-ERBA RWA engine → Power BI / HTML).
SVG so it renders inline on GitHub and stays version-controllable.

## Showing Python depth — in-place, plus a separate engine project

Considered forking this repo into a parallel "Python-heavy" copy and rejected it: two copies
of the same pipeline diverge, cost maintenance, and read as padding rather than range. Senior
signal comes from using the *right tool per job* — which is exactly the ELT split here (SQL
for set-based analytics, Python for the iterative/numeric work). So Python depth is shown
**in-place** where it's genuinely the right tool: the **SEC-ERBA RWA engine** (`src/rwa/`),
the config-driven ingestion, the validation/reconciliation logic, and the pytest suite.

For a *pure* Python showcase, the plan is a **separate, genuinely different project** (not a
fork) — see the next entry / the dedicated repo when built.

## The deal resolver — and a small win for failing loudly

Built `resolve_deal` (in `src/ingest/deals.py`) test-first: six pytest cases pin down the
contract before the function exists. It turns a short id (`AVON2`) into the absolute path of
that deal's tape by globbing the folder for a filename *pattern*, and deliberately **refuses to
guess** — if zero files match, or more than one, it raises rather than picking something.

That strictness paid off immediately. The first real run against the Avon folder found *three*
files matching `*Data_Tape*.xlsx` (the combined workbook plus two split exports) and stopped
with a clear error naming all three. A looser "just take the first match" resolver would have
silently fed the wrong file into the pipeline. The fix was to tighten the pattern to the
combined workbook only (`*Data_Tape*_20[0-9][0-9].xlsx`). Small thing, but it's exactly the
kind of defensive, fail-loud data engineering that prevents silent bad loads in production.

## The five formats share one standard — the AR-field template

Reconnaissance on the five programmes' tapes (Avon, Bletchley, Canterbury, Hadrian, Stratton)
revealed they all use the **ESMA / Bank of England securitisation disclosure template** —
the regulatory RMBS loan-level field codes `AR1…AR236`. `AR3` is the loan id in every tape;
`AR67` is current balance in every tape.

So the "format chaos" is **packaging, not vocabulary**: the tapes differ by data-sheet name
(`AF 2 Current`, `Sheet1`, `Pool 4`, `BOE Template`), by AR-code subset (Avon carries 141 of
them, the BoE tapes ~233), by **extra columns** (Bletchley adds `EXTRA1…EXTRA11`, Avon adds
`Additional`/`Month End Interest`), by minor naming quirks (Hadrian's `AR162_`), by file type
(Stratton ships both `.xlsx` and `.csv`), and even by **schema drift within one programme**
(a Bletchley month with an added column).

This is the key to scaling to 50+: because the field codes are shared, the conform logic is
largely common (`AR3 → LoanID` everywhere). Onboarding a new programme reduces to a tiny
descriptor — which sheet, which header row, which file type, how to treat gaps/extras — while
the AR→canonical mapping, decoding and casting are written once, in SQL. The recognisable skill
on display: seeing the shared regulatory standard underneath superficially different tapes, and
conforming them to one canonical model in an isolated, version-controlled layer.

## The BoE template becomes the canonical foundation

Naveen surfaced the official **Bank of England RMBS loan-level reporting template** — the form every
UK issuer is mandated to file. We extracted its 233-field dictionary to `config/boe_rmbs_fields.csv`
(field code, mandatory/optional, static/dynamic, official name, category, data type, definition).

Three decisions fell out of it:
1. **Use the official BoE field names** — the canonical schema is self-documenting and audit-traceable
   straight back to the regulatory template.
2. **A two-table star, driven by the template's own static/dynamic flag:** `dim_loan` (static, one row
   per loan) + `fact_loan_period` (dynamic, one row per loan per cut-off). The template literally tells
   us which attributes are slowly-changing vs periodic — and this doubles as the Power BI star schema.
3. **Coverage = the mandatory set** (curated to ~58 analytically relevant fields), because mandatory
   fields are guaranteed present in every compliant tape, so harmonising them is reliable. This pulled
   in fields the first draft missed — cumulative recoveries (true loss severity), forbearance type,
   arrears-1/2-months-ago (arrears migration without prior tapes), payment frequency, BTL DSCR/rental,
   and EPC energy ratings.

The template also pins units: LTV and interest rates are specified in **decimal format** (4.8% → 0.048).
Avon's data carries them as percents — a concrete unit mismatch the conform layer normalises, and a
tidy illustration of *why* a conform layer is needed even when the field codes already match.

## The warehouse goes live — and the code decoder ring

Stood up BigQuery as the warehouse: project `rmbs-rwa-pipeline`, datasets `rmbs_staging` (raw) and
`rmbs_marts` (curated), in the EU region. Rather than write SQL trapped in the browser console, the
workflow is **`.sql` files in the repo, run with the `bq` CLI from VS Code** (`bq query
--use_legacy_sql=false < file.sql`) — so every transformation is version-controlled in git, which is
the whole point of the SQL showcase.

First transformations built: the `ref_*` **code-list tables**. UK RMBS tapes store coded values — e.g.
occupancy `3`, not "Buy-to-let"; account status `2`, not "Arrears". These small two-column lookup
tables (`code → label`) hold the meaning of each BoE code in one place, so the conform step can `JOIN`
to them to turn regulatory codes into human labels. Defining each code once — rather than scattering
`CASE WHEN` ladders across the codebase — is what keeps the pipeline legible and scalable to 50+ deals.
`ref_occupancy` (AR130) and `ref_account_status` (AR166) are done; ~15 more follow the same pattern.

(Worth noting for anyone running this on a machine with AVG/antivirus: AVG's TLS scanning broke the
`bq` CLI's SSL until we pointed gcloud at a CA bundle including AVG's root, and AVG's file shield had
to have the repo folder excluded so saves weren't blocked. Real-world tooling friction, solved.)

## Postcode-to-region mapping — handling what issuers actually send

The BoE template says AR128 (Geographic Region) should contain **ITL1 codes** — the official UK
territorial classification (`UKI` for London, `UKM` for Scotland, etc.). But in practice, many
issuers populate AR128 with **postcode outcodes** (e.g., `SW1`, `M15`, `EH3`) because that's what
their loan origination systems or broker platforms capture. When you scale to 50+ programmes, the
clean ITL1 codes are the exception, not the rule.

The solution: a **postcode-area-to-region mapping table** (`ref_postcode_to_region`). UK postcodes
have a predictable structure — the first 1–2 letters (the "postcode area") map directly to a region:

| Postcode area | Region |
|---------------|--------|
| SW, W, WC, EC, E, N, NW, SE, BR, CR, HA, IG, RM, TW, UB | London (UKI) |
| M, L, PR, WA, WN, BL, OL, SK, CW, BB, CA, CH, FY, LA | North West (UKD) |
| EH, G, ML, PA, FK, KY, DD, AB, DG, IV, KA, KW, PH, TD, ZE | Scotland (UKM) |
| BT | Northern Ireland (UKN) — *all of NI uses BT* |
| … | … |

The conform layer then handles all formats transparently:

```sql
LEFT JOIN ref_postcode_to_region p
  ON REGEXP_EXTRACT(UPPER(AR128), r'^([A-Z]{1,2})') = p.postcode_area
LEFT JOIN ref_region r
  ON COALESCE(p.region_code, AR128) = r.code
```

The regex extracts 1–2 leading letters before any digit — critical because some areas are single
letters (M, L, S, E, N, W, G, B). A naive `LEFT(AR128, 2)` would turn `"M15"` into `"M1"` and fail.

If AR128 is already `UKI` → no regex match → falls through to direct region lookup. If it's
`SW1A 2AA` → extract `SW` → map to `UKI` → join to region label. If it's `M15` → extract `M` →
map to `UKD` (North West). One mapping table, written once, handles the real-world messiness that 50 different
`CASE WHEN` statements never could.

This is the kind of harmonisation logic that only comes from working with real UK RMBS data — and
it's exactly what makes the pipeline scalable.

## The conform layer — one view per deal, one canonical output

Built the first **conform view** (`conform_avon_dim_loan`) in pair mode. The pattern:

1. **SELECT** AR columns → rename to canonical names (AR3 → LoanID, AR130 → OccupancyType)
2. **LEFT JOIN** ref_* tables → decode codes to labels (AR130 = "3" → "Buy-to-let")
3. **CAST/transform** → correct types, handle NULLs, normalise units
4. **FROM** the staging table (raw AR-coded data)

Each deal gets its own conform view (`conform_avon_dim_loan`, `conform_bletchley_dim_loan`, etc.)
because deals have quirks: Avon stores LTV as decimal (0.86), another might store as percent (86).
The per-deal view handles that; the final `dim_loan` table just UNIONs them all.

This is the scalability architecture: shared ref_* tables + shared canonical schema + per-deal
conform logic. Onboard a new deal = write one small conform view, not rewrite the pipeline.

## Analytics marts — stratification views

With the star schema in place (`dim_loan` + `fact_loan_period`), the next layer is **analytics marts**:
aggregate views that slice the portfolio by risk dimensions. These are the views Power BI consumes.

Built seven marts:

| Mart | Dimensions | SQL techniques |
|------|------------|----------------|
| `pool_summary` | Deal × Period | `SUM`, `SAFE_DIVIDE`, weighted averages |
| `strat_ltv` | LTV bands | `CASE` banding, window `SUM() OVER` for % of total |
| `strat_delinquency` | Arrears buckets | `CASE` + `COUNTIF` |
| `strat_region` | ITL1 region | JOIN to `dim_loan.Region` |
| `strat_seasoning` | Vintage bands | `DATE_DIFF` + `CASE` |
| `strat_occupancy` | OO vs BTL | Categorical grouping |
| `strat_repayment` | IO vs Capital | Categorical grouping |

Each mart returns one row per (DealID, CutoffDate, Band) — ready for a Power BI matrix or chart with
a period slicer. The window function `SUM(x) OVER (PARTITION BY DealID, CutoffDate)` calculates
each band's share of the total without a self-join.

**Portfolio insights surfaced:**
- 82% Interest-Only at 82% WA LTV — textbook non-conforming risk profile
- 99.7% pre-2010 vintage — legacy book, fully seasoned
- 30% of balance at 90%+ LTV; WA LTV rises with delinquency (75% → 83%)
- 40% geographic concentration in South East + London

These insights are exactly what a credit analyst or investor would look for in a deal review — and
the SQL that produces them is the portfolio's "SQL depth" evidence.

## Controls — data quality checks

Built `sql/controls/controls_reconciliation.sql` with five checks:

| Check | What it validates |
|-------|-------------------|
| ROW_COUNT_MISMATCH | Staging rows = conform rows |
| BALANCE_MISMATCH | Sum of balances reconciles |
| NULL_LOAN_ID | No NULL keys in dim_loan |
| NULL_BALANCE | No NULL balances in fact |
| ORPHAN_FACT_ROWS | Every fact row has a matching dim |
| NEGATIVE_BALANCE | Flags loans with balance < 0 |

The query returns **only failing checks** — an empty result means all passed. This pattern ("report
exceptions only") is standard for production reconciliation: no news is good news, failures surface
immediately.

Avon results: all passed except 2 loans with tiny negative balances (-£0.01, -£0.03) — these are
overpayments, not data errors, and acceptable in RMBS data.

**Important: when onboarding a new programme, run controls BEFORE building analytics marts.** The
correct pipeline order is:

1. Load to staging
2. Create conform views
3. **Run controls** — validate row counts, balances, NULLs
4. Build analytics marts (stratifications)

We built analytics first for Avon (iterating on the showcase), but production onboarding should
validate data quality before metrics are built on top of it.

**GitHub transparency:** Publish a summary of control results (pass/fail, row counts, balance totals)
in the README or a dedicated `docs/data_quality.md`. This builds trust in the metrics — readers can
see the data was validated, not just transformed. Professional pipelines show their receipts.

## SEC-ERBA RWA engine — the Python showcase

The RWA engine (`src/rwa/`) implements Basel 3.1's Securitisation External Ratings-Based Approach.
This is where the Python depth lives — numeric calculations, data classes, and a comprehensive test
suite (24 unit tests).

**Architecture:**

| Module | Purpose |
|--------|---------|
| `sec_erba.py` | Risk weight lookup table (17 ratings × 2 seniorities), maturity interpolation, 15% floor, 1250% unrated |
| `capital_structure.py` | `Tranche` and `CapitalStructure` dataclasses, attachment/detachment/thickness |
| `rwa_calculator.py` | `RWA = EAD × Risk Weight`, `Capital = RWA × 8%`, formatted reporting |

**Key features:**
- **Rating normalisation** — accepts both S&P (AAA) and Moody's (Aaa) formats
- **Maturity interpolation** — linear between 1yr and 5yr anchor points per Basel spec
- **Thickness adjustment** — thin mezzanine tranches get scaled-up risk weights
- **Validation** — detects overlapping tranches, missing senior designation

**Avon result (Nov 2020):**

| Tranche | Rating | Thickness | RW | RWA | Capital |
|---------|--------|-----------|-----|-----|---------|
| Class A | AAA | 85% | 18.1% | £129M | £10.3M |
| Class B | AA | 7% | 46.4% | £27M | £2.2M |
| Class C | A | 4% | 85.4% | £29M | £2.3M |
| Class D | BBB | 3% | 159.6% | £40M | £3.2M |
| FLP | NR | 1% | 1250% | £105M | £8.4M |
| **Total** | | | **39.4%** | **£330M** | **£26.4M** |

The FLP (first loss piece) dominates capital consumption — at 1250% risk weight, £8.4M of the pool
requires £105M RWA. This is the Basel penalty for holding unrated equity risk.

Run: `python scripts/run_rwa.py`
