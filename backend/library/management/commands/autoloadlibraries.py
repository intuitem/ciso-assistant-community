import signal
from pathlib import Path

import structlog
from django.core.management.base import BaseCommand

from core.models import StoredLibrary

logger = structlog.getLogger(__name__)

signal.signal(signal.SIGINT, signal.SIG_DFL)


class Command(BaseCommand):
    help = "Load autoloaded libraries into the database"

    def handle(self, *args, **options):
        StoredLibrary.__init_class__()
        try:
            libs = StoredLibrary.objects.filter(autoload=True, is_loaded=False)
            for lib in libs:
                logger.info("Autoloading library", library=lib)
                lib.load()
        except Exception:
            logger.error("Failed to query autoloaded libraries", exc_info=True)
