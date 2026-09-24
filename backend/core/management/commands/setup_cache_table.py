from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, router


class Command(BaseCommand):
    help = (
        "Create the tables behind any database-backed cache, in whichever database "
        "the routers assign them to. Idempotent, and a no-op when no cache is "
        "database-backed."
    )

    # Nothing else has to exist yet, so this is safe to run before `migrate` --
    # which is where it has to run, because `migrate` ends with core.startup and
    # that reads the cache.
    requires_system_checks = []
    requires_migrations_checks = False

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        for alias in settings.CACHES:
            cache = caches[alias]
            if not isinstance(cache, BaseDatabaseCache):
                continue
            database = router.db_for_write(cache.cache_model_class) or DEFAULT_DB_ALIAS
            call_command(
                "createcachetable",
                cache._table,
                database=database,
                verbosity=verbosity,
            )
