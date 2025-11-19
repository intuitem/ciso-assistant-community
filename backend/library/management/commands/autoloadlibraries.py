import signal

import structlog
from django.core.management.base import BaseCommand
from django.db.models import Subquery, OuterRef, Max

from core.models import LoadedLibrary, StoredLibrary

logger = structlog.getLogger(__name__)

signal.signal(signal.SIGINT, signal.SIG_DFL)


class Command(BaseCommand):
    help = "Load/Update from autoloaded libraries into the database"

    def handle(self, *args, **options):
        StoredLibrary.__init_class__()
        try:
            libs = StoredLibrary.objects.filter(autoload=True, is_loaded=False)
            for lib in libs:
                logger.info("Autoloading library", library=lib)
                lib.load()
        except Exception:
            logger.error("Failed to query autoloaded libraries", exc_info=True)

        try:
            libs_to_update = LoadedLibrary.objects.filter(
                version__lt=Subquery(
                    StoredLibrary.objects.filter(urn=OuterRef("urn"), autoload=True)
                    .values("urn")
                    .annotate(max_version=Max("version"))
                    .values("max_version")
                )
            )
            for lib in libs_to_update:
                if (error_msg := lib.update()) is not None:
                    logger.error(
                        "Failed to automatically update library",
                        library=lib,
                        error_msg=error_msg,
                    )
        except:
            pass
