#! python3
from datetime import datetime
import sys
from pathlib import Path
import tempfile
import hashlib
import struct
import click
import requests
import os
from dotenv import load_dotenv
import json
from rich import print as rprint
from typing import Optional, Callable, Dict
import uuid

from icecream import ic

cli_cfg = dict()
auth_data = dict()

GLOBAL_FOLDER_ID: Optional[str] = None

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
    data = res.json()
    if folder and isinstance(data, dict):
        my_map = data.get(folder)
    else:
        my_map = data
    return my_map


def get_global_folder_id() -> Optional[str]:
    global GLOBAL_FOLDER_ID
    if GLOBAL_FOLDER_ID:
        return GLOBAL_FOLDER_ID
    url = f"{API_URL}/folders/"
    headers = {"Authorization": f"Token {TOKEN}"}

    res = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATE)
    if res.status_code == 200:
        output = res.json()
        for folder in output["results"]:
            if folder["content_type"] == "GLOBAL":
                GLOBAL_FOLDER_ID = folder["id"]
                return GLOBAL_FOLDER_ID
    else:
        print(
            f"The server didn't reply as expected: {res.status_code} {res.reason}: {res.text}",
            file=sys.stderr,
        )


@cli.command(name="get-folders")
def get_folders():
    """Get folders."""
    print(json.dumps(ids_map("folders"), ensure_ascii=False))


@cli.command(name="get-perimeters")
def get_perimeters():
    """getting perimeters as a json"""
    print(json.dumps(ids_map("perimeters"), ensure_ascii=False))


@cli.command(name="get-matrices")
def get_matrices():
    """getting loaded matrix as a json"""
    print(json.dumps(ids_map("risk-matrices", folder="Global"), ensure_ascii=False))


