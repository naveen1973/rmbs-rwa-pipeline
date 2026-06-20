-- ref_region — decodes BoE field AR128 (Geographic Region) to a label.
-- Uses UK ITL1 (International Territorial Level 1) region codes.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_region.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_region` AS
SELECT 'UKC' AS code, 'North East England'        AS label UNION ALL
SELECT 'UKD',         'North West England'                 UNION ALL
SELECT 'UKE',         'Yorkshire and The Humber'           UNION ALL
SELECT 'UKF',         'East Midlands'                      UNION ALL
SELECT 'UKG',         'West Midlands'                      UNION ALL
SELECT 'UKH',         'East of England'                    UNION ALL
SELECT 'UKI',         'London'                             UNION ALL
SELECT 'UKJ',         'South East England'                 UNION ALL
SELECT 'UKK',         'South West England'                 UNION ALL
SELECT 'UKL',         'Wales'                              UNION ALL
SELECT 'UKM',         'Scotland'                           UNION ALL
SELECT 'UKN',         'Northern Ireland'                   UNION ALL
SELECT 'ND',          'No Data'
;
