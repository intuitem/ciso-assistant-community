# CISO Assistant Custom n8n Node

Custom n8n node for interacting with the CISO Assistant API.

## Prerequisites

- Node.js 22+
- npm

## Quick Start

### 1. Install n8n globally

```bash
npm install -g n8n
```

### 2. Install dependencies

```bash
npm install
```

### 3. Build the node

```bash
npm run build
```

### 4. Start n8n with the custom node

```bash
N8N_CUSTOM_EXTENSIONS=/Users/abder/mydev/intuitem/staging/ciso-assistant-community/automation/n8n/n8n-nodes-ca n8n start
```

Or set it as an environment variable:

```bash
export N8N_CUSTOM_EXTENSIONS=/path/to/ciso-assistant-community/automation/n8n/n8n-nodes-ca
n8n start
```

### 5. Access n8n

Open your browser at `http://localhost:5678`

## Development

After making changes to the node:

```bash
npm run build
```

Then restart n8n with the custom extensions path.

## Configuration

In n8n, create a new credential for "CISO Assistant API":
- **Base URL**: Your CISO Assistant instance URL (e.g., `http://localhost:8000/api`)
- **API Token**: Your authentication token from CISO Assistant

## Available Resources

- System (build info, users)
- Domains (folders)
- Perimeters
- Assets
- Audits (compliance assessments)
- Risk Assessments
- Incidents
- Vulnerabilities
- Applied Controls
- Task Occurrences & Definitions
- Findings Tracking & Findings
- Security Exceptions
- Evidence (with revisions)
- Entities (TPRM)
- Solutions (TPRM)
- Representatives (TPRM)
- Entity Assessments (TPRM)
- Right Requests (Privacy)
- Data Breaches (Privacy)
- Frameworks
- Risk Matrices

## Notes

- Most operations support optional folder UUID filtering
- Names are case-sensitive for getByName operations
- All date fields expect ISO format (YYYY-MM-DD or ISO 8601 for datetime)
