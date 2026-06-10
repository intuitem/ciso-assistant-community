"""
Stress-test data generator: create a large population of users, each with its
own dedicated folder.

Designed for volume testing (e.g. validating list/pagination behaviour before
enabling bulk SCIM provisioning). Uses bulk_create in batches so it bypasses
per-row save() hooks, auditlog signals and IAM-group provisioning — which is
exactly what makes 250k rows tractable.

Usage:
    poetry run python manage.py populate_users                 # 250k users
    poetry run python manage.py populate_users --users 1000    # smaller run
    poetry run python manage.py populate_users --fresh         # wipe + recreate
    poetry run python manage.py populate_users --clean         # wipe only

All generated rows are tagged with a prefix so --clean can find and remove them
without touching real data.
"""

from allauth.account.models import EmailAddress
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from iam.models import Folder, User

DEFAULT_PREFIX = "loadtest"
EMAIL_DOMAIN = "loadtest.local"


class Command(BaseCommand):
    help = "Populate a large number of users, each with a dedicated folder, for volume testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=250_000,
            help="Number of users (and folders) to create (default: 250000).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5_000,
            help="Rows per bulk_create batch (default: 5000).",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default=DEFAULT_PREFIX,
            help=f"Tag applied to emails/folders for safe cleanup (default: {DEFAULT_PREFIX}).",
        )
        parser.add_argument(
            "--no-email-address",
            action="store_true",
            help="Skip creating allauth EmailAddress rows (faster, but users can't log in locally).",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all generated data and exit (no creation).",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete generated data first, then create a fresh population.",
        )

    def handle(self, *args, **options):
        total = options["users"]
        batch_size = options["batch_size"]
        prefix = options["prefix"]
        make_email = not options["no_email_address"]
        clean = options["clean"]
        fresh = options["fresh"]

        if clean or fresh:
            self._clean(prefix)
        if clean and not fresh:
            self.stdout.write(self.style.SUCCESS("Clean completed. No data created."))
            return

        root = Folder.get_root_folder()
        # Continue numbering after any rows left from a previous (non-clean) run
        # so emails stay unique.
        start = User.objects.filter(
            email__startswith=f"{prefix}-"
        ).count()
        unusable_pw = make_password(None)

        self.stdout.write(
            f"Creating {total} users + folders (prefix='{prefix}', "
            f"batch={batch_size}, email_address={make_email})..."
        )

        created = 0
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            self._create_batch(
                start + batch_start,
                start + batch_end,
                root,
                unusable_pw,
                prefix,
                make_email,
            )
            created += batch_end - batch_start
            self.stdout.write(f"  {created}/{total} users created...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created} users, {created} folders"
                f"{' and email addresses' if make_email else ''}."
            )
        )

    @transaction.atomic
    def _create_batch(self, lo, hi, root, unusable_pw, prefix, make_email):
        folders = [
            Folder(
                name=f"{prefix}-folder-{i:07d}",
                description=f"Load-test folder for user {i:07d}",
                parent_folder=root,
                content_type=Folder.ContentType.DOMAIN,
                create_iam_groups=False,
                builtin=False,
                is_published=True,
            )
            for i in range(lo, hi)
        ]
        Folder.objects.bulk_create(folders)

        users = [
            User(
                email=f"{prefix}-{i:07d}@{EMAIL_DOMAIN}",
                first_name="Load",
                last_name=f"Test {i:07d}",
                is_active=True,
                is_published=True,
                keep_local_login=False,
                password=unusable_pw,
                folder=folder,
                preferences={"lang": "en"},
            )
            for i, folder in zip(range(lo, hi), folders)
        ]
        User.objects.bulk_create(users)

        if make_email:
            EmailAddress.objects.bulk_create(
                [
                    EmailAddress(
                        user=user,
                        email=user.email,
                        verified=True,
                        primary=True,
                    )
                    for user in users
                ]
            )

    def _clean(self, prefix):
        self.stdout.write(f"Cleaning generated data (prefix='{prefix}')...")

        email_qs = EmailAddress.objects.filter(email__startswith=f"{prefix}-")
        n_emails = email_qs.count()
        email_qs._raw_delete(email_qs.db)

        user_qs = User.objects.filter(email__startswith=f"{prefix}-")
        n_users = user_qs.count()
        # _raw_delete skips signals/auditlog — essential at this scale.
        user_qs._raw_delete(user_qs.db)

        folder_qs = Folder.objects.filter(name__startswith=f"{prefix}-folder-")
        n_folders = folder_qs.count()
        folder_qs._raw_delete(folder_qs.db)

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {n_users} users, {n_folders} folders, {n_emails} email addresses."
            )
        )
