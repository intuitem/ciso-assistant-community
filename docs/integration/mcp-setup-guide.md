---
description: >-
  This guide explains how to connect your AI assistant to CISO Assistant using
  the Model Context Protocol (MCP). Once set up, you'll be able to ask your AI
  to create risk assessments, manage compliance
---

# MCP setup guide

### What is MCP?

MCP (Model Context Protocol) allows AI assistants like Claude to interact with external tools and services. Think of it as giving your AI a set of capabilities to read and write data in CISO Assistant.

The CISO Assistant MCP server provides **80+ tools** covering:

* Risk management (assessments, scenarios, matrices)
* Compliance audits (frameworks, requirements)
* Asset management
* Third-party risk management (TPRM)
* EBIOS RM methodology
* And more...

### Why stdio Transport?

The MCP server uses **stdio (standard input/output)** transport instead of HTTP. Here's why:

1. **Local file access** - stdio allows the server to read and process local files on your machine, which HTTP-based servers cannot do securely.
2. **Network control** - All API calls to CISO Assistant go through your local machine. You have full visibility and control over network traffic, and can use your existing firewall rules and proxies.
3. **No open ports** - Unlike HTTP servers, stdio doesn't require opening any ports on your machine, reducing your attack surface.
4. **Simpler security model** - The AI client spawns the MCP server as a subprocess. No need for API keys between the client and MCP server, or dealing with CORS and network authentication.
5. **Works offline** - The MCP server itself runs locally. Only the actual CISO Assistant API calls require network access.

### Step 0: Get the MCP Server Code

The MCP server code is included in the CISO Assistant repository. You need to download it to your machine first.

#### Option A: Clone with Git (recommended)

```bash
git clone https://github.com/intuitem/ciso-assistant-community.git
cd ciso-assistant-community/cli
```

This makes it easy to update later with `git pull`.

#### Option B: Download as ZIP

1. Go to https://github.com/intuitem/ciso-assistant-community
2. Click the green **Code** button
3. Select **Download ZIP**
4. Extract the ZIP file to a folder of your choice
5. Navigate to the `cli` folder inside

> **Note:** The MCP server lives in the `cli` folder. You'll need the full path to this folder for the configuration steps below.

***

### Prerequisites

Before you begin, make sure you have:

1. **CISO Assistant running** - Either locally or on a server (can be the same machine or a remote server)
2. **Python 3.12+** installed
3.  **uv** package manager (recommended) - Install with:

    ```bash
    # macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Windows
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

### Step 1: Generate a Personal Access Token (PAT)

You need a token to authenticate the MCP server with CISO Assistant:

1. Log in to CISO Assistant
2. Click on your profile icon (top right)
3. Go to **Settings** → **Personal Access Tokens**
4. Click **Create Token**
5. Give it a name (e.g., "MCP Integration")
6. Copy the token - you'll need it in the next step

> **Important:** Save this token somewhere safe. You won't be able to see it again.

### Step 2: Configure the MCP Server

Navigate to the `cli` folder in your CISO Assistant installation:

```bash
cd /path/to/ciso-assistant-community/cli
```

Create your configuration file:

```bash
cp .mcp.env.example .mcp.env
```

Edit `.mcp.env` with your details:

```env
# Your Personal Access Token from Step 1
TOKEN=your-token-here

# Your CISO Assistant API URL
API_URL=http://localhost:8000/api

# Set to "true" if using HTTPS with a valid certificate
# Set to "false" for local development or self-signed certs
VERIFY_CERTIFICATE=false
```

**Common API URLs:**

* Local Docker setup: `http://localhost:8000/api`
* Local development: `http://127.0.0.1:8000/api`
* Production server: `https://your-server.com/api`

***

### Setup for Claude Desktop

Claude Desktop uses a JSON configuration file to know about MCP servers.

#### Find your config file location

| Operating System | Config File Path                                                  |
| ---------------- | ----------------------------------------------------------------- |
| macOS            | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows          | `%APPDATA%\Claude\claude_desktop_config.json`                     |
| Linux            | `~/.config/Claude/claude_desktop_config.json`                     |

#### Create or edit the config file

If the file doesn't exist, create it. Add the following configuration:

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

**Replace `/path/to/ciso-assistant-community/cli`** with your actual path.

#### Example paths by OS

**macOS:**

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/yourname/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

**Windows:**

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\yourname\\ciso-assistant-community\\cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

**Linux:**

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/yourname/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

#### Alternative: Pass credentials via environment

