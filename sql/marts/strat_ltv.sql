-- strat_ltv.sql
-- LTV band stratification: loan count, balance, WA rate per band.
-- Demonstrates CASE banding + GROUP BY for stratification tables.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/strat_ltv.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.strat_ltv` AS

SELECT
  f.DealID,
  f.CutoffDate,

  -- LTV band (CASE banding)
  CASE
    WHEN f.CurrentLTV IS NULL THEN 'Unknown'
    WHEN f.CurrentLTV < 0.60 THEN '<60%'
    WHEN f.CurrentLTV < 0.70 THEN '60-70%'
    WHEN f.CurrentLTV < 0.80 THEN '70-80%'
    WHEN f.CurrentLTV < 0.90 THEN '80-90%'
    WHEN f.CurrentLTV < 1.00 THEN '90-100%'
    ELSE '>100%'
  END AS LTV_Band,

  -- Sort order for reporting
  CASE
    WHEN f.CurrentLTV IS NULL THEN 99
    WHEN f.CurrentLTV < 0.60 THEN 1
    WHEN f.CurrentLTV < 0.70 THEN 2
    WHEN f.CurrentLTV < 0.80 THEN 3
    WHEN f.CurrentLTV < 0.90 THEN 4
    WHEN f.CurrentLTV < 1.00 THEN 5
    ELSE 6
  END AS Band_Order,

  -- Metrics per band
  COUNT(*)                              AS LoanCount,
  SUM(f.CurrentBalance)                 AS Balance,
  SAFE_DIVIDE(
    SUM(f.CurrentBalance),
    SUM(SUM(f.CurrentBalance)) OVER (PARTITION BY f.DealID, f.CutoffDate)
  )                                     AS Balance_Pct,

  -- WA metrics within band
  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentLTV),
    SUM(f.CurrentBalance)
  )                                     AS WA_LTV,

  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentInterestRate),
    SUM(f.CurrentBalance)
  )                                     AS WA_Rate,

  -- Arrears within band
  COUNTIF(f.MonthsInArrears > 0)        AS LoansInArrears,
  SUM(f.ArrearsBalance)                 AS ArrearsBalance

FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` f

GROUP BY f.DealID, f.CutoffDate, LTV_Band, Band_Order
;
