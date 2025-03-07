import sys
from pathlib import Path

import click
import os
import requests
import yaml
import json
from rich import print as rprint

from icecream import ic

from kafka import KafkaConsumer

cli_cfg = dict()
auth_data = dict()

API_URL = ""
GLOBAL_FOLDER_ID = None
TOKEN = ""
EMAIL = ""
PASSWORD = ""

CONSUMER_CONFG_PATH = ".consumer_config.yaml"


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
        f"This will create {CONSUMER_CONFG_PATH} for you to fill and will RESET any exisiting one. Do you wish to continue?"
    ):
        with open(CONSUMER_CONFG_PATH, "w") as yfile:
            yaml.safe_dump(
                template_data, yfile, default_flow_style=False, sort_keys=False
            )
            print(
                f"Config file is available at {CONSUMER_CONFG_PATH}. Please update it with your credentials."
            )


try:
    with open(CONSUMER_CONFG_PATH, "r") as yfile:
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


# # Create a consumer client
# consumer = KafkaConsumer(
#     # topic
#     "observation",
#     # consumer configs
#     bootstrap_servers=os.getenv("REDPANDA_BROKERS", "localhost:9092"),
#     group_id="my-group",
#     auto_offset_reset="earliest",
#     # value_deserializer=lambda v: v,
# )
#
# # Consume messages from a Redpanda topic
# for msg in consumer:
#     rprint(f"Consumed record. key={msg.key}, value={msg.value}")
