## Anatomy of an Extension Package
Each extension package contains a single file with **metadata** about the extension and one or more **components**. 
This is a simplified diagram of the folder structure of an extension package: 
```
extension-package/
├── metadata.json
└── components/
    ├── component_A/
    │   ├── doc/
    │   ├── test/
    │   ├── src/
    │   │   └── procedure.sql
    │   └── metadata.json
    └── component_B/
        ├── doc/
        ├── test/
        ├── src/
        │   └── procedure.sql
        └── metadata.json
```
___

### Extension's metadata
The extension's metadata file defines attributes like its name, the group or category the extension belongs, version, author, description, icon, etc. 

Extension's metadata is defined in a [`metadata.json`](../metadata.json) file in the root folder of this repo.

In that file, you will see that there is a `details` array  that accepts different custom objects defined by `"name"` and `"value"` properties. 

These details will render in the CARTO UI when displaying the extension details. This is an example: 
```json
"details": [
    {
        "name": "License",
        "value": "Apache 2.0"
    },
    {
        "name": "Custom detail",
        "value": "Value for custom detail"
    }
]
```

There is also a `components` object that should contain an array of all the components included in the extension. For example: 
```json
"components": [
    "my_custom_component",
    "another_custom_component"
]
```
___

### Components

Components should aim to cover specific functionality, like adding a new column with a UUID, running an analysis and storing the result on an additional column or sending an HTTP request to a specific endpoint. 

Tipically, a component receives one or more inputs; it has some settings that influence the execution of the code; and produce an output. 

In Workflows, most components produce a table that contains the same columns from the input plus an additional set of columns that contain the result. This is not a hard requirement though, and your component doesn't need to follow this pattern.

Each component should be created on a separate folder inside [`/components`](../components/) and it's defined by **metadata** and **logic** (implemented as a stored procedure). 
#### Component's metadata
Each component has its own [`metadata.json`](../components/template/metadata.json) file, where you can define a name, category, description, icon, etc. And most importantly, **inputs**, **outputs** and a link with the corresponding stored procedure.

Find more information about the component's metadata in the specific [documentation](./component_metadata.md).

#### Logic
The logic for each component is defined as an stored procedure in the [`components/<component_name>/src/procedure.sql`](../components/template/src/procedure.sql) file.

Find a more complete documentation about creating stored procedures for custom components in [this documentation](./procedure.md).

#### Joining metadata and logic
Inputs, settings, and outputs of a component are defined in the metadata file, and then used in the stored procedure. 

For these two parts of a custom component to work well together, we just need to ensure consistency between what's declared in metadata and what's used in the stored procedure.

For this example we'll create a very simple component that just adds a new column with a fixed value.

##### Inputs
As mentioned before, inputs defined in the metadata need to match the inputs of the stored procedure. For example: 
```json
"inputs": [
    {
      "name": "input_table",
      "title": "Input A",
      "description": "A table to be used as input for my component",
      "type": "Table"
    },
    {
      "name": "value",
      "title": "Value",
      "description": "A value that will be used to populate the new column",
      "type": "String"
  }
]
```

for those inputs, the procedure should be declared as follows: 
```sql
CREATE OR REPLACE PROCEDURE ADD_FIXED_VALUE_COLUMN(
  input_table STRING, 
  value STRING
)
BEGIN
    (...)
END;
```
##### Outputs
Outputs work the same way: they need to be defined in metadata, taken into account in your procedure's declaration and used in the code. Extending the previous example, we would have this in metadata: 
```json
"outputs": [
    {
        "name": "output_table",
        "title": "Output table",
        "description": "The table with the new column added",
        "type": "Table"
    }
]
```
And our procedure would look like: 
```sql
CREATE OR REPLACE PROCEDURE ADD_FIXED_VALUE_COLUMN(
  input_table STRING, 
  value STRING, 
  output_table STRING
)
BEGIN
  EXECUTE IMMEDIATE '''
  CREATE TABLE IF NOT EXISTS ''' || output_table || '''
  AS SELECT *, ''' || value || ''' AS added_column
  FROM ''' || input_table;
END;
```

>💡 **Tip**
> 
> There is an additional `dry_run BOOL` parameter that needs to be included in the procedure. It has been omitted for the sake of simplification. Please refer to [this section](./procedure.md#managing-the-execution-of-dry-run-queries) to understand how to use it.

##### Procedure's name
Finally, in order to link our metadata with the procedure's code, we need to specify the procedure's name like: 
```json
"procedureName": "ADD_FIXED_VALUE_COLUMN"
```
And as showed in the previous examples, our procedure is created like: 
```sql
CREATE OR REPLACE PROCEDURE ADD_FIXED_VALUE_COLUMN(...)
```
___

### Test
Each component can also have its own set of tests to validate the results when running the component. 

Tests are optional, but highly recommended.

The content of the [`/components/<component_name>/test/`](../components/template/test/) is as follows: 
``` 
test/
    ├── test.json
    ├── table1.ndjson
    └── fixtures/
        ├── 1.json
        └── 2.json
```
##### `test.json`
Contains an array with the definition of each test, specifying the `id` of each test and the values for each input: 
```json
[
    {
        "id": 1,
        "inputs": {
            "input_table": "table1",
            "value": "test"
        }
    },
    {
        "id": 2,
        "inputs": {
            "input_table": "table1",
            "value": "test2"
        }
    }
]
```
##### `table1.ndjson`
An NDJSON file that contains the data to be used in the test. It can have any arbitrary name, but make sure it's correctly referenced in `input_table` in your `test.json` file. For example: 

```json
{"id":1,"name":"Alice"}
{"id":2,"name":"Bob"}
{"id":3,"name":"Carol"}
```
##### `fixtures/<id>.json`

The fixture files contain the expected result for each test defined in `test.json`. For example, for our test `1` we would have a `1.json` file with this content: 
```json
{
  "output_table": [
    {
      "name": "Bob",
      "id": 2,
      "fixed_value_col": "test"
    },
    {
      "name": "Carol",
      "id": 3,
      "fixed_value_col": "test"
    },
    {
      "name": "Alice",
      "id": 1,
      "fixed_value_col": "test"
    }
  ]
}
```

When developing new components, the `fixture` folder and its content will be automatically generated by running the `capture` command: 

```bash
$ python carto_extension.py capture
```

Learn more about how to run these tests in your data warehouse in [this document](./running-tests.md).
___
### Component's documentation
Inside each component's folder, there can be a `/doc` subfolder with any number of additional Markdown files to document your component's usage. 

This is completely optional, but we recommend documenting your custom components comprehensively. 

___

### Icons

Custom icons are supported, for the extension and also for each component. 

Place your SVG files in the [`icons`](../icons/) folder, and make sure that you reference them using their name in the `metadata.json` files for the extension and each component. 

[Learn more about how to create custom icons](./icons.md).