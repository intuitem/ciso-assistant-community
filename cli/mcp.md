## Claude Desktop

- python 3.12
- uv
- authenticate with CISO Assistant clica

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "<full_uv_path>/uv",
      "args": [
        "--directory",
        "<full_path_to_dir>/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```
