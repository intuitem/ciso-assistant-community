from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

import requests
import yaml
import json
from rich import print as rprint

import sys

from pathlib import Path

cli_cfg = dict()
auth_data = dict()

API_URL = ""
GLOBAL_FOLDER_ID = None
TOKEN = ""
EMAIL = ""
PASSWORD = ""

CLICA_CONFG_PATH = ".clica_config.yaml"

try:
    with open(CLICA_CONFG_PATH, "r") as yfile:
        cli_cfg = yaml.safe_load(yfile)
except FileNotFoundError:
    print(
        "Config file not found. Running the init command to create it but you need to fill it.",
        file=sys.stderr,
    )

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
        print("Could not find authentication data.")


TOKEN = check_auth()


@mcp.tool()
async def get_risk_scenarios():
    """Get risks scenarios

    Query CISO Assistant Risk Registry
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/risk-scenarios/"
    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)
    data = res.json()

    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No risk scenarios found", file=sys.stderr)
        return
    scenarios = [
        f"|{rs.get('name')}|{rs.get('description')}|{rs.get('current_level')}|{rs.get('residual_level')}|{rs.get('folder')}|"
        for rs in data["results"]
    ]
    return (
        "|name|description|current_level|residual_level|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(scenarios)
    )


@mcp.tool()
async def get_applied_controls():
    """Get applied controls

    Query CISO Assistant combined action plan
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/applied-controls/"
    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)
    data = res.json()

    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No applied controls found", file=sys.stderr)
        return
    items = [
        f"|{item.get('name')}|{item.get('description')}|{item.get('status')}|{item.get('eta')}|{item.get('folder')['str']}|"
        for item in data["results"]
    ]
    return (
        "|name|description|status|eta|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(items)
    )


@mcp.tool()
async def get_audits_progress():
    """Get the audits progress
    Query CISO Assistant compliance engine for audits progress
    """
    headers = {
        "Authorization": f"Token {TOKEN}",
    }
    # Get evidence ID by name
    url = f"{API_URL}/compliance-assessments/"
    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)
    data = res.json()

    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No audits found", file=sys.stderr)
        return
    items = [
        f"|{item.get('name')}|{item.get('framework')['str']}|{item.get('status')}|{item.get('progress')}|{item.get('folder')['str']}|"
        for item in data["results"]
    ]
    return (
        "|name|framework|status|progress|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(items)
    )


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
