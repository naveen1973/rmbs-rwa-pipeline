-- fact_loan_period.sql
-- Final fact table: UNION ALL conform views from each deal.
-- Dynamic loan metrics (one row per DealID + LoanID + CutoffDate).
--
-- To add a new deal: create conform_<deal>_fact_loan_period view, add to UNION below.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/fact_loan_period.sql

CREATE OR REPLACE VIEW `rmbs-rwa-pipeline.rmbs_marts.fact_loan_period` AS

SELECT * FROM `rmbs-rwa-pipeline.rmbs_marts.conform_avon_fact_loan_period`
UNION ALL
SELECT * FROM `rmbs-rwa-pipeline.rmbs_marts.conform_bletchley_fact_loan_period`

-- UNION ALL SELECT * FROM `rmbs-rwa-pipeline.rmbs_marts.conform_canterbury_fact_loan_period`
-- (add more deals here)
;
