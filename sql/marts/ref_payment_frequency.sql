-- ref_payment_frequency — decodes BoE field AR70 (Payment Frequency) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_payment_frequency.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_payment_frequency` AS
SELECT '1'  AS code, 'Monthly'        AS label UNION ALL
SELECT '2',          'Quarterly'               UNION ALL
SELECT '3',          'Semi annually'           UNION ALL
SELECT '4',          'Annual'                  UNION ALL
SELECT '5',          'Bullet'                  UNION ALL
SELECT '6',          'Other'                   UNION ALL
SELECT 'ND',         'No Data'
;
