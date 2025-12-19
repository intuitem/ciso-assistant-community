import signal
from pathlib import Path

import structlog
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef

from ciso_assistant.settings import LIBRARIES_PATH
from core.models import StoredLibrary, LoadedLibrary

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
            except Exception:
                logger.error("Invalid library file", filename=fname)

        invisible_libraries = (
            LoadedLibrary.objects.filter(
                builtin=False,
            )
            .annotate(
                is_stored=Exists(StoredLibrary.objects.filter(urn=OuterRef("urn")))
            )
            .filter(is_stored=False)
        )

        # If a user loaded a custom library with an urn U and then deleted the stored library with an urn U
        # Then the user would not be able to see the library in the frontend libraries list view as it fetches from the stored-libraries endpoint, making the library effectively "invisible".
        # This fixes this problem by recreating a StoredLibrary for every "orphaned" custom library.
        # The library will fail to be reloaded if the user ever unloads it (because content is empty(== dict()))
        # In that case the user will have to delete it and reupload it again to get back a sane version of the StoredLibrary.
        for library in invisible_libraries:
            StoredLibrary.objects.create(
                urn=library.urn,
                locale=library.locale,
                name=library.name,
                description=library.description,
                is_published=True,
                annotation=library.annotation,
                copyright=library.copyright,
                provider=library.provider,
                packager=library.packager,
                publication_date=library.publication_date,
                translations=library.translations,
                builtin=library.builtin,
                objects_meta=library.objects_meta,
                dependencies=[
                    dependency.urn for dependency in library.dependencies.all()
                ],
                version=library.version,
                ref_id=library.ref_id,
                is_loaded=True,
                hash_checksum="0" * 64,
                content=dict(),
                autoload=True,
            )
