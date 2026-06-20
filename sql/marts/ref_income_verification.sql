-- ref_income_verification — decodes BoE field AR27 (Income Verification for Primary Income) to a label.
-- Also used for AR29 (Income Verification for Secondary Income).
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_income_verification.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_income_verification` AS
SELECT '1'  AS code, 'Self-certified no checks'                   AS label UNION ALL
SELECT '2',          'Self-certified with affordability confirmation'     UNION ALL
SELECT '3',          'Verified'                                           UNION ALL
SELECT '4',          'Non-Verified Income'                                UNION ALL
SELECT '5',          'Other'                                              UNION ALL
SELECT 'ND',         'No Data'
;
