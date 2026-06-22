-- conform_bletchley_fact_loan_period.sql
-- Transforms Bletchley staging data → canonical fact_loan_period schema.
-- Bletchley-specific: AR109 already decimal (no /100), has more AR columns than Avon.
--
-- Run:  bq query --use_legacy_sql=false < sql/conform/conform_bletchley_fact_loan_period.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.conform_bletchley_fact_loan_period` AS

SELECT
  -- Keys
  s.DealID,
  CAST(s.AR3 AS STRING)               AS LoanID,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR1 AS STRING)) AS CutoffDate,

  -- Balance & payment fields (SAFE_CAST handles ND → NULL)
  SAFE_CAST(s.AR67 AS NUMERIC)        AS CurrentBalance,
  SAFE_CAST(s.AR71 AS NUMERIC)        AS PaymentDue,
  SAFE_CAST(s.AR97 AS NUMERIC)        AS PrepaymentAmount,
  SAFE_CAST(s.AR100 AS NUMERIC)       AS CumulativePrepayments,

  -- Interest rate fields (Bletchley: already decimal, no /100)
  idx.label                           AS CurrentInterestRateIndex,
  CAST(s.AR108 AS STRING)             AS CurrentInterestRateIndex_code,
  SAFE_CAST(s.AR109 AS NUMERIC)       AS CurrentInterestRate,
  SAFE_CAST(s.AR110 AS NUMERIC)       AS CurrentInterestRateMargin,
  SAFE_CAST(s.AR111 AS INT64)         AS InterestRateResetInterval,  -- ND → NULL

  -- Valuation fields (SAFE_CAST handles ND → NULL)
  SAFE_CAST(s.AR141 AS NUMERIC)       AS CurrentLTV,
  SAFE_CAST(s.AR143 AS NUMERIC)       AS CurrentValuation,
  valtype.label                       AS CurrentValuationType,
  CAST(s.AR144 AS STRING)             AS CurrentValuationType_code,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR145 AS STRING)) AS CurrentValuationDate,

  -- Decoded fields (Bletchley has these, unlike Avon)
  forb.label                          AS ForbearanceType,
  CAST(s.AR123 AS STRING)             AS ForbearanceType_code,

  epc.label                           AS CurrentEPC,
  CAST(s.AR162 AS STRING)             AS CurrentEPC_code,

  acct.label                          AS AccountStatus,
  CAST(s.AR166 AS STRING)             AS AccountStatus_code,

  -- Arrears fields (SAFE_CAST handles ND → NULL)
  SAFE_CAST(s.AR169 AS NUMERIC)       AS ArrearsBalance,
  SAFE_CAST(s.AR170 AS NUMERIC)       AS MonthsInArrears,
  SAFE_CAST(s.AR171 AS NUMERIC)       AS Arrears1MonthAgo,
  SAFE_CAST(s.AR172 AS NUMERIC)       AS Arrears2MonthsAgo,

  -- Additional fields
  CAST(s.AR36 AS STRING)              AS BankruptcyFlag,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR56 AS STRING)) AS DateOfLoanMaturity,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR113 AS STRING)) AS NextRevisionDate,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR173 AS STRING)) AS PerformanceArrangementDate,
  CAST(s.AR174 AS STRING)             AS Litigation,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR175 AS STRING)) AS RedemptionDate,

  -- Default & loss fields (SAFE_CAST handles ND → NULL)
  SAFE_CAST(s.AR177 AS NUMERIC)       AS DefaultAmount,
  SAFE.PARSE_DATE('%Y-%m-%d', CAST(s.AR178 AS STRING)) AS DateOfDefault,
  SAFE_CAST(s.AR179 AS NUMERIC)       AS SalePrice,
  SAFE_CAST(s.AR180 AS NUMERIC)       AS LossOnSale,
  SAFE_CAST(s.AR181 AS NUMERIC)       AS CumulativeRecoveries

FROM `rmbs-rwa-pipeline.rmbs_staging.loans_bletchley` s

-- JOINs to decode tables
LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_interest_rate_index` idx
  ON CAST(s.AR108 AS STRING) = idx.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_valuation_type` valtype
  ON CAST(s.AR144 AS STRING) = valtype.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_forbearance_type` forb
  ON CAST(s.AR123 AS STRING) = forb.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_epc_rating` epc
  ON CAST(s.AR162 AS STRING) = epc.code

LEFT JOIN `rmbs-rwa-pipeline.rmbs_marts.ref_account_status` acct
  ON CAST(s.AR166 AS STRING) = acct.code

-- Filter out header/empty rows
WHERE s.AR3 IS NOT NULL
;
