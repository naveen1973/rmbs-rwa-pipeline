-- ref_forbearance_type — decodes BoE field AR123 (Forbearance Type) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_forbearance_type.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_forbearance_type` AS
SELECT '1'  AS code, 'Term extension'                           AS label UNION ALL
SELECT '2',          'Temporary transfer to IO'                          UNION ALL
SELECT '3',          'Permanent transfer to IO'                          UNION ALL
SELECT '4',          'Arrears capitalisation'                            UNION ALL
SELECT '5',          'Payment arrangement'                               UNION ALL
SELECT '6',          'Non contractual payment holiday'                   UNION ALL
SELECT '7',          'Other'                                             UNION ALL
SELECT '8',          'Multiple forbearance options exercised'            UNION ALL
SELECT '9',          'Not in forbearance'
;
