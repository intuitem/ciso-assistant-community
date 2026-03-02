import structlog
from django.core.management.base import BaseCommand
from core.models import *
from iam.models import User, Folder
from ciso_assistant.settings import CISO_ASSISTANT_SUPERUSER_EMAIL

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Send welcome email"

    def handle(self, *args, **kwargs):
        admin = User.objects.get(email=CISO_ASSISTANT_SUPERUSER_EMAIL)
        logger.info("Attempting to send welcome email", recipient=admin.email)
        try:
            admin.mailing(
                email_template_name="registration/first_connexion_email.html",
                subject="Welcome to CISO Assistant!",
            )
            logger.info("Welcome email sent successfully", recipient=admin.email)
            self.stdout.write(self.style.SUCCESS("Welcome mail sent successfully"))
        except Exception as e:
            logger.error(
                "Failed to send welcome email", recipient=admin.email, error=str(e)
            )
            self.stdout.write(self.style.ERROR(f"Cannot send welcome mail: {str(e)}"))
