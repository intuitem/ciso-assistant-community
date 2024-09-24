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
USERNAME = ""
PASSWORD = ""

with open("cli_config.yaml", "r") as yfile:
    cli_cfg = yaml.safe_load(yfile)

try:
    API_URL = cli_cfg["rest"]["url"]
except KeyError:
    print("Missing API URL. Check the yaml file")
    sys.exit(1)

try:
    USERNAME = cli_cfg["credentials"]["username"]
    PASSWORD = cli_cfg["credentials"]["password"]
except KeyError:
    print(
        "Missing credentials in the config file. You need to pass them to the CLI in this case."
    )


def check_auth():
    if Path(".tmp.yaml").exists():
        click.echo("Found auth data. Trying them")
        with open(".tmp.yaml", "r") as yfile:
            auth_data = yaml.safe_load(yfile)
            return auth_data["token"]
    else:
        click.echo("Could not find authentication data.")


TOKEN = check_auth()


@click.group()
def cli():
    """CLICA is the CLI tool to interact with CISO Assistant REST API."""
    pass


@click.command()
@click.option("--email", required=False)
@click.option("--password", required=False)
def auth(email, password):
    """Authenticate to get a temp token. Pass the email and password or set them on the config file"""
    url = f"{API_URL}/iam/login/"
    if email and password:
        data = {"username": email, "password": password}
    else:
        print("trying credentials from the config file")
        if USERNAME and PASSWORD:
            data = {"username": USERNAME, "password": PASSWORD}
        else:
            print("Could not find any usable credentials.")
            sys.exit(1)
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, data, headers)
    print(res.status_code)
    if res.status_code == 200:
        with open(".tmp.yaml", "w") as yfile:
            yaml.safe_dump(res.json(), yfile)
            print("Looks good, you can move to other commands.")
    else:
        print(
            "Check your credentials again. You can set them on the config file or on the command line."
        )


def _get_folders():
    url = f"{API_URL}/folders/"
    headers = {"Authorization": f"Token {TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        output = res.json()
        for folder in output["results"]:
            if folder["content_type"] == "GLOBAL":
                GLOBAL_FOLDER_ID = folder["id"]
                return GLOBAL_FOLDER_ID


@click.command()
def get_folders():
    """Get folders"""
    GLOBAL_FOLDER_ID = _get_folders()
    print("GLOBAL_FOLDER_ID: ", GLOBAL_FOLDER_ID)


@click.command()
@click.option("--ifile", required=True, help="Path of the csv file with assets")
def import_assets(ifile):
    """import assets from a csv"""
    GLOBAL_FOLDER_ID = _get_folders()
    df = pd.read_csv(ifile)
    url = f"{API_URL}/assets/"
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
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
        res = requests.post(url, json=data, headers=headers)
        if res.status_code != 201:
            click.echo("❌ something went wrong")
            print(res.json())
        else:
            print(f"✅ {name} created")


@click.command()
@click.option(
    "--ifile", required=True, help="Path of the csv file with applied controls"
)
def import_controls(ifile):
    """import applied controls"""
    df = pd.read_csv(ifile)
    GLOBAL_FOLDER_ID = _get_folders()
    url = f"{API_URL}/applied-controls/"
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    print(GLOBAL_FOLDER_ID)
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
        res = requests.post(url, json=data, headers=headers)
        if res.status_code != 201:
            click.echo("❌ something went wrong")
            print(res.json())
        else:
            print(f"✅ {name} created")


# Add commands to the CLI group
cli.add_command(get_folders)
cli.add_command(auth)
cli.add_command(import_assets)
cli.add_command(import_controls)

if __name__ == "__main__":
    cli()
