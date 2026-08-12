"""
Native Windows development runserver entrypoint

Place this script at the following path from the CISO Assistant repository root:
backend/.win_native_dev_runserver.py

Django's default development server listen backlog is small. In native Windows
development, runserver can drain bursts of incoming API connections more slowly
than on Linux. SvelteKit SSR may then open enough concurrent API connections to
fill that queue, which intermittently causes `ECONNREFUSED` on `127.0.0.1:8000`
before requests reach Django. This wrapper keeps the normal Django runserver
behavior, but raises the listen backlog through DJANGO_RUNSERVER_BACKLOG.
"""

import os
import sys

from django.core.management import execute_from_command_line
from django.core.servers import basehttp


def configure_runserver_backlog() -> None:
    backlog = int(os.environ.get("DJANGO_RUNSERVER_BACKLOG", "512"))
    basehttp.WSGIServer.request_queue_size = backlog
    basehttp.ThreadedWSGIServer.request_queue_size = backlog


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
    configure_runserver_backlog()
    execute_from_command_line(["manage.py", "runserver", *sys.argv[1:]])
