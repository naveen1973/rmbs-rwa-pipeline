-- dim_loan.sql
-- Final dimension table: UNION ALL conform views from each deal.
-- Static loan attributes (one row per DealID + LoanID).
--
-- To add a new deal: create conform_<deal>_dim_loan view, add to UNION below.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/dim_loan.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.dim_loan` AS

SELECT * FROM `rmbs-rwa-pipeline.rmbs_marts.conform_avon_dim_loan`
UNION ALL
SELECT * FROM `rmbs-rwa-pipeline.rmbs_marts.conform_bletchley_dim_loan`

-- UNION ALL SELECT * FROM `rmbs-rwa-pipeline.rmbs_marts.conform_canterbury_dim_loan`
-- (add more deals here)
;
