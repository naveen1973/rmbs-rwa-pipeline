# RMBS RWA Pipeline

A UK RMBS surveillance **and** securitisation regulatory-capital (RWA) platform.
It ingests issuer loan-level data tapes and investor reports, builds a BigQuery cloud
data warehouse, computes **Basel 3.1 / UK CRR securitisation RWA (SEC-ERBA)** on the
note tranches, and serves the results to a Power BI dashboard.

## What this project demonstrates

This project is a portfolio piece built to evidence three core competencies:

1. **Securitisation knowledge** — working fluently with real UK RMBS data: the loan-level
   data tape and investor report, prepayment (CPR/SMM/PSA), delinquency and arrears, default
   and loss severity, the note capital structure, and Basel 3.1 / UK CRR securitisation
   regulatory capital (SEC-ERBA RWA).
2. **ETL pipeline engineering** — a real source-to-warehouse pipeline: ingestion and
   validation in Python, a BigQuery cloud data warehouse (staging → marts), SQL
   transformations, reconciliation controls and documented data lineage.
3. **Power BI dashboard depth** — a properly modelled star schema with DAX measures,
   designed for genuine management information, not just charts.

## What it does

- **Ingest** — parses the European DataWarehouse AR-field loan-level tape (8,000+ loans),
  decodes coded fields, derives investor metrics (CPR/SMM/PSA, delinquency buckets, LTV,
  loss severity), and the redemptions/defaults log.
- **Warehouse** — loads curated facts and dimensions into **BigQuery** (`staging` + `marts` datasets).
- **RWA** — computes tranche attachment/detachment, thickness, SEC-ERBA risk weights,
  RWA and 8% capital per tranche and per deal; tracks period-on-period movement.
- **Serve** — Power BI dashboard (star schema + DAX measures) connected to BigQuery.

## Power BI Dashboard

Three-page dashboard connected to BigQuery via native connector:

| Page | Purpose | Key Visuals |
|------|---------|-------------|
| **Pool Analysis** | Pool composition snapshot | KPIs (Balance, Count, WA_LTV, WA_Rate), Region bar, LTV band bar, Occupancy donut |
| **Capital Structure** | Tranche-level RWA | Waterfall of tranches, RW by rating, Capital requirements |
| **Time Series** | Performance over time | Pool Factor, CPR, Arrears 90+, Balance trends |

![Pool Analysis](docs/screenshots/01_pool_analysis.png)
![Capital Structure](docs/screenshots/02_capital_structure.png)
![Time Series](docs/screenshots/03_time_series.png)

## Architecture

![RMBS RWA pipeline architecture](docs/architecture.svg)

Source → pre-processing → BigQuery warehouse → SQL/RWA processing → consumers, on Google Cloud.
See **[docs/pipeline.md](docs/pipeline.md)** for the stage-by-stage mapping and run order, and
**[docs/decisions/0001-ingestion-and-transformation.md](docs/decisions/0001-ingestion-and-transformation.md)**
for why ingestion runs locally and transformation runs as BigQuery SQL.

## SEC-ERBA RWA Engine

The pipeline includes a **Basel 3.1 / UK CRR securitisation RWA engine** implementing the
**External Ratings-Based Approach (SEC-ERBA)** — the regulatory method for calculating
risk-weighted assets on rated securitisation positions.

### How it works

**Risk-Weighted Assets (RWA)** determine how much capital a bank must hold against a position:

```
RWA = Exposure × Risk Weight
Capital Requirement = RWA × 8%
```

SEC-ERBA assigns risk weights based on three factors:

| Factor | Impact |
|--------|--------|
| **Credit Rating** | AAA → 15%, BBB → 105%, Unrated → 1250% |
| **Seniority** | Senior tranches get lower risk weights |
| **Maturity** | Longer WAL → higher risk weight (interpolate 1yr ↔ 5yr) |

### Capital structure concepts

```
         100% ┌─────────────────────────────┐
              │     Class A (Senior)        │ ← AAA, 85% thickness, 15-20% RW
         15%  ├─────────────────────────────┤
              │     Class B (Mezz)          │ ← AA, 7% thickness
          8%  ├─────────────────────────────┤
              │     Class C (Mezz)          │ ← A, 4% thickness
          4%  ├─────────────────────────────┤
              │     Class D (Junior)        │ ← BBB, 3% thickness
          1%  ├─────────────────────────────┤
              │     FLP (First Loss)        │ ← Unrated, 1250% RW
          0%  └─────────────────────────────┘
              ↑                             ↑
         Attachment                    Detachment
```

- **Attachment point (A)** = where losses start hitting this tranche
- **Detachment point (D)** = where losses fully wipe out this tranche
- **Thickness = D − A** = tranche size as % of pool
- **Credit Enhancement (CE)** = subordination below senior tranche (here: 15%)

### Example output (AVON2)

```
Tranche    Rating   Balance       RW        RWA           Capital
───────────────────────────────────────────────────────────────────
Class A    AAA      £648.2M      18.1%     £117.5M        £9.4M
Class B    AA        £32.5M      43.8%      £14.2M        £1.1M
Class C    A         £32.5M      76.2%      £24.8M        £2.0M
Class D    BBB       £24.4M     140.0%      £34.1M        £2.7M
Class E    BB        £20.3M     330.0%      £67.0M        £5.4M
Class F    B          £8.1M     750.0%      £60.9M        £4.9M
Class Z    NR        £28.4M    1250.0%     £355.5M       £28.4M
───────────────────────────────────────────────────────────────────
TOTAL               £794.5M      84.9%     £674.1M       £53.9M
```

**Key insight:** The unrated Class Z (3.5% of pool) consumes **53% of total RWA** —
this is Basel's penalty for holding equity risk in a securitisation.

For the full methodology with worked examples, see **[docs/RWA_METHODOLOGY.md](docs/RWA_METHODOLOGY.md)**.

## Disclaimer
Built from public-style securitisation data for learning/demonstration. The RWA figures
use documented, simplified assumptions and are **not** a production regulatory calculation.
