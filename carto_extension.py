from google.cloud import bigquery
from dotenv import load_dotenv
import argparse
from sys import argv
import os
import zipfile
import json
from uuid import uuid4

WORKFLOWS_TEMP_SCHEMA = "WORKFLOWS_TEMP"
EXTENSIONS_TABLENAME = "WORKFLOWS_EXTENSIONS"
WORKFLOWS_TEMP_PLACEHOLDER = "@@workflows_temp@@"

load_dotenv()

bq_workflows_temp = f"`{os.getenv('BQ_TEST_PROJECT')}.{os.getenv('BQ_TEST_DATASET')}`"

def create_metadata(add_namespace=False):
    current_folder = os.path.dirname(os.path.abspath(__file__))
    metadata_file = os.path.join(current_folder, "metadata.json")
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    components = []
    components_folder = os.path.join(current_folder, 'components')
    for component in os.listdir(components_folder):
        metadata_file = os.path.join(
            components_folder, component, "metadata.json")
        with open(metadata_file, "r") as f:
            component_metadata = json.load(f)
            if add_namespace:
                component_metadata["name"] = f'{metadata["name"]}.{component_metadata["name"]}'
            components.append(component_metadata)
        help_file = os.path.join(
            components_folder, component, "doc", "README.md")
        with open(help_file, "r") as f:
            help_text = f.read()
            component_metadata["help"] = help_text

    metadata['components'] = components
    return metadata


def create_sql_code_bq(metadata):
    procedures_code = ""
    current_folder = os.path.dirname(os.path.abspath(__file__))
    components_folder = os.path.join(current_folder, 'components')
    for component in os.listdir(components_folder):
        procedure_file = os.path.join(
            components_folder, component, "src", "procedure.sql")
        with open(procedure_file, "r") as f:
            procedure_code = f.read()
            procedures_code += "\n" + procedure_code
    procedures = [c["procedureName"] for c in metadata["components"]]

    code = f'''
DECLARE procedures ARRAY <STRING>;
DECLARE i INT64 DEFAULT 0;

CREATE TABLE IF NOT EXISTS {WORKFLOWS_TEMP_PLACEHOLDER}.{EXTENSIONS_TABLENAME} (
    name STRING,
    metadata STRING,
    procedures STRING
);

-- remove procedures from previous installations

SET procedures = ARRAY(
    SELECT procedures
    FROM {WORKFLOWS_TEMP_PLACEHOLDER}.{EXTENSIONS_TABLENAME}
    WHERE name = '{metadata["name"]}'
);
LOOP
    SET i = i + 1;
    IF i > ARRAY_LENGTH(procedures) THEN
        LEAVE;
    END IF;
    EXECUTE IMMEDIATE 'DROP PROCEDURE {WORKFLOWS_TEMP_PLACEHOLDER}.' || procedures[ORDINAL(i)];
END LOOP;

DELETE FROM {WORKFLOWS_TEMP_PLACEHOLDER}.{EXTENSIONS_TABLENAME}
WHERE name = '{metadata["name"]}';

-- create procedures
{procedures_code}

-- add to extensions table

INSERT INTO {WORKFLOWS_TEMP_PLACEHOLDER}.{EXTENSIONS_TABLENAME} (name, metadata, procedures)
VALUES ('{metadata["name"]}', '{json.dumps(metadata)}', '{','.join(procedures)}');
    '''

    return code


def create_sql_code_sf(metadata):
    pass


def deploy_bq(metadata, destination):
    print("Deploying extension to BigQuery...")
    destination = f"`{destination}`" if destination else bq_workflows_temp
    sql_code = create_sql_code_bq(metadata)
    sql_code = sql_code.replace(
        WORKFLOWS_TEMP_PLACEHOLDER,
        destination
    )
    if verbose:
        print(sql_code)
    query_job = bq_client.query(sql_code)
    query_job.result()
    print("Extension correctly deployed to BigQuery.")


def deploy_sf(metadata, destination):
    pass


def deploy(destination):
    metadata = create_metadata(True)
    if metadata["provider"] == "bigquery":
        deploy_bq(metadata, destination)
    else:
        deploy_sf(metadata, destination)


def _upload_test_table_bq(filename, component):
    dataset_id = os.getenv('BQ_TEST_DATASET')
    table_id = f"{component['name']}_{os.path.basename(filename).split('.')[0]}"

    dataset_ref = bq_client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)
    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    job_config.autodetect = True
    job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE

    with open(filename, "rb") as source_file:
        job = bq_client.load_table_from_file(
            source_file,
            table_ref,
            job_config=job_config,
        )
    try:
        job.result()
    except Exception as e:
        pass


