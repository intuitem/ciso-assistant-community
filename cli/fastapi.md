Setup MCP Server for CISO Assistant

sudo pip install -r requirements.txt
sudo pip install -r fastapi_requirements.txt

create/edit .mcp.env
Set the following:

TOKEN=(your generated token from inside CISO Assistant - refer to instruction item 2 in mcp.md)
VERIFY_CERTIFICATE=(true if using 3rd party cert, false if using host generated cert or no cert)
API_URL= (url value set in docker config for PUBLIC_BACKEND_API_EXPOSED_URL)
PORT=(the port this will listen on - cannot be one already in use)

Once done, run the fastapi_wrapper.py file (python3 fastapi_wrapper.py).

Open your Claude Desktop
Click File > Settings > Developer
Click Edit Config
Edit the file claude_desktop_config.json

Add the following (assumes this is the only MCP server)

{
  "mcpServers": {
    "ciso-assistant": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://xyzhost:3443/sse",
		"--allow-http"
      ]
    }
  }
}

Where http://xyzhost:3443 is the hostname of your CISO Assistant server and the Port defined in your .mcp.env file.
Ensure /sse is left at the end.

Save the file and fully restart Claude desktop (kill all running instances from Task Manager to properly close).