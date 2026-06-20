-- ref_repayment_method — decodes BoE field AR69 (Repayment Method) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_repayment_method.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_repayment_method` AS
SELECT '1'  AS code, 'Interest Only'      AS label UNION ALL
SELECT '2',          'Repayment'                   UNION ALL
SELECT '3',          'Endowment'                   UNION ALL
SELECT '4',          'Pension'                     UNION ALL
SELECT '5',          'ISA/PEP'                     UNION ALL
SELECT '6',          'Index-Linked'                UNION ALL
SELECT '7',          'Part & Part'                 UNION ALL
SELECT '8',          'Savings Mortgage'            UNION ALL
SELECT '9',          'Other'                       UNION ALL
SELECT 'ND',         'No Data'
;
