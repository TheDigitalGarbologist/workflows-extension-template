EXECUTE IMMEDIATE '''
CREATE OR REPLACE TABLE ''' || output_table || '''
OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
AS 
SELECT 
    r.* EXCEPT (geom),  
    NULL AS segmentid,  
    NULL AS segment_wkt,  
    NULL AS geom,  
    NULL AS segment_length_km  
FROM ''' || input_table || ''' r
WHERE 1 = 0;
''';