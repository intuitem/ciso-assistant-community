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
        if mailer.custom_configuration() is not None:
            for spec in mailer.active_mailers():
                options = {k: v for k, v in spec.options.items() if k != "password"}
                self.stdout.write(
                    f"mailer {spec.alias} (custom): {spec.backend} {options}"
                )
        else:
            for line in describe(getattr(settings, "MAILERS", {}) or {}):
                self.stdout.write(line)
        self.stdout.write(f"sender: {mailer.sender_address() or '(unset)'}")

        result = mailer.send_test(recipient)

        for alias, error in result.skipped:
            self.stdout.write(self.style.WARNING(f"mailer {alias} skipped: {error}"))
        self._print_health()
        if not result.ok:
            raise CommandError(result.summary)
        self.stdout.write(self.style.SUCCESS(result.summary))

    def _print_health(self):
        from global_settings.models import MailerHealth

        for row in MailerHealth.objects.all():
            line = (
                f"health {row.alias} ({row.source}): {row.last_outcome} at "
                f"{row.last_attempt_at:%Y-%m-%d %H:%M:%S}"
            )
            if row.via_failover:
                line += ", reached by failover"
            if row.last_error:
                line += f", error: {row.last_error}"
            self.stdout.write(line)
