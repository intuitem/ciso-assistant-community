import sys
from pathlib import Path

import click
import yaml

API_URL = ""
GLOBAL_FOLDER_ID = None
TOKEN = ""
EMAIL = ""
PASSWORD = ""

CONSUMER_CONFG_PATH = ".consumer_config.yaml"

config = dict()


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
        config = yaml.safe_load(yfile)
except FileNotFoundError:
    print(
        "Config file not found. Running the init command to create it but you need to fill it.",
        file=sys.stderr,
    )
    init_config()

try:
    API_URL = config["rest"]["url"]
except KeyError:
    print(
        "Missing API URL. Check that the config.yaml file is properly set or trigger init command to create a new one.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    EMAIL = config["credentials"]["email"]
    PASSWORD = config["credentials"]["password"]
except KeyError:
    print(
        "Missing credentials in the config file. You need to pass them to the CLI in this case.",
        file=sys.stderr,
    )

VERIFY_CERTIFICATE = config["rest"].get("verify_certificate", True)


def check_auth():
    if Path(".tmp.yaml").exists():
        with open(".tmp.yaml", "r") as yfile:
            auth_data = yaml.safe_load(yfile)
            return auth_data["token"]
    else:
        click.echo("Could not find authentication data.", err=True)


TOKEN = check_auth()
