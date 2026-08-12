---
description: >-
  This guide explains how to connect your AI assistant to CISO Assistant using
  the Model Context Protocol (MCP). Once set up, you'll be able to ask your AI
  to create risk assessments, manage compliance
---

# MCP setup guide

Compatible with: SaaS or on-premises, CE or Pro

Tested MCP clients: Claude Desktop, Claude Code, LM Studio, OpenWebUI

### What is MCP?

MCP (Model Context Protocol) allows AI assistants like Claude to interact with external tools and services. Think of it as giving your AI a set of capabilities to read and write data in CISO Assistant.

The CISO Assistant MCP server provides **105 tools** covering:

* Risk management (assessments, scenarios, matrices)
* Compliance audits (frameworks, requirements)
* Asset management
* Third-party risk management (TPRM)
* EBIOS RM methodology
* Privacy / GDPR records (processings, personal data, data subjects, breaches, right requests)
* Findings, evidences, policies and managed documents
* Threat models, TTP catalogs (tactics, techniques) and CWEs

Most tools are dedicated to one object type. Three are generic and work across
every supported type: `list_objects`, `get_object` and `count_objects`.

Use `count_objects` for any question whose answer is a number — "how many
vulnerabilities are exploitable?", "what is the breakdown of controls by
status?". It returns exact server-side counts rather than counting rows, so the
answer stays correct however large the register is.

### Choosing a transport

The server speaks two transports. **stdio is the default and the right choice for
most people.**

**stdio (default)** — the AI client starts the MCP server as a subprocess on your
machine.

1. **No open ports** - nothing listens on the network, so there is no new attack surface.
2. **Network control** - every API call to CISO Assistant leaves from your own machine, through your existing firewall rules and proxies.
3. **Simpler security model** - no credential travels between the client and the MCP server, and there is no CORS or network authentication to configure.
4. **Works offline** - the server itself runs locally; only the CISO Assistant API calls need the network.

Use stdio with Claude Desktop, Claude Code, LM Studio, Cursor and any other client
that can launch a local process.

**Streamable HTTP** — the server listens on a port and several users share it.
Choose this only when the client cannot start a local process, which is the case
for **ChatGPT** and **Microsoft Copilot Studio**, since those run in the vendor's
cloud rather than on your machine.

