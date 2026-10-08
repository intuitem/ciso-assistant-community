"""Send a test email through the configured mailers and report the outcome.

The logic lives in ``core.mailer.send_test`` so the UI can offer the same
check; this command is the shell entry point for operators.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ciso_assistant.mailers import describe
from core import mailer


class Command(BaseCommand):
    help = "Send a test email to the given address through the configured mailers."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="address to send the test email to")

    def handle(self, *args, recipient, **options):
        for line in describe(getattr(settings, "MAILERS", {}) or {}):
            self.stdout.write(line)
        self.stdout.write(f"sender: {settings.DEFAULT_FROM_EMAIL or '(unset)'}")

        result = mailer.send_test(recipient)

        for alias, error in result.skipped:
            self.stdout.write(self.style.WARNING(f"mailer {alias} skipped: {error}"))
        if not result.ok:
            raise CommandError(result.summary)
        self.stdout.write(self.style.SUCCESS(result.summary))
