from django.core.management.base import BaseCommand
from core.models import *
from iam.models import User, Folder
from ciso_assistant.settings import CISO_ASSISTANT_SUPERUSER_EMAIL


class Command(BaseCommand):
    help = "Send welcome email"

    def handle(self, *args, **kwargs):
        admin = User.objects.get(email=CISO_ASSISTANT_SUPERUSER_EMAIL)
        print(admin)
        try:
            admin.mailing(
                email_template_name="registration/first_connexion_email.html",
                subject="Welcome to CISO Assistant!",
            )
            self.stdout.write("welcome mail sent")
        except Exception as e:
            self.stdout.write("cannot send welcome mail")
