# Running tests
This document goes over the basic steps to create tests for the components included in your extension

## Data Warehouse configuration

For running the `test` and `capture` scripts, you need to configure the access to the data warehouse where your extension is supposed to run. To do so, rename the `.env.template` file in the root of the repository to `.env` and edit it with the appropriate values for each provider (BigQuery or Snowflake). 

For BigQuery, we only need to specify the project and dataset where the tests will run. 
```
BQ_TEST_PROJECT=
BQ_TEST_DATASET=
```
Check [this section](./tooling.md#authentication-with-the-data-warehouse) to ensure you have authenticated correctly with BigQuery.

For Snowflake, we also need to set credentials to authenticate in the `.env` file.
```
SF_ACCOUNT=
SF_TEST_DATABASE=
SF_TEST_SCHEMA=
SF_USER=
SF_PASSWORD=
```

## Setup
Setup the elements in the `test` folder to define how the test should be run to verify that the component is correctly working. 
Checkout [this section](./anatomy_of_an_extension.md#test) to understand which files are necessary to define the tests. 

Run the `capture` script to create the test fixtures from the results of running your components in the corresponding datawarehouse.
```bash
$ python carto_extension.py capture
```
This command will generate fixture files in the `fixtures` folder.
Check the created files to ensure that the output is as expected. 

From that point, you can now run the `test` script to run tests and check if they match the captured outputs, whenever you change the implementation of any of the components.
```bash
$ python carto_extension.py test
```

## CI configuration

This template includes a GitHub workflow to run the extension test suite when new changes are pushed to the repository (provided that the `capture` script has been run and test fixtures have been captured). 

GitHub secrets must be configured in order to have the workflow correctly running. Check the [`.github/.workflow/CI_tests.yml`](../.github/.workflow/CI_tests.yml) file for more information.