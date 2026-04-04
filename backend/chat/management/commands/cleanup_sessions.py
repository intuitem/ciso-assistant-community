"""Delete old chat sessions to prevent unbounded DB growth."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Delete chat sessions older than N days (default 90). Messages cascade-delete."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Delete sessions with no activity in the last N days (default: 90)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        from chat.models import ChatSession

        days = options["days"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        # Find sessions where the latest message is older than cutoff
        # (or sessions with no messages at all older than cutoff)
        old_sessions = ChatSession.objects.filter(updated_at__lt=cutoff)
        count = old_sessions.count()

        if count == 0:
            self.stdout.write("No sessions to clean up.")
            return

        if dry_run:
            self.stdout.write(
                f"Would delete {count} session(s) older than {days} days."
            )
            return

        deleted, details = old_sessions.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} session(s) and {deleted - count} related object(s)."
            )
        )
