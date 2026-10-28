import logging
import os

import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
    django.setup()
    logging.basicConfig(level=logging.INFO)

    import uvicorn

    from mcp_server.app import build_app

    uvicorn.run(
        build_app(),
        host=os.environ.get("CA_MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("CA_MCP_PORT", "8001")),
    )


if __name__ == "__main__":
    main()