def is_uuid(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def flatten_mapping(mapping) -> Dict[str, str]:
    flat: Dict[str, str] = {}
    if isinstance(mapping, dict):
        for key, value in mapping.items():
            if isinstance(value, dict):
                flat.update(flatten_mapping(value))
            elif isinstance(value, str):
                flat[key] = value
    return flat


def resolve_named_id(
    model: str, name: Optional[str], *, folder: Optional[str] = None
) -> Optional[str]:
    if not name:
        return None
    if is_uuid(name):
        return name
    mapping = ids_map(model, folder=folder)
    if not isinstance(mapping, dict):
        return None
    flat = flatten_mapping(mapping)
    value = flat.get(name)
    if value:
        return value
    return None


def ensure_identifier(
    name: Optional[str],
    model: str,
    description: str,
    *,
    folder: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    if not name:
        if required:
            click.echo(f"❌ Missing required {description}.", err=True)
            sys.exit(1)
        return None
    identifier = resolve_named_id(model, name, folder=folder)
    if not identifier:
        if is_uuid(name):
            return name
        click.echo(f"❌ Unable to resolve {description} '{name}'.", err=True)
        sys.exit(1)
    return identifier


def resolve_folder_id(
    folder_name: Optional[str], *, required: bool = False
) -> Optional[str]:
    if folder_name:
        if is_uuid(folder_name):
            return folder_name
        folder_map = ids_map("folders")
        if isinstance(folder_map, dict):
            folder_id = folder_map.get(folder_name)
            if folder_id:
                return folder_id
        click.echo(f"❌ Unable to resolve folder '{folder_name}'.", err=True)
        sys.exit(1)
    if required:
        folder_id = get_global_folder_id()
        if folder_id:
            return folder_id
        click.echo(
            "❌ Unable to determine a folder. Please provide --folder.", err=True
        )
        sys.exit(1)
    return None


def upload_data_wizard_file(
    *,
    model_type: str,
    file_path: str,
    folder: Optional[str],
    perimeter: Optional[str],
    framework: Optional[str],
    matrix: Optional[str],
    requires_folder: bool,
    requires_perimeter: bool,
    requires_framework: bool,
    requires_matrix: bool,
):
    if not TOKEN:
        print(
            "No authentication token available. Please set PAT token in .clica.env.",
            file=sys.stderr,
        )
        sys.exit(1)

    folder_id = resolve_folder_id(folder, required=requires_folder)
    perimeter_id = ensure_identifier(
        perimeter, "perimeters", "perimeter", required=requires_perimeter
    )
    framework_id = ensure_identifier(
        framework, "frameworks", "framework", required=requires_framework
    )
    matrix_id = ensure_identifier(
        matrix, "risk-matrices", "matrix", required=requires_matrix
    )

    filename = Path(file_path).name
    headers = {
        "Authorization": f"Token {TOKEN}",
        "X-Model-Type": model_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if folder_id:
        headers["X-Folder-Id"] = folder_id
    if perimeter_id:
        headers["X-Perimeter-Id"] = perimeter_id
    if framework_id:
        headers["X-Framework-Id"] = framework_id
    if matrix_id:
        headers["X-Matrix-Id"] = matrix_id

    url = f"{API_URL}/data-wizard/load-file/"
    with open(file_path, "rb") as payload:
        response = requests.post(
            url, headers=headers, data=payload.read(), verify=VERIFY_CERTIFICATE
        )
    try:
        body = response.json()
        pretty_body = json.dumps(body, indent=2)
    except Exception:
        body = None
        pretty_body = response.text

    rprint(f"{response.status_code} {response.reason} {response.url}")
    rprint(pretty_body)
    if body and response.status_code >= 400:
        sys.exit(1)


DATA_WIZARD_COMMANDS = [
    {
        "command": "import_assets",
        "model_type": "Asset",
        "help": "Import assets using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_applied_controls",
        "model_type": "AppliedControl",
        "help": "Import applied controls using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_evidences",
        "model_type": "Evidence",
        "help": "Import evidences using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_users",
        "model_type": "User",
        "help": "Import users using the Data Wizard backend.",
        "requires_folder": False,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_folders",
        "model_type": "Folder",
        "help": "Import folders using the Data Wizard backend.",
        "requires_folder": False,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_perimeters",
        "model_type": "Perimeter",
        "help": "Import perimeters using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_compliance_assessments",
        "model_type": "ComplianceAssessment",
        "help": "Import compliance assessments using the Data Wizard backend.",
        "requires_folder": False,
        "requires_perimeter": True,
        "requires_framework": True,
        "requires_matrix": False,
    },
    {
        "command": "import_findings_assessments",
        "model_type": "FindingsAssessment",
        "help": "Import findings assessments using the Data Wizard backend.",
        "requires_folder": False,
        "requires_perimeter": True,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_risk_assessment",
        "model_type": "RiskAssessment",
        "help": "Import risk assessments using the Data Wizard backend.",
        "requires_folder": False,
        "requires_perimeter": True,
        "requires_framework": False,
        "requires_matrix": True,
    },
    {
        "command": "import_elementary_actions",
        "model_type": "ElementaryAction",
        "help": "Import elementary actions using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_reference_controls",
        "model_type": "ReferenceControl",
        "help": "Import reference controls using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_threats",
        "model_type": "Threat",
        "help": "Import threats using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_processings",
        "model_type": "Processing",
        "help": "Import processings using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_tprm",
        "model_type": "TPRM",
        "help": "Import third-party records using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": False,
    },
    {
        "command": "import_ebios_rm_study_arm",
        "model_type": "EbiosRMStudyARM",
        "help": "Import EBIOS RM ARM studies using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": True,
    },
    {
        "command": "import_ebios_rm_study",
        "model_type": "EbiosRMStudyExcel",
        "help": "Import EBIOS RM Excel studies using the Data Wizard backend.",
        "requires_folder": True,
        "requires_perimeter": False,
        "requires_framework": False,
        "requires_matrix": True,
    },
]


def register_data_wizard_command(config: Dict[str, object]) -> None:
    command_name = str(config["command"])
    cli_name = command_name.replace("_", "-")
    model_type = str(config["model_type"])
    help_text = str(config["help"])
    requires_folder = bool(config.get("requires_folder", False))
    requires_perimeter = bool(config.get("requires_perimeter", False))
    requires_framework = bool(config.get("requires_framework", False))
    requires_matrix = bool(config.get("requires_matrix", False))
    show_folder_option = config.get(
        "show_folder_option",
        model_type
        not in {
            "ComplianceAssessment",
            "FindingsAssessment",
            "RiskAssessment",
            "User",
            "Folder",
        },
    )
    show_perimeter_option = config.get("show_perimeter_option", requires_perimeter)
    show_framework_option = config.get("show_framework_option", requires_framework)
    show_matrix_option = config.get("show_matrix_option", requires_matrix)

    @cli.command(name=cli_name, help=help_text)
    @click.option(
        "--file",
        required=True,
        type=click.Path(exists=True, dir_okay=False, path_type=str),
        help="Path to the source file.",
    )
    @click.option(
        "--folder",
        required=requires_folder,
        help="Folder name or UUID.",
        hidden=not show_folder_option,
    )
    @click.option(
        "--perimeter",
        required=requires_perimeter,
        help="Perimeter name or UUID.",
        hidden=not show_perimeter_option,
    )
    @click.option(
        "--framework",
        required=requires_framework,
        help="Framework name or UUID.",
        hidden=not show_framework_option,
    )
    @click.option(
        "--matrix",
        required=requires_matrix,
        help="Risk matrix name or UUID.",
        hidden=not show_matrix_option,
    )
    def command(
        file,
        folder,
        perimeter,
        framework,
        matrix,
        _model=model_type,
        _requires_folder=requires_folder,
        _requires_perimeter=requires_perimeter,
        _requires_framework=requires_framework,
        _requires_matrix=requires_matrix,
    ):
        upload_data_wizard_file(
            model_type=_model,
            file_path=file,
            folder=folder,
            perimeter=perimeter,
            framework=framework,
            matrix=matrix,
            requires_folder=_requires_folder,
            requires_perimeter=_requires_perimeter,
            requires_framework=_requires_framework,
            requires_matrix=_requires_matrix,
        )

    globals()[command_name] = command


for cfg in DATA_WIZARD_COMMANDS:
    register_data_wizard_command(cfg)


@cli.command(name="upload-attachment")
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


@cli.command(name="backup-full")
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
        with open(manifest_file, "r") as f:  # FIX: "r" not "a"
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("downloaded"):
                        # Verify file actually exists on disk before adding to manifest
                        evidence_id = entry.get("evidence_id")
                        version = entry.get("version")
                        filename = entry.get("filename")
                        file_path = (
                            attachments_dir / f"{evidence_id}_v{version}_{filename}"
                        )

                        if file_path.exists():
                            existing_manifest[entry["id"]] = entry
                        # If file doesn't exist, simply don't add it to existing_manifest
                        # (it will be re-downloaded)

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

        # Skip if already downloaded with matching hash AND file exists on disk
        if revision_id in existing_manifest:
            manifest_entry = existing_manifest[revision_id]
            if manifest_entry.get("hash") == file_hash:
                # Verify file actually exists on disk
                evidence_id = meta["evidence_id"]
                version = meta["version"]
                filename = meta["filename"]
                file_path = attachments_dir / f"{evidence_id}_v{version}_{filename}"

                if file_path.exists():
                    continue

        to_download.append(meta)

    total_downloaded = 0
    total_bytes = 0

    if not to_download:
        rprint("[green]✓ All attachments already downloaded[/green]")
    else:
        rprint(
            f"[cyan]Downloading {len(to_download)} attachments in batches of {batch_size}...[/cyan]"
        )

        # Download in batches
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

                    # Add to manifest
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

                    existing_manifest[header["id"]] = manifest_entry

            rprint(
                f"[green]✓ Batch {i // batch_size + 1} completed ({total_downloaded} files, {total_bytes / 1024 / 1024:.1f} MB)[/green]"
            )

        rprint(
            f"[bold green]✓ Downloaded {total_downloaded} attachments ({total_bytes / 1024 / 1024:.1f} MB total)[/bold green]"
        )

    # Rebuild manifest removing duplicates and missing files
    if existing_manifest or total_downloaded > 0:
        rprint("[dim]Cleaning up manifest...[/dim]")
        with open(manifest_file, "w") as f:
            for entry in existing_manifest.values():
                f.write(json.dumps(entry) + "\n")
    rprint("[bold green]Full backup completed successfully![/bold green]")
    rprint(f"[dim]Location: {dest_path}[/dim]")


@cli.command(name="restore-full")
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

            # Stream to temp file with reasonable buffering
            temp_attachments = tempfile.NamedTemporaryFile(
                suffix=".dat", delete=False, buffering=8 * 1024 * 1024
            )  # 8MB buffer

            for file_info in to_upload:
                with open(file_info["path"], "rb") as f:
                    file_bytes = f.read()

                # Build header
                header = {
                    "id": file_info["id"],
                    "evidence_id": file_info["evidence_id"],
                    "version": file_info["version"],
                    "filename": file_info["filename"],
                    "hash": file_info["hash"],
                    "size": len(file_bytes),
                }
                header_bytes = json.dumps(header).encode("utf-8")
                total_size = len(header_bytes) + len(file_bytes)

                # Write directly (OS will buffer intelligently)
                temp_attachments.write(struct.pack(">I", total_size))
                temp_attachments.write(header_bytes)
                temp_attachments.write(file_bytes)
            temp_attachments.close()
            attachments_data = temp_attachments.name

            total_size_mb = Path(attachments_data).stat().st_size / 1024 / 1024
            rprint(
                f"[dim]Prepared {len(to_upload)} attachments for upload ({total_size_mb:.1f} MB)[/dim]"
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


if __name__ == "__main__":
    cli()
