-- conform_avon_fact_loan_period.sql
-- Transforms raw staging data (AR codes) → canonical fact_loan_period schema.
-- Dynamic fields: one row per (DealID, LoanID, CutoffDate).
--
-- Run:  bq query --use_legacy_sql=false < sql/conform/conform_avon_fact_loan_period.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.conform_avon_fact_loan_period` AS

SELECT
  -- ===========================================
  -- KEYS
  -- ===========================================
  s.DealID,
  CAST(s.AR3 AS STRING)               AS LoanID,
  CAST(s.AR1 AS DATE)                 AS CutoffDate,

  -- ===========================================
  -- BALANCE & PAYMENT FIELDS (SAFE_CAST handles ND → NULL)
  -- ===========================================
  SAFE_CAST(s.AR67 AS NUMERIC)        AS CurrentBalance,
  SAFE_CAST(s.AR71 AS NUMERIC)        AS PaymentDue,
  SAFE_CAST(s.AR97 AS NUMERIC)        AS PrepaymentAmount,
  SAFE_CAST(s.AR100 AS NUMERIC)       AS CumulativePrepayments,

  -- ===========================================
  -- INTEREST RATE FIELDS
  -- ===========================================
  idx.label                           AS CurrentInterestRateIndex,
  CAST(s.AR108 AS STRING)             AS CurrentInterestRateIndex_code,
  SAFE_CAST(s.AR109 AS NUMERIC) / 100 AS CurrentInterestRate,      -- Avon stores as %, normalise to decimal
  SAFE_CAST(s.AR110 AS NUMERIC) / 100 AS CurrentInterestRateMargin, -- Avon stores as %, normalise to decimal
  SAFE_CAST(s.AR111 AS INT64)         AS InterestRateResetInterval,  -- ND/header → NULL

  -- ===========================================
  -- VALUATION FIELDS
  -- ===========================================
  SAFE_CAST(s.AR141 AS NUMERIC)       AS CurrentLTV,
  SAFE_CAST(s.AR143 AS NUMERIC)       AS CurrentValuation,
  valtype.label                       AS CurrentValuationType,
  CAST(s.AR144 AS STRING)             AS CurrentValuationType_code,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR145 AS STRING)) AS CurrentValuationDate,

  -- ===========================================
  -- DECODED FIELDS (AR123 ForbearanceType, AR162 EPC not in Avon — NULL placeholders)
  -- ===========================================
  CAST(NULL AS STRING)                AS ForbearanceType,
  CAST(NULL AS STRING)                AS ForbearanceType_code,
  CAST(NULL AS STRING)                AS CurrentEPC,
  CAST(NULL AS STRING)                AS CurrentEPC_code,

  acct.label                          AS AccountStatus,
  CAST(s.AR166 AS STRING)             AS AccountStatus_code,

  -- ===========================================
  -- ARREARS FIELDS (SAFE_CAST handles ND → NULL)
  -- ===========================================
  SAFE_CAST(s.AR169 AS NUMERIC)       AS ArrearsBalance,
  SAFE_CAST(s.AR170 AS NUMERIC)       AS MonthsInArrears,
  SAFE_CAST(s.AR171 AS NUMERIC)       AS Arrears1MonthAgo,
  SAFE_CAST(s.AR172 AS NUMERIC)       AS Arrears2MonthsAgo,

  -- ===========================================
  -- YOUR TURN: Add remaining fields
  -- ===========================================

  CAST(s.AR36 AS STRING)              AS BankruptcyFlag,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR56 AS STRING))  AS DateOfLoanMaturity,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR113 AS STRING)) AS NextRevisionDate,
  CAST(NULL AS DATE)                  AS PerformanceArrangementDate,  -- not in Avon
  CAST(s.AR174 AS STRING)             AS Litigation,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR175 AS STRING)) AS RedemptionDate,

  -- ===========================================
  -- DEFAULT & LOSS FIELDS (SAFE_CAST handles ND → NULL)
  -- ===========================================
  SAFE_CAST(s.AR177 AS NUMERIC)       AS DefaultAmount,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR178 AS STRING)) AS DateOfDefault,
  SAFE_CAST(s.AR179 AS NUMERIC)       AS SalePrice,
  SAFE_CAST(s.AR180 AS NUMERIC)       AS LossOnSale,
  SAFE_CAST(s.AR181 AS NUMERIC)       AS CumulativeRecoveries

FROM `rmbs-rwa-pipeline.rmbs_staging.loans_avon` s

-- ===========================================
-- JOINs to decode tables
-- ===========================================
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_interest_rate_index` idx
  ON CAST(s.AR108 AS STRING) = idx.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_valuation_type` valtype
  ON CAST(s.AR144 AS STRING) = valtype.code

-- AR123 (ForbearanceType), AR162 (EPC) not in Avon — JOINs omitted

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_account_status` acct
  ON CAST(s.AR166 AS STRING) = acct.code
;
