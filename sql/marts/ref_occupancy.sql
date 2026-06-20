-- ref_occupancy — decodes BoE field AR130 (Occupancy Type) to a label.
-- Codes from the AR130 definition in config/boe_rmbs_fields.csv:
--   1=Owner-occupied  2=Partially owner-occupied  3=Non-owner-occupied / Buy-to-let
--   4=Holiday / Second home  ND=No Data
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_occupancy.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_occupancy` AS
SELECT '1'  AS code, 'Owner-occupied'                 AS label UNION ALL
SELECT '2',          'Partially owner-occupied'              UNION ALL
SELECT '3',          'Non-owner-occupied / Buy-to-let'       UNION ALL
SELECT '4',          'Holiday / Second home'                 UNION ALL
SELECT 'ND',         'No Data'
;