The trade-off is real: HTTP means a listening service, and for a cloud client it
means that service must be reachable from the internet. See
[Streamable HTTP transport](#streamable-http-transport) below.

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

1. **CISO Assistant running** - Either locally or on a server (can be the same machine or a remote server). The API must be reachable from the machine running the MCP server, which means that machine's IP must be in the [Allowed IP whitelist](../configuration/settings/infra-config-allowed-ip.md). On **SaaS**, IP filtering is already enabled — just add your IP under **Settings → Infrastructure**. **On-premises** administrators should enable it first (`ENABLE_INFRA_CONFIG_MANAGEMENT=True`) and add their IPs. Remember that allowlist changes take about 10 minutes to apply.
2. **Python 3.14+** installed
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

### Streamable HTTP transport

Only needed for clients that cannot start a local process — ChatGPT and Microsoft
Copilot Studio. If your client can launch a subprocess, use stdio instead.

#### Option A: Docker Compose (recommended)

If you deployed CISO Assistant with Docker Compose, the MCP server ships as an
optional service on the same stack. It is off by default — enable it with a
profile:

```bash
docker compose --profile mcp up -d
```

That starts the server and routes it through the proxy you already run, so it is
served at `https://<your-host>:8443/mcp` on the existing certificate. Nothing new
is published on the host: the container has no `ports:` mapping and is reachable
only through the proxy.

{% hint style="info" %}
The service defaults to **read-only**. To allow an assistant to create or modify
records, set `CA_MCP_READ_ONLY=false` in the `mcp` service environment and
recreate it. See [Read-only by default](#read-only-by-default) before you do.
{% endhint %}

If you generated your deployment with `config/make_config.py`, answer yes to the
MCP question and the service, the proxy route and the read-only choice are
written into your compose file for Caddy, Traefik or BunkerWeb alike.

#### Option B: Run from source

```bash
cd cli
API_URL=http://localhost:8000/api \
CA_MCP_TRANSPORT=http \
CA_MCP_ALLOWED_HOSTS=your-public-hostname:port \
uv run python ca_mcp.py
```

The server listens on `127.0.0.1:8001/mcp`.

#### Making it reachable

`CA_MCP_ALLOWED_HOSTS` validates the `Host` header of incoming requests — it does
**not** change what the server binds to. Left at its default the server is
loopback-only, which is the safe default and means a cloud client cannot reach it
yet.

Put an HTTPS reverse proxy or a tunnel in front, forwarding `/mcp` to
`127.0.0.1:8001`, and set `CA_MCP_ALLOWED_HOSTS` to the public hostname the client
will use. That keeps TLS termination, certificates and access logging in
infrastructure you already run. Option A does all of this for you.

{% hint style="warning" %}
`CA_MCP_ALLOWED_HOSTS` is matched against the `Host` header **exactly, port
included**. A client connecting to `https://grc.example.com:8443/mcp` sends
`Host: grc.example.com:8443`, so a value of `grc.example.com` alone is rejected
with **421 Misdirected Request**. On the default HTTPS port the port is omitted
instead. When in doubt list both forms, comma-separated:
`grc.example.com,grc.example.com:8443`.
{% endhint %}

Binding directly to a non-loopback address with `CA_MCP_HOST=0.0.0.0` is possible
but puts a plaintext HTTP listener on the network; both clients require HTTPS, so
you would still need TLS in front. If you do bind widely, restrict the port by
firewall.

For a server that should not be published at all, ChatGPT offers a Secure MCP
Tunnel, which reaches a private or on-premises server without a public listener.

#### Each user brings their own token

By default the server holds **no** credential of its own in HTTP mode. Every
request must carry the caller's Personal Access Token, and the call runs with
exactly that user's permissions and domain scope. A request without a token is
rejected rather than served with a shared identity.

Setting `CA_MCP_ALLOW_ENV_TOKEN=true` changes that: requests arriving without a
token are served using the server's own `TOKEN`. Every caller then shares one
identity and one set of permissions, and the audit trail can no longer tell them
apart. Only use it for a single-user deployment.

Send the token either way:

```text
Authorization: Token <PAT>
X-CISO-Token: <PAT>
```

Use `X-CISO-Token` if the client reserves or rewrites `Authorization`.

#### Read-only by default

The HTTP endpoint exposes **only read tools (48)**. Set
`CA_MCP_READ_ONLY=false` to expose the write tools as well — a deliberate choice,
since an agent driven by a third-party orchestrator would then be able to modify
your GRC data.

#### Connecting ChatGPT

Requires developer mode. Create a new plugin, set the connection to your server
URL ending in `/mcp`, choose **Access token / API key** with a **Custom Header**
named `Authorization`, then enter the PAT itself when prompted for the key. Enter
the token on its own, with no `Token` or `Bearer` prefix in the value field.

#### Connecting Microsoft Copilot Studio

On your agent, go to **Tools** → **Add a tool** → **New tool** → **Model Context
Protocol**. Fill in the server name, description and URL, then choose **API key**
authentication with type **Header** and the header name `Authorization`. Write a
precise server description: the agent's orchestrator uses it to decide whether to
call your server at all.

Two prerequisites are outside CISO Assistant's control. The environment needs
**Copilot Credits** allocated to it, and because MCP access rides on Power
Platform connectors, a tenant data policy governing connectors also governs this.

#### Exposing the server

Both clients call from the vendor's cloud, so a self-hosted instance behind a
corporate firewall needs either a published HTTPS endpoint or a tunnel — see
Making it reachable above. Set `CA_MCP_ALLOWED_HOSTS` to the hostname the client
will use; requests arriving with any other `Host` header are refused. Loopback
addresses stay allowed so local tools keep working.

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
* "Create an audit for ISO 27001"

**Analyze and report:**

* "Show me the gap analysis for my SOC2 audit"
* "What are the high-risk scenarios in my assessment?"
* "List all controls that are not yet implemented"

**Manage third parties:**

* "List all our vendors"
* "Create an entity assessment for Acme Corp"
* "What contracts are expiring soon?"

**Count and measure:**

* "How many vulnerabilities do we have?"
* "Give me a breakdown of applied controls by status"
* "What proportion of our risk scenarios are still open?"

**Privacy and GDPR:**

* "List our processing activities"
* "What personal data categories do we hold?"
* "Show the open data subject right requests"

***

### FAQ

* What about ChatGPT compatibility?
  * Supported, via the [Streamable HTTP transport](#streamable-http-transport). It needs developer mode enabled in ChatGPT, and because ChatGPT calls from OpenAI's cloud the server must be reachable from there — either published behind an HTTPS reverse proxy, or connected through OpenAI's Secure MCP Tunnel, which reaches a private server without a public listener. The endpoint is read-only by default and every request carries its own token. For a single user on their own machine, stdio remains simpler and exposes nothing.
* What about Microsoft Copilot Studio?
  * The same HTTP transport applies. Beyond reachability, the Power Platform environment needs Copilot Credits allocated to it, and tenant data policies covering connectors also cover MCP access.

### Need Help?

* **CISO Assistant Documentation:** https://intuitem.gitbook.io&#x20;
* **GitHub:** https://github.com/intuitem/ciso-assistant-community
* **Discord:** [https://discord.gg/qvkaMdQ8da](https://discord.gg/qvkaMdQ8da)

***

### Quick Reference: Environment Variables

| Variable             | Required | Default                     | Description                               |
| -------------------- | -------- | --------------------------- | ----------------------------------------- |
| `TOKEN`              | stdio only | -                         | Personal Access Token. Unused in HTTP mode by default, where each request carries its own; used as a shared fallback if `CA_MCP_ALLOW_ENV_TOKEN=true` |
| `API_URL`            | No       | `http://localhost:8000/api` | CISO Assistant API endpoint               |
| `VERIFY_CERTIFICATE` | No       | `true`                      | SSL certificate verification. Set to `false` for self-signed certificates |

Additional variables for the HTTP transport:

| Variable                    | Default     | Description                                     |
| --------------------------- | ----------- | ----------------------------------------------- |
| `CA_MCP_TRANSPORT`          | `stdio`     | Set to `http` for Streamable HTTP               |
| `CA_MCP_READ_ONLY`          | `true`      | Expose only read tools                          |
| `CA_MCP_HOST`               | `127.0.0.1` | Listen address                                  |
| `CA_MCP_PORT`               | `8001`      | Listen port                                     |
| `CA_MCP_PATH`               | `/mcp`      | Endpoint path                                   |
| `CA_MCP_ALLOWED_HOSTS`      | -           | Comma-separated hostnames accepted in the `Host` header, port included. Validates `Host`; does **not** set the listen address. Loopback is always allowed |
| `CA_MCP_ALLOW_ENV_TOKEN`    | `false`     | Allow HTTP callers with no token to be served using `TOKEN`. Collapses every caller into one identity |

Response size limits, which apply to both transports:

| Variable                     | Default | Description                                |
| ---------------------------- | ------- | ------------------------------------------ |
| `CA_MCP_PAGE_LIMIT`          | `100`   | Rows returned per list call                |
| `CA_MCP_MAX_ITEMS`           | `200`   | Cap when a tool follows pagination itself  |
| `CA_MCP_MAX_RESPONSE_CHARS`  | `20000` | Cap on a single tool response              |

Lists say how much they are showing — `Found 100 of 1592 vulnerabilities (rows
1-100; pass offset=100 for the next page)` — so a truncated answer is never
mistaken for a complete one. Counts and percentages are computed over the whole
set regardless of these limits.
