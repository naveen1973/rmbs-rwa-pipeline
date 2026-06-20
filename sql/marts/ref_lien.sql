-- ref_lien — decodes BoE field AR84 (Lien) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_lien.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_lien` AS
SELECT '1'  AS code, '1st Lien'   AS label UNION ALL
SELECT '2',          '2nd Lien'            UNION ALL
SELECT '3',          '3rd Lien'            UNION ALL
SELECT '4',          'Other'               UNION ALL
SELECT 'ND',         'No Data'
;
