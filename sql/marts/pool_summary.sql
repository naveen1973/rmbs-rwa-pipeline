-- pool_summary.sql
-- Aggregate pool metrics per deal per period.
-- Weighted averages use CurrentBalance as the weight.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/pool_summary.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.pool_summary` AS

SELECT
  f.DealID,
  f.CutoffDate,

  -- Counts & totals
  COUNT(*)                                              AS LoanCount,
  SUM(f.CurrentBalance)                                 AS TotalBalance,
  AVG(f.CurrentBalance)                                 AS AvgBalance,

  -- Weighted average interest rate (weight = CurrentBalance)
  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentInterestRate),
    SUM(f.CurrentBalance)
  )                                                     AS WA_InterestRate,

  -- Weighted average LTV
  SAFE_DIVIDE(
    SUM(f.CurrentBalance * f.CurrentLTV),
    SUM(f.CurrentBalance)
  )                                                     AS WA_LTV,

  -- Weighted average seasoning (months since origination)
  SAFE_DIVIDE(
    SUM(f.CurrentBalance * DATE_DIFF(f.CutoffDate, d.LoanOriginationDate, MONTH)),
    SUM(f.CurrentBalance)
  )                                                     AS WA_Seasoning_Months,

  -- Arrears metrics
  SUM(f.ArrearsBalance)                                 AS TotalArrearsBalance,
  SAFE_DIVIDE(SUM(f.ArrearsBalance), SUM(f.CurrentBalance)) AS ArrearsRate,
  COUNTIF(f.MonthsInArrears > 0)                        AS LoansInArrears,

  -- Prepayment (for CPR calculation later)
  SUM(f.PrepaymentAmount)                               AS TotalPrepayment,
  SUM(f.CumulativePrepayments)                          AS TotalCumulativePrepayments

FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` f
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.dim_loan` d
  ON f.DealID = d.DealID AND f.LoanID = d.LoanID

GROUP BY f.DealID, f.CutoffDate
;
