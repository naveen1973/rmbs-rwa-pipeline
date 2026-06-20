-- ref_shared_ownership — decodes BoE field AR60 (Shared Ownership) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_shared_ownership.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_shared_ownership` AS
SELECT '1'  AS code, 'Not Shared Ownership'       AS label UNION ALL
SELECT '2',          'Central Government Scheme'          UNION ALL
SELECT '3',          'Local Government Scheme'            UNION ALL
SELECT '4',          'Housing Associations'               UNION ALL
SELECT '5',          'Building Developers'                UNION ALL
SELECT '6',          'Other'                              UNION ALL
SELECT 'ND',         'No Data'
;
