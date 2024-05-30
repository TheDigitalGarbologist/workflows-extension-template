# Writing the component procedure

The procedure in the `procedure.sql` file must implement the logic of the component.

The signature of the function must contain the inputs in the same order as they appear in the metadata file. They must be followed by the outputs.

Parameter types must match those declared in the metadata file. For `Table` parameters (in both inputs and outputs), STRING (or VARCHAR) types must be used in the procedure signature, since they will contain the names of the tables.

A boolean parameter named `dry_run` must be added as the last argument of the stored procedure, but it must not be described in the metadata JSON. It will be true when the execution of the stored procedure is called as part of a dry-run, false otherwise. When a dry-run is performed, the procedure should create the table in the passed output path, but it should be an empty table, which will be used to figure out the output schemas of the component.

Below you can see an example of a stored procedure built following the approach defined above. This procedure takes a table and generates a new one that includes and additional column with a unique identifier.

```sql
CREATE OR REPLACE PROCEDURE ADD_UUID(input STRING, output STRING, dry_run BOOLEAN)
BEGIN
    IF (dry_run) THEN
        EXECUTE IMMEDIATE '''
        CREATE TABLE IF NOT EXISTS ''' || output || '''
        OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
        AS SELECT *, GENERATE_UUID() AS uuid
        FROM ''' || input || '''
        WHERE 1 = 0;
        ''';
    ELSE
        EXECUTE IMMEDIATE '''
        CREATE TABLE IF NOT EXISTS ''' || output || '''
        OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 30 DAY))
        AS SELECT *, GENERATE_UUID() AS uuid
        FROM ''' || input || ';';
    END IF;
END;
```

## Table names and API execution

When a workflow is run from the Workflows UI, table names of the tables created by its components are fully qualified. That means that, if your custom component is connected to an upstream components and uses a table from it, the name that it will received in the corresponding parameter will be a FQN (that is, in the form `project.dataset.table`). Output names received in the output parameters will also be FQNs.

However, when the workflow is run as a stored procedure (when exported or when executed via API), all tables created in components are session tables that are single names (that is, something like `tablename` instead of `project.dataset.table`). That means that inputs that come from other components, and also output table names, will be single-name tables.

You should prepare your component to deal with this situation. Check the input/output table names to see whether they are fully-qualified or not, and implement the corresponding logic to run in each case.
