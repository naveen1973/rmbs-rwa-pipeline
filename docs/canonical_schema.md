# Canonical Loan-Level Schema (v2 — BoE-aligned)

**Status: Accepted (2026-06-17).** Field set signed off; changes from here are tracked as edits.

![Canonical star schema](canonical_schema.svg)

The single standard shape every programme conforms to (Step 4a). Built from the **official Bank of
England RMBS loan-level template** (`config/boe_rmbs_fields.csv`, 233 AR fields). Because every UK
RMBS issuer is mandated to use this template, the field codes are shared across all five programmes —
conforming is *select these AR columns → rename to the official name → decode List fields → cast →
normalise units → tag DealID*.

**Model:** a two-table star, driven by the template's own `static`/`dynamic` flag:
- **`dim_loan`** — *static* attributes, **one row per (DealID, LoanID)**.
- **`fact_loan_period`** — *dynamic* attributes, **one row per (DealID, LoanID, CutoffDate)**.

This is also the Power BI star schema (goal 3): `fact_loan_period` *—many-to-one→* `dim_loan`, both
sharing the `(DealID, LoanID)` key; `dim_deal` and `dim_date` join on top.

Coverage = curated **mandatory** set (+ a few high-value optional, flagged `O`). ~58 fields; the
other ~175 AR fields (2nd-borrower bureau scores, Continental-EU-only codes, blanks) are deferred —
the conform layer can pull any of them in later by adding a column, never a rewrite.

---

## Conventions

- **Units (normalise on conform, per BoE spec "decimal format"):**
  - LTV → **decimal fraction** (`0.7580`).  Interest rate & margin → **decimal fraction** (`0.0480`).
  - ⚠ Avon stores these as percents (`75.80`, `4.80`) → conform divides by 100. *This is the kind of
    per-programme unit fix the conform layer exists for.*
  - Balances/amounts → GBP `NUMERIC`. Months/terms → numeric months.
- **`List` fields** → store the decoded **label** (e.g. `Buy-to-let`) via a join to a `ref_*` seed
  table, and keep the raw code as `<field>_code` for lineage.
