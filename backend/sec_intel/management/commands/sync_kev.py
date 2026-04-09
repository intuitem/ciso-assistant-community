from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync KEV feed data into existing CVEs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to local KEV JSON file (for air-gapped environments)",
        )

    def handle(self, *args, **options):
        from sec_intel.feeds import KEVFeed

        file_path = Path(options["file"]) if options["file"] else None
        try:
            feed = KEVFeed(file_path=file_path)
            result = feed.sync()
            self.stdout.write(
                self.style.SUCCESS(
                    f"KEV sync complete: {result['created']} created, {result['updated']} updated"
                )
            )
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"KEV sync failed: {e}"))
