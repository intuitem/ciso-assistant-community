#! python3
import sys
from pathlib import Path

import click
import pandas as pd
import requests
import yaml
import json
from rich import print as rprint

from icecream import ic

cli_cfg = dict()
auth_data = dict()

API_URL = ""
GLOBAL_FOLDER_ID = None
TOKEN = ""
EMAIL = ""
PASSWORD = ""

CLICA_CONFG_PATH = ".clica_config.yaml"


@click.group()
def cli():
    """CLICA is the CLI tool to interact with CISO Assistant REST API."""
    pass


@click.command()
def init_config():
    """Create/Reset the config file."""
    template_data = {
        "rest": {
            "url": "https://localhost:8443/api",
            "verify_certificate": True,
        },
        "credentials": {"email": "user@company.org", "password": ""},
    }
    if click.confirm(
        f"This will create {CLICA_CONFG_PATH} for you to fill and will RESET any exisiting one. Do you wish to continue?"
    ):
        with open(CLICA_CONFG_PATH, "w") as yfile:
            yaml.safe_dump(
                template_data, yfile, default_flow_style=False, sort_keys=False
            )
            print(
                f"Config file is available at {CLICA_CONFG_PATH}. Please update it with your credentials."
            )


try:
    with open(CLICA_CONFG_PATH, "r") as yfile:
        cli_cfg = yaml.safe_load(yfile)
except FileNotFoundError:
    print(
        "Config file not found. Running the init command to create it but you need to fill it.",
        file=sys.stderr,
    )
    init_config()

try:
    API_URL = cli_cfg["rest"]["url"]
except KeyError:
    print(
        "Missing API URL. Check that the config.yaml file is properly set or trigger init command to create a new one.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    EMAIL = cli_cfg["credentials"]["email"]
    PASSWORD = cli_cfg["credentials"]["password"]
except KeyError:
    print(
        "Missing credentials in the config file. You need to pass them to the CLI in this case.",
        file=sys.stderr,
    )

VERIFY_CERTIFICATE = cli_cfg["rest"].get("verify_certificate", True)


def check_auth():
    if Path(".tmp.yaml").exists():
        with open(".tmp.yaml", "r") as yfile:
            auth_data = yaml.safe_load(yfile)
            return auth_data["token"]
    else:
        click.echo("Could not find authentication data.", err=True)


TOKEN = check_auth()


@click.command()
@click.option("--email", required=False)
@click.option("--password", required=False)
def auth(email, password):
    """Authenticate to get a temp token (config file or params). Pass the email and password or set them on the config file"""
    url = f"{API_URL}/iam/login/"
    if email and password:
        data = {"username": email, "password": password}
    else:
        print("trying credentials from the config file", file=sys.stderr)
        if EMAIL and PASSWORD:
            data = {"username": EMAIL, "password": PASSWORD}
        else:
            print("Could not find any usable credentials.", file=sys.stderr)
            sys.exit(1)
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, data, headers, verify=VERIFY_CERTIFICATE)
    print(res.status_code)
    if res.status_code == 200:
        with open(".tmp.yaml", "w") as yfile:
            yaml.safe_dump(res.json(), yfile)
            print("Looks good, you can move to other commands.", file=sys.stderr)
    else:
        print(
            "Check your credentials again. You can set them on the config file or on the command line.",
            file=sys.stderr,
        )
        print(res.json())


def ids_map(model, folder=None):
    my_map = dict()
    url = f"{API_URL}/{model}/ids/"
    headers = {"Authorization": f"Token {TOKEN}"}
    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)
    if res.status_code != 200:
        print("something went wrong. check authentication.")
        sys.exit(1)
    if folder:
        my_map = res.json().get(folder)
    else:
        my_map = res.json()
    return my_map


def _get_folders():
    url = f"{API_URL}/folders/"
    headers = {"Authorization": f"Token {TOKEN}"}
    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)
    if res.status_code == 200:
        output = res.json()
        for folder in output["results"]:
            if folder["content_type"] == "GLOBAL":
                GLOBAL_FOLDER_ID = folder["id"]
                return GLOBAL_FOLDER_ID, output.get("results")


@click.command()
def get_folders():
    """Get folders."""
    print(json.dumps(ids_map("folders"), ensure_ascii=False))


@click.command()
def get_perimeters():
    """getting perimeters as a json"""
    print(json.dumps(ids_map("perimeters"), ensure_ascii=False))


@click.command()
def get_matrices():
    """getting loaded matrix as a json"""
    print(json.dumps(ids_map("risk-matrices", folder="Global"), ensure_ascii=False))


