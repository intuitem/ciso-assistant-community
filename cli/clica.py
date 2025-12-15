#! python3
from datetime import datetime
import sys
from pathlib import Path
import tempfile
import hashlib
import struct
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


@click.command()
@click.option(
    "--dest-dir",
    default="./db_backup",
    help="Destination directory to save backup files (default: ./db_backup)",
    type=click.Path(file_okay=False, dir_okay=True),
)
@click.option(
    "--batch-size",
    default=200,
    help="Number of files to download per batch (default: 200)",
    type=int,
)
@click.option(
    "--resume/--no-resume",
    default=True,
    help="Resume from existing manifest (default: True)",
)
def backup_full(dest_dir, batch_size, resume):
    """Create a full backup including database and attachments using streaming"""
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)

    headers = {"Authorization": f"Token {TOKEN}"}
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    manifest_file = dest_path / "backup-manifest.jsonl"
    attachments_dir = dest_path / "attachments" / "evidence-revisions"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Backup database
    rprint("[bold blue]Step 1/2: Exporting database backup...[/bold blue]")
    url = f"{API_URL}/serdes/dump-db/"
    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)

    if res.status_code != 200:
        rprint(
            f"[bold red]Error exporting database: {res.status_code}[/bold red]",
            file=sys.stderr,
        )
        rprint(res.text, file=sys.stderr)
        sys.exit(1)

    backup_file = dest_path / "backup.json.gz"
    with open(backup_file, "wb") as f:
        f.write(res.content)
    rprint(f"[green]✓ Database backup saved to {backup_file}[/green]")

    # Step 2: Backup attachments using streaming approach
    rprint("[bold blue]Step 2/2: Backing up attachments...[/bold blue]")

    # Load existing manifest if resuming
    existing_manifest = {}
    if resume and manifest_file.exists():
        rprint("[dim]Loading existing manifest for resume...[/dim]")
        with open(manifest_file, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("downloaded"):
                        existing_manifest[entry["id"]] = entry
        rprint(f"[dim]Found {len(existing_manifest)} already downloaded files[/dim]")

    # Fetch all attachment metadata from API (paginated)
    rprint("[dim]Fetching attachment metadata from server...[/dim]")
    all_metadata = []
    url = f"{API_URL}/serdes/attachment-metadata/"

    while url:
        res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)

        if res.status_code != 200:
            rprint(
                f"[bold red]Error fetching metadata: {res.status_code}[/bold red]",
                file=sys.stderr,
            )
            rprint(res.text, file=sys.stderr)
            sys.exit(1)

        data = res.json()
        all_metadata.extend(data["results"])
        url = data.get("next")
        if url and not url.startswith("http"):
            # Convert relative URL to absolute
            url = f"{API_URL}/serdes/attachment-metadata/{url}"

    rprint(f"[cyan]Found {len(all_metadata)} total attachments[/cyan]")

    # Determine which files need to be downloaded
    to_download = []
    for meta in all_metadata:
        revision_id = meta["id"]
        file_hash = meta["attachment_hash"]

        # Skip if already downloaded with matching hash
        if revision_id in existing_manifest:
            if existing_manifest[revision_id].get("hash") == file_hash:
                continue

        to_download.append(meta)

    if not to_download:
        rprint("[green]✓ All attachments already downloaded[/green]")
    else:
        rprint(
            f"[cyan]Downloading {len(to_download)} attachments in batches of {batch_size}...[/cyan]"
        )

        # Download in batches
        total_downloaded = 0
        total_bytes = 0

        for i in range(0, len(to_download), batch_size):
            batch = to_download[i : i + batch_size]
            batch_ids = [meta["id"] for meta in batch]

            rprint(
                f"[dim]Downloading batch {i // batch_size + 1}/{(len(to_download) + batch_size - 1) // batch_size}...[/dim]"
            )

            # Request batch download
            url = f"{API_URL}/serdes/batch-download-attachments/"
            res = requests.post(
                url,
                headers=headers,
                json={"revision_ids": batch_ids},
                verify=VERIFY_CERTIFICATE,
                stream=True,
            )

            if res.status_code != 200:
                rprint(
                    f"[bold red]Error downloading batch: {res.status_code}[/bold red]",
                    file=sys.stderr,
                )
                rprint(res.text, file=sys.stderr)
                continue

            # Parse streaming response
            buffer = b""
            for chunk in res.iter_content(chunk_size=10240 * 1024):  # NOTE: 10MB chunks
                buffer += chunk

                while len(buffer) >= 4:
                    # Read 4-byte length prefix
                    total_size = struct.unpack(">I", buffer[:4])[0]

                    if len(buffer) < 4 + total_size:
                        # Not enough data yet
                        break

                    # Extract block
                    block_data = buffer[4 : 4 + total_size]
                    buffer = buffer[4 + total_size :]

                    # Parse JSON header (try up to 1KB)
                    header = None
                    header_end = 0
                    for j in range(1, min(1024, len(block_data))):
                        try:
                            header = json.loads(block_data[:j].decode("utf-8"))
                            header_end = j
                            break
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue

                    if not header:
                        rprint(
                            "[yellow]Warning: Could not parse header in block[/yellow]"
                        )
                        continue

                    file_bytes = block_data[header_end:]

                    # Save file
                    evidence_id = header["evidence_id"]
                    version = header["version"]
                    filename = header["filename"]
                    file_hash = header["hash"]

                    file_path = attachments_dir / f"{evidence_id}_v{version}_{filename}"
                    with open(file_path, "wb") as f:
                        f.write(file_bytes)

                    total_downloaded += 1
                    total_bytes += len(file_bytes)

                    # Append to manifest
                    manifest_entry = {
                        "id": header["id"],
                        "evidence_id": evidence_id,
                        "version": version,
                        "filename": filename,
                        "hash": file_hash,
                        "size": len(file_bytes),
                        "downloaded": True,
                        "timestamp": datetime.now().isoformat(),
                    }

                    with open(manifest_file, "a") as f:
                        f.write(json.dumps(manifest_entry) + "\n")

            rprint(
                f"[green]✓ Batch {i // batch_size + 1} completed ({total_downloaded} files, {total_bytes / 1024 / 1024:.1f} MB)[/green]"
            )

        rprint(
            f"[bold green]✓ Downloaded {total_downloaded} attachments ({total_bytes / 1024 / 1024:.1f} MB total)[/bold green]"
        )

    rprint("[bold green]Full backup completed successfully![/bold green]")
    rprint(f"[dim]Location: {dest_path}[/dim]")


