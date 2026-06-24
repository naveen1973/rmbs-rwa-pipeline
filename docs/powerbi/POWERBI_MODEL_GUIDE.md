# Power BI Model Guide — RMBS RWA Dashboard

This document explains the Power BI data model for the RMBS surveillance dashboard.
It covers concepts essential for the **Microsoft PL-300 (Power BI Data Analyst)** certification.

---

## Contents

1. [Data Source: BigQuery Connection](#1-data-source-bigquery-connection)
2. [Power Query: Data Transformation](#2-power-query-data-transformation)
3. [Data Model: Star Schema Design](#3-data-model-star-schema-design)
4. [Relationships: Cardinality and Cross-Filter](#4-relationships-cardinality-and-cross-filter)
5. [DAX Measures: Aggregations and Context](#5-dax-measures-aggregations-and-context)
6. [The LASTDATE Pattern: Why KPIs Need Custom Measures](#6-the-lastdate-pattern-why-kpis-need-custom-measures)
7. [Best Practices for PL-300](#7-best-practices-for-pl-300)

---

## 1. Data Source: BigQuery Connection

### Connection Type

Power BI connects to **Google BigQuery** using the native connector:
- **Home → Get Data → Google BigQuery**
- Authentication: Google account with BigQuery access
- Mode: **Import** (data loaded into Power BI) vs DirectQuery (live queries)

### Why Import Mode?

| Mode | Pros | Cons |
|------|------|------|
| **Import** | Fast visuals, offline access, full DAX support | Data refresh needed, memory limits |
| **DirectQuery** | Always live, no refresh needed | Slower visuals, limited DAX, query costs |

For this dashboard, we use **Import mode** because:
- Data changes monthly (not real-time)
- Complex DAX measures require Import
- Faster user experience

### Tables Imported

| Table | Source | Purpose |
|-------|--------|---------|
| `dim_deal` | rmbs_marts | Deal dimension (AVON2, BLETCHLEY) |
| `dim_tranche` | rmbs_marts | Tranche details (Class A, B, etc.) |
| `dim_loan` | rmbs_marts | Loan-level attributes |
| `pool_summary` | rmbs_marts | Monthly pool metrics |
| `fact_loan_period` | rmbs_marts | Loan-level time series |
| `tranche_rwa` | rmbs_marts | SEC-ERBA RWA calculations |
| `investor_report_metrics` | rmbs_marts | IR-extracted metrics (CPR, CE, etc.) |
| `strat_*` | rmbs_marts | Stratification tables (region, LTV, etc.) |

---

## 2. Power Query: Data Transformation

### What is Power Query?

Power Query (M language) transforms data **before** it reaches the data model.
Access via: **Home → Transform Data**

### Transformations Applied

In this model, most transformations happen in **BigQuery SQL** (upstream), but Power Query handles:

```
1. Data Type Inference
   - Ensure CutoffDate is Date type (not DateTime)
   - Ensure numeric columns are Decimal/Integer

2. Column Renaming
   - BigQuery columns use snake_case
   - Power BI prefers readable names (optional)

3. Removing Unnecessary Columns
   - Reduce model size by excluding unused columns
```

### Power Query Best Practice (PL-300)

**Fold queries when possible:**
- Query folding pushes transformations to the source (BigQuery)
- Non-folding operations (e.g., custom M functions) run in Power BI
- Check: Right-click step → "View Native Query" (if available, it's folding)

---

## 3. Data Model: Star Schema Design

### What is a Star Schema?

A **star schema** has:
- **One central fact table** (or multiple related facts)
- **Dimension tables** radiating out from facts
- **Single hub** for relationships (typically a dimension)

### This Model's Structure

```
                    ┌─────────────────┐
                    │    dim_deal     │  ← Central dimension (1 side)
                    │    (DealID)     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  pool_summary   │ │   dim_tranche   │ │   tranche_rwa   │
│   (*:1)         │ │     (*:1)       │ │     (*:1)       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │
         ▼
┌─────────────────┐
│ fact_loan_period│
│     (*:1)       │
└─────────────────┘
```

### Why dim_deal is the Hub

- `dim_deal` contains one row per deal (AVON2, BLETCHLEY)
- All other tables have **multiple rows per deal** (time series, tranches, loans)
- Relationships flow **from many → to one** (dim_deal is always the "1" side)

### Common Mistake (Lesson Learned)

Early in this project, we created relationships like:
```
pool_summary.DealID (1) ─── dim_tranche.DealID (*)  ❌ WRONG
```

This caused duplicate key errors because `pool_summary` has multiple rows per DealID.

**Correct approach:**
```
pool_summary.DealID (*) ─── dim_deal.DealID (1)    ✓ CORRECT
dim_tranche.DealID  (*) ─── dim_deal.DealID (1)    ✓ CORRECT
```

---

## 4. Relationships: Cardinality and Cross-Filter

### Cardinality Types (PL-300 Essential)

| Cardinality | Meaning | Example |
|-------------|---------|---------|
| **1:1** | One row matches one row | Rare; usually merge tables |
| **1:*** | One row matches many rows | dim_deal (1) → pool_summary (*) |
| ***:1** | Many rows match one row | pool_summary (*) → dim_deal (1) |
| ***:*** | Many-to-many | Requires bridge table or composite model |

### Cross-Filter Direction

| Direction | Meaning |
|-----------|---------|
| **Single** | Filters flow from "1" to "*" only |
| **Both** | Filters flow both ways (use cautiously) |

**Best practice:** Use **Single** direction. Bidirectional can cause:
- Ambiguous paths
- Performance issues
- Unexpected filter behavior

### This Model's Relationships

| From Table | To Table | Cardinality | Direction |
|------------|----------|-------------|-----------|
| pool_summary | dim_deal | *:1 | Single |
| dim_tranche | dim_deal | *:1 | Single |
| tranche_rwa | dim_deal | *:1 | Single |
| fact_loan_period | dim_deal | *:1 | Single |
| strat_region | dim_deal | *:1 | Single |
| strat_ltv | dim_deal | *:1 | Single |
| investor_report_metrics | dim_deal | *:1 | Single |

---

## 5. DAX Measures: Aggregations and Context

### Implicit vs Explicit Measures

**Implicit measure:**
```
Drag "TotalBalance" to a visual → Power BI auto-sums
```
- Quick but limited
- Can't control aggregation logic
- Doesn't respect complex business rules

**Explicit measure (DAX):**
```dax
Pool Balance = SUM(pool_summary[TotalBalance])
```
- Full control over calculation
- Can add filters, conditions, context modifiers
- Recommended for production dashboards

### Filter Context (PL-300 Core Concept)

Every DAX calculation runs in a **filter context** — the set of active filters from:
- Slicers
- Visual filters
- Row/column context (in tables/matrices)
- Page/report filters

**Example:**
```
User selects "AVON2" in slicer
  → Filter context now includes: DealID = "AVON2"
  → All measures automatically filter to AVON2
```

### Measures in This Model

| Measure | DAX | Purpose |
|---------|-----|---------|
| Pool Balance | `CALCULATE(SUM([TotalBalance]), LASTDATE([CutoffDate]))` | Latest period balance |
| Total Loans | `CALCULATE(SUM([LoanCount]), LASTDATE([CutoffDate]))` | Latest period loan count |
| WA LTV | `CALCULATE(AVERAGE([WA_LTV]), LASTDATE([CutoffDate]))` | Latest period WA LTV |
| WA Int Rate | `CALCULATE(AVERAGE([WA_InterestRate]), LASTDATE([CutoffDate]))` | Latest period rate |
| Total RWA | `SUM(tranche_rwa[RWA])` | Sum of tranche RWA |
| Capital Required | `SUM(tranche_rwa[Capital])` | Sum of capital requirement |
| Avg Risk Weight | `DIVIDE(SUM([RWA]), SUM([CurrentBalance]), 0)` | RWA density |

---

## 6. The LASTDATE Pattern: Why KPIs Need Custom Measures

### The Problem

Consider `pool_summary` for AVON2:

| CutoffDate | TotalBalance |
|------------|--------------|
| 2020-09-30 | £839M |
| 2020-10-31 | £835M |
| 2020-11-30 | £831M |
| 2020-12-31 | £825M |
| 2021-01-31 | £820M |
| 2021-02-28 | £815M |

**What happens with a simple SUM?**
```dax
Pool Balance = SUM(pool_summary[TotalBalance])
```
Result: £839M + £835M + ... + £815M = **£4.97bn** ❌

This sums ALL periods — meaningless for a "current balance" KPI.

### The Solution: LASTDATE

```dax
Pool Balance = 
CALCULATE(
    SUM(pool_summary[TotalBalance]),
    LASTDATE(pool_summary[CutoffDate])
)
```

**How it works:**
1. `LASTDATE()` returns the latest date in the current filter context
2. `CALCULATE()` modifies the filter context to include only that date
3. `SUM()` now aggregates only the latest period

Result: **£815M** ✓ (Feb 2021 balance)

### When the User Selects a Date

If a date slicer filters to "2020-11-30":
- `LASTDATE()` returns 2020-11-30 (the latest date *in the filtered context*)
- Result: **£831M** (Nov 2020 balance)

### Alternative Patterns

| Pattern | Use Case |
|---------|----------|
| `LASTDATE()` | Show most recent value |
| `FIRSTDATE()` | Show earliest value |
| `DATEADD()` | Compare to prior period |
| `SAMEPERIODLASTYEAR()` | Year-over-year comparison |
| `TOTALYTD()` | Year-to-date accumulation |

---

## 7. Best Practices for PL-300

### Data Modeling

1. **Use star schema** — one central dimension, facts radiate out
2. **Avoid bidirectional relationships** unless absolutely necessary
3. **Hide foreign keys** from report view (users don't need to see DealID twice)
4. **Create a date table** for time intelligence (we use CutoffDate from source)

### DAX

1. **Use explicit measures** — don't rely on implicit aggregations
2. **Use DIVIDE()** not `/` — handles divide-by-zero gracefully
3. **Use variables (VAR)** for readability and performance
4. **Understand filter context** — it's the foundation of DAX

### Performance

1. **Remove unused columns** in Power Query
2. **Use Import mode** for complex calculations
3. **Avoid calculated columns** when measures work
4. **Use aggregations** for large datasets (100M+ rows)

### Security (Row-Level Security)

Not implemented in this model, but for PL-300:
```dax
[DealID] = USERPRINCIPALNAME()
```
This restricts users to see only their assigned deals.

### Deployment

1. **Publish to Power BI Service** (cloud)
2. **Set up scheduled refresh** (daily/hourly)
3. **Create a workspace** for the team
4. **Use deployment pipelines** (Dev → Test → Prod)

---

## Summary

This RMBS dashboard demonstrates:

| PL-300 Topic | Implementation |
|--------------|----------------|
| Data connection | BigQuery native connector (Import mode) |
| Power Query | Type inference, column selection |
| Star schema | dim_deal as central hub |
| Relationships | *:1 with single-direction filter |
| DAX measures | LASTDATE pattern for time series |
| Filter context | Slicer → measure → visual |
| Best practices | Explicit measures, DIVIDE(), no bidirectional |

---

*For the full SEC-ERBA RWA methodology, see [../RWA_METHODOLOGY.md](../RWA_METHODOLOGY.md).*
