import os
import sys
from pathlib import Path
from ciso_assistant.settings import LIBRARIES_PATH
from typing import Any
from django.core.management.base import BaseCommand
from core.models import StoredLibrary

import structlog

logger = structlog.getLogger(__name__)


class Command(BaseCommand):
    help = "Store libraries in the database"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--path", type=str, help="Path to library files")

    def handle(self, *args: Any, **options: Any) -> str | None:
        StoredLibrary.__init_class__()
        logger.info("Storing libraries")
        path = Path(options.get("path") or LIBRARIES_PATH)
        if path.is_dir():
            library_files = [
                f for f in path.iterdir() if f.is_file and f.suffix == ".yaml"
            ]
        else:
            library_files = [path]
        for fname in library_files:
            logger.info("Begin library file storage", filename=fname)
            error = StoredLibrary.store_library_file(fname)
            if error is not None:
                logger.error(
                    "Can't import libary file",
                    filename=fname,
                    error=error,
                )
            logger.info("End library file storage", filename=fname)
