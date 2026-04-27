from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Delete all security advisory records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            default=None,
            help="Only delete advisories from this source (CVE, EUVD, GHSA, other)",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        from sec_intel.models import SecurityAdvisory

        qs = SecurityAdvisory.objects.all()
        if options["source"]:
            qs = qs.filter(source=options["source"])

        count = qs.count()
        if count == 0:
            self.stdout.write("No security advisories to delete")
            return

        if not options["confirm"]:
            self.stdout.write(f"This will delete {count} security advisories.")
            answer = input("Are you sure? [y/N] ")
            if answer.lower() != "y":
                self.stdout.write("Aborted")
                return

        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} security advisories"))