Instead of using `.mcp.env`, you can pass credentials directly in the config:

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ],
      "env": {
        "TOKEN": "your-token-here",
        "API_URL": "http://localhost:8000/api",
        "VERIFY_CERTIFICATE": "false"
      }
    }
  }
}
```

#### Restart Claude Desktop

After saving the config file, completely quit and restart Claude Desktop. The MCP server should now be available.

#### Verify it works

In Claude Desktop, try asking:

> "What folders exist in CISO Assistant?"

If configured correctly, Claude will use the MCP tools to query your CISO Assistant instance.

***

### Setup for Claude Code (CLI)

Claude Code reads MCP configuration from a `.mcp.json` file.

#### Create the config file

In your home directory or project folder, create `.mcp.json`:

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

#### Config file locations

Claude Code looks for `.mcp.json` in these locations (in order):

1. Current working directory
2. Home directory (`~/.mcp.json`)

#### Alternative: Specify full path to uv

If `uv` isn't in your PATH, use the full path:

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "/Users/yourname/.cargo/bin/uv",
      "args": [
        "--directory",
        "/path/to/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

Find uv's location with:

```bash
which uv  # macOS/Linux
where uv  # Windows
```

#### Verify it works

Start Claude Code and ask:

> "List all risk assessments in CISO Assistant"

***

### Setup for LM Studio

LM Studio supports MCP servers through an `mcp.json` configuration file, similar to Claude Desktop.

#### Step 1: Open the MCP configuration

1. Open **LM Studio**
2. Go to **Settings** (gear icon)
3. Click on the **Program** tab
4. Find **Integrations** section
5. Click the **Install** button
6. Select **Edit mcp.json**

#### Step 2: Add the CISO Assistant server

Add the following configuration to your `mcp.json`:

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ],
      "env": {
        "TOKEN": "your-personal-access-token",
        "VERIFY_CERTIFICATE": "false",
        "API_URL": "http://localhost:8000/api"
      }
    }
  }
}
```

**Replace:**

* `/path/to/uv` with your actual uv path (find it with `which uv` on macOS/Linux)
* `/path/to/ciso-assistant-community/cli` with your actual cli folder path
* `your-personal-access-token` with the token from Step 1

#### Example (macOS)

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "/Users/yourname/.cargo/bin/uv",
      "args": [
        "--directory",
        "/Users/yourname/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ],
      "env": {
        "TOKEN": "your-personal-access-token",
        "VERIFY_CERTIFICATE": "false",
        "API_URL": "http://localhost:8000/api"
      }
    }
  }
}
```

#### Step 3: Save and restart

Save the `mcp.json` file and restart LM Studio for the changes to take effect

***

### Troubleshooting

#### "Connection refused" or "Cannot connect to API"

* Make sure CISO Assistant is running
* Verify the `API_URL` is correct
* Check if you can access the API in your browser: `http://localhost:8000/api/`

#### "Authentication failed" or "401 Unauthorized"

* Verify your token is correct in `.mcp.env`
* Make sure the token hasn't expired
* Generate a new token if needed

#### "Certificate verification failed"

* For local development, set `VERIFY_CERTIFICATE=false`
* For production with self-signed certs, also set to `false`
* For production with valid SSL, set to `true`

#### MCP server not appearing in Claude Desktop

1. Check the config file location is correct for your OS
2. Verify the JSON syntax is valid (use a JSON validator)
3. Make sure paths use forward slashes `/` (even on Windows) or escape backslashes `\\`
4. Restart Claude Desktop completely (quit, don't just close)

#### "uv: command not found"

* Install uv (see Prerequisites section)
* Use the full path to uv in your config
* On macOS/Linux, you may need to add `~/.cargo/bin` to your PATH

#### Check MCP server logs

Test the server directly from terminal:

```bash
cd /path/to/ciso-assistant-community/cli
uv run ca_mcp.py
```

If there are configuration errors, they'll appear here.

***

### What Can You Do With It?

Once connected, try these example prompts:

**Explore your data:**

* "Show me all risk assessments"
* "List the compliance frameworks I have imported"
* "What assets are in the Production folder?"

**Create new items:**

* "Create a new folder called 'IT Security'"
* "Add a risk scenario for ransomware affecting the CRM system"
* "Create a compliance assessment for ISO 27001"

**Analyze and report:**

* "Show me the gap analysis for my SOC2 audit"
* "What are the high-risk scenarios in my assessment?"
* "List all controls that are not yet implemented"

**Manage third parties:**

* "List all our vendors"
* "Create an entity assessment for Acme Corp"
* "What contracts are expiring soon?"

***

### Need Help?

* **CISO Assistant Documentation:** https://intuitem.gitbook.io&#x20;
* **GitHub:** https://github.com/intuitem/ciso-assistant-community
* **Discord:** [https://discord.gg/qvkaMdQ8da](https://discord.gg/qvkaMdQ8da)

***

### Quick Reference: Environment Variables

| Variable             | Required | Default                     | Description                               |
| -------------------- | -------- | --------------------------- | ----------------------------------------- |
| `TOKEN`              | Yes      | -                           | Personal Access Token from CISO Assistant |
| `API_URL`            | No       | `http://localhost:8000/api` | CISO Assistant API endpoint               |
| `VERIFY_CERTIFICATE` | No       | `false`                     | SSL certificate verification              |
