from contextvars import ContextVar

focus_folder_id_var = ContextVar("focus_folder_id", default=None)

# The MCP access of the request, set by the MCP listener: None for every other
# credential. Cleared when each request starts, so a streaming response keeps it.
mcp_access_var = ContextVar("mcp_access", default=None)
