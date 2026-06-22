-- conform_bletchley_dim_loan.sql
-- Transforms Bletchley staging data → canonical dim_loan schema.
-- Bletchley-specific: AR55 is actual date (not quarterly), AR109 already decimal.
--
-- Run:  bq query --use_legacy_sql=false < sql/conform/conform_bletchley_dim_loan.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.conform_bletchley_dim_loan` AS

SELECT
  -- Keys
  s.DealID,
  CAST(s.AR3 AS STRING)               AS LoanID,
  CAST(s.AR7 AS STRING)               AS BorrowerID,
  CAST(s.AR8 AS STRING)               AS PropertyID,

  -- Identifiers
  CAST(s.AR2 AS STRING)               AS Pool,
  CAST(s.AR5 AS STRING)               AS Originator,
  CAST(s.AR6 AS STRING)               AS ServicerID,

  -- Decoded fields
  emp.label                           AS EmploymentStatus,
  CAST(s.AR21 AS STRING)              AS EmploymentStatus_code,

  inc.label                           AS IncomeVerification,
  CAST(s.AR27 AS STRING)              AS IncomeVerification_code,

  occ.label                           AS OccupancyType,
  CAST(s.AR130 AS STRING)             AS OccupancyType_code,

  chan.label                          AS OriginationChannel,
  CAST(s.AR58 AS STRING)              AS OriginationChannel_code,

  ref_lp.label                        AS Purpose,
  CAST(s.AR59 AS STRING)              AS Purpose_code,

  ref_rm.label                        AS RepaymentMethod,
  CAST(s.AR69 AS STRING)              AS RepaymentMethod_code,

  ref_pt.label                        AS PropertyType,
  CAST(s.AR131 AS STRING)             AS PropertyType_code,

  reg.label                           AS Region,
  CAST(s.AR128 AS STRING)             AS Region_code,

  -- Numeric fields
  SAFE_CAST(s.AR19 AS INT64)          AS NumberOfDebtors,  -- ND → NULL
  CAST(s.AR26 AS NUMERIC)             AS PrimaryIncome,
  CAST(s.AR28 AS NUMERIC)             AS SecondaryIncome,
  SAFE_CAST(s.AR61 AS INT64)          AS LoanTerm,         -- ND → NULL
  CAST(s.AR66 AS NUMERIC)             AS OriginalBalance,
  CAST(s.AR135 AS NUMERIC)            AS OriginalLTV,  -- Bletchley: check if decimal or percent
  CAST(s.AR136 AS NUMERIC)            AS OriginalValuation,

  -- Date fields (Bletchley uses actual dates, not quarterly)
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR55 AS STRING)) AS LoanOriginationDate,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR57 AS STRING)) AS AccountStatusDate,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR138 AS STRING)) AS OriginalValuationDate

FROM `rmbs-rwa-pipeline.rmbs_staging.loans_bletchley` s

-- JOINs to decode tables
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_employment_status` emp
  ON CAST(s.AR21 AS STRING) = emp.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_income_verification` inc
  ON CAST(s.AR27 AS STRING) = inc.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_occupancy` occ
  ON CAST(s.AR130 AS STRING) = occ.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_origination_channel` chan
  ON CAST(s.AR58 AS STRING) = chan.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_loan_purpose` ref_lp
  ON CAST(s.AR59 AS STRING) = ref_lp.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_repayment_method` ref_rm
  ON CAST(s.AR69 AS STRING) = ref_rm.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_property_type` ref_pt
  ON CAST(s.AR131 AS STRING) = ref_pt.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_region` reg
  ON CAST(s.AR128 AS STRING) = reg.code

-- Filter out header/empty rows
WHERE s.AR3 IS NOT NULL

-- Deduplicate: keep one row per loan (most recent period)
QUALIFY ROW_NUMBER() OVER (PARTITION BY s.DealID, CAST(s.AR3 AS STRING) ORDER BY CAST(s.AR1 AS DATE) DESC) = 1
;
