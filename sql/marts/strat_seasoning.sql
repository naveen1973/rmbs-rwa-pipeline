-- strat_seasoning.sql
-- Seasoning stratification: vintage analysis by months since origination.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/strat_seasoning.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.strat_seasoning` AS

SELECT
  f.DealID,
  f.CutoffDate,

  -- Seasoning band (months since origination)
  CASE
    WHEN d.LoanOriginationDate IS NULL THEN 'Unknown'
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 12 THEN '<1yr'
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 36 THEN '1-3yr'
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 60 THEN '3-5yr'
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 120 THEN '5-10yr'
    ELSE '10yr+'
  END AS Seasoning_Band,

  -- Sort order
  CASE
    WHEN d.LoanOriginationDate IS NULL THEN 99
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 12 THEN 1
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 36 THEN 2
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 60 THEN 3
    WHEN DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH) < 120 THEN 4
    ELSE 5
  END AS Band_Order,

  -- Metrics
  COUNT(*)                              AS LoanCount,
  SUM(f.CurrentBalance)                 AS Balance,
  SAFE_DIVIDE(
    SUM(f.CurrentBalance),
    SUM(SUM(f.CurrentBalance)) OVER (PARTITION BY f.DealID, f.CutoffDate)
  )                                     AS Balance_Pct,

  -- WA seasoning in months
  AVG(DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH)) AS Avg_Seasoning_Months,

  -- Arrears
  COUNTIF(f.MonthsInArrears > 0)        AS LoansInArrears,
  SAFE_DIVIDE(
    SUM(f.ArrearsBalance),
    SUM(f.CurrentBalance)
  )                                     AS ArrearsRate

FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` f
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.dim_loan` d
  ON f.DealID = d.DealID AND f.LoanID = d.LoanID

GROUP BY f.DealID, f.CutoffDate, Seasoning_Band, Band_Order
;
