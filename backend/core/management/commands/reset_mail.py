import structlog
from django.core.management.base import BaseCommand
from core.models import *
from iam.models import User, Folder
from ciso_assistant.settings import CISO_ASSISTANT_SUPERUSER_EMAIL
from django.utils.translation import gettext_lazy as _

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Send reset email"

    def handle(self, *args, **kwargs):
        admin = User.objects.get(email=CISO_ASSISTANT_SUPERUSER_EMAIL)
        logger.info("Attempting to send password reset email", recipient=admin.email)
        try:
            admin.mailing(
                email_template_name="registration/password_reset_email.html",
                subject=_("CISO Assistant: Password Reset"),
            )
            logger.info("Password reset email sent successfully", recipient=admin.email)
            self.stdout.write(self.style.SUCCESS("Reset mail sent successfully"))
        except Exception as e:
            logger.error(
                "Failed to send password reset email",
                recipient=admin.email,
                error=str(e),
            )
            self.stdout.write(self.style.ERROR(f"Cannot send reset mail: {str(e)}"))
