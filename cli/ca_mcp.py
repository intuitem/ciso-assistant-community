"""
CISO Assistant MCP Server - Backward Compatibility Wrapper

This file maintains backward compatibility by importing from the new modular structure.
The actual implementation is now in the ca_mcp/ module.

Transport is selected by CA_MCP_TRANSPORT (stdio by default, or "http").
"""

from ca_mcp.server import main

if __name__ == "__main__":
    main()
