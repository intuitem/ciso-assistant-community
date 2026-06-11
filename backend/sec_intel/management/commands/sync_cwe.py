from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync CWE catalog from MITRE into CWE records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to local CWE XML zip file (for air-gapped environments)",
        )

    def handle(self, *args, **options):
        from sec_intel.feeds import CWEFeed

        file_path = Path(options["file"]) if options["file"] else None
        try:
            feed = CWEFeed(file_path=file_path)
            result = feed.sync()
            self.stdout.write(
                self.style.SUCCESS(
                    f"CWE sync complete: {result['created']} created, {result['updated']} updated"
                )
            )
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"CWE sync failed: {e}"))
