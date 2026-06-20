-- ref_employment_status — decodes BoE field AR21 (Borrower's Employment Status) to a label.
-- Also used for AR189 (Second Borrower's Employment Status).
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_employment_status.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_employment_status` AS
SELECT '1'  AS code, 'Employed or full loan is guaranteed'       AS label UNION ALL
SELECT '2',          'Employed with partial support'                      UNION ALL
SELECT '3',          'Protected life-time employment'                     UNION ALL
SELECT '4',          'Unemployed'                                         UNION ALL
SELECT '5',          'Self-employed'                                      UNION ALL
SELECT '6',          'No employment, borrower is legal entity'            UNION ALL
SELECT '7',          'Student'                                            UNION ALL
SELECT '8',          'Pensioner'                                          UNION ALL
SELECT '9',          'Other'                                              UNION ALL
SELECT 'ND',         'No Data'
;
