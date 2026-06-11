import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Enrich security advisories with NVD data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cve-id",
            type=str,
            default=None,
            help="Specific CVE ID to enrich (e.g., CVE-2024-1234)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Enrich all existing CVEs that have empty fields",
        )
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to local NVD JSON response file",
        )

    def handle(self, *args, **options):
        from sec_intel.feeds import NVDFeed
        from sec_intel.models import SecurityAdvisory

        if options["cve_id"]:
            self._enrich_single(options["cve_id"], options.get("file"))
        elif options["all"]:
            self._enrich_all()
        else:
            self.stderr.write(self.style.ERROR("Specify --cve-id or --all"))

    def _enrich_single(self, cve_id: str, file_path: str | None):
        from sec_intel.feeds import NVDFeed
        from sec_intel.models import SecurityAdvisory

        cve = SecurityAdvisory.objects.filter(ref_id=cve_id).first()
        if not cve:
            self.stderr.write(self.style.ERROR(f"CVE {cve_id} not found in database"))
            return

        try:
            if file_path:
                raw = json.loads(Path(file_path).read_text())
            else:
                raw = NVDFeed.fetch_cve(cve.ref_id)

            if raw is None:
                self.stderr.write(
                    self.style.ERROR(f"Failed to fetch data for {cve_id}")
                )
                return

            fields = NVDFeed.parse_cve(raw)
            if not fields:
                self.stdout.write(f"No enrichment data found for {cve_id}")
                return

            # Verify the parsed data matches the target advisory
            parsed_id = fields.get("ref_id")
            if parsed_id and parsed_id != cve_id:
                self.stderr.write(
                    self.style.ERROR(
                        f"Data mismatch: file contains {parsed_id} but target is {cve_id}"
                    )
                )
                return

            update_fields = []
            for k, v in fields.items():
                current = getattr(cve, k, None)
                if current in (None, "", 0):
                    setattr(cve, k, v)
                    update_fields.append(k)

            if update_fields:
                cve.save(update_fields=update_fields)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Enriched {cve_id}: updated {', '.join(update_fields)}"
                    )
                )
            else:
                self.stdout.write(f"{cve_id} already has all fields populated")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to enrich {cve_id}: {e}"))

    def _enrich_all(self):
        from sec_intel.feeds import NVDFeed
        from sec_intel.models import SecurityAdvisory

        from django.db.models import Q

        cves = SecurityAdvisory.objects.filter(ref_id__startswith="CVE-").filter(
            Q(published_date__isnull=True)
            | Q(cvss_base_score__isnull=True)
            | Q(description__isnull=True)
            | Q(description="")
        )
        total = cves.count()

        if total == 0:
            self.stdout.write("No CVEs need enrichment")
            return

        self.stdout.write(f"Enriching {total} CVEs (rate-limited: ~10 per minute)...")
        count = 0
        for i, cve in enumerate(cves.iterator()):
            try:
                # Bypass settings check — management command is explicit admin action
                raw = NVDFeed.fetch_cve(cve.ref_id)
                if raw:
                    fields = NVDFeed.parse_cve(raw)
                    update_fields = []
                    for k, v in fields.items():
                        current = getattr(cve, k, None)
                        if current in (None, "", 0):
                            setattr(cve, k, v)
                            update_fields.append(k)
                    if update_fields:
                        cve.save(update_fields=update_fields)
                        count += 1
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(f"Failed to enrich {cve.ref_id}: {e}")
                )

            if (i + 1) % 10 == 0:
                self.stdout.write(f"  Progress: {i + 1}/{total}")

            # NVD rate limit: ~5 requests per 30 seconds without API key
            time.sleep(6)

        self.stdout.write(self.style.SUCCESS(f"Enriched {count}/{total} CVEs"))
