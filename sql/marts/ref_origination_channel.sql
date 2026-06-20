-- ref_origination_channel — decodes BoE field AR58 (Origination Channel) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_origination_channel.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_origination_channel` AS
SELECT '1'  AS code, 'Office / branch network'  AS label UNION ALL
SELECT '2',          'Central / Direct'                  UNION ALL
SELECT '3',          'Broker'                            UNION ALL
SELECT '4',          'Internet'                          UNION ALL
SELECT '5',          'Packager'                          UNION ALL
SELECT 'ND',         'No Data'
;
