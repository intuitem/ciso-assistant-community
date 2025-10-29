"""
CISO Assistant MCP Server - Backward Compatibility Wrapper

This file maintains backward compatibility by importing from the new modular structure.
The actual implementation is now in the ca_mcp/ module.
"""

from ca_mcp.server import run_server

if __name__ == "__main__":
    # Initialize and run the server
    run_server()
