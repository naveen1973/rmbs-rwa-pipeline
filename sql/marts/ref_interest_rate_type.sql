-- ref_interest_rate_type — decodes BoE field AR107 (Interest Rate Type) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_interest_rate_type.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_interest_rate_type` AS
SELECT '1'  AS code, 'Floating rate loan (for life)'                         AS label UNION ALL
SELECT '2',          'Floating rate loan linked to Libor/Euribor/BoE SVR'             UNION ALL
SELECT '3',          'Fixed rate loan (for life)'                                     UNION ALL
SELECT '4',          'Fixed with future periodic resets'                              UNION ALL
SELECT '5',          'Fixed rate loan with compulsory future switch to floating'      UNION ALL
SELECT '6',          'Capped'                                                         UNION ALL
SELECT '7',          'Discount'                                                       UNION ALL
SELECT '8',          'Other'                                                          UNION ALL
SELECT 'ND',         'No Data'
;
