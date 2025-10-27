#! python3
import sys
from pathlib import Path
import shutil
import sqlite3

import click
import pandas as pd
import requests
import os
from dotenv import load_dotenv
import json
from rich import print as rprint

from icecream import ic

cli_cfg = dict()
auth_data = dict()

GLOBAL_FOLDER_ID = None

CLICA_CONFG_PATH = ".clica_config.yaml"

load_dotenv(".clica.env")


@click.group()
def cli():
    """CLICA is the CLI tool to interact with CISO Assistant REST API."""
    pass


# Read TOKEN, API_URL and VERIFY_CERTIFICATE from environment variables
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = os.getenv("VERIFY_CERTIFICATE", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)


def ids_map(model, folder=None):
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
    default=False,
    help="Create all associated objects (threats, assets)",
)
def import_risk_assessment(file, folder, perimeter, name, matrix, create_all):
    """crawl a risk assessment (see template) and create the assoicated objects"""
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
            "description": scenario.description,
            "justification": scenario.justification,
            "risk_assessment": ra_id,
            "treatment": str(scenario.treatment).lower(),
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
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)
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
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)

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


def get_dir_size(path):
    """Calculate total size of a directory in bytes."""
    total_size = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    return total_size


def format_size(bytes_size):
    """Format bytes into human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def validate_sqlite_db(db_path):
    """Validate that a file is a valid SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return len(tables) > 0
    except sqlite3.Error:
        return False


