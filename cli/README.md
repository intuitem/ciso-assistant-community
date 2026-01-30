# CISO Assistant CLI (CLICA)

CLICA is a command-line interface tool for interacting with the CISO Assistant REST API. It provides powerful functionality for importing and managing cybersecurity data, including risk assessments, assets, controls, and evidence.

## Table of Contents

- [Installation](#installation)
- [Authentication Setup](#authentication-setup)
- [Configuration](#configuration)
- [Available Commands](#available-commands)
  - [Query Commands](#query-commands)
  - [Import Commands](#import-commands)
  - [File Upload Commands](#file-upload-commands)
  - [Instance Management Commands](#instance-management-commands)
- [Data Formats](#data-formats)
- [MCP Integration](#mcp-integration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.12 or higher
- Required Python packages (install via pip):

```bash
pip install -r requirements.txt
```

### Dependencies

The CLI requires the following Python packages:

- pandas
- rich
- requests
- click
- pyyaml
- icecream
- python-dotenv

## Authentication Setup

CLICA uses Personal Access Tokens (PAT) for authentication with the CISO Assistant API.

### Step 1: Generate a PAT in CISO Assistant

1. Log into your CISO Assistant instance
2. Select "My Profile"
3. Go to "Settings"
4. Generate a new Personal Access Token
5. Copy the token for use in the next step

### Step 2: Configure Authentication

Create or use existing `.clica.env` file in the CLI directory with the following content:

```env
TOKEN=
API_URL=http://localhost:8000/api
VERIFY_CERTIFICATE=true
```

**Configuration Parameters:**

- `TOKEN`: Your Personal Access Token from CISO Assistant
- `API_URL`: The base URL of your CISO Assistant API endpoint
- `VERIFY_CERTIFICATE`: Set to `false` if using self-signed certificates (not recommended for production)

## Configuration

The CLI uses environment variables for configuration. Make sure your `.clica.env` file is properly configured before running any commands.

> [!WARNING]
> Never commit your `.clica.env` file to version control as it contains sensitive authentication information.

## Available Commands

### Query Commands

These commands retrieve information from your CISO Assistant instance:

#### `get_folders`

Retrieves all available folders/domains from your CISO Assistant instance.

```bash
python clica.py get-folders
```

**Output:** JSON list of all folders with their IDs and names.

#### `get_perimeters`

Lists all available perimeters in your CISO Assistant instance.

```bash
python clica.py get-perimeters
```

**Output:** JSON list of perimeters organized by folder.

#### `get_matrices`

Retrieves all loaded risk matrices from the Global folder.

```bash
python clica.py get-matrices
```

**Output:** JSON list of available risk matrices with their IDs and names.

### Import Commands

These commands import data from CSV files into CISO Assistant:

#### `import_risk_assessment`

Imports a complete risk assessment from a CSV file, including risk scenarios, assets, threats, and controls.

```bash
python clica.py import-risk-assessment \
  --file RA_sample.csv \
  --folder "Business Unit 1" \
  --perimeter "Network Infrastructure" \
  --matrix "4x4 Risk Matrix" \
  --name "Q1 2024 Risk Assessment" \
  --create_all
```

**Parameters:**

- `--file`: Path to the CSV file containing risk assessment data
- `--folder`: Target folder name in CISO Assistant
- `--perimeter`: Perimeter name to associate with the assessment
- `--matrix`: Risk matrix name to use for impact/probability mapping
- `--name`: Name for the new risk assessment
- `--create_all`: (Optional) Automatically create associated objects (threats, assets, controls)

**Features:**

- Automatically creates missing assets, threats, and controls when `--create_all` is used
- Maps risk matrix values to proper impact and probability levels
- Supports multiple risk treatment options
- Handles complex relationships between risk scenarios and their components

#### `import_assets`

Imports assets from a CSV file into the Global folder.

```bash
python clica.py import-assets --file sample_assets.csv
```

**Parameters:**

- `--file`: Path to the CSV file containing asset data

**CSV Format:**

```csv
name,description,domain,type
Server01,Production web server,Global,Primary
Backup Storage,Backup storage system,Global,Support
```

#### `import_controls`

Imports applied controls (security measures) from a CSV file.

```bash
python clica.py import-controls --file sample_controls.csv
```

**Parameters:**

- `--file`: Path to the CSV file containing control data

**CSV Format:**

```csv
name,description,category,csf_function
Firewall,Network traffic control,Technical,Protect
Security Training,Employee awareness program,Process,Protect
```

#### `import_evidences`

Imports evidence records from a CSV file.

```bash
python clica.py import-evidences --file evidences.csv
```

**Parameters:**

- `--file`: Path to the CSV file containing evidence data

**CSV Format:**

```csv
name,description
Asset Management Policy,Documented asset management procedures
Security Audit Report,Annual security assessment results
```

### File Upload Commands

#### `upload_attachment`

Uploads a file as an attachment to an existing evidence record.

```bash
python clica.py upload-attachment \
  --file /path/to/document.pdf \
  --name "Asset Management Policy"
```

**Parameters:**

- `--file`: Path to the file to upload
- `--name`: Name of the existing evidence record to attach the file to

### Backup and Restore Commands

#### `backup_full`

Creates a complete backup of your CISO Assistant instance using a memory-efficient streaming approach. Supports resume capability for interrupted backups.

```bash
python clica.py backup-full --dest-dir ./db --batch-size 200 --resume
```

**Parameters:**

- `--dest-dir`: Destination directory to save backup files (default: `./db`)
- `--batch-size`: Number of files to download per batch (default: 200)
- `--resume/--no-resume`: Resume from existing manifest if backup was interrupted (default: True)

**Output:**

- `backup.json.gz`: Compressed database backup
- `backup-manifest.jsonl`: JSON Lines manifest tracking all downloaded files with hashes
- `attachments/evidence-revisions/`: Directory containing all attachment files with naming pattern `{evidence_id}_v{version}_{filename}`

**How it works:**

1. **Database Backup**: Downloads the database backup as `backup.json.gz`
2. **Metadata Fetch**: Retrieves metadata for all attachments (pagination handled automatically)
3. **Resume Logic**: Compares server metadata with local manifest to identify missing/changed files (based on SHA256 hash comparison)
4. **Batch Download**: Downloads files in configurable batches using custom streaming protocol
5. **Manifest Update**: Appends each successfully downloaded file to manifest (crash-safe, append-only)

**Advantages:**

- **No ZIP Processing**: Avoids loading large ZIP files into memory
- **Resume Capability**: Can continue interrupted backups without re-downloading existing files
- **Hash Verification**: Uses SHA256 hashes to detect file changes and skip unchanged files
- **Memory Efficient**: Streams files in 1MB chunks, never loads full files in memory
- **Progress Tracking**: Shows batch progress and total data downloaded

**Notes:**

- Requires `has_backup_permission` flag in your user profile
- If backup is interrupted, simply run the same command again with `--resume` (default)
- The manifest file tracks which files have been downloaded with their hashes
- Files are only re-downloaded if their hash changes on the server

#### `restore_full`

Restores a complete backup of your CISO Assistant instance using a memory-efficient streaming approach. Supports resume capability for interrupted restores.

```bash
python clica.py restore-full --src-dir ./db --verify-hashes
```

**Parameters:**

- `--src-dir`: Source directory containing backup files (default: `./db`)
- `--verify-hashes/--no-verify-hashes`: Verify local file hashes before upload (default: True)

**Requirements:**

- The source directory must contain `backup.json.gz`
- The source directory must contain `backup-manifest.jsonl` (for attachments restore)
- Attachments should be in `attachments/evidence-revisions/` directory
- Requires `has_backup_permission` flag in your user profile

**How it works:**

1. **Database Restore**: Uploads and restores the database backup
2. **Manifest Load**: Reads the backup manifest to identify files to upload
3. **Hash Verification** (optional): Verifies local file hashes match manifest entries
4. **Resume Logic**: Skips files already marked as uploaded in the manifest
5. **Batch Upload**: Uploads files in configurable batches using custom streaming protocol
6. **Server-Side Deduplication**: Server skips files if hash matches existing attachment (idempotent)
7. **Manifest Update**: Marks successfully uploaded files in manifest after each batch

**Advantages:**

- **No ZIP Processing**: Avoids creating large ZIP files in memory
- **Resume Capability**: Can continue interrupted restores without re-uploading existing files
- **Hash Verification**: Validates file integrity before upload
- **Idempotent**: Server skips files that already match (safe to re-run)
- **Memory Efficient**: Streams files in batches, never loads all files in memory
- **Partial Success Handling**: Continues processing even if some files fail, reports errors

**Notes:**

- The restore process happens in **two separate steps** (database first, then attachments)
- After database restore, you'll need to regenerate your Personal Access Token
- If restore is interrupted, run the same command again with `--resume` (default)
- Files with hash mismatches (detected during `--verify-hashes`) are skipped and reported
- Server validates uploaded file hashes and skips if they match existing attachments

> [!WARNING]
> Restoring a backup will **replace all existing data** in your CISO Assistant instance. Make sure you have a current backup before performing a restore operation.

> [!TIP]
> **Best Practices:**
> - Run `backup-full` regularly to maintain disaster recovery capabilities
> - Use `--batch-size` to tune performance based on your network and file sizes
> - Keep the manifest file safe - it enables resume functionality
> - After restore completes, regenerate your Personal Access Token immediately

**Technical Details:**

The backup/restore system uses a custom binary streaming protocol to avoid memory issues:

- **Format**: Each file is transmitted as `[4-byte length][JSON header][file bytes]`
- **Hashing**: SHA256 hashes computed using 1MB chunks (no full file in memory)
- **Deduplication**: Files are skipped if their hash matches (both client and server-side)
- **Manifest**: JSON Lines format allows incremental append (crash-safe)
- **Batch Processing**: Configurable batch sizes balance efficiency vs memory usage

### Instance Management Commands


## Data Formats

### Risk Assessment CSV Format

The risk assessment CSV file should use semicolon (`;`) as delimiter and include the following columns:

```csv
ref_id;assets;threats;name;description;existing_controls;current_impact;current_proba;current_risk;additional_controls;residual_impact;residual_proba;residual_risk;treatment
```

**Column Descriptions:**

- `ref_id`: Unique reference identifier for the risk scenario
- `assets`: Comma-separated list of asset names
- `threats`: Comma-separated list of threat names
- `name`: Risk scenario name
- `description`: Detailed description of the risk
- `existing_controls`: Comma-separated list of current control names
- `current_impact`: Current impact level (must match risk matrix values)
- `current_proba`: Current probability level (must match risk matrix values)
- `current_risk`: Current risk level (calculated)
- `additional_controls`: Comma-separated list of additional control names
- `residual_impact`: Residual impact level after controls
- `residual_proba`: Residual probability level after controls
- `residual_risk`: Residual risk level (calculated)
- `treatment`: Risk treatment option

### Risk Treatment Options

The CLI supports the following risk treatment options:

- `open`: Risk is identified but not yet treated
- `mitigate`: Implement controls to reduce risk
- `accept`: Accept the risk as is
- `avoid`: Eliminate the risk by avoiding the activity
- `transfer`: Transfer risk to a third party (e.g., insurance)

## MCP Integration

CLICA includes Model Context Protocol (MCP) integration for use with Claude Desktop and other MCP-compatible clients.

### Setup for Claude Desktop

1. Install prerequisites:
   - Python 3.12
   - uv package manager
   - Node.js
   - Claude Desktop

2. Configure your `.mcp.env` file with the same parameters as `.clica.env`
3. Update Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "/full/path/to/uv",
      "args": ["--directory", "/full/path/to/cli/folder", "run", "ca_mcp.py"]
    }
  }
}
```

4. Restart Claude Desktop

### Available MCP Tools

- `get_risk_scenarios()`: Retrieve risk scenarios from CISO Assistant
- `get_applied_controls()`: Retrieve applied controls/action plan
- `get_audits_progress()`: Retrieve compliance assessment progress

## Examples

### Complete Risk Assessment Import

```bash
# First, check available folders, perimeters, and matrices
python clica.py get-folders
python clica.py get-perimeters
python clica.py get-matrices

# Import a complete risk assessment
python clica.py import-risk-assessment \
  --file RA_sample.csv \
  --folder "Business Unit 1" \
  --perimeter "IT Infrastructure" \
  --matrix "4x4 risk matrix from EBIOS-RM" \
  --name "2024 Q1 Risk Assessment" \
  --create_all
```

### Import Supporting Data

```bash
# Import assets
python clica.py import-assets --file sample_assets.csv

# Import security controls
python clica.py import-controls --file sample_controls.csv

# Import evidence records
python clica.py import-evidences --file evidences.csv

# Upload supporting documents
python clica.py upload-attachment \
  --file "security_policy.pdf" \
  --name "Information Security Policy"
```

### Backup and Restore Operations

```bash
# Create a full backup with timestamp
BACKUP_DATE=$(date +%Y-%m-%d_%H-%M-%S)
python clica.py backup-full --dest-dir "./backups/backup-$BACKUP_DATE"

# List backups
ls -lh ./backups/

# Restore from a specific backup
python clica.py restore-full --src-dir "./backups/backup-2024-01-15_10-30-00"

# Automated daily backup (can be added to cron)
python clica.py backup-full --dest-dir "/var/backups/ciso-assistant/$(date +%Y-%m-%d)"
```

## Troubleshooting

### Error Messages

- `"No authentication token available"`: Configure your PAT token in `.clica.env`
- `"something went wrong. check authentication"`: Verify your token and API URL
- `"Matrix doesn't match the labels used on your input file"`: Ensure impact/probability values match your risk matrix

### Getting Help

For additional support:

1. Check the CISO Assistant documentation
2. Verify your API endpoint is accessible
3. Review the sample CSV files for proper formatting
4. Ensure all required dependencies are installed
5. Contact us on our Discord !

## Security Considerations

- Never commit `.clica.env` or `.mcp.env` files to version control
- Use `VERIFY_CERTIFICATE=true` in production environments
