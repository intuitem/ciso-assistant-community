from urllib.parse import urlparse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.mfa.adapter import DefaultMFAAdapter
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
            user = serializer.validated_data["user"]
            if not user.is_local:
                raise NotImplementedError(
                    "This user is not allowed to use local login."
                )

            return user
        except Exception:
            return None


class MFAAdapter(DefaultMFAAdapter):
    def is_mfa_enabled(self, user, types=None) -> bool:
        from allauth.account.authentication import get_authentication_records
        from allauth.core import context

        # Skip local MFA challenge for SSO logins — the IdP already
        # authenticated the user.
        records = get_authentication_records(context.request)
        if any(r.get("method") == "socialaccount" for r in records):
            return False

        return super().is_mfa_enabled(user, types=types)

    def get_public_key_credential_rp_entity(self):
        rp_id = urlparse(settings.CISO_ASSISTANT_URL).hostname
        return {
            "id": rp_id,
            "name": "CISO Assistant",
        }


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    @staticmethod
    def _find_email_in_dict(data, _depth=0, _max_depth=5):
        """Recursively search for an email in a dict or list, checking known keys at each level."""
        if _depth >= _max_depth:
            return None
        if isinstance(data, dict):
            email = data.get("email") or data.get("email_address")
            if isinstance(email, str) and email:
                return email
            if isinstance(email, list):
                candidate = next((e for e in email if isinstance(e, str) and e), None)
                if candidate:
                    return candidate
            for value in data.values():
                if isinstance(value, (dict, list)):
                    email = SocialAccountAdapter._find_email_in_dict(
                        value, _depth=_depth + 1, _max_depth=_max_depth
                    )
                    if email:
                        return email
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    email = SocialAccountAdapter._find_email_in_dict(
                        item, _depth=_depth + 1, _max_depth=_max_depth
                    )
                    if email:
                        return email
        return None

    @staticmethod
    def _extract_name_claims(sociallogin):
        """
        Pull (first_name, last_name) out of the sociallogin payload, regardless
        of provider shape. Falls back to '' so JIT user creation never crashes
        on a sparse IdP.
        """
        extra = sociallogin.account.extra_data
        provider = sociallogin.account.provider

        def _first(value):
            if isinstance(value, list):
                return next((v for v in value if isinstance(v, str) and v), "")
            return value or ""

        if provider == "saml":
            attrs = extra.get("attributes", {}) or {}
            first = _first(attrs.get("first_name") or attrs.get("givenName"))
            last = _first(attrs.get("last_name") or attrs.get("familyName"))
            return first, last

        for source in (extra.get("userinfo", {}), extra.get("id_token", {}), extra):
            if not isinstance(source, dict):
                continue
            first = source.get("given_name") or source.get("givenName")
            last = source.get("family_name") or source.get("familyName")
            if first or last:
                return first or "", last or ""

            # Some IdPs only emit a combined "name" claim.
            name = source.get("name")
            if isinstance(name, str) and name.strip():
                parts = name.strip().split(None, 1)
                return parts[0], parts[1] if len(parts) > 1 else ""

        return "", ""

    @staticmethod
    def _extract_groups_from_sociallogin(sociallogin, oidc_claim, saml_attr):
        """Return a list of IdP group identifiers from the sociallogin extra_data."""
        extra = sociallogin.account.extra_data
        provider = sociallogin.account.provider

        if provider == "saml":
            attrs = extra.get("attributes", {})
            raw = attrs.get(saml_attr, [])
            if isinstance(raw, str):
                return [raw]
            return list(raw) if raw else []

        for source in (extra.get("userinfo", {}), extra.get("id_token", {}), extra):
            raw = source.get(oidc_claim)
            if raw is not None:
                return (
                    [str(raw)] if not isinstance(raw, list) else [str(g) for g in raw]
                )
        return []

    @staticmethod
    def _sync_idp_groups(user, sociallogin):
        """
        Sync the user's managed UserGroup memberships from IdP group claims.

        Only UserGroups that have at least one IdPGroupMapping ("managed"
        groups) are ever touched; all other memberships are left untouched.

        Behavior is governed by two flags under settings.group_sync:
          - enabled:        master switch. If false, sync is skipped entirely.
          - authoritative:  if true the IdP is the source of truth — any managed
                            membership the IdP no longer claims is removed,
                            including the case where the IdP sends no matching
                            group at all. If false, sync is additive
                            (memberships are only added, never removed).
        """
        from iam import group_membership as gm
        from iam.models import IdPGroupMapping
        from iam.sso.models import SSOSettings

        extra = sociallogin.account.extra_data
        logger.debug(
            "idp_group_sync: extra_data snapshot",
            provider=sociallogin.account.provider,
            extra_keys=list(extra.keys()),
            userinfo_keys=list(extra.get("userinfo", {}).keys()),
            id_token_keys=list(extra.get("id_token", {}).keys()),
        )

        try:
            cfg = (SSOSettings.objects.get().settings or {}).get("group_sync", {})
        except Exception:
            return

        if not cfg.get("enabled", False):
            logger.debug("idp_group_sync: disabled, skipping", user_id=str(user.id))
            return

        authoritative = cfg.get("authoritative", False)
        oidc_claim = cfg.get("oidc_groups_claim", "groups")
        saml_attr = cfg.get("saml_groups_attribute", "groups")

        idp_group_ids = SocialAccountAdapter._extract_groups_from_sociallogin(
            sociallogin, oidc_claim, saml_attr
        )
        logger.info(
            "idp_group_sync: extracted groups",
            user_id=str(user.id),
            oidc_claim=oidc_claim,
            saml_attr=saml_attr,
            idp_group_ids=idp_group_ids,
            authoritative=authoritative,
            mapping_count=IdPGroupMapping.objects.count(),
        )

        # Reconcile the user's SSO-channel memberships through the provenance
        # side-table. Additive always; when authoritative, SSO rows for routes
        # the IdP no longer claims are removed. Manual and SCIM memberships are
        # never touched, so each provisioning channel owns only its own rows.
        gm.sync_sso_user(user, idp_group_ids, authoritative)
        logger.info(
            "idp_group_sync: reconciled",
            user_id=str(user.id),
            authoritative=authoritative,
            claimed=idp_group_ids,
        )

    def pre_social_login(self, request, sociallogin):
        extra = sociallogin.account.extra_data
        logger.debug(
            "pre_social_login: extra_data received",
            extra_data=extra,
            provider=sociallogin.account.provider,
        )
        # Primary lookup (legacy format)
        email_address = extra.get("email") or extra.get("email_address")
        # allauth 65.8.0+ stores userinfo under "userinfo" key
        if not email_address:
            userinfo = extra.get("userinfo", {})
            email_address = userinfo.get("email") or userinfo.get("email_address")
        # Also check id_token claims (for OIDC providers)
        if not email_address:
            id_token = extra.get("id_token", {})
            email_address = id_token.get("email") or id_token.get("email_address")
        # Fallback: check preferred_username / upn (common in IdPs that scope
        # the OIDC `email` claim and surface the user principal name instead).
        if not email_address:
            for source in [extra, extra.get("userinfo", {}), extra.get("id_token", {})]:
                candidate = source.get("preferred_username") or source.get("upn")
                # preferred_username/upn can be a non-email identifier, only accept if it contains '@'
                if candidate and "@" in candidate:
                    email_address = candidate
                    break
        # Fallback: deep search in nested dicts (some IdPs nest email in sub-objects like "attributes")
        if not email_address:
            email_address = self._find_email_in_dict(extra)
        # Fallback: first string value containing '@'
        if not email_address:
            email_address = next(
                (v for v in extra.values() if isinstance(v, str) and "@" in v), None
            )
        if isinstance(email_address, list):
            # We assume the first email is the primary one
            email_address = email_address[0] if email_address else None
        if not email_address:
            logger.error(
                "pre_social_login: no email found in extra_data",
                extra_data_keys=list(extra.keys()),
                userinfo_keys=list(extra.get("userinfo", {}).keys()),
                id_token_keys=list(extra.get("id_token", {}).keys()),
            )
            return Response(
                {"message": "Email not provided."}, status=HTTP_401_UNAUTHORIZED
            )
        logger.debug(
            "pre_social_login: resolved email from IdP",
            idp_email=email_address,
            idp_email_repr=repr(email_address),
            provider=sociallogin.account.provider,
        )
        try:
            user = User.objects.get(email__iexact=email_address)
            logger.debug(
                "pre_social_login: user matched",
                idp_email=email_address,
                db_email=user.email,
                user_id=str(user.id),
                is_active=user.is_active,
            )
            sociallogin.user = user
            sociallogin.connect(request, user)
            logger.info(
                "pre_social_login: social account connected",
                provider=sociallogin.account.provider,
                user_id=str(user.id),
            )
            self._sync_idp_groups(user, sociallogin)
        except User.DoesNotExist:
            # Just-in-time provisioning: the IdP already authenticated this
            # person, so we create the local user record on the fly. Group
            # membership is then driven by _sync_idp_groups below.
            from iam.models import Folder

            first_name, last_name = self._extract_name_claims(sociallogin)
            try:
                from global_settings.models import GlobalSettings

                general = GlobalSettings.objects.filter(name="general").first()
                default_lang = (
                    general.value.get("default_language", "en")
                    if general and isinstance(general.value, dict)
                    else "en"
                )
            except Exception:
                default_lang = "en"

            user = User(
                email=email_address.lower(),
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_published=True,
                keep_local_login=False,
                folder=Folder.get_root_folder(),
                preferences={"lang": default_lang},
            )
            user.set_unusable_password()
            user.save()

            try:
                from allauth.account.models import EmailAddress

                EmailAddress.objects.get_or_create(
                    user=user,
                    email=user.email,
                    defaults={"verified": True, "primary": True},
                )
            except Exception:
                pass

            logger.info(
                "pre_social_login: JIT user provisioned",
                provider=sociallogin.account.provider,
                user_id=str(user.id),
                email=user.email,
            )
            sociallogin.user = user
            sociallogin.connect(request, user)
            self._sync_idp_groups(user, sociallogin)

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
