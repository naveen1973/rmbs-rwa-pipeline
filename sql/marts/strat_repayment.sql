-- strat_repayment.sql
-- Repayment method stratification: Interest-Only vs Capital Repayment vs Part-and-Part.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/strat_repayment.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.strat_repayment` AS

SELECT
  f.DealID,
  f.CutoffDate,

  COALESCE(d.RepaymentMethod, 'Unknown') AS RepaymentMethod,

  -- Metrics
  COUNT(*)                              AS LoanCount,
  SUM(f.CurrentBalance)                 AS Balance,
  SAFE_DIVIDE(
    SUM(f.CurrentBalance),
    SUM(SUM(f.CurrentBalance)) OVER (PARTITION BY f.DealID, f.CutoffDate)
  )                                     AS Balance_Pct,

  -- WA metrics
  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentLTV),
    SUM(f.CurrentBalance)
  )                                     AS WA_LTV,

  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentInterestRate),
    SUM(f.CurrentBalance)
  )                                     AS WA_Rate,

  -- Arrears
  COUNTIF(f.MonthsInArrears > 0)        AS LoansInArrears,
  SUM(f.ArrearsBalance)                 AS ArrearsBalance

FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` f
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.dim_loan` d
  ON f.DealID = d.DealID AND f.LoanID = d.LoanID

GROUP BY f.DealID, f.CutoffDate, RepaymentMethod
;
