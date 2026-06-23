# SEC-ERBA RWA Methodology

This document explains how Risk-Weighted Assets (RWA) are calculated for RMBS tranches
using the **Securitisation External Ratings-Based Approach (SEC-ERBA)** under Basel 3.1 / UK CRR.

## Contents

1. [What is SEC-ERBA?](#1-what-is-sec-erba)
2. [The Risk Weight Lookup Table](#2-the-risk-weight-lookup-table)
3. [Worked Example: AVON2 Class A](#3-worked-example-avon2-class-a)
4. [Capital Structure and RWA Distribution](#4-capital-structure-and-rwa-distribution)
5. [Why This Matters](#5-why-this-matters)

---

## 1. What is SEC-ERBA?

SEC-ERBA is the regulatory method for calculating how much capital a bank must hold against
rated securitisation positions (e.g., RMBS tranches).

**The core formulas:**

```
Risk Weight (RW)  = f(Credit Rating, Seniority, Maturity)
RWA               = Exposure at Default (EAD) × Risk Weight
Capital Required  = RWA × 8%
```

Where:
- **EAD** = Current tranche balance (what the bank is exposed to)
- **Risk Weight** = Percentage looked up from the SEC-ERBA table
- **8%** = Basel III minimum capital ratio

### Risk Weight Drivers

| Factor | Impact on Risk Weight |
|--------|----------------------|
| **Credit Rating** | AAA = 15-20%, BBB = 70-140%, Unrated = 1250% |
| **Seniority** | Senior tranches get lower RW than mezzanine/junior |
| **Maturity (WAL)** | Longer weighted-average life → higher RW |
| **Thickness** | Thinner tranches → higher RW (concentrated risk) |

---

## 2. The Risk Weight Lookup Table

The SEC-ERBA table provides anchor risk weights at 1-year and 5-year maturities.
Intermediate maturities are linearly interpolated.

### Senior Tranches

| Rating | 1-Year | 5-Year |
|--------|--------|--------|
| AAA    | 15%    | 20%    |
| AA+    | 15%    | 25%    |
| AA     | 20%    | 30%    |
| AA-    | 25%    | 35%    |
| A+     | 30%    | 45%    |
| A      | 35%    | 55%    |
| A-     | 45%    | 70%    |
| BBB+   | 55%    | 85%    |
| BBB    | 70%    | 105%   |
| BBB-   | 90%    | 140%   |
| BB+    | 120%   | 185%   |
| BB     | 140%   | 250%   |
| BB-    | 170%   | 300%   |
| B+     | 220%   | 380%   |
| B      | 280%   | 460%   |
| B-     | 380%   | 620%   |
| CCC+   | 530%   | 800%   |
| CCC    | 700%   | 1050%  |
| Unrated| 1250%  | 1250%  |

### Non-Senior Tranches

Non-senior (mezzanine/junior) tranches receive **higher risk weights** than senior tranches
at the same rating, reflecting their subordinated position in the capital structure.

| Rating | 1-Year | 5-Year |
|--------|--------|--------|
| AAA    | 15%    | 30%    |
| AA     | 25%    | 50%    |
| A      | 50%    | 80%    |
| BBB    | 90%    | 140%   |
| BB     | 170%   | 330%   |
| B      | 470%   | 750%   |
| Unrated| 1250%  | 1250%  |

### Maturity Interpolation

For a tranche with WAL = 3.5 years:

```
RW = RW_1yr + (RW_5yr - RW_1yr) × (WAL - 1) / 4
   = 15% + (20% - 15%) × (3.5 - 1) / 4
   = 15% + 5% × 0.625
   = 18.125%
```

---

## 3. Worked Example: AVON2 Class A

Let's calculate the RWA for the senior tranche of Avon Finance No. 2:

### Input Data

| Field | Value |
|-------|-------|
| Tranche | Class A |
| Current Balance | £648,188,082 |
| Credit Rating | AAA |
| Seniority | Senior |
| WAL (Weighted Average Life) | 3.5 years |
| Attachment Point | 18% |
| Detachment Point | 100% |

### Step 1: Look Up Risk Weight

From the SEC-ERBA table for **AAA Senior**:
- RW at 1 year = 15%
- RW at 5 years = 20%

Interpolate for WAL = 3.5 years:
```
RW = 15% + (20% - 15%) × (3.5 - 1) / 4
   = 15% + 3.125%
   = 18.125%
```

### Step 2: Calculate RWA

```
RWA = Balance × Risk Weight
    = £648,188,082 × 18.125%
    = £117,484,090
```

### Step 3: Calculate Capital Requirement

```
Capital = RWA × 8%
        = £117,484,090 × 8%
        = £9,398,727
```

### Summary

| Metric | Value |
|--------|-------|
| Risk Weight | 18.1% |
| RWA | £117.5M |
| Capital Required | £9.4M |

**Interpretation:** A bank holding the £648M Class A tranche must allocate £9.4M of capital
against this position. The low risk weight (18.1%) reflects the AAA rating and senior position.

---

## 4. Capital Structure and RWA Distribution

The capital structure shows how tranches stack, with senior at top and first-loss at bottom.
Risk weights increase dramatically as you move down the structure.

### AVON2 Capital Structure

```
                                                    Risk      
Detachment                                          Weight         RWA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
100% ┌─────────────────────────────────────────┐
     │                                         │
     │         Class A  (AAA, Senior)          │   18.1%      £117.5M
     │              £648.2M                    │
     │                                         │
 18% ├─────────────────────────────────────────┤
     │         Class B  (AA)      £32.5M       │   43.8%       £14.2M
 14% ├─────────────────────────────────────────┤
     │         Class C  (A)       £32.5M       │   76.2%       £24.8M
 10% ├─────────────────────────────────────────┤
     │         Class D  (BBB)     £24.4M       │  140.0%       £34.1M
  7% ├─────────────────────────────────────────┤
     │         Class E  (BB)      £20.3M       │  330.0%       £67.0M
4.5% ├─────────────────────────────────────────┤
     │         Class F  (B)        £8.1M       │  750.0%       £60.9M
3.5% ├─────────────────────────────────────────┤
     │         Class Z  (Unrated)  £28.4M      │ 1250.0%      £355.5M
  0% └─────────────────────────────────────────┘
     ▲
     │
     Attachment Point = Credit Enhancement
```

### Key Observations

1. **Class A (85% of pool)** generates only **17% of total RWA** — low-risk, low-capital position

2. **Class Z (3.5% of pool)** generates **53% of total RWA** — the Basel penalty for holding
   unrated equity risk

3. **The "cliff effect"**: Moving from B (750% RW) to Unrated (1250% RW) nearly doubles the
   capital requirement

### Deal Comparison

| Deal | Total Balance | Total RWA | Capital | RWA Density |
|------|---------------|-----------|---------|-------------|
| AVON2 | £794M | £674M | £54M | 84.9% |
| BLETCHLEY | £242M | £133M | £11M | 55.1% |

AVON2 has higher RWA density because it includes an unrated Class Z tranche.
BLETCHLEY's excess spread tranches (X1, X2) are also unrated but smaller in proportion.

---

## 5. Why This Matters

### For Banks (Investors)

RWA directly impacts **return on capital**:

```
Return on Capital = Net Interest Income / Capital Held
```

A bank buying the AAA tranche at SONIA + 90bps with 18% RW needs much less capital than
one buying the BB tranche at SONIA + 450bps with 330% RW. The higher spread may not
compensate for the higher capital charge.

### For Originators (Issuers)

Understanding investor RWA constraints helps structure deals that are:
- **Capital-efficient** for target investors
- **Priced appropriately** for each tranche's regulatory cost

### For Regulators

SEC-ERBA ensures banks hold capital commensurate with risk:
- Senior AAA tranches with 18% subordination → low capital
- First-loss equity absorbing initial defaults → punitive capital

This prevents the pre-2008 practice of holding AAA-rated but thinly-supported tranches
with minimal capital.

### For This Portfolio

This implementation demonstrates:

1. **Securitisation knowledge** — understanding attachment/detachment, credit enhancement,
   and the waterfall structure

2. **Regulatory expertise** — correct application of SEC-ERBA lookup tables with maturity
   interpolation

3. **Data engineering** — automated calculation from BigQuery warehouse to Power BI dashboard

---

## References

- Basel Committee on Banking Supervision, "Basel III: Finalising post-crisis reforms" (2017)
- UK CRR Article 263: Securitisation External Ratings-Based Approach
- EBA Guidelines on the STS criteria for securitisation (2018)

---

*This methodology is implemented in [`scripts/export_rwa.py`](../scripts/export_rwa.py)
with the full SEC-ERBA lookup table.*
