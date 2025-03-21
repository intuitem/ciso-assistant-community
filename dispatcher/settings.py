import sys
import os
from pathlib import Path

import click
import yaml

from loguru import logger

CONSUMER_CONFG_PATH = ".consumer_config.yaml"

DEBUG = os.getenv("DEBUG", False)

API_URL = os.getenv("API_URL", "https://localhost:8443")
GLOBAL_FOLDER_ID = os.getenv("GLOBAL_FOLDER_ID", "")
USER_EMAIL = os.getenv("USER_EMAIL", "user@company.org")
USER_PASSWORD = os.getenv("USER_PASSWORD", "")
TOKEN = os.getenv("TOKEN", "")

ERRORS_TOPIC = os.getenv("ERRORS_TOPIC", "errors")

S3_URL = os.getenv("S3_URL", "http://localhost:9000")

config = dict()

VERIFY_CERTIFICATE = (
    os.getenv(
        "VERIFY_CERTIFICATE", config.get("rest", {}).get("verify_certificate", "True")
    )
    == "True"
)


@click.command()
@click.option("-y", required=False, is_flag=True)
def init_config(y: bool):
    """Create/Reset the config file."""
    template_data = {
        "rest": {
            "url": API_URL,
            "verify_certificate": VERIFY_CERTIFICATE,
        },
        "credentials": {"email": USER_EMAIL, "password": USER_PASSWORD},
    }
    if y or click.confirm(
        f"This will create {CONSUMER_CONFG_PATH} for you to fill and will RESET any exisiting one. Do you wish to continue?"
    ):
        with open(CONSUMER_CONFG_PATH, "w") as yfile:
            yaml.safe_dump(
                template_data, yfile, default_flow_style=False, sort_keys=False
            )
            logger.info(
                f"Config file is available at {CONSUMER_CONFG_PATH}. Please update it with your credentials."
            )


try:
    with open(CONSUMER_CONFG_PATH, "r") as yfile:
        config = yaml.safe_load(yfile)
except FileNotFoundError:
    logger.warning(
        "Config file not found. Running the init command to create it but you need to fill it.",
        file=sys.stderr,
    )
    init_config()

try:
    API_URL = config["rest"]["url"]
except KeyError:
    logger.error(
        "Missing API URL. Check that the config.yaml file is properly set or trigger init command to create a new one.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    USER_EMAIL = config["credentials"]["email"]
    USER_PASSWORD = config["credentials"]["password"]
except KeyError:
    logger.error(
        "Missing credentials in the config file. You need to pass them to the CLI in this case.",
        file=sys.stderr,
    )


def check_auth():
    if Path(".tmp.yaml").exists():
        with open(".tmp.yaml", "r") as yfile:
            auth_data = yaml.safe_load(yfile)
            return auth_data["token"]
    else:
        click.echo("Could not find authentication data.", err=True)


TOKEN = check_auth()
