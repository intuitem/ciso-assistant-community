from django.apps import AppConfig


class IamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"

    def ready(self):
        from django.apps import apps

        ServiceAccount = apps.get_model("iam", "ServiceAccount")

        self._patch_client_check_secret(ServiceAccount)

    def _patch_client_check_secret(self, ServiceAccount):
        """adapter hook for multi-secret/grace-period support."""
        from allauth.idp.oidc.models import Client
        from django.contrib.auth.hashers import check_password
        from django.utils import timezone

        original_check_secret = Client.check_secret

        def check_secret_with_grace_period(self, secret):
            if original_check_secret(self, secret):
                return True
            service_account = ServiceAccount.objects.filter(client=self).first()
            if not service_account or not service_account.previous_secret_hash:
                return False
            if (
                not service_account.previous_secret_expires_at
                or service_account.previous_secret_expires_at < timezone.now()
            ):
                return False
            return check_password(secret, service_account.previous_secret_hash)

        Client.check_secret = check_secret_with_grace_period