def get_unique_parsed_values(df, column_name):
    unique_values = df[column_name].dropna().unique()
    parsed_values = []

    for value in unique_values:
        value_str = str(value)
        split_values = [v.strip() for v in value_str.split(",")]
        parsed_values.extend(split_values)

    return set(parsed_values)


def batch_create(model, items, folder_id):
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    output = dict()
    url = f"{API_URL}/{model}/"
    for item in items:
        data = {
            "folder": folder_id,
            "name": item,
        }
        res = requests.post(url, json=data, headers=headers)
        if res.status_code != 201:
            print("something went wrong")
            print(res.json())
        else:
            output.update({item: res.json()["id"]})
    return output


@click.command()
@click.option("--file", required=True, help="")
@click.option("--folder", required=True, help="")
@click.option("--perimeter", required=True, help="")
@click.option("--matrix", required=True, help="")
@click.option("--name", required=True, help="")
@click.option(
    "--create_all",
    required=False,
    is_flag=True,
    default=True,
    help="Create all associated objects (threats, assets)",
)
def import_risk_assessment(file, folder, perimeter, name, matrix, create_all):
    """crawl a risk assessment (see template) and create the assoicated objects"""
    df = pd.read_csv(file, delimiter=";")
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    folder_id = ids_map("folders").get(folder)
    perimeter_id = ids_map("perimeters", folder=folder).get(perimeter)
    matrix_id = ids_map("risk-matrices", folder="Global").get(matrix)

    # post to create risk assessment
    data = {
        "name": name,
        "folder": folder_id,
        "perimeter": perimeter_id,
        "risk_matrix": matrix_id,
    }
    res = requests.post(
        f"{API_URL}/risk-assessments/",
        json=data,
        headers=headers,
        verify=VERIFY_CERTIFICATE,
    )
    ra_id = None
    if res.status_code == 201:
        ra_id = res.json().get("id")
        print("ok")
    else:
        print("something went wrong.")
        print(res.json())

    if create_all:
        threats = get_unique_parsed_values(df, "threats")
        batch_create("threats", threats, folder_id)
        assets = get_unique_parsed_values(df, "assets")
        batch_create("assets", assets, folder_id)
        existing_controls = get_unique_parsed_values(df, "existing_controls")
        batch_create("applied-controls", existing_controls, folder_id)
        additional_controls = get_unique_parsed_values(df, "additional_controls")
        batch_create("applied-controls", additional_controls, folder_id)

    res = requests.get(f"{API_URL}/risk-matrices/{matrix_id}", headers=headers)
    if res.status_code == 200:
        matrix_def = res.json().get("json_definition")
        matrix_def = json.loads(matrix_def)
        # ic(matrix_def)
        impact_map = dict()
        proba_map = dict()
        # this can be factored as one map probably
        for item in matrix_def["impact"]:
            impact_map[item["name"]] = item["id"]
            if item.get("translations"):
                langs = item.get("translations")
                for lang in langs:
                    impact_map[langs[lang]["name"]] = item["id"]
        for item in matrix_def["probability"]:
            proba_map[item["name"]] = item["id"]
            if item.get("translations"):
                langs = item.get("translations")
                for lang in langs:
                    proba_map[langs[lang]["name"]] = item["id"]

        ic(impact_map)
        ic(proba_map)

    df = df.fillna("--")

    threats = ids_map("threats", folder)
    assets = ids_map("assets", folder)
    controls = ids_map("applied-controls", folder)

    for scenario in df.itertuples():
        data = {
            "ref_id": scenario.ref_id,
            "name": scenario.name,
            "risk_assessment": ra_id,
        }
        if None in [
            impact_map.get(scenario.current_impact),
            proba_map.get(scenario.current_proba),
            impact_map.get(scenario.residual_impact),
            proba_map.get(scenario.residual_proba),
        ]:
            print("Matrix doesn't match the labels used on your input file")

        if scenario.current_impact != "--":
            data.update({"current_impact": impact_map.get(scenario.current_impact)})
        if scenario.current_proba != "--":
            data.update({"current_proba": proba_map.get(scenario.current_proba)})

        if scenario.residual_impact != "--":
            data.update({"residual_impact": impact_map.get(scenario.residual_impact)})
        if scenario.residual_proba != "--":
            data.update({"residual_proba": proba_map.get(scenario.residual_proba)})

        if scenario.existing_controls != "--":
            items = str(scenario.existing_controls).split(",")
            data.update(
                {"existing_applied_controls": [controls[item] for item in items]}
            )

        if scenario.additional_controls != "--":
            items = str(scenario.additional_controls).split(",")
            data.update({"applied_controls": [controls[item] for item in items]})

        if scenario.assets != "--":
            items = str(scenario.assets).split(",")
            data.update({"assets": [assets[item] for item in items]})

        if scenario.threats != "--":
            items = str(scenario.threats).split(",")
            data.update({"threats": [threats[item] for item in items]})

        res = requests.post(f"{API_URL}/risk-scenarios/", json=data, headers=headers)
        if res.status_code != 201:
            rprint(res.json())
            rprint(data)


