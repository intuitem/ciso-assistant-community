import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def startup(sender: AppConfig, **kwargs):
    from .models import GlobalSettings
    from allauth.socialaccount.providers.saml.provider import SAMLProvider

    default_attribute_mapping = SAMLProvider.default_attribute_mapping

    settings = {
        "attribute_mapping": {
            "uid": default_attribute_mapping["uid"],
            "email_verified": default_attribute_mapping["email_verified"],
            "email": default_attribute_mapping["email"],
        },
        "idp": {
            "entity_id": "",
            "metadata_url": "",
            "sso_url": "",
            "slo_url": "",
            "x509cert": "",
        },
        "sp": {
            "entity_id": "ciso-assistant",
        },
        "advanced": {
            "allow_repeat_attribute_name": True,
            "allow_single_label_domains": False,
            "authn_request_signed": False,
            "digest_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "logout_request_signed": False,
            "logout_response_signed": False,
            "metadata_signed": False,
            "name_id_encrypted": False,
            "reject_deprecated_algorithm": True,
            "reject_idp_initiated_sso": True,
            "signature_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "want_assertion_encrypted": False,
            "want_assertion_signed": False,
            "want_attribute_statement": True,
            "want_message_signed": False,
            "want_name_id": False,
            "want_name_id_encrypted": False,
        },
    }

    if not GlobalSettings.objects.filter(name=GlobalSettings.Names.SSO).exists():
        GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.SSO,
            value={"client_id": "0", "settings": settings},
        )


class SettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settings"

    def ready(self):
        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
