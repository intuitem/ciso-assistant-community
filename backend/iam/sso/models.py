import structlog
from allauth.socialaccount.models import providers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _

from global_settings.models import GlobalSettings
from iam.sso.saml.defaults import DEFAULT_SAML_SETTINGS

logger = structlog.get_logger(__name__)


class SSOSettingsQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self._result_cache = None
        self._iter = None

    def _fetch_all(self):
        if self._result_cache is None:
            if not GlobalSettings.objects.filter(
                name=GlobalSettings.Names.SSO
            ).exists():
                logger.info("SSO settings not found, creating default settings")
                _settings = GlobalSettings.objects.create(
                    name=GlobalSettings.Names.SSO,
                    value={"client_id": "0", "settings": DEFAULT_SAML_SETTINGS},
                )
                logger.info("SSO settings created", settings=_settings.value)
            else:
                _settings = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO)

            self._result_cache = [
                SSOSettings(
                    id=_settings.id,
                    name=_settings.name,
                    created_at=_settings.created_at,
                    updated_at=_settings.updated_at,
                    is_published=_settings.is_published,
                    is_enabled=_settings.value.get("is_enabled"),
                    provider=_settings.value.get("provider"),
                    client_id=_settings.value.get("client_id"),
                    provider_id=_settings.value.get("provider_id"),
                    provider_name=_settings.value.get("name"),
                    secret=_settings.value.get("secret"),
                    key=_settings.value.get("key"),
                    settings=_settings.value.get("settings"),
                )
            ]

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

    is_enabled = models.BooleanField(
        verbose_name=_("is enabled"),
        default=False,
    )

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
        default="0",
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

    def get_name(self):
        return GlobalSettings.Names.SSO.label

    def __str__(self):
        return self.get_name()

    def save(self, *args, **kwargs):
        raise NotImplementedError("SSOSettings is read-only.")

    def get_provider_display(self):
        _providers = {p[0]: p[1] for p in providers.registry.as_choices()}
        return _providers.get(self.provider)

    def get_provider(self, request):
        provider_class = providers.registry.get_class(self.provider)
        return provider_class(request=request, app=self)
