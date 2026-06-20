-- ref_property_type — decodes BoE field AR131 (Property Type) to a label.
--
-- Run:  bq query --use_legacy_sql=false < sql/marts/ref_property_type.sql

CREATE OR REPLACE TABLE `rmbs-rwa-pipeline.rmbs_marts.ref_property_type` AS
SELECT '1'  AS code, 'Residential (House)'                                  AS label UNION ALL
SELECT '2',          'Residential (Flat/Apartment)'                                  UNION ALL
SELECT '3',          'Residential (Bungalow)'                                        UNION ALL
SELECT '4',          'Residential (Terraced House)'                                  UNION ALL
SELECT '5',          'Multifamily house with recourse'                               UNION ALL
SELECT '6',          'Multifamily house without recourse'                            UNION ALL
SELECT '7',          'Partially commercial use'                                      UNION ALL
SELECT '8',          'Commercial/business use with recourse'                         UNION ALL
SELECT '9',          'Commercial/business use without recourse'                      UNION ALL
SELECT '10',         'Land Only'                                                     UNION ALL
SELECT '11',         'Other'                                                         UNION ALL
SELECT 'ND',         'No Data'
;
