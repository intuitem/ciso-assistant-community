#! python3
from typing import Required
import click
import requests
import yaml
from rich import print
import sys, os
import pandas as pd

cli_cfg = dict()
auth_data = dict()

API_URL = ""
TOKEN = ""
GLOBAL_FOLDER_ID = None

with open("cli_config.yaml", "r") as yfile:
    cli_cfg = yaml.safe_load(yfile)

try:
    API_URL = cli_cfg["rest"]["url"]
except:
    print("Missing API URL. Check the yaml file")
    sys.exit(1)

with open(".tmp.yaml", "r") as yfile:
    auth_data = yaml.safe_load(yfile)

try:
    TOKEN = auth_data["token"]
except:
    print("Missing a valid token. Try the auth command.")
    sys.exit(1)


@click.group()
def cli():
    """A CLI tool to interact with CISO Assistant REST API."""
    pass


@click.command()
@click.option("--user-id", default=1, help="User ID to fetch data for.")
def get_user(user_id):
    """Get user details by user ID."""
    response = requests.get(f"{API_URL}/users/{user_id}")

    if response.status_code == 200:
        user = response.json()
        click.echo(f"Name: {user['name']}")
        click.echo(f"Username: {user['username']}")
        click.echo(f"Email: {user['email']}")
    else:
        click.echo("Failed to retrieve user.")


@click.command()
@click.option("--email", required=True)
@click.option("--password", required=True)
def auth(email, password):
    """Authenticate to get a temp token"""
    url = f"{API_URL}/iam/login/"
    data = {"username": email, "password": password}
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, data, headers)
    with open(".tmp.yaml", "w") as yfile:
        yaml.safe_dump(res.json(), yfile)


@click.command()
def get_folders():
    """Get folders"""
    url = f"{API_URL}/folders/"
    headers = {"Authorization": f"Token {TOKEN}"}
    res = requests.get(url, headers=headers)
    # TODO: should we handle pagination for this one?
    if res.status_code == 200:
        output = res.json()
        for folder in output["results"]:
            if folder["content_type"] == "GLOBAL":
                GLOBAL_FOLDER_ID = folder["id"]
                break
    print(res.json())


@click.command()
@click.option("--ifile", required=True, help="Path of the csv file with assets")
def import_assets(ifile):
    """import assets from a csv"""
    df = pd.read_csv(ifile)
    url = f"{API_URL}/assets/"
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    for id, row in df.iterrows():
        asset_type = "SP"
        name = row["name"]
        if row["type"]:
            asset_type = row["type"]

        data = {
            "name": "titi",
            "folder": "2e9fb22c-c521-4f16-839d-c16b6ed0670d",
            "type": "SP",
        }
        res = requests.post(url, data=data, headers=headers)
        if res.status_code != 200:
            click.echo("something went wrong")


# Add commands to the CLI group
cli.add_command(get_folders)
cli.add_command(auth)
cli.add_command(import_assets)

if __name__ == "__main__":
    cli()
