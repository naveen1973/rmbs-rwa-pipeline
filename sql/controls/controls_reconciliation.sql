-- controls_reconciliation.sql
-- Data quality & reconciliation checks. Run after conform views, BEFORE analytics.
-- Returns rows only if checks FAIL — empty result = all checks passed.
--
-- Run:  bq query --use_legacy_sql=false < sql/controls/controls_reconciliation.sql

-- ===========================================
-- CHECK 1: Row count match (staging vs conform)
-- ===========================================
WITH staging_counts AS (
  SELECT 'AVON2' AS DealID, COUNT(*) AS staging_rows
  FROM `rmbs-rwa-pipeline.rmbs_staging.loans_avon`
),
conform_counts AS (
  SELECT DealID, COUNT(*) AS conform_rows
  FROM `rmbs-rwa-pipeline.rmbs_marts.dim_loan`
  GROUP BY DealID
)
SELECT
  'ROW_COUNT_MISMATCH' AS check_name,
  s.DealID,
  CAST(s.staging_rows AS STRING) AS expected,
  CAST(c.conform_rows AS STRING) AS actual,
  CAST(s.staging_rows - c.conform_rows AS STRING) AS difference
FROM staging_counts s
LEFT JOIN conform_counts c ON s.DealID = c.DealID
WHERE s.staging_rows != COALESCE(c.conform_rows, 0)

UNION ALL

-- ===========================================
-- CHECK 2: Balance reconciliation
-- ===========================================
SELECT
  'BALANCE_MISMATCH' AS check_name,
  'AVON2' AS DealID,
  CAST(ROUND(stg.staging_balance, 2) AS STRING) AS expected,
  CAST(ROUND(mart.mart_balance, 2) AS STRING) AS actual,
  CAST(ROUND(stg.staging_balance - mart.mart_balance, 2) AS STRING) AS difference
FROM (
  SELECT SUM(CAST(AR67 AS NUMERIC)) AS staging_balance
  FROM `rmbs-rwa-pipeline.rmbs_staging.loans_avon`
) stg,
(
  SELECT SUM(CurrentBalance) AS mart_balance
  FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period`
  WHERE DealID = 'AVON2'
) mart
WHERE ABS(stg.staging_balance - mart.mart_balance) > 0.01

UNION ALL

-- ===========================================
-- CHECK 3: Critical NULL checks (keys must not be null)
-- ===========================================
SELECT
  'NULL_LOAN_ID' AS check_name,
  DealID,
  '0' AS expected,
  CAST(COUNT(*) AS STRING) AS actual,
  'LoanID should not be NULL' AS difference
FROM `rmbs-rwa-pipeline.rmbs_marts.dim_loan`
WHERE LoanID IS NULL
GROUP BY DealID
HAVING COUNT(*) > 0

UNION ALL

SELECT
  'NULL_BALANCE' AS check_name,
  DealID,
  '0' AS expected,
  CAST(COUNT(*) AS STRING) AS actual,
  'CurrentBalance should not be NULL' AS difference
FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period`
WHERE CurrentBalance IS NULL
GROUP BY DealID
HAVING COUNT(*) > 0

UNION ALL

-- ===========================================
-- CHECK 4: Orphan check (fact without dim)
-- ===========================================
SELECT
  'ORPHAN_FACT_ROWS' AS check_name,
  f.DealID,
  '0' AS expected,
  CAST(COUNT(*) AS STRING) AS actual,
  'fact rows with no matching dim' AS difference
FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` f
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.dim_loan` d
  ON f.DealID = d.DealID AND f.LoanID = d.LoanID
WHERE d.LoanID IS NULL
GROUP BY f.DealID
HAVING COUNT(*) > 0

UNION ALL

-- ===========================================
-- CHECK 5: Negative balance check
-- ===========================================
SELECT
  'NEGATIVE_BALANCE' AS check_name,
  DealID,
  '0' AS expected,
  CAST(COUNT(*) AS STRING) AS actual,
  'Loans with negative balance' AS difference
FROM `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period`
WHERE CurrentBalance < 0
GROUP BY DealID
HAVING COUNT(*) > 0
;
