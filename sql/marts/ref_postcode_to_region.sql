-- ref_postcode_to_region — maps UK postcode areas to ITL1 region codes.
--
-- This table stores a simple two-column lookup: postcode_area (1-2 letters) → region_code (ITL1).
-- Example rows:  SW → UKI (London),  M → UKD (North West),  EH → UKM (Scotland)
--
-- WHY THIS EXISTS: The BoE spec says AR128 should be ITL1 codes (UKC, UKD, etc.),
-- but in practice many issuers populate it with postcode outcodes (e.g., "SW1A", "M15"),
-- partial postcodes ("SW1A 2AA"), or even full postcodes — because that's what their
-- loan origination systems or broker platforms capture.
--
-- HOW TO USE (in the conform views we build later, not in this file):
--
--   LEFT JOIN ref_postcode_to_region p
--     ON REGEXP_EXTRACT(UPPER(AR128), r'^([A-Z]{1,2})') = p.postcode_area
--   LEFT JOIN ref_region r
--     ON COALESCE(p.region_code, AR128) = r.code
--
-- The REGEXP_EXTRACT pulls 1-2 leading letters before any digit:
--   "SW1A" → SW,  "M15" → M,  "SW1A 2AA" → SW,  "L1 8JQ" → L
-- If AR128 is already an ITL1 code like "UKI", the regex returns "UK" (no match here),
-- so it falls through to the direct ref_region lookup via COALESCE.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_postcode_to_region.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_postcode_to_region` AS

-- UKC: North East England
SELECT 'DH' AS postcode_area, 'UKC' AS region_code UNION ALL
SELECT 'DL', 'UKC' UNION ALL
SELECT 'NE', 'UKC' UNION ALL
SELECT 'SR', 'UKC' UNION ALL
SELECT 'TS', 'UKC' UNION ALL

-- UKD: North West England
SELECT 'BB', 'UKD' UNION ALL
SELECT 'BL', 'UKD' UNION ALL
SELECT 'CA', 'UKD' UNION ALL
SELECT 'CH', 'UKD' UNION ALL
SELECT 'CW', 'UKD' UNION ALL
SELECT 'FY', 'UKD' UNION ALL
SELECT 'L',  'UKD' UNION ALL
SELECT 'LA', 'UKD' UNION ALL
SELECT 'M',  'UKD' UNION ALL
SELECT 'OL', 'UKD' UNION ALL
SELECT 'PR', 'UKD' UNION ALL
SELECT 'SK', 'UKD' UNION ALL
SELECT 'WA', 'UKD' UNION ALL
SELECT 'WN', 'UKD' UNION ALL

-- UKE: Yorkshire and The Humber
SELECT 'BD', 'UKE' UNION ALL
SELECT 'DN', 'UKE' UNION ALL
SELECT 'HD', 'UKE' UNION ALL
SELECT 'HG', 'UKE' UNION ALL
SELECT 'HU', 'UKE' UNION ALL
SELECT 'HX', 'UKE' UNION ALL
SELECT 'LS', 'UKE' UNION ALL
SELECT 'S',  'UKE' UNION ALL
SELECT 'WF', 'UKE' UNION ALL
SELECT 'YO', 'UKE' UNION ALL

-- UKF: East Midlands
SELECT 'DE', 'UKF' UNION ALL
SELECT 'LE', 'UKF' UNION ALL
SELECT 'LN', 'UKF' UNION ALL
SELECT 'NG', 'UKF' UNION ALL
SELECT 'NN', 'UKF' UNION ALL

-- UKG: West Midlands
SELECT 'B',  'UKG' UNION ALL
SELECT 'CV', 'UKG' UNION ALL
SELECT 'DY', 'UKG' UNION ALL
SELECT 'HR', 'UKG' UNION ALL
SELECT 'ST', 'UKG' UNION ALL
SELECT 'TF', 'UKG' UNION ALL
SELECT 'WR', 'UKG' UNION ALL
SELECT 'WS', 'UKG' UNION ALL
SELECT 'WV', 'UKG' UNION ALL

-- UKH: East of England
SELECT 'AL', 'UKH' UNION ALL
SELECT 'CB', 'UKH' UNION ALL
SELECT 'CM', 'UKH' UNION ALL
SELECT 'CO', 'UKH' UNION ALL
SELECT 'IP', 'UKH' UNION ALL
SELECT 'LU', 'UKH' UNION ALL
SELECT 'NR', 'UKH' UNION ALL
SELECT 'PE', 'UKH' UNION ALL
SELECT 'SG', 'UKH' UNION ALL
SELECT 'SS', 'UKH' UNION ALL
SELECT 'HP', 'UKH' UNION ALL

-- UKI: London (inner)
SELECT 'E',  'UKI' UNION ALL
SELECT 'EC', 'UKI' UNION ALL
SELECT 'N',  'UKI' UNION ALL
SELECT 'NW', 'UKI' UNION ALL
SELECT 'SE', 'UKI' UNION ALL
SELECT 'SW', 'UKI' UNION ALL
SELECT 'W',  'UKI' UNION ALL
SELECT 'WC', 'UKI' UNION ALL
-- UKI: London (Greater London boroughs)
SELECT 'BR', 'UKI' UNION ALL
SELECT 'CR', 'UKI' UNION ALL
SELECT 'DA', 'UKI' UNION ALL
SELECT 'EN', 'UKI' UNION ALL
SELECT 'HA', 'UKI' UNION ALL
SELECT 'IG', 'UKI' UNION ALL
SELECT 'KT', 'UKI' UNION ALL
SELECT 'RM', 'UKI' UNION ALL
SELECT 'SM', 'UKI' UNION ALL
SELECT 'TW', 'UKI' UNION ALL
SELECT 'UB', 'UKI' UNION ALL
SELECT 'WD', 'UKI' UNION ALL

-- UKJ: South East England
SELECT 'BN', 'UKJ' UNION ALL
SELECT 'CT', 'UKJ' UNION ALL
SELECT 'GU', 'UKJ' UNION ALL
SELECT 'ME', 'UKJ' UNION ALL
SELECT 'MK', 'UKJ' UNION ALL
SELECT 'OX', 'UKJ' UNION ALL
SELECT 'PO', 'UKJ' UNION ALL
SELECT 'RG', 'UKJ' UNION ALL
SELECT 'RH', 'UKJ' UNION ALL
SELECT 'SL', 'UKJ' UNION ALL
SELECT 'SO', 'UKJ' UNION ALL
SELECT 'TN', 'UKJ' UNION ALL

-- UKK: South West England
SELECT 'BA', 'UKK' UNION ALL
SELECT 'BH', 'UKK' UNION ALL
SELECT 'BS', 'UKK' UNION ALL
SELECT 'DT', 'UKK' UNION ALL
SELECT 'EX', 'UKK' UNION ALL
SELECT 'GL', 'UKK' UNION ALL
SELECT 'PL', 'UKK' UNION ALL
SELECT 'SN', 'UKK' UNION ALL
SELECT 'SP', 'UKK' UNION ALL
SELECT 'TA', 'UKK' UNION ALL
SELECT 'TQ', 'UKK' UNION ALL
SELECT 'TR', 'UKK' UNION ALL

-- UKL: Wales
SELECT 'CF', 'UKL' UNION ALL
SELECT 'LD', 'UKL' UNION ALL
SELECT 'LL', 'UKL' UNION ALL
SELECT 'NP', 'UKL' UNION ALL
SELECT 'SA', 'UKL' UNION ALL
SELECT 'SY', 'UKL' UNION ALL

-- UKM: Scotland
SELECT 'AB', 'UKM' UNION ALL
SELECT 'DD', 'UKM' UNION ALL
SELECT 'DG', 'UKM' UNION ALL
SELECT 'EH', 'UKM' UNION ALL
SELECT 'FK', 'UKM' UNION ALL
SELECT 'G',  'UKM' UNION ALL
SELECT 'HS', 'UKM' UNION ALL
SELECT 'IV', 'UKM' UNION ALL
SELECT 'KA', 'UKM' UNION ALL
SELECT 'KW', 'UKM' UNION ALL
SELECT 'KY', 'UKM' UNION ALL
SELECT 'ML', 'UKM' UNION ALL
SELECT 'PA', 'UKM' UNION ALL
SELECT 'PH', 'UKM' UNION ALL
SELECT 'TD', 'UKM' UNION ALL
SELECT 'ZE', 'UKM' UNION ALL

-- UKN: Northern Ireland (all NI uses BT)
SELECT 'BT', 'UKN'
;
