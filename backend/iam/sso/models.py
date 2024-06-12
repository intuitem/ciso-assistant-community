from allauth.socialaccount.models import providers, SocialAppManager
from django.db import models
from core.base_models import AbstractBaseModel
from django.utils.translation import gettext_lazy as _

from iam.models import FolderMixin


class IdentityProvider(AbstractBaseModel, FolderMixin):
    objects = SocialAppManager()

    # The provider type, e.g. "google", "telegram", "saml".
    provider = models.CharField(
        verbose_name=_("provider"),
        max_length=30,
    )
    # For providers that support subproviders, such as OpenID Connect and SAML,
    # this ID identifies that instance. SocialAccount's originating from app
    # will have their `provider` field set to the `provider_id` if available,
    # else `provider`.
    provider_id = models.CharField(
        verbose_name=_("provider ID"),
        max_length=200,
        blank=True,
    )
    name = models.CharField(verbose_name=_("name"), max_length=200)
    client_id = models.CharField(
        verbose_name=_("client id"),
        max_length=191,
        help_text=_("App ID, or consumer key"),
    )
    secret = models.CharField(
        verbose_name=_("secret key"),
        max_length=191,
        blank=True,
        help_text=_("API secret, client secret, or consumer secret"),
    )
    key = models.CharField(
        verbose_name=_("key"), max_length=191, blank=True, help_text=_("Key")
    )
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("identity provider")
        verbose_name_plural = _("identity providers")

    def __str__(self):
        return self.name

    def get_provider_display(self):
        _providers = {p[0]: p[1] for p in providers.registry.as_choices()}
        return _providers.get(self.provider)

    def get_provider(self, request):
        provider_class = providers.registry.get_class(self.provider)
        return provider_class(request=request, app=self)
