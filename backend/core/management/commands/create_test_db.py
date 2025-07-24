import signal
import shutil
import os
from typing import Callable

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from django.apps import apps

from iam.models import User, Folder, _get_root_folder
from core.apps import startup

signal.signal(signal.SIGINT, signal.SIG_DFL)

TEST_ADMIN_EMAIL = "admin@tests.com"
TEST_ADMIN_PASSWORD = "1234"
INITIAL_BACKUP_FNAME = "initial-db-backup.sqlite3"
DB_DIRECTORY = settings.DATABASES["default"]["NAME"].parent
TEST_DB_DIRECTORY = DB_DIRECTORY / "tests"
BLANK_DB_NAME = "blank-test-database.sqlite3"

# mapping(test_name => list of objects/lazy-loaded objects to create)
TEST_DATA: dict[str, list[models.Model | Callable[[], models.Model]]] = {
    "detailed/compliance-assessments.test.ts": [
        # Lambda functions serve as lazy-loaded objects
        lambda: Folder(
            name="Compliance-Assessments Test Domain", parent_folder=_get_root_folder()
        )
    ]
}


class Command(BaseCommand):
    help = "Create functional test databases (if this command corrupted the main database use the backup stored at initial-db-backup.sqlite3)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-k",
            "--keep-blank-db",
            action="store_true",
            help=f"Use the current cached blank database({BLANK_DB_NAME}) if it exists, otherwise create it and store it for later use.",
        )

    def handle(self, *args, **options):
        keep_blank_db = options["keep_blank_db"]

        sqlite_file_path = settings.DATABASES["default"]["NAME"]
        backup_file_path = DB_DIRECTORY / INITIAL_BACKUP_FNAME
        if not TEST_DB_DIRECTORY.exists():
            TEST_DB_DIRECTORY.mkdir()
        blank_test_db_file_path = TEST_DB_DIRECTORY / BLANK_DB_NAME

        shutil.copy(sqlite_file_path, backup_file_path)
        if keep_blank_db and blank_test_db_file_path.exists():
            shutil.copy(blank_test_db_file_path, sqlite_file_path)
        else:
            with open(sqlite_file_path, "wb") as f:
                pass

            call_command("migrate")
            app_config = apps.get_app_config("core")
            startup(app_config)

            call_command("createsuperuser", interactive=False, email=TEST_ADMIN_EMAIL)
            user = User.objects.get(email=TEST_ADMIN_EMAIL)
            user.set_password(TEST_ADMIN_PASSWORD)
            user.save()
            shutil.copy(sqlite_file_path, blank_test_db_file_path)

        for test_file_path, objects_to_create in TEST_DATA.items():
            test_name = test_file_path.split("/")[-1].split(".")[0]
            test_sqlite_filename = f"db/tests/{test_name}.sqlite3"

            for obj in objects_to_create:
                # Handle lazy-loaded objects (where obj is a lambda function)
                if callable(obj):
                    obj = obj()
                obj.save()
            shutil.copy(sqlite_file_path, test_sqlite_filename)
            shutil.copy(blank_test_db_file_path, sqlite_file_path)

        shutil.copy(backup_file_path, sqlite_file_path)
        if not keep_blank_db:
            os.remove(blank_test_db_file_path)
        os.remove(backup_file_path)
