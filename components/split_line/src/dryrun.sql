EXECUTE IMMEDIATE '''
CREATE TABLE IF NOT EXISTS ''' || output_table || '''
OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
AS SELECT *, ''' || unique_id_field || ''' AS unique_id
FROM ''' || input_table || '''
WHERE 1 = 0;
''';


