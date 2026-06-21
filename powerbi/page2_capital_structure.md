# Page 2: Capital Structure (Bonds / CE / Factor)

## Step 1: Add dim_tranche table

1. Home → Get Data → BigQuery
2. Select `rmbs_mart.dim_tranche`
3. Create relationship: `dim_tranche[deal_id]` → `dim_deal[deal_id]` (Many-to-One)

## Step 2: DAX Measures

Add these to your Measures table:

```dax
// Current balance formatted
Current Balance = SUM(dim_tranche[current_balance])

// Original balance
Original Balance = SUM(dim_tranche[original_balance])

// Weighted average factor
WA Factor = 
DIVIDE(
    SUMX(dim_tranche, dim_tranche[current_balance] * dim_tranche[factor]),
    [Current Balance]
)

// Credit Enhancement (for selected tranche)
Credit Enhancement % = 
SELECTEDVALUE(dim_tranche[credit_enhancement]) * 100

// Tranche thickness
Thickness % = 
(SELECTEDVALUE(dim_tranche[detachment]) - SELECTEDVALUE(dim_tranche[attachment])) * 100

// Paydown amount
Paydown = [Original Balance] - [Current Balance]

// Paydown %
Paydown % = DIVIDE([Paydown], [Original Balance])
```

## Step 3: Page Layout

### Top Row (KPI Cards)
| Card | Measure | Format |
|------|---------|--------|
| Total Outstanding | [Current Balance] | £#,##0,,"M" |
| WA Factor | [WA Factor] | 0.00% |
| Classes | COUNTROWS(dim_tranche) | 0 |

### Middle: Stacked Bar (Waterfall)
- Visual: **Stacked Bar Chart**
- Y-axis: `tranche_id` (sorted by attachment descending → A at top)
- X-axis: `current_balance`
- Legend: `tranche_id`
- Colors: A=Navy, B=Blue, C=Teal, D=Green, E=Yellow, F=Orange, Z=Red

### Bottom Left: Table
| Column | Field |
|--------|-------|
| Tranche | tranche_id |
| ISIN | isin |
| Balance | current_balance |
| Factor | factor |
| CE | credit_enhancement |
| Coupon | coupon |

### Bottom Right: Gauge or Bar
- Credit Enhancement by tranche (horizontal bar)
- X: credit_enhancement, Y: tranche_id

## Step 4: Slicer
- Add Deal slicer (if multiple deals later): `dim_deal[deal_id]`
