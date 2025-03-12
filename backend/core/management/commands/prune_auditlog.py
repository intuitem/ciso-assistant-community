from django.core.management.base import BaseCommand
from auditlog.models import LogEntry

from django.conf import settings


class Command(BaseCommand):
    help = "Prunes auditlog entries to maintain maximum count"

    def handle(self, *args, **options):
        MAX_RECORDS = getattr(settings, "AUDITLOG_MAX_RECORDS", 50000) + 1000

        # Count all records
        count = LogEntry.objects.count()

        # If we exceed the limit, delete the oldest record(s)
        if count > MAX_RECORDS:
            # Get IDs of oldest records to delete
            ids_to_delete = LogEntry.objects.order_by("timestamp")[
                : count - MAX_RECORDS
            ].values_list("id", flat=True)

            # Delete in chunks to avoid memory issues
            deleted_count = 0
            chunk_size = 1000
            total_to_delete = len(ids_to_delete)

            for i in range(0, total_to_delete, chunk_size):
                chunk = ids_to_delete[i : i + chunk_size]
                result = LogEntry.objects.filter(id__in=chunk).delete()
                deleted_count += result[0]

            self.stdout.write(
                self.style.SUCCESS(f"Successfully pruned {deleted_count} log entries")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Nothing to clean up"))
