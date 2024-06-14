from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import QuerySet

from allauth.socialaccount.models import providers
from settings.models import GlobalSettings


class SSOSettingsQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self._result_cache = None
        self._iter = None

    def _fetch_all(self):
        if self._result_cache is None:
            try:
                _settings = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO)
                self._result_cache = [
                    SSOSettings(
                        provider=_settings.value.get("provider"),
                        provider_id=_settings.value.get("provider_id"),
                        provider_name=_settings.value.get("provider_name"),
                        client_id=_settings.value.get("client_id"),
                        secret=_settings.value.get("secret"),
                        key=_settings.value.get("key"),
                        settings=_settings.value.get("settings"),
                    )
                ]
            except ObjectDoesNotExist:
                self._result_cache = []

    def iterator(self):
        self._fetch_all()
        for obj in self._result_cache:
            yield obj

    def get(self, *args, **kwargs):
        self._fetch_all()
        if not self._result_cache:
            raise ObjectDoesNotExist("SSOSettings matching query does not exist.")
        return self._result_cache[0]


class SSOSettingsManager(models.Manager):
    def get_queryset(self):
        return SSOSettingsQuerySet(self.model, using=self._db)


class SSOSettings(GlobalSettings):
    objects = SSOSettingsManager()

    provider = models.CharField(
        verbose_name=_("provider"),
        max_length=30,
    )
    provider_id = models.CharField(
        verbose_name=_("provider ID"),
        max_length=200,
        blank=True,
    )
    provider_name = models.CharField(verbose_name=_("name"), max_length=200)
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
        managed = False
        proxy = True

    def __str__(self):
        return self.provider_name or "sso"

    def save(self, *args, **kwargs):
        _settings = self.global_settings
        _settings.value = {
            "provider": self.provider,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "client_id": self.client_id,
            "secret": self.secret,
            "key": self.key,
            "settings": self.settings,
        }
        _settings.save()

    def get_provider_display(self):
        _providers = {p[0]: p[1] for p in providers.registry.as_choices()}
        return _providers.get(self.provider)

    def get_provider(self, request):
        provider_class = providers.registry.get_class(self.provider)
        return provider_class(request=request, app=self)