def _get_test_results_bq(metadata, component):
    results = {}
    if component:
        components = [c for c in metadata["components"] if c["name"] == component]
    else:
        components = metadata["components"]
    current_folder = os.path.dirname(os.path.abspath(__file__))
    components_folder = os.path.join(current_folder, 'components')
    for component in components:
        component_folder = os.path.join(components_folder, component["name"])
        test_folder = os.path.join(component_folder, "test")
        # upload test tables
        for filename in os.listdir(test_folder):
            if filename.endswith(".ndjson"):
                _upload_test_table_bq(os.path.join(test_folder, filename), component)
        # run tests
        test_configuration_file = os.path.join(test_folder, "test.json")
        with open(test_configuration_file, "r") as f:
            test_configurations = json.load(f)
        tables = {}
        param_values = []
        component_results = {}
        for test_configuration in test_configurations:
            test_id = test_configuration["id"]
            component_results[test_id] = {}
            for inputparam in component["inputs"]:
                if inputparam["type"] == "table":
                    tablename = f"'{bq_workflows_temp}.{component['name']}_{test_configuration['inputs'][inputparam['name']]}'"
                    param_values.append(tablename)
                elif inputparam["type"] == "string":
                    param_values.append(f"'{test_configuration['inputs'][inputparam['name']]}'")
                else:
                    param_values.append(test_configuration["inputs"][inputparam["name"]])
            for outputparam in component["outputs"]:
                tablename = f"{bq_workflows_temp}._table_{uuid4().hex}"
                param_values.append(f"'{tablename}'")
                tables[outputparam["name"]] = tablename
            param_values.append(False) # dry run
            query = f"CALL {bq_workflows_temp}.{component['procedureName']}({','.join([str(p) for p in param_values])});"
            if verbose:
                print(query)
            query_job = bq_client.query(query)
            result = query_job.result()
            for output in component["outputs"]:
                query = f"SELECT * FROM {tables[output['name']]}"
                query_job = bq_client.query(query)
                result = query_job.result()
                rows = [{k: v for k,v in row.items()} for row in result]
                component_results[test_id][output["name"]] = rows
        results[component['name']] = component_results
    return results


def test_bq(metadata, component):
    print("Testing extension...")
    deploy_bq(metadata, None)
    current_folder = os.path.dirname(os.path.abspath(__file__))
    components_folder = os.path.join(current_folder, 'components')
    results = _get_test_results_bq(metadata, component)
    for component in metadata["components"]:
        component_folder = os.path.join(components_folder, component["name"])
        for test_id, outputs in results[component["name"]].items():
            test_folder = os.path.join(component_folder, "test", "fixtures")
            test_filename = os.path.join(test_folder, f"{test_id}.json")
            with open(test_filename, "r") as f:
                expected_rows = json.load(f)
                for output_name, output in outputs.items():
                    print(output)
                    print(expected_rows[output_name])
                    assert \
                        sorted(expected_rows[output_name], key=json.dumps) == sorted(output, key=json.dumps), \
                        f"Test '{test_id}' failed for component {component['name']}."

    print("Extension correctly tested.")


def test_sf(metadata, component):
    pass


def test(component):
    metadata = create_metadata(False)
    if metadata["provider"] == "bigquery":
        test_bq(metadata, component)
    else:
        test_sf(metadata, component)


def capture_bq(metadata, component):
    print("Capturing fixtures... ")
    current_folder = os.path.dirname(os.path.abspath(__file__))
    components_folder = os.path.join(current_folder, 'components')
    deploy_bq(metadata, None)
    results = _get_test_results_bq(metadata, component)
    for component in metadata["components"]:
        component_folder = os.path.join(components_folder, component["name"])
        for test_id, outputs in results[component["name"]].items():
            test_folder = os.path.join(component_folder, "test", "fixtures")
            os.makedirs(test_folder, exist_ok=True)
            test_filename = os.path.join(test_folder, f"{test_id}.json")
            with open(test_filename, "w") as f:
                f.write(json.dumps(outputs, indent=2))
    print("Fixtures correctly captured.")


def capture_sf(metadata, component):
    pass


def capture(component):
    metadata = create_metadata(False)
    if metadata["provider"] == "bigquery":
        capture_bq(metadata, component)
    else:
        capture_sf(metadata, component)


def package():
    print("Packaging extension...")
    current_folder = os.path.dirname(os.path.abspath(__file__))
    metadata = create_metadata(True)
    sql_code = create_sql_code_bq(
        metadata) if metadata["provider"] == "bigquery" else create_sql_code_sf(metadata)
    package_filename = os.path.join(current_folder, 'extension.zip')
    with zipfile.ZipFile(package_filename, "w") as z:
        with z.open("metadata.json", "w") as f:
            f.write(json.dumps(metadata, indent=2).encode("utf-8"))
        with z.open("extension.sql", "w") as f:
            f.write(sql_code.encode("utf-8"))
    print(f"Extension correctly packaged to '{package_filename}' file.")


parser = argparse.ArgumentParser()
parser.add_argument('action', nargs=1, type=str, choices=[
                    'package', 'deploy', 'test', 'capture'])
parser.add_argument('--component', type=str)
parser.add_argument('--destination', type=str, required=("deploy" in argv))
parser.add_argument('-v', help='Verbose mode', action='store_true')
args = parser.parse_args()
action = args.action[0]
verbose = args.v
if args.component and action not in ['capture', 'test']:
    parser.error("Component can only be used with 'capture' and 'test' actions")
if args.destination and action not in ['deploy']:
    parser.error("Destination can only be used with 'deploy' action")

if action in ['deploy', 'test', 'capture']:
    bq_client = bigquery.Client()

if action == 'package':
    package()
elif action == 'deploy':
    deploy(args.destination)
elif action == 'test':
    test(args.component)
elif action == 'capture':
    capture(args.component)
