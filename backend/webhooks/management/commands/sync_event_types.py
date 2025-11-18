from django.core.management.base import BaseCommand
from webhooks.registry import webhook_registry
from webhooks.models import WebhookEventType


class Command(BaseCommand):
    help = "Syncs event types from the code registry to the WebhookEventType database model"

    def handle(self, *args, **options):
        self.stdout.write("Syncing event types with the database...")
        all_types = webhook_registry.get_all_event_types()

        # Find types in DB that are no longer in code
        types_in_db = set(WebhookEventType.objects.values_list("name", flat=True))
        removed_types = types_in_db - set(all_types)

        if removed_types:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(removed_types)} were removed from the codebase, but are still present in the database."
                )
            )
            for type_name in removed_types:
                self.stdout.write(self.style.WARNING(f"  - {type_name}"))

        # Add new types from code
        created_count = 0
        for event_name in all_types:
            obj, created = WebhookEventType.objects.get_or_create(name=event_name)
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Found {len(all_types)} total types. "
                f"Added {created_count} new types."
            )
        )