@click.command()
@click.option(
    "--source-db",
    default="../backend/db/ciso-assistant.sqlite3",
    help="Path to source SQLite database (default: ../backend/db/ciso-assistant.sqlite3)",
)
@click.option(
    "--dest-db",
    required=True,
    help="Path to destination SQLite database",
)
@click.option(
    "--source-attachments",
    default="../backend/db/attachments",
    help="Path to source attachments directory (default: ../backend/db/attachments)",
)
@click.option(
    "--dest-attachments",
    required=True,
    help="Path to destination attachments directory",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite destination files if they exist",
)
def clone_instance(source_db, dest_db, source_attachments, dest_attachments, force):
    """Clone a CISO Assistant instance by copying the database and evidence attachments.

    This command creates a complete copy of a CISO Assistant instance, including:
    - SQLite database file
    - Evidence attachments directory

    Example:
        clica.py clone-instance --dest-db /path/to/backup.sqlite3 --dest-attachments /path/to/backup/attachments
    """

    # Convert paths to absolute paths
    source_db = os.path.abspath(source_db)
    dest_db = os.path.abspath(dest_db)
    source_attachments = os.path.abspath(source_attachments)
    dest_attachments = os.path.abspath(dest_attachments)

    rprint("\n[bold cyan]CISO Assistant Instance Cloning[/bold cyan]")
    rprint("=" * 60)

    # Validate source database exists
    if not os.path.exists(source_db):
        rprint(
            f"[bold red]✗[/bold red] Source database not found: {source_db}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate source database is a valid SQLite database
    if not validate_sqlite_db(source_db):
        rprint(
            f"[bold red]✗[/bold red] Source file is not a valid SQLite database: {source_db}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check if destination database already exists
    if os.path.exists(dest_db) and not force:
        rprint(
            f"[bold yellow]⚠[/bold yellow] Destination database already exists: {dest_db}",
            file=sys.stderr,
        )
        if not click.confirm("Do you want to overwrite it?"):
            rprint("[bold red]✗[/bold red] Operation cancelled.", file=sys.stderr)
            sys.exit(1)

    # Check if destination attachments directory already exists
    if os.path.exists(dest_attachments) and os.listdir(dest_attachments) and not force:
        rprint(
            f"[bold yellow]⚠[/bold yellow] Destination attachments directory is not empty: {dest_attachments}",
            file=sys.stderr,
        )
        if not click.confirm(
            "Do you want to continue? (existing files may be overwritten)"
        ):
            rprint("[bold red]✗[/bold red] Operation cancelled.", file=sys.stderr)
            sys.exit(1)

    # Calculate sizes
    db_size = os.path.getsize(source_db)
    attachments_size = get_dir_size(source_attachments)
    total_size = db_size + attachments_size

    # Display summary
    rprint("\n[bold]Clone Summary:[/bold]")
    rprint(f"  Source database:     {source_db}")
    rprint(f"  Database size:       {format_size(db_size)}")
    rprint(f"  Source attachments:  {source_attachments}")
    rprint(f"  Attachments size:    {format_size(attachments_size)}")
    rprint(f"  [bold]Total size:          {format_size(total_size)}[/bold]")
    rprint(f"\n  Destination database:    {dest_db}")
    rprint(f"  Destination attachments: {dest_attachments}")

    # Final confirmation
    if not click.confirm("\n[bold]Proceed with cloning?[/bold]"):
        rprint("[bold red]✗[/bold red] Operation cancelled.", file=sys.stderr)
        sys.exit(1)

    rprint("\n[bold cyan]Starting clone operation...[/bold cyan]\n")

    try:
        # Create destination directory for database if it doesn't exist
        dest_db_dir = os.path.dirname(dest_db)
        if dest_db_dir and not os.path.exists(dest_db_dir):
            os.makedirs(dest_db_dir, exist_ok=True)
            rprint(f"[bold green]✓[/bold green] Created directory: {dest_db_dir}")

        # Copy database
        rprint(f"[bold]Copying database...[/bold]")
        shutil.copy2(source_db, dest_db)
        rprint(
            f"[bold green]✓[/bold green] Database copied successfully ({format_size(db_size)})"
        )

        # Verify copied database
        if not validate_sqlite_db(dest_db):
            rprint(
                f"[bold red]✗[/bold red] Copied database validation failed!",
                file=sys.stderr,
            )
            sys.exit(1)

        # Copy attachments directory
        if os.path.exists(source_attachments):
            rprint(f"\n[bold]Copying attachments directory...[/bold]")

            # Count files for progress
            file_count = sum(
                [len(files) for _, _, files in os.walk(source_attachments)]
            )

            if file_count > 0:
                if os.path.exists(dest_attachments):
                    # If destination exists, copy contents
                    for item in os.listdir(source_attachments):
                        source_item = os.path.join(source_attachments, item)
                        dest_item = os.path.join(dest_attachments, item)
                        if os.path.isdir(source_item):
                            if os.path.exists(dest_item):
                                shutil.rmtree(dest_item)
                            shutil.copytree(source_item, dest_item)
                        else:
                            shutil.copy2(source_item, dest_item)
                else:
                    # If destination doesn't exist, copy entire directory
                    shutil.copytree(source_attachments, dest_attachments)

                rprint(
                    f"[bold green]✓[/bold green] Attachments copied successfully ({file_count} files, {format_size(attachments_size)})"
                )
            else:
                rprint(
                    f"[bold yellow]⚠[/bold yellow] No attachments found in source directory"
                )
                os.makedirs(dest_attachments, exist_ok=True)
        else:
            rprint(
                f"[bold yellow]⚠[/bold yellow] Source attachments directory does not exist: {source_attachments}"
            )
            os.makedirs(dest_attachments, exist_ok=True)
            rprint(
                f"[bold green]✓[/bold green] Created empty destination attachments directory"
            )

        # Success message
        rprint("\n" + "=" * 60)
        rprint("[bold green]✓ Clone completed successfully![/bold green]")
        rprint(f"\n[bold]New instance location:[/bold]")
        rprint(f"  Database:    {dest_db}")
        rprint(f"  Attachments: {dest_attachments}")
        rprint(
            "\n[bold yellow]Note:[/bold yellow] To use the cloned instance, update your CISO Assistant"
        )
        rprint("configuration to point to the new database and attachments paths.")

    except PermissionError as e:
        rprint(f"\n[bold red]✗ Permission error:[/bold red] {e}", file=sys.stderr)
        rprint(
            "Make sure you have write permissions to the destination directory.",
            file=sys.stderr,
        )
        sys.exit(1)
    except shutil.Error as e:
        rprint(f"\n[bold red]✗ Copy error:[/bold red] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        rprint(f"\n[bold red]✗ Unexpected error:[/bold red] {e}", file=sys.stderr)
        sys.exit(1)


cli.add_command(get_folders)
cli.add_command(get_perimeters)
cli.add_command(import_assets)
cli.add_command(import_controls)
cli.add_command(import_evidences)
cli.add_command(upload_attachment)
cli.add_command(import_risk_assessment)
cli.add_command(get_matrices)
cli.add_command(clone_instance)
if __name__ == "__main__":
    cli()
