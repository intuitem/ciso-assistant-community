from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import requests
import json
from rich import print as rprint
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .mcp.env file
load_dotenv(".mcp.env")

# Initialize FastMCP server
mcp = FastMCP("ciso-assistant")

cli_cfg = dict()
auth_data = dict()
GLOBAL_FOLDER_ID = None

# Read TOKEN and VERIFY_CERTIFICATE from environment variables
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = os.getenv("VERIFY_CERTIFICATE", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)


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
