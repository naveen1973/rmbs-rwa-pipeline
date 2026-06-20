-- ref_valuation_type — decodes BoE field AR137 (Original Valuation Type) to a label.
-- Also used for AR144 (Current Valuation Type).
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_valuation_type.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_valuation_type` AS
SELECT '1'  AS code, 'Full, internal and external inspection'   AS label UNION ALL
SELECT '2',          'Full, only external inspection'                    UNION ALL
SELECT '3',          'Drive-by'                                          UNION ALL
SELECT '4',          'AVM'                                               UNION ALL
SELECT '5',          'Indexed'                                           UNION ALL
SELECT '6',          'Desktop'                                           UNION ALL
SELECT '7',          'Managing Agent / Estate Agent'                     UNION ALL
SELECT '8',          'Tax Authority'                                     UNION ALL
SELECT '9',          'Other'                                             UNION ALL
SELECT 'ND',         'No Data'
;
