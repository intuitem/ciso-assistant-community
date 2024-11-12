from urllib.parse import urlparse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import (
    DefaultSocialAccountAdapter,
    MultipleObjectsReturned,
    warnings,
)
from allauth.socialaccount.models import app_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED

import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()


class AccountAdapter(DefaultAccountAdapter):
    def is_safe_url(self, url):
        allowed_hosts = {urlparse(settings.CISO_ASSISTANT_URL).hostname} | set(
            settings.ALLOWED_HOSTS
        )

        if urlparse(url).port:
            url = url.replace(":" + str(urlparse(url).port), "")

        return url_has_allowed_host_and_scheme(url, allowed_hosts=allowed_hosts)

    def is_open_for_signup(self, request):
        return False

    def authenticate(self, request, **credentials):
        try:
            serializer = AuthTokenSerializer(
                data={
                    "username": credentials.get("email"),
                    "password": credentials.get("password"),
                }
            )
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data["user"]
        except Exception:
            return None


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email_address = next(iter(sociallogin.account.extra_data.values()))[0]
        try:
            user = User.objects.get(email=email_address)
            sociallogin.user = user
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found."}, status=HTTP_401_UNAUTHORIZED
            )

    def list_apps(self, request, provider=None, client_id=None):
        """SSOSettings's can be setup in the database, or, via
        `settings.SOCIALACCOUNT_PROVIDERS`.  This methods returns a uniform list
        of all known apps matching the specified criteria, and blends both
        (db/settings) sources of data.
        """
        # NOTE: Avoid loading models at top due to registry boot...
        from .sso.models import SSOSettings

        # Map provider to the list of apps.
        provider_to_apps = {}

        # First, populate it with the DB backed apps.
        db_apps = SSOSettings.objects.all()
        if provider:
            db_apps = db_apps.filter(Q(provider=provider) | Q(provider_id=provider))
        if client_id:
            db_apps = db_apps.filter(client_id=client_id)
        for app in db_apps:
            apps = provider_to_apps.setdefault(app.provider, [])
            apps.append(app)

        # Then, extend it with the settings backed apps.
        for p, pcfg in app_settings.PROVIDERS.items():
            app_configs = pcfg.get("APPS")
            if app_configs is None:
                app_config = pcfg.get("APP")
                if app_config is None:
                    continue
                app_configs = [app_config]

            apps = provider_to_apps.setdefault(p, [])
            for config in app_configs:
                app = SSOSettings(provider=p)
                for field in [
                    "name",
                    "provider_id",
                    "client_id",
                    "secret",
                    "key",
                    "settings",
                ]:
                    if field in config:
                        setattr(app, field, config[field])
                if "certificate_key" in config:
                    warnings.warn("'certificate_key' should be moved into app.settings")
                    app.settings["certificate_key"] = config["certificate_key"]
                if client_id and app.client_id != client_id:
                    continue
                if (
                    provider
                    and app.provider_id != provider
                    and app.provider != provider
                ):
                    continue
                apps.append(app)

        # Flatten the list of apps.
        apps = []
        for provider_apps in provider_to_apps.values():
            apps.extend(provider_apps)
        return apps

    def get_app(self, request, provider, client_id=None):
        from .sso.models import SSOSettings

        apps = self.list_apps(request, provider=provider, client_id=client_id)
        if len(apps) > 1:
            visible_apps = [app for app in apps if not app.settings.get("hidden")]
            if len(visible_apps) != 1:
                raise MultipleObjectsReturned
            apps = visible_apps
        elif len(apps) == 0:
            raise SSOSettings.DoesNotExist()
        return apps[0]
