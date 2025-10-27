import os
import shutil
import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = """Clone a CISO Assistant instance by copying the database and evidence attachments.

    This command creates a complete copy of a CISO Assistant instance, including:
    - SQLite database file
    - Evidence attachments directory

    Example:
        python manage.py clone_instance --dest-db /path/to/backup.sqlite3 --dest-attachments /path/to/backup/attachments
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-db",
            type=str,
            help="Path to source SQLite database (default: current database from settings)",
        )
        parser.add_argument(
            "--dest-db",
            type=str,
            required=True,
            help="Path to destination SQLite database",
        )
        parser.add_argument(
            "--source-attachments",
            type=str,
            help="Path to source attachments directory (default: MEDIA_ROOT from settings)",
        )
        parser.add_argument(
            "--dest-attachments",
            type=str,
            required=True,
            help="Path to destination attachments directory",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite destination files if they exist without prompting",
        )

    def get_dir_size(self, path):
        """Calculate total size of a directory in bytes."""
        total_size = 0
        if os.path.exists(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        return total_size

    def format_size(self, bytes_size):
        """Format bytes into human-readable size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"

    def validate_sqlite_db(self, db_path):
        """Validate that a file is a valid SQLite database."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                return len(tables) > 0
        except sqlite3.Error:
            return False

    def handle(self, *args, **options):
        # Get source database path from settings if not provided
        if options["source_db"]:
            source_db = options["source_db"]
        else:
            # Try to get SQLite database path from settings
            db_config = settings.DATABASES.get("default", {})
            if db_config.get("ENGINE") == "django.db.backends.sqlite3":
                source_db = db_config.get("NAME")
            else:
                raise CommandError(
                    "Source database not specified and default database is not SQLite. "
                    "Please specify --source-db for PostgreSQL databases."
                )

        # Get source attachments path from settings if not provided
        if options["source_attachments"]:
            source_attachments = options["source_attachments"]
        else:
            # Get from settings
            if hasattr(settings, "MEDIA_ROOT") and settings.MEDIA_ROOT:
                source_attachments = str(settings.MEDIA_ROOT)
            elif hasattr(settings, "LOCAL_STORAGE_DIRECTORY"):
                source_attachments = str(settings.LOCAL_STORAGE_DIRECTORY)
            else:
                raise CommandError(
                    "Source attachments directory not specified and could not be determined from settings. "
                    "Please specify --source-attachments."
                )

        dest_db = options["dest_db"]
        dest_attachments = options["dest_attachments"]
        force = options["force"]

        # Convert paths to absolute paths
        source_db = os.path.abspath(source_db)
        dest_db = os.path.abspath(dest_db)
        source_attachments = os.path.abspath(source_attachments)
        dest_attachments = os.path.abspath(dest_attachments)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("CISO Assistant Instance Cloning"))
        self.stdout.write("=" * 70)

        # Validate source database exists
        if not os.path.exists(source_db):
            raise CommandError(f"Source database not found: {source_db}")

        # Validate source database is a valid SQLite database
        if not self.validate_sqlite_db(source_db):
            raise CommandError(
                f"Source file is not a valid SQLite database: {source_db}"
            )

        # Check if destination database already exists
        if os.path.exists(dest_db) and not force:
            self.stdout.write(
                self.style.WARNING(f"Destination database already exists: {dest_db}")
            )
            try:
                confirm = input("Do you want to overwrite it? [y/N]: ")
                if confirm.lower() != "y":
                    raise CommandError("Operation cancelled.")
            except EOFError:
                raise CommandError(
                    "Operation cancelled (no input available). Use --force to skip prompts."
                )

        # Check if destination attachments directory already exists
        if (
            os.path.exists(dest_attachments)
            and os.listdir(dest_attachments)
            and not force
        ):
            self.stdout.write(
                self.style.WARNING(
                    f"Destination attachments directory is not empty: {dest_attachments}"
                )
            )
            confirm = input(
                "Do you want to continue? (existing files may be overwritten) [y/N]: "
            )
            if confirm.lower() != "y":
                raise CommandError("Operation cancelled.")

        # Calculate sizes
        db_size = os.path.getsize(source_db)
        attachments_size = self.get_dir_size(source_attachments)
        total_size = db_size + attachments_size

        # Display summary
        self.stdout.write(self.style.MIGRATE_HEADING("\nClone Summary:"))
        self.stdout.write(f"  Source database:     {source_db}")
        self.stdout.write(
            self.style.SUCCESS(f"  Database size:       {self.format_size(db_size)}")
        )
        self.stdout.write(f"  Source attachments:  {source_attachments}")
        self.stdout.write(
            self.style.SUCCESS(
                f"  Attachments size:    {self.format_size(attachments_size)}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Total size:          {self.format_size(total_size)}")
        )
        self.stdout.write(
            f"\n  Destination database:    {self.style.MIGRATE_LABEL(dest_db)}"
        )
        self.stdout.write(
            f"  Destination attachments: {self.style.MIGRATE_LABEL(dest_attachments)}"
        )

        # Final confirmation
        if not force:
            confirm = input("\nProceed with cloning? [y/N]: ")
            if confirm.lower() != "y":
                raise CommandError("Operation cancelled.")

        self.stdout.write(
            "\n" + self.style.MIGRATE_HEADING("Starting clone operation...") + "\n"
        )

        try:
            # Create destination directory for database if it doesn't exist
            dest_db_dir = os.path.dirname(dest_db)
            if dest_db_dir and not os.path.exists(dest_db_dir):
                os.makedirs(dest_db_dir, exist_ok=True)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created directory: {dest_db_dir}")
                )

            # Copy database
            self.stdout.write("Copying database...")
            shutil.copy2(source_db, dest_db)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Database copied successfully ({self.format_size(db_size)})"
                )
            )

            # Verify copied database
            if not self.validate_sqlite_db(dest_db):
                raise CommandError("Copied database validation failed!")

            # Copy attachments directory
            if os.path.exists(source_attachments):
                self.stdout.write("\nCopying attachments directory...")

                # Count files for progress
                file_count = sum(
                    [len(files) for _, _, files in os.walk(source_attachments)]
                )

                if file_count > 0:
                    # Copy directory tree, merging with existing files
                    shutil.copytree(
                        source_attachments, dest_attachments, dirs_exist_ok=True
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("No attachments found in source directory")
                    )
                    os.makedirs(dest_attachments, exist_ok=True)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Source attachments directory does not exist: {source_attachments}"
                    )
                )
                os.makedirs(dest_attachments, exist_ok=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        "✓ Created empty destination attachments directory"
                    )
                )

            # Success message
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("✓ Clone completed successfully!"))
            self.stdout.write("\nNew instance location:")
            self.stdout.write(f"  Database:    {dest_db}")
            self.stdout.write(f"  Attachments: {dest_attachments}")
            self.stdout.write(
                "\n"
                + self.style.WARNING("Note:")
                + " To use the cloned instance, update your CISO Assistant"
            )
            self.stdout.write(
                "configuration to point to the new database and attachments paths."
            )

        except PermissionError as e:
            raise CommandError(
                f"Permission error: {e}\n"
                "Make sure you have write permissions to the destination directory."
            )
        except shutil.Error as e:
            raise CommandError(f"Copy error: {e}")
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}")
