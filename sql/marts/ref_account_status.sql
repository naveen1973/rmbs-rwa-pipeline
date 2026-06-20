-- ref_account_status — decodes BoE field AR166 (Account Status) to a label.
-- Same pattern as ref_occupancy: CREATE OR REPLACE TABLE ... AS a UNION ALL stack.
-- Codes from the AR166 definition in config/boe_rmbs_fields.csv:
--   1=Performing  2=Arrears  3=Default or Foreclosure  4=Redeemed
--   5=Repurchased by Seller  6=Other  ND=No Data
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_account_status.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_account_status` AS
SELECT '1' AS code, 'Performing' AS label UNION ALL
SELECT '2', 'Arrears' AS label UNION ALL
SELECT '3', 'Default or Foreclosure' AS label UNION ALL
SELECT '4', 'Redeemed' AS label UNION ALL
SELECT '5', 'Repurchased by Seller' AS label UNION ALL
SELECT '6', 'Other' AS label UNION ALL
SELECT 'ND', 'No Data' AS label;