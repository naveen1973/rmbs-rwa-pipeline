-- ref_loan_purpose — decodes BoE field AR59 (Purpose) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_loan_purpose.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_loan_purpose` AS
SELECT '1'  AS code, 'Purchase'                       AS label UNION ALL
SELECT '2',          'Re-mortgage'                             UNION ALL
SELECT '3',          'Renovation'                              UNION ALL
SELECT '4',          'Equity release'                          UNION ALL
SELECT '5',          'Construction'                            UNION ALL
SELECT '6',          'Debt consolidation'                      UNION ALL
SELECT '7',          'Other'                                   UNION ALL
SELECT '8',          'Re-mortgage with Equity Release'         UNION ALL
SELECT '9',          'Re-mortgage on Different Terms'          UNION ALL
SELECT '10',         'Combination Mortgage'                    UNION ALL
SELECT '11',         'Investment Mortgage'                     UNION ALL
SELECT '12',         'Right to Buy'                            UNION ALL
SELECT '13',         'Government Sponsored Loan'               UNION ALL
SELECT '14',         'SCPI'                                    UNION ALL
SELECT '15',         'Besson'                                  UNION ALL
SELECT '16',         'Perissol'                                UNION ALL
SELECT '17',         'DOM'                                     UNION ALL
SELECT '18',         'Other'                                   UNION ALL
SELECT 'ND',         'No Data'
;
