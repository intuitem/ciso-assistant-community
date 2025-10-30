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

Set the custom extensions path as an environment variable:

```bash
export N8N_CUSTOM_EXTENSIONS=/path/to/ciso-assistant-community/automation/n8n/n8n-nodes-ca
n8n start
```

### 5. Access n8n

Open your browser at `http://localhost:5678`

## Running with Docker/Container

If you're running n8n in a Docker container, you need to mount the custom node directory and set the environment variable.

### Option 1: Docker Run

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -e N8N_CUSTOM_EXTENSIONS=/custom-nodes \
  -v /path/to/ciso-assistant-community/automation/n8n/n8n-nodes-ca:/custom-nodes \
  n8nio/n8n
```

### Option 2: Docker Compose

Add to your `docker-compose.yml`:

```yaml
version: "3.8"

services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_CUSTOM_EXTENSIONS=/custom-nodes
    volumes:
      - n8n_data:/home/node/.n8n
      - /path/to/ciso-assistant-community/automation/n8n/n8n-nodes-ca:/custom-nodes:ro

volumes:
  n8n_data:
```

**Important**:

- Replace `/path/to/ciso-assistant-community/automation/n8n/n8n-nodes-ca` with the actual path on your host
- The node must be **built** before mounting (run `npm run build` in the node directory first)
- Restart the container after rebuilding the node

## Development

After making changes to the node:

```bash
npm run build
```

Then restart n8n with the custom extensions path.

## Configuration

In n8n, create a new credential for "CISO Assistant API":

- **API URL**: Your CISO Assistant instance URL (e.g., `http://localhost:8000/api`)
- **Personal Access Token (PAT)**: Your authentication token from CISO Assistant
- **Skip TLS verification**: Enable if using self-signed certificates (optional)

## Available Resources

- System (build info, users)
- Domains (folders)
- Perimeters
- Assets
- Audits (compliance assessments)
- Risk Assessments
- Risk Scenarios
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
