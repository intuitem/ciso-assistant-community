from django.core.management.base import BaseCommand
from auditlog.models import LogEntry

from django.conf import settings


class Command(BaseCommand):
    help = "Prunes auditlog entries to maintain maximum count"

    def _prune_queryset(self, queryset, keep):
        count = queryset.count()
        if count <= keep:
            return 0

        ids_to_delete = list(
            queryset.order_by("timestamp")[: count - keep].values_list("id", flat=True)
        )

        deleted_count = 0
        chunk_size = 1000
        for i in range(0, len(ids_to_delete), chunk_size):
            chunk = ids_to_delete[i : i + chunk_size]
            deleted_count += LogEntry.objects.filter(id__in=chunk).delete()[0]
        return deleted_count

    def handle(self, *args, **options):
        security_actions = getattr(settings, "AUDITLOG_SECURITY_ACTIONS", [])
        regular_keep = getattr(settings, "AUDITLOG_MAX_RECORDS", 50000)
        security_keep = getattr(settings, "AUDITLOG_SECURITY_MAX_RECORDS", 5000)

        regular = LogEntry.objects.exclude(action__in=security_actions)
        deleted_count = self._prune_queryset(regular, regular_keep)

        if security_actions:
            security = LogEntry.objects.filter(action__in=security_actions)
            deleted_count += self._prune_queryset(security, security_keep)

        if deleted_count:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully pruned {deleted_count} log entries")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Nothing to clean up"))
