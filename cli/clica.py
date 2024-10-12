#! python3
import sys
from pathlib import Path

import click
import pandas as pd
import requests
import yaml
from rich import print

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
        "Config file not found. Running the init command to create it but you need to fill it."
    )
    init_config()

try:
    API_URL = cli_cfg["rest"]["url"]
except KeyError:
    print(
        "Missing API URL. Check that the config.yaml file is properly set or trigger init command to create a new one."
    )
    sys.exit(1)

try:
    EMAIL = cli_cfg["credentials"]["email"]
    PASSWORD = cli_cfg["credentials"]["password"]
except KeyError:
    print(
        "Missing credentials in the config file. You need to pass them to the CLI in this case."
    )

VERIFY_CERTIFICATE = cli_cfg["rest"].get("verify_certificate", True)

def check_auth():
    if Path(".tmp.yaml").exists():
        click.echo("Found auth data. Trying them")
        with open(".tmp.yaml", "r") as yfile:
            auth_data = yaml.safe_load(yfile)
            return auth_data["token"]
    else:
        click.echo("Could not find authentication data.")


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
        print("trying credentials from the config file")
        if EMAIL and PASSWORD:
            data = {"username": EMAIL, "password": PASSWORD}
        else:
            print("Could not find any usable credentials.")
            sys.exit(1)
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, data, headers, verify=VERIFY_CERTIFICATE)
    print(res.status_code)
    if res.status_code == 200:
        with open(".tmp.yaml", "w") as yfile:
            yaml.safe_dump(res.json(), yfile)
            print("Looks good, you can move to other commands.")
    else:
        print(
            "Check your credentials again. You can set them on the config file or on the command line."
        )
        print(res.json())


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
    GLOBAL_FOLDER_ID, res = _get_folders()
    print("GLOBAL_FOLDER_ID: ", GLOBAL_FOLDER_ID)
    print(res)


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
            res = requests.post(url, json=data, headers=headers, verify=VERIFY_CERTIFICATE)
            if res.status_code != 201:
                click.echo("❌ something went wrong")
                print(res.json())
            else:
                print(f"✅ {name} created")


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
            res = requests.post(url, json=data, headers=headers, verify=VERIFY_CERTIFICATE)
            if res.status_code != 201:
                click.echo("❌ something went wrong")
                print(res.json())
            else:
                print(f"✅ {name} created")


@click.command()
@click.option(
    "--file", required=True, help="Path of the csv file with the list of evidences"
)
def evidences_templates(file):
    """Create evidences templates. Check the samples for format."""
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
            res = requests.post(url, json=data, headers=headers, verify=VERIFY_CERTIFICATE)
            if res.status_code != 201:
                click.echo("❌ something went wrong")
                print(res.json())
            else:
                print(f"✅ {row['name']} created")


@click.command()
@click.option("--file", required=True, help="Path to the attachment to upload")
@click.option("--name", required=True, help="Name of the evidence")
def upload_evidence(file, name):
    """Upload attachment as evidence"""

    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/evidences/"
    res = requests.get(url, headers=headers, params={"name": name}, verify=VERIFY_CERTIFICATE)
    data = res.json()
    if res.status_code != 200:
        print(data)
        print(f"Error: check credentials or filename.")
        return
    if not data["results"]:
        print(f"Error: No evidence found with name '{name}'")
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
    print(res)
    print(res.text)


cli.add_command(get_folders)
cli.add_command(auth)
cli.add_command(import_assets)
cli.add_command(import_controls)
cli.add_command(evidences_templates)
cli.add_command(init_config)
cli.add_command(upload_evidence)
if __name__ == "__main__":
    cli()