- **`ND` ("No Data")** and blanks → `NULL`.
- **Missing AR columns** (e.g. Avon's reduced subset) → selected as `NULL`; never errors.
- **Keys added by the pipeline:** `DealID` (from `deals.yml`); `CutoffDate` from AR1.

---

## Table A — `dim_loan` (static · one row per DealID, LoanID)

| Canonical | AR | Pri | Type | Decode (ref table) | Notes |
|---|---|---|---|---|---|
| DealID | — | — | STRING | | from deals.yml |
| LoanID | AR3 | M | STRING | | natural key |
| BorrowerID | AR7 | M | STRING | | borrower-level grouping |
| PropertyID | AR8 | M | STRING | | |
| Pool | AR2 | M | STRING | | |
| Originator | AR5 | M | STRING | | |
| ServicerID | AR6 | M | STRING | | |
| RegulatedLoan | AR4 | O | STRING | Y/N/ND | |
| BorrowerCreditQuality | AR17 | O | STRING | | originator's prime/near-prime/etc. — key for non-conforming |
| NumberOfDebtors | AR19 | M | INT64 | | |
| EmploymentStatus | AR21 | M | STRING | `ref_employment_status` | |
| FirstTimeBuyer | AR22 | O | STRING | Y/N/ND | |
| PrimaryIncome | AR26 | M | NUMERIC | | underwritten gross annual |
| IncomeVerification | AR27 | M | STRING | `ref_income_verification` | |
| SecondaryIncome | AR28 | M | NUMERIC | | |
| CCJUnsatisfiedNumber | AR33 | M | INT64 | | credit history |
| LoanOriginationDate | AR55 | M | DATE | | may be quarter `Q2-1997` → parse |
| AccountStatusDate | AR57 | M | DATE | | date sold into pool |
| OriginationChannel | AR58 | M | STRING | `ref_origination_channel` | |
| Purpose | AR59 | M | STRING | `ref_purpose` | |
| SharedOwnership | AR60 | M | STRING | `ref_shared_ownership` | |
| LoanTerm | AR61 | M | INT64 | | original term, months |
| OriginalBalance | AR66 | M | NUMERIC | | |
| RepaymentMethod | AR69 | M | STRING | `ref_repayment_method` | drives IO flag |
| PaymentFrequency | AR70 | M | STRING | `ref_payment_frequency` | |
| Lien | AR84 | M | STRING | `ref_lien` | 1st/2nd lien |
| InterestRateType | AR107 | M | STRING | `ref_interest_rate_type` | fixed/floating/etc. |
| GeographicRegion | AR128 | M | STRING | `ref_region` | ITL1 region |
| OccupancyType | AR130 | M | STRING | `ref_occupancy` | drives BTL flag |
| PropertyType | AR131 | M | STRING | `ref_property_type` | |
| OriginalLTV | AR135 | M | NUMERIC | | fraction |
| OriginalValuation | AR136 | M | NUMERIC | | |
| OriginalValuationType | AR137 | M | STRING | `ref_valuation_type` | |
| OriginalValuationDate | AR138 | M | DATE | | |
| GrossAnnualRentalIncome | AR154 | M | NUMERIC | | BTL |
| NumberOfBTLProperties | AR155 | M | INT64 | | BTL |
| DebtServiceCoverageRatio | AR156 | M | NUMERIC | | BTL |

## Table B — `fact_loan_period` (dynamic · one row per DealID, LoanID, CutoffDate)

| Canonical | AR | Pri | Type | Decode (ref table) | Notes |
|---|---|---|---|---|---|
| DealID | — | — | STRING | | FK → dim_loan |
| LoanID | AR3 | M | STRING | | FK → dim_loan |
| CutoffDate | AR1 | M | DATE | | period key |
| CurrentBalance | AR67 | M | NUMERIC | | clip ≥ 0 |
| DateOfLoanMaturity | AR56 | M | DATE | | |
| PaymentDue | AR71 | M | NUMERIC | | |
| CurrentInterestRateIndex | AR108 | M | STRING | `ref_rate_index` | |
| CurrentInterestRate | AR109 | M | NUMERIC | | fraction |
| CurrentInterestRateMargin | AR110 | M | NUMERIC | | fraction |
| InterestRateResetInterval | AR111 | M | INT64 | | months |
| NextRevisionDate | AR113 | M | DATE | | reversion / fixed-period end |
| PrepaymentAmount | AR97 | M | NUMERIC | | partial prepay in month |
| CumulativePrepayments | AR100 | M | NUMERIC | | |
| ForbearanceType | AR123 | M | STRING | `ref_forbearance` | |
| CurrentLTV | AR141 | M | NUMERIC | | fraction |
| CurrentValuation | AR143 | M | NUMERIC | | |
| CurrentValuationType | AR144 | M | STRING | `ref_valuation_type` | |
| CurrentValuationDate | AR145 | M | DATE | | |
| CurrentEPC | AR162 | M | STRING | `ref_epc` | energy rating A–G |
| BankruptcyFlag | AR36 | M | STRING | Y/N/ND | |
| AccountStatus | AR166 | M | STRING | `ref_account_status` | performing/arrears/default/redeemed |
| ArrearsBalance | AR169 | M | NUMERIC | | |
| MonthsInArrears | AR170 | M | NUMERIC | | decimals allowed |
| Arrears1MonthAgo | AR171 | M | NUMERIC | | enables arrears migration w/o prior tape |
| Arrears2MonthsAgo | AR172 | M | NUMERIC | | |
| PerformanceArrangementDate | AR173 | M | DATE | | |
| Litigation | AR174 | M | STRING | Y/N/ND | |
| RedemptionDate | AR175 | M | DATE | | exit |
| DefaultAmount | AR177 | M | NUMERIC | | total default before recoveries |
| DateOfDefault | AR178 | M | DATE | | |
| SalePrice | AR179 | M | NUMERIC | | foreclosure sale |
| LossOnSale | AR180 | M | NUMERIC | | net loss (gain = negative) |
| CumulativeRecoveries | AR181 | M | NUMERIC | | for proper loss severity |

---

## Code-list reference tables (`ref_*`, joined in conform)

Seeded from the code lists embedded in the BoE field definitions (`config/boe_rmbs_fields.csv`). One
row per `(code, label)`. Needed for the `List` fields above:

`ref_employment_status` (AR21) · `ref_income_verification` (AR27) · `ref_origination_channel` (AR58) ·
`ref_purpose` (AR59) · `ref_shared_ownership` (AR60) · `ref_repayment_method` (AR69) ·
`ref_payment_frequency` (AR70) · `ref_lien` (AR84) · `ref_interest_rate_type` (AR107) ·
`ref_rate_index` (AR108) · `ref_forbearance` (AR123) · `ref_region` (AR128) · `ref_occupancy` (AR130) ·
`ref_property_type` (AR131) · `ref_valuation_type` (AR137/AR144) · `ref_epc` (AR162) ·
`ref_account_status` (AR166).

## Derived later (Step 4b — NOT in canonical)

Bands (`LTVBand`, `SeasoningBand`…), flags (`IsBTL`, `IsInterestOnly`, `Underwater`, `IsDelinquent`),
seasoning / remaining term, loss severity (`LossOnSale − CumulativeRecoveries`), the **exits** view
(rows where `DefaultAmount > 0` or redeemed), and all weighted-average pool metrics are computed in the
analytics marts from `dim_loan` + `fact_loan_period`. Canonical = conformed source truth only.