@click.command()
@click.option(
    "--src-dir",
    default="./db_backup",
    help="Source directory containing backup files (default: ./db_backup)",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--verify-hashes/--no-verify-hashes",
    default=True,
    help="Verify file hashes before upload (default: True)",
)
def restore_full(src_dir, verify_hashes):
    """Restore a full backup using atomic combo endpoint (avoids token invalidation)"""
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)

    headers = {"Authorization": f"Token {TOKEN}"}
    src_path = Path(src_dir)

    # Check for required backup file
    backup_file = src_path / "backup.json.gz"
    if not backup_file.exists():
        rprint(
            f"[bold red]Error: backup.json.gz not found in {src_dir}[/bold red]",
            file=sys.stderr,
        )
        sys.exit(1)

    manifest_file = src_path / "backup-manifest.jsonl"
    attachments_dir = src_path / "attachments" / "evidence-revisions"

    rprint("[bold blue]Starting atomic restore (database + attachments)...[/bold blue]")

    # Prepare attachments data if available
    attachments_data = None
    if attachments_dir.exists() and manifest_file.exists():
        rprint("[dim]Loading manifest and preparing attachments...[/dim]")

        # Load manifest
        manifest = {}
        with open(manifest_file, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    manifest[entry["id"]] = entry

        # Scan attachments directory and match with manifest

        to_upload = []
        for manifest_id, entry in manifest.items():
            evidence_id = entry["evidence_id"]
            version = entry["version"]
            filename = entry["filename"]
            expected_hash = entry.get("hash")

            file_path = attachments_dir / f"{evidence_id}_v{version}_{filename}"

            if not file_path.exists():
                continue

            # Verify hash if requested
            if verify_hashes and expected_hash:
                hash_obj = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(10240 * 1024), b""):
                        hash_obj.update(chunk)
                actual_hash = hash_obj.hexdigest()

                if actual_hash != expected_hash:
                    rprint(
                        f"[yellow]Warning: Hash mismatch for {filename}, skipping[/yellow]"
                    )
                    continue

            to_upload.append(
                {
                    "id": manifest_id,
                    "evidence_id": evidence_id,
                    "version": version,
                    "filename": filename,
                    "hash": expected_hash or "",
                    "path": file_path,
                }
            )

        if to_upload:
            rprint(f"[cyan]Found {len(to_upload)} attachments to restore[/cyan]")

            # Build streaming data for ALL attachments
            body_parts = []
            for file_info in to_upload:
                # Read file
                with open(file_info["path"], "rb") as f:
                    file_bytes = f.read()

                # Build JSON header
                header = {
                    "id": file_info["id"],
                    "evidence_id": file_info["evidence_id"],
                    "version": file_info["version"],
                    "filename": file_info["filename"],
                    "hash": file_info["hash"],
                    "size": len(file_bytes),
                }
                header_bytes = json.dumps(header).encode("utf-8")

                # Calculate total size: header + file
                total_size = len(header_bytes) + len(file_bytes)

                # Add: [4-byte length][header][file]
                body_parts.append(struct.pack(">I", total_size))
                body_parts.append(header_bytes)
                body_parts.append(file_bytes)

            # Create temporary file for attachments binary data

            temp_attachments = tempfile.NamedTemporaryFile(suffix=".dat", delete=False)
            temp_attachments.write(b"".join(body_parts))
            temp_attachments.close()
            attachments_data = temp_attachments.name

            rprint(
                f"[dim]Prepared {len(to_upload)} attachments for upload ({sum(len(p) for p in body_parts) / 1024 / 1024:.1f} MB)[/dim]"
            )

    # Send SINGLE request with both database and attachments
    url = f"{API_URL}/serdes/full-restore/"

    files = {
        "backup": ("backup.json.gz", open(backup_file, "rb"), "application/gzip"),
    }

    if attachments_data:
        files["attachments"] = (
            "attachments.dat",
            open(attachments_data, "rb"),
            "application/octet-stream",
        )
        rprint(
            "[dim]Sending restore request (database + attachments in single request)...[/dim]"
        )
    else:
        rprint("[dim]Sending restore request (database only)...[/dim]")

    try:
        res = requests.post(
            url,
            headers=headers,
            files=files,
            verify=VERIFY_CERTIFICATE,
        )
    finally:
        # Close file handles
        for file_tuple in files.values():
            file_tuple[1].close()

        # Clean up temp file
        if attachments_data:
            Path(attachments_data).unlink()

    if res.status_code != 200:
        rprint(
            f"[bold red]Error during restore: {res.status_code}[/bold red]",
            file=sys.stderr,
        )
        try:
            error_data = res.json()
            rprint(f"[red]{error_data}[/red]", file=sys.stderr)
        except:
            rprint(res.text, file=sys.stderr)
        sys.exit(1)

    result = res.json()

    rprint(f"[green]✓ Database restored successfully[/green]")

    if "attachments_restored" in result:
        restored = result["attachments_restored"]
        processed = result.get("attachments_processed", restored)
        skipped = result.get("attachments_skipped", 0)
        rprint(
            f"[green]✓ Attachments restored: {restored} restored, {skipped} skipped, {processed} total processed[/green]"
        )

        if result.get("attachment_errors_count"):
            rprint(
                f"[yellow]Warning: {result['attachment_errors_count']} errors encountered[/yellow]"
            )

    if result.get("status") == "partial_success":
        rprint("[bold yellow]Restore completed with warnings[/bold yellow]")
    else:
        rprint("[bold green]Full restore completed successfully![/bold green]")

    rprint("[dim]Note: You will need to regenerate your Personal Access Token[/dim]")


cli.add_command(get_folders)
cli.add_command(get_perimeters)
cli.add_command(import_assets)
cli.add_command(import_controls)
cli.add_command(import_evidences)
cli.add_command(upload_attachment)
cli.add_command(import_risk_assessment)
cli.add_command(get_matrices)
cli.add_command(backup_full)
cli.add_command(restore_full)
if __name__ == "__main__":
    cli()