@click.command()
@click.option("--file", required=True, help="Path of the csv file with assets")
def import_assets(file):
    """import assets from a csv. Check the samples for format."""
    GLOBAL_FOLDER_ID, _ = _get_folders()
    df = pd.read_csv(file)
    url = f"{API_URL}/assets/"
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    if click.confirm(f"I'm about to create {len(df)} assets. Are you sure?"):
        for _, row in df.iterrows():
            asset_type = "SP"
            name = row["name"]
            if row["type"].lower() == "primary":
                asset_type = "PR"
            else:
                asset_type = "SP"

            data = {
                "name": name,
                "folder": GLOBAL_FOLDER_ID,
                "type": asset_type,
            }
            res = requests.post(
                url, json=data, headers=headers, verify=VERIFY_CERTIFICATE
            )
            if res.status_code != 201:
                click.echo("❌ something went wrong", err=True)
                rprint(res.json())
            else:
                rprint(f"✅ {name} created", file=sys.stderr)


@click.command()
@click.option(
    "--file", required=True, help="Path of the csv file with applied controls"
)
def import_controls(file):
    """import applied controls. Check the samples for format."""
    df = pd.read_csv(file)
    GLOBAL_FOLDER_ID, _ = _get_folders()
    url = f"{API_URL}/applied-controls/"
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    if click.confirm(f"I'm about to create {len(df)} applied controls. Are you sure?"):
        for _, row in df.iterrows():
            name = row["name"]
            description = row["description"]
            csf_function = row["csf_function"]
            category = row["category"]

            data = {
                "name": name,
                "folder": GLOBAL_FOLDER_ID,
                "description": description,
                "csf_function": csf_function.lower(),
                "category": category.lower(),
            }
            res = requests.post(
                url, json=data, headers=headers, verify=VERIFY_CERTIFICATE
            )
            if res.status_code != 201:
                click.echo("❌ something went wrong", err=True)
                rprint(res.json())
            else:
                rprint(f"✅ {name} created", file=sys.stderr)


@click.command()
@click.option(
    "--file", required=True, help="Path of the csv file with the list of evidences"
)
def import_evidences(file):
    """Import evidences. Check the samples for format."""
    df = pd.read_csv(file)
    GLOBAL_FOLDER_ID, _ = _get_folders()

    url = f"{API_URL}/evidences/"
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    if click.confirm(f"I'm about to create {len(df)} evidences. Are you sure?"):
        for _, row in df.iterrows():
            data = {
                "name": row["name"],
                "description": row["description"],
                "folder": GLOBAL_FOLDER_ID,
                "applied_controls": [],
                "requirement_assessments": [],
            }
            res = requests.post(
                url, json=data, headers=headers, verify=VERIFY_CERTIFICATE
            )
            if res.status_code != 201:
                click.echo("❌ something went wrong", err=True)
                rprint(res.json())
            else:
                rprint(f"✅ {row['name']} created", file=sys.stderr)


@click.command()
@click.option("--file", required=True, help="Path to the attachment to upload")
@click.option("--name", required=True, help="Name of the evidence")
def upload_attachment(file, name):
    """Upload attachment as evidence"""

    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/evidences/"
    res = requests.get(
        url, headers=headers, params={"name": name}, verify=VERIFY_CERTIFICATE
    )
    data = res.json()
    rprint(data)
    if res.status_code != 200:
        rprint(data)
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No evidence found with name '{name}'", file=sys.stderr)
        return

    evidence_id = data["results"][0]["id"]

    # Upload file
    url = f"{API_URL}/evidences/{evidence_id}/upload/"
    filename = Path(file).name
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Disposition": f'attachment;filename="{filename}"',
    }
    with open(file, "rb") as f:
        res = requests.post(url, headers=headers, data=f, verify=VERIFY_CERTIFICATE)
    rprint(res)
    rprint(res.text)


cli.add_command(get_folders)
cli.add_command(get_perimeters)
cli.add_command(auth)
cli.add_command(import_assets)
cli.add_command(import_controls)
cli.add_command(import_evidences)
cli.add_command(init_config)
cli.add_command(upload_attachment)
cli.add_command(import_risk_assessment)
cli.add_command(get_matrices)
if __name__ == "__main__":
    cli()
