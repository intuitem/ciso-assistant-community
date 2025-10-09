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
