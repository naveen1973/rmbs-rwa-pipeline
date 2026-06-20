-- strat_delinquency.sql
-- Delinquency bucket stratification: Current / 1M / 2M / 3M+ / Default.
-- Uses MonthsInArrears for bucketing, AccountStatus for default flag.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/strat_delinquency.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.strat_delinquency` AS

SELECT
  f.DealID,
  f.CutoffDate,

  -- Delinquency bucket
  CASE
    WHEN f.AccountStatus = 'Defaulted' THEN 'Default'
    WHEN f.AccountStatus = 'Redeemed' THEN 'Redeemed'
    WHEN f.MonthsInArrears IS NULL OR f.MonthsInArrears = 0 THEN 'Current'
    WHEN f.MonthsInArrears < 1 THEN '<1M'
    WHEN f.MonthsInArrears < 2 THEN '1-2M'
    WHEN f.MonthsInArrears < 3 THEN '2-3M'
    ELSE '3M+'
  END AS Delinquency_Bucket,

  -- Sort order
  CASE
    WHEN f.AccountStatus = 'Redeemed' THEN 0
    WHEN f.MonthsInArrears IS NULL OR f.MonthsInArrears = 0 THEN 1
    WHEN f.MonthsInArrears < 1 THEN 2
    WHEN f.MonthsInArrears < 2 THEN 3
    WHEN f.MonthsInArrears < 3 THEN 4
    WHEN f.AccountStatus = 'Defaulted' THEN 6
    ELSE 5
  END AS Bucket_Order,

  -- Metrics
  COUNT(*)                              AS LoanCount,
  SUM(f.CurrentBalance)                 AS Balance,
  SAFE_DIVIDE(
    SUM(f.CurrentBalance),
    SUM(SUM(f.CurrentBalance)) OVER (PARTITION BY f.DealID, f.CutoffDate)
  )                                     AS Balance_Pct,

  SUM(f.ArrearsBalance)                 AS ArrearsBalance,

  -- WA LTV within bucket (risk indicator)
  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentLTV),
    SUM(f.CurrentBalance)
  )                                     AS WA_LTV

FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` f

GROUP BY f.DealID, f.CutoffDate, Delinquency_Bucket, Bucket_Order
;
