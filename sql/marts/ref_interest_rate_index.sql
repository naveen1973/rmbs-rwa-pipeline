-- ref_interest_rate_index — decodes BoE field AR108 (Current Interest Rate Index) to a label.
-- Also used for AR118 (Revised Interest Rate Index).
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_interest_rate_index.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_interest_rate_index` AS
SELECT '1'  AS code, '1 month LIBOR'            AS label UNION ALL
SELECT '2',          '1 month EURIBOR'                   UNION ALL
SELECT '3',          '3 month LIBOR'                     UNION ALL
SELECT '4',          '3 month EURIBOR'                   UNION ALL
SELECT '5',          '6 month LIBOR'                     UNION ALL
SELECT '6',          '6 month EURIBOR'                   UNION ALL
SELECT '7',          '12 month LIBOR'                    UNION ALL
SELECT '8',          '12 month EURIBOR'                  UNION ALL
SELECT '9',          'BoE Base Rate'                     UNION ALL
SELECT '10',         'ECB Base Rate'                     UNION ALL
SELECT '11',         'Standard Variable Rate'            UNION ALL
SELECT '12',         'Other'                             UNION ALL
SELECT 'ND',         'No Data'
;
