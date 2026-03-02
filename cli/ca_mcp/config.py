"""Configuration module for CISO Assistant MCP server"""

import os
from dotenv import load_dotenv

# Load environment variables from .mcp.env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".mcp.env"))

# Configuration dictionary (for backward compatibility)
cli_cfg = dict()
auth_data = dict()
GLOBAL_FOLDER_ID = None

# Read TOKEN and VERIFY_CERTIFICATE from environment variables
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = os.getenv("VERIFY_CERTIFICATE", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)
HTTP_TIMEOUT = 30  # seconds
