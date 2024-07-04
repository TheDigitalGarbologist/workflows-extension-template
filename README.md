# Workflows extensions template repository

Use this repository template to create a new extension for CARTO Workflows.

Follow these steps to implement your own extension.

1. Create a new repository based on this one.
1. Install the requirements needed by the repository scripts. Python 3 is required to run the repository scripts:

    `$ pip install -r ./requirements.txt`

1. Edit the `metadata.json` file in the root folder of the repo so it contains the correct information for the extension.
1. Copy the `template` folder and rename it with the desired internal name (i.e. mycomponent) of the component to add.
1. Edit the `procedure.sql` file in that copied folder to define the logic of the new component. For more details, see [here](./docs/procedure.md)
1. Edit the component metadata file. For more information, see [here](./doc/component_metadata.md)
1. Setup the elements in the `test` folder to define how the test should be run to verify that the component is correctly working. Use the `test.json` file to define the test case, and add the tables that you need for your test as `.ndjson` files in that same folder. You can refer to those files as input values using the filename without the extension (see the provided example with the `table1.ndjson` file)
1. Write the component documentation in the `README` file.
1. Repeat steps 3-7 as many times as components will be included in the extension.
1. Use the `check` script to ensure that the extension is correctly defined.

    `$ python carto_extension.py check`

1. Run the `capture` script to create the test fixtures from the results of running your components in the corresponding datawarehouse.

    `$ python carto_extension.py capture`

1. Check the created files to ensure that the output is as expected. From that point, you can now run the `test` script to run tests and check if they match the captured outputs, whenever you change the implementation of any of the components.

    `$ python carto_extension.py test`

1. Run the `package` script to create the `extension.zip` file.

    `$ python carto_extension.py package`

Now you are ready to distribute your extension.

The `capture` and `test` actions support a `--component` parameter, which will make them run only for the selected component, instead of all the ones in the extension.

`$ python carto_extension.py capture --component=mycomponent`

## Deploying the extension

You can deploy the extension in a given destination (project.dataset in the case of BigQuery, database.schema in the case of Snowflake), using the `deploy` command with the following syntax:

`$ python carto_extension.py deploy --destination=[myproject.mydataset]`

## Data Warehouse configuration

For running the "deploy", "test" and "capture" scripts, you need to configure the access to the data warehouse where your extension is supposed to run. To do so, rename the `.env.template` file in the root of the repository to `.env` and edit it with the appropriate values.

If you are creating a BigQuery extension, Install the Google Cloud SDK and run the following in your console to authenticate:

`$ gcloud auth application-default login`

## CI configuration

The template includes a GitHub workflow to run the extension test suite when new changes are pushed to the repository (provided that the `capture` script has been run and test fixtures have been captured). GitHub secrets must be configured in order to have the workflow correctly running. Check the `CI_test.yml` file for more information.
