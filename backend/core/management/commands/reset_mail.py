from django.core.management.base import BaseCommand
from core.models import *
from iam.models import User, Folder
from ciso_assistant.settings import CISO_ASSISTANT_SUPERUSER_EMAIL


class Command(BaseCommand):
    help = "Send reset email"

    def handle(self, *args, **kwargs):
        admin = User.objects.get(email=CISO_ASSISTANT_SUPERUSER_EMAIL)
        print(admin)
        try:
            admin.mailing(
                email_template_name="registration/password_reset_email.html",
                subject="CISO Assistant: Password Reset",
            )
            self.stdout.write("reset mail sent")
        except Exception as e:
            self.stdout.write("cannot send reset mail")
