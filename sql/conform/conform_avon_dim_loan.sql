-- conform_avon_dim_loan.sql
-- Transforms raw staging data (AR codes) → canonical dim_loan schema.
-- This is a VIEW so it always reflects the latest staging data.
--
-- Pattern:
--   1. SELECT AR columns → rename to canonical names
--   2. JOIN ref_* tables → decode codes to human labels
--   3. CAST/transform → correct types, handle NULLs, normalise units
--   4. FROM the staging table
--
-- Run:  bq query --use_legacy_sql=false < sql/conform/conform_avon_dim_loan.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.conform_avon_dim_loan` AS

SELECT
  -- ===========================================
  -- KEYS (pipeline-added + natural keys)
  -- ===========================================
  s.DealID,                                           -- from staging (we added it)
  CAST(s.AR3 AS STRING)               AS LoanID,      -- AR3 = Loan Identifier
  CAST(s.AR7 AS STRING)               AS BorrowerID,  -- AR7 = Borrower Identifier
  CAST(s.AR8 AS STRING)               AS PropertyID,  -- AR8 = Property Identifier

  -- ===========================================
  -- IDENTIFIERS (simple renames, no decode)
  -- ===========================================
  CAST(s.AR2 AS STRING)               AS Pool,        -- AR2 = Pool Identifier
  CAST(s.AR5 AS STRING)               AS Originator,  -- AR5 = Originator
  CAST(s.AR6 AS STRING)               AS ServicerID,  -- AR6 = Servicer Identifier

  -- ===========================================
  -- DECODED FIELDS (JOIN to ref_* tables)
  -- Example: AR21 stores "5", we want "Self-employed"
  -- ===========================================

  -- AR21 = Employment Status → join ref_employment_status
  emp.label                           AS EmploymentStatus,
  CAST(s.AR21 AS STRING)              AS EmploymentStatus_code,  -- keep raw for lineage

  -- AR27 = Income Verification → join ref_income_verification
  inc.label                           AS IncomeVerification,
  CAST(s.AR27 AS STRING)              AS IncomeVerification_code,

  -- AR130 = Occupancy Type → join ref_occupancy
  occ.label                           AS OccupancyType,
  CAST(s.AR130 AS STRING)             AS OccupancyType_code,


  -- ===========================================
  -- YOUR TURN: Add more decoded fields
  -- Pattern: ref_table.label AS CanonicalName, CAST(s.ARxx AS STRING) AS CanonicalName_code
  -- ===========================================

  -- AR58 = Origination Channel → join ref_origination_channel
  chan.label AS OriginationChannel,
  CAST(s.AR58 AS String) AS Originationchannel_code,


ref_lp.label AS Purpose,
CAST(s.AR59 AS String) AS Purpose_code,

ref_rm.label AS RepaymentMethod,
CAST(s.AR69 AS String) AS RepaymentMethod_code,

ref_pt.label AS PropertyType,
CAST(s.AR131 AS String) AS PropertyType_code,

  -- AR128 = Geographic Region (ITL1 code in Avon)
  reg.label                             AS Region,
  CAST(s.AR128 AS STRING)               AS Region_code,

  -- ===========================================
  -- NUMERIC FIELDS (cast + unit normalisation)
  -- ===========================================
  SAFE_CAST(s.AR19 AS INT64)          AS NumberOfDebtors,       -- ND → NULL
  CAST(s.AR26 AS NUMERIC)             AS PrimaryIncome,
  CAST(s.AR28 AS NUMERIC)             AS SecondaryIncome,
  SAFE_CAST(s.AR61 AS INT64)          AS LoanTerm,              -- ND → NULL
  CAST(s.AR66 AS NUMERIC)             AS OriginalBalance,

  -- AR135 = Original LTV
  -- IMPORTANT: Avon stores as percent (75.8), BoE spec says decimal (0.758)
  -- So we divide by 100 to normalise
  CAST(s.AR135 AS NUMERIC)       AS OriginalLTV,

  CAST(s.AR136 AS NUMERIC)            AS OriginalValuation,

  -- ===========================================
  -- DATE FIELDS
  -- ===========================================
  -- AR55 is quarterly format "Q4-2006" → parse to end-of-quarter date
  CASE REGEXP_EXTRACT(CAST(s.AR55 AS STRING), r'^Q(\d)')
    WHEN '1' THEN DATE(SAFE_CAST(REGEXP_EXTRACT(CAST(s.AR55 AS STRING), r'(\d{4})$') AS INT64), 3, 31)
    WHEN '2' THEN DATE(SAFE_CAST(REGEXP_EXTRACT(CAST(s.AR55 AS STRING), r'(\d{4})$') AS INT64), 6, 30)
    WHEN '3' THEN DATE(SAFE_CAST(REGEXP_EXTRACT(CAST(s.AR55 AS STRING), r'(\d{4})$') AS INT64), 9, 30)
    WHEN '4' THEN DATE(SAFE_CAST(REGEXP_EXTRACT(CAST(s.AR55 AS STRING), r'(\d{4})$') AS INT64), 12, 31)
  END AS LoanOriginationDate,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR57 AS STRING))  AS AccountStatusDate,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR138 AS STRING)) AS OriginalValuationDate

FROM `rmbs-rwa-pipeline.rmbs_staging.loans_avon` s

-- ===========================================
-- JOINs to decode tables
-- LEFT JOIN so missing codes don't drop rows
-- ===========================================
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

-- Deduplicate: keep one row per loan (most recent period)
QUALIFY ROW_NUMBER() OVER (PARTITION BY s.DealID, CAST(s.AR3 AS STRING) ORDER BY CAST(s.AR1 AS DATE) DESC) = 1
;
