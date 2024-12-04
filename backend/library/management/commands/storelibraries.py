from pathlib import Path

import structlog, signal
from ciso_assistant.settings import LIBRARIES_PATH
from core.models import StoredLibrary
from django.core.management.base import BaseCommand

logger = structlog.getLogger(__name__)

signal.signal(signal.SIGINT, signal.SIG_DFL)


class Command(BaseCommand):
    help = "Store libraries in the database"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--path", type=str, help="Path to library files")

    def handle(self, *args, **options):
        StoredLibrary.__init_class__()
        path = Path(options.get("path") or LIBRARIES_PATH)
        if path.is_dir():
            library_files = sorted(
                f for f in path.iterdir() if f.is_file and f.suffix == ".yaml"
            )
        else:
            library_files = [path]
        for fname in library_files:
            # logger.info("Begin library file storage", filename=fname)
            try:
                library = StoredLibrary.store_library_file(fname, True)
                if library:
                    logger.info(
                        "Successfully stored library",
                        filename=fname,
                        library=library,
                    )
            except:
                logger.error("Invalid library file", filename=fname)
