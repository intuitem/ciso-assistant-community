from django.core.management.base import BaseCommand
from auditlog.models import LogEntry

from django.conf import settings

from iam.signals import LOGIN_FAILED_ACTION


def prune(entries, max_records):
    """Delete the oldest of `entries` beyond `max_records`; return how many."""
    count = entries.count()
    if count <= max_records:
        return 0

    # Get IDs of oldest records to delete
    ids_to_delete = entries.order_by("timestamp")[: count - max_records].values_list(
        "id", flat=True
    )

    # Delete in chunks to avoid memory issues
    deleted_count = 0
    chunk_size = 1000
    total_to_delete = len(ids_to_delete)

    for i in range(0, total_to_delete, chunk_size):
        chunk = ids_to_delete[i : i + chunk_size]
        result = LogEntry.objects.filter(id__in=chunk).delete()
        deleted_count += result[0]
    return deleted_count


class Command(BaseCommand):
    help = "Prunes auditlog entries to maintain maximum count"

    def handle(self, *args, **options):
        MAX_RECORDS = getattr(settings, "AUDITLOG_MAX_RECORDS", 50000) + 1000

        # Failed logins are recorded without authentication, so they are capped
        # on their own: a flood of them cannot push other entries out.
        deleted_count = prune(
            LogEntry.objects.exclude(action=LOGIN_FAILED_ACTION), MAX_RECORDS
        ) + prune(LogEntry.objects.filter(action=LOGIN_FAILED_ACTION), MAX_RECORDS)

        if deleted_count:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully pruned {deleted_count} log entries")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Nothing to clean up"))
