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

#### `import_audit`

Imports compliance assessment (audit) data from a CSV file. This command creates a compliance assessment and updates requirement assessments with compliance results, progress status, observations, and optional scores.

```bash
python clica.py import-audit \
  --file sample_audit.csv \
  --folder "DEMO" \
  --perimeter "Smart Fridge" \
  --framework "ISO 27001:2026" \
  --name "Q1 2024 Compliance Assessment"
```

**Parameters:**

- `--file`: Path to the CSV file containing audit/compliance data (required)
- `--folder`: Target folder name in CISO Assistant (required)
- `--perimeter`: Perimeter name to associate with the assessment (required)
- `--framework`: Framework name for the assessment (e.g., "ISO 27001:2022", "NIST CSF") (required)
- `--name`: Name for the compliance assessment (optional, auto-generated if not provided)

**CSV Format:**

The CSV file must contain either a `ref_id` or `urn` column to identify requirements, plus the following columns:

```csv
urn;ref_id;name;description;compliance_result;requirement_progress;score;observations
urn:intuitem:risk:req_node:nist-csf-2.0:gv;GV;GOVERN;The organization's cybersecurity risk management strategy, expectations, and policy are established, communicated, and monitored;;;;
urn:intuitem:risk:req_node:nist-csf-2.0:gv.oc;GV.OC;Organizational Context;The circumstances - mission, ;;;;
urn:intuitem:risk:req_node:nist-csf-2.0:gv.oc-01;GV.OC-01;;The organizational mission is understood and  management;partially_compliant;in_progress;2;

```

**Column Descriptions:**

- `ref_id`: Requirement reference ID from the framework (use this OR urn)
- `urn`: Universal requirement identifier (use this OR ref_id)
- `compliance_result`: Compliance status - values: `compliant`, `non_compliant`, `partially_compliant`, `not_applicable`, `not_assessed`
- `requirement_progress`: Progress status - values: `to_do`, `in_progress`, `in_review`, `done`
- `observations`: Text observations/notes about the requirement assessment
- `score`: Optional numerical score for the requirement

**Features:**

- Automatically creates a compliance assessment with requirement assessments
- Updates existing requirement assessments with compliance data
- Supports both ref_id and urn for requirement identification
- Handles optional scoring
- Provides detailed progress feedback during import
- Reports success/failure counts at completion

**Important Notes:**

- The framework must already exist in CISO Assistant with loaded requirements
- The compliance assessment will automatically generate requirement assessments based on the framework
- The CSV must use comma (`,` or `;`) as delimiter

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

### Instance Management Commands

#### `clone_instance`

Creates a complete clone of a CISO Assistant instance by copying both the SQLite database and evidence attachments directory. This is useful for creating backups, testing environments, or migrating instances.

```bash
python clica.py clone-instance \
  --dest-db /path/to/backup/ciso-assistant.sqlite3 \
  --dest-attachments /path/to/backup/attachments
```

**Parameters:**

- `--source-db`: Path to source SQLite database (default: `../backend/db/ciso-assistant.sqlite3`)
- `--dest-db`: Path to destination SQLite database (required)
- `--source-attachments`: Path to source attachments directory (default: `../backend/db/attachments`)
- `--dest-attachments`: Path to destination attachments directory (required)
- `--force`: Overwrite destination files if they exist without prompting (optional)

**Features:**

- Validates source database is a valid SQLite file before cloning
- Calculates and displays total size of data to be copied
- Shows detailed summary before proceeding
- Requires confirmation before starting the clone operation
- Verifies copied database integrity after cloning
- Provides detailed progress feedback
- Creates necessary destination directories automatically
- Handles permission errors and edge cases gracefully

**Important Notes:**

- The clone operation does not require API authentication (no TOKEN needed)
- After cloning, update your CISO Assistant configuration to use the new database and attachments paths
- For production use, consider stopping the CISO Assistant service before cloning to ensure data consistency
- The cloned instance is a complete snapshot and can be used independently

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

### Audit/Compliance Assessment CSV Format

The audit CSV file uses comma (`,` or `;`) as delimiter and must include either `ref_id` or `urn` for requirement identification:

**Required Columns:**
- `ref_id` OR `urn`: Identifier to match requirements in the framework
**Optional Columns:**
- `compliance_result`: Compliance status (compliant, non_compliant, partially_compliant, not_applicable, not_assessed)
- `requirement_progress`: Progress status (to_do, in_progress, in_review, done)
- `observations`: Text notes and observations
- `score`: Numerical score (integer)

**Example:**
```csv
urn;ref_id;name;description;compliance_result;requirement_progress;score;observations
urn:f-2.0:gv;GV;GOVERN;The organization's cybersecurity risk management ;;;;
urn:f-2.0:gv.oc;GV.OC;Organizational Context;The circumstances - mission, ;;;;
urn:f-2.0:gv.oc-01;GV.OC-01;;The organizational mission is understood and;partially_compliant;in_progress;2;
urn:f-2.0:gv.oc-02;GV.OC-02;;Internal and external stakeholders are undeidered;compliant;in_review;;
urn:f-2.0:gv.oc-03;GV.OC-03;;Legal, regulatory, and contractual aged;compliant;done;;
urn:f-2.0:gv.oc-04;GV.OC-04;;Critical objectives, capabilities, municated;partially_compliant;in_review;;
```

The CSV format matches the Data Wizard import format, ensuring consistency across import methods.

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

### Import Audit/Compliance Assessment

```bash
# First, check available folders, perimeters, and frameworks
python clica.py get-folders
python clica.py get-perimeters

# Import compliance assessment data
python clica.py import-audit \
  --file sample_audit.csv \
  --folder "Business Unit 1" \
  --perimeter "IT Infrastructure" \
  --framework "ISO 27001:2022" \
  --name "2024 Q1 ISO 27001 Assessment"

# Import without specifying name (auto-generated timestamp)
python clica.py import-audit \
  --file audit_results.csv \
  --folder "Global" \
  --perimeter "Organization-wide" \
  --framework "NIST CSF"
```

### Clone Instance for Backup or Testing

```bash
# Create a complete backup of your instance
python clica.py clone-instance \
  --dest-db /backups/ciso-assistant-backup-$(date +%Y%m%d).sqlite3 \
  --dest-attachments /backups/attachments-backup-$(date +%Y%m%d)

# Clone to a test environment
python clica.py clone-instance \
  --source-db /prod/db/ciso-assistant.sqlite3 \
  --source-attachments /prod/db/attachments \
  --dest-db /test/db/ciso-assistant.sqlite3 \
  --dest-attachments /test/db/attachments
```
# Force database and attachments directory overwrite without prompts
```bash
python clica.py clone-instance \
  --dest-db /backup/ciso-assistant.sqlite3 \
  --dest-attachments /backup/attachments \
  --force
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
