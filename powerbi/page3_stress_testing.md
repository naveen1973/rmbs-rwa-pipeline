# Page 3: Stress Testing & Sensitivity

## Concept
Show how HPI shocks affect LTV distribution and potential losses vs. credit support.

## Step 1: Create Stress Parameters Table

In Power BI: Enter Data → create table `stress_scenarios`:

| scenario | hpi_shock | description |
|----------|-----------|-------------|
| Base | 0 | No shock |
| Mild | -0.10 | 10% HPI decline |
| Moderate | -0.20 | 20% HPI decline |
| Severe | -0.30 | 30% HPI decline |
| Extreme | -0.40 | 40% HPI decline |

## Step 2: DAX Measures

```dax
// Selected HPI shock
HPI Shock = SELECTEDVALUE(stress_scenarios[hpi_shock], 0)

// Stressed LTV = Current LTV / (1 + HPI shock)
// If HPI drops 20%, property worth less → LTV rises
Stressed WA LTV = 
VAR BaseWALTV = [WA Current LTV]
VAR Shock = [HPI Shock]
RETURN DIVIDE(BaseWALTV, 1 + Shock)

// Loans breaching 100% LTV (negative equity)
Negative Equity Count = 
VAR Shock = [HPI Shock]
RETURN CALCULATE(
    COUNTROWS(fact_loan_period),
    FILTER(
        fact_loan_period,
        DIVIDE(fact_loan_period[current_balance], 
               fact_loan_period[valuation_amount] * (1 + Shock)) > 1
    )
)

// Negative equity % of pool
Negative Equity % = 
DIVIDE([Negative Equity Count], COUNTROWS(fact_loan_period))

// Simple expected loss (loans > 100% LTV × avg severity)
Expected Loss = 
VAR AvgSeverity = 0.25
RETURN [Negative Equity %] * AvgSeverity * [Pool Balance]

// Loss vs CE headroom
CE Headroom = 
VAR TotalCE = CALCULATE(SUM(dim_tranche[current_balance]), 
                        dim_tranche[tranche_id] <> "Class A")
RETURN TotalCE - [Expected Loss]
```

## Step 3: Page Layout

### Top: Scenario Slicer
- Slicer: `stress_scenarios[description]`
- Style: Buttons (horizontal)

### Middle Row: KPI Cards
| Card | Measure |
|------|---------|
| HPI Shock | [HPI Shock] as % |
| Stressed WA LTV | [Stressed WA LTV] |
| Negative Equity Loans | [Negative Equity Count] |
| Expected Loss | [Expected Loss] |
| CE Headroom | [CE Headroom] |

### Bottom Left: LTV Distribution Shift
- Clustered Column Chart
- Show base vs stressed LTV bands
- Use `ltv_bucket` (create calculated column if needed)

### Bottom Right: Waterfall or Bullet
- Show: Pool Balance → Losses → CE → Surplus/Deficit
- Or: Bullet chart comparing Expected Loss vs CE buffer

## Step 4: Conditional Formatting
- CE Headroom card: Green if positive, Red if negative
- Negative Equity %: Gradient scale
