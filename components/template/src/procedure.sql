CREATE OR REPLACE PROCEDURE @@workflows_temp@@.ADD_FIXED_VALUE_COLUMN(input_table STRING, output_table STRING, dryRun BOOLEAN)
BEGIN
    IF (dryRun) THEN
        EXECUTE IMMEDIATE '''
        CREATE TABLE IF NOT EXISTS ''' || output_table || '''
        OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
        AS SELECT *, 'hello' AS fixed_value_col
        FROM ''' || input_table || '''
        WHERE 1 = 0;
        ''';
    ELSE
        EXECUTE IMMEDIATE '''
        CREATE TABLE IF NOT EXISTS ''' || output_table || '''
        OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
        AS SELECT *, 'hello' AS fixed_value_col
        FROM ''' || input_table || ';';
    END IF;
END;