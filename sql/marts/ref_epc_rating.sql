-- ref_epc_rating — decodes BoE field AR162 (Current Energy Performance Certificate Value) to a label.
-- Also used for AR163 (Potential EPC Value).
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_epc_rating.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_epc_rating` AS
SELECT 'A'  AS code, 'EPC A'                              AS label UNION ALL
SELECT 'B',          'EPC B'                                       UNION ALL
SELECT 'C',          'EPC C'                                       UNION ALL
SELECT 'D',          'EPC D'                                       UNION ALL
SELECT 'E',          'EPC E'                                       UNION ALL
SELECT 'F',          'EPC F'                                       UNION ALL
SELECT 'G',          'EPC G'                                       UNION ALL
SELECT 'NR',         'Not required to have EPC rating'             UNION ALL
SELECT 'ND',         'No Data'
;
