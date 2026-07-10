from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync EPSS feed data into existing CVEs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to local EPSS CSV/gzip file (for air-gapped environments)",
        )

    def handle(self, *args, **options):
        from sec_intel.feeds import EPSSFeed

        file_path = Path(options["file"]) if options["file"] else None
        try:
            feed = EPSSFeed(file_path=file_path)
            count = feed.sync()
            self.stdout.write(
                self.style.SUCCESS(f"EPSS sync complete: {count} CVEs updated")
            )
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"EPSS sync failed: {e}"))
