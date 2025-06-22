## Claude Desktop

Note: MCP technology is still maturing so the instructions might vary.

### prerequisites

- python 3.12
- uv
- node
- Claude Desktop (other mcp clients should work but were not tested)

### instructions

1. Login to CISO Assistant and generate a PAT: click on the three dots next to the email -> my profile -> settings
2. Under the `cli` folder, update the `.mcp.env` with your token
3. Update the settings of mcpServers of your Claude Desktop app. The path will vary depending on your OS. On MacOS it's under `~/Library/Application\ Support/Claude/claude_desktop_config.json`. Make sure to put the **full absolute paths** for `uv` binary and the `cli` folder of your cloned repo

Here is a sample:

```json
{
  "mcpServers": {
    "ciso-assistant": {
      "command": "/Users/abder/.cargo/bin/uv",
      "args": [
        "--directory",
        "/Users/abder/mydev/ituitem/ciso-assistant-community/cli",
        "run",
        "ca_mcp.py"
      ]
    }
  }
}
```

4. make sure to kill and restart Claude Desktop app to apply the settings
5. Start a new chat and if the settings are correct, you should see `ciso-assistant` under the chat extensions. You will see a count of the supported `tools` which reflect the currently supported data feeds from the app.

<img width="1538" alt="image" src="https://github.com/user-attachments/assets/1345eb19-3f5e-4a0c-8abe-dae5a86dd59a" />


6. You can now chat with your data, either by mentioning some keywords like applied controls or risks, or explicitly asking about ciso assistant.
