from urllib.parse import urlparse
import ipaddress
import structlog
import time
from typing import Optional

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.headless.base.response import RateLimitResponse
from allauth.mfa.adapter import DefaultMFAAdapter
from allauth.socialaccount.adapter import (
    DefaultSocialAccountAdapter,
    MultipleObjectsReturned,
    warnings,
)
from allauth.socialaccount.models import app_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED
from django.contrib.contenttypes.models import ContentType
from auditlog.models import LogEntry
from auditlog.cid import get_cid
from auditlog.context import set_actor

from iam.rate_limiting import get_ban_cache
from global_settings.models import GlobalSettings
from global_settings.serializers import InfraConfigSerializer

logger = structlog.get_logger(__name__)

User = get_user_model()

DEFAULT_ATTRIBUTE_MAPPING_GROUPS = ["groups"]


def parse_ip(
    ip_address: str,
) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """
    Parse an IP address (which may come from the `X-Forwarded-For` HTTP header).

    Accepts:
    - `1.2.3.4`, `1.2.3.4:5678`, `2001:db8::1`, `[2001:db8::1]` and `[2001:db8::1]:443`.
    - IPv4-mapped IPv6 addresses (`::ffff:1.2.3.4`) are converted to IPv4.

    Return `None` if `ip_address` is not a valid IP address.
    """
    ip_address = (ip_address or "").strip()
    if ip_address.startswith("["):
        ip_address = ip_address[1:].split("]", 1)[0]
    elif ip_address.count(":") == 1:
        ip_address = ip_address.split(":", 1)[0]

    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return

    if isinstance(parsed_ip, ipaddress.IPv6Address) and parsed_ip.ipv4_mapped:
        return parsed_ip.ipv4_mapped
    return parsed_ip


def is_in_networks(
    target_ip: str | ipaddress.IPv4Address | ipaddress.IPv6Address,
    ip_networks: list[str],
) -> bool:
    """
    Return `True` if the `target_ip` match one of the IP/CIDR Range in `ip_networks`, return `False` otherwise.

    Invalid `target_ip` and invalid `ip_networks` entries never raise (they do not match anything).
    """
    ip = target_ip if not isinstance(target_ip, str) else parse_ip(target_ip)
    if ip is None:
        return False

    for raw_network in ip_networks:
        try:
            network = ipaddress.ip_network(str(raw_network).strip(), strict=False)
        except ValueError:
            continue

        if network.version == ip.version and ip in network:
            return True

    return False


def resolve_client_ip(
    request: Optional[HttpRequest], proxy_ips: list[str]
) -> Optional[str]:
    """Return the real client IP address from which the `request` originates (`None` if it can't be determined)."""
    if request is None:
        return

    client_ip = parse_ip(request.META.get("REMOTE_ADDR", ""))
    if client_ip is None:
        return

    def is_trusted_proxy(ip) -> bool:
        return ip.is_loopback or is_in_networks(ip, proxy_ips)

    if is_trusted_proxy(client_ip):
        x_forwarded_ip_entry = request.headers.get("X-Forwarded-For", "").split(",")[-1]
        x_forwarded_ip = parse_ip(x_forwarded_ip_entry)
        if x_forwarded_ip is None:
            # Malformed entry (nothing on its left can be trusted).
            return str(client_ip)

        return str(x_forwarded_ip)
    else:
        return str(client_ip)


AUDIT_LOG_COUNT_TIME_UNIT = 86400
AUDIT_LOG_COUNT: tuple[int, int] = (
    int(time.monotonic() / AUDIT_LOG_COUNT_TIME_UNIT),
    0,
)
AUDIT_LOG_LIMIT = 500


def create_ip_ban_audit_log(ip_address: str, user: Optional[User]):
    global AUDIT_LOG_COUNT
    start_time, count = AUDIT_LOG_COUNT
    current_time = int(time.monotonic() / AUDIT_LOG_COUNT_TIME_UNIT)
    if current_time > start_time:
        # Reset the `count` every `AUDIT_LOG_COUNT_TIME_UNIT` seconds.
        count = 0

    if count >= AUDIT_LOG_LIMIT:
        # Naive rate limiting to limit IP ban audit log spamming.
        return

    AUDIT_LOG_COUNT = (current_time, count + 1)

    try:
        from enterprise_core.models import LogEntryAction

        action = LogEntryAction.IP_BANNED
    except ImportError:
        # Community edition (`enterprise_core` isn't installed).
        action = LogEntry.Action.ACCESS

    try:
        with set_actor(actor=None, remote_addr=ip_address):
            LogEntry.objects.create(
                content_type=ContentType.objects.get_for_model(User),
                object_pk=str(user.pk) if user else "",
                object_repr=str(user) if user else "unknown user",
                action=action,
                changes={},
                additional_data={"folder_id": None},
                cid=get_cid(),
            )
    except Exception:
        logger.exception("Could not create the failed-login ban audit log")


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

    def authenticate(self, request: HttpRequest, **credentials):
        infra_settings_obj = GlobalSettings.objects.filter(
            name=GlobalSettings.Names.INFRA_CONFIG
        ).first()
        infra_settings = infra_settings_obj.value if infra_settings_obj else {}

        is_rate_limit_activated = infra_settings.get("is_rate_limit_activated", False)

        proxy_ips = infra_settings.get(
            "proxy_ips", list(InfraConfigSerializer.DEFAULT_PROXY_IPS)
        )
        not_rate_limited_ips = infra_settings.get("not_rate_limited_ips", [])

        ip_address = resolve_client_ip(request, proxy_ips)

        # Outside the try below, otherwise `except Exception` would swallow it
        if is_rate_limit_activated and ip_address is not None:
            is_rate_limited = not is_in_networks(ip_address, not_rate_limited_ips)

            if is_rate_limited:
                try:
                    is_banned = get_ban_cache().is_banned(ip_address)
                except Exception as e:
                    logger.error("Failed to to check if an IP was banned", exc_info=e)
                    is_banned = False

                if is_banned:
                    raise ImmediateHttpResponse(RateLimitResponse(request))

        email = credentials.get("email")

        try:
            serializer = AuthTokenSerializer(
                data={
                    "username": email,
                    "password": credentials.get("password"),
                },
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data["user"]
            if not user.is_local:
                raise NotImplementedError(
                    "This user is not allowed to use local login."
                )

            return user
        except Exception:
            # Failed login: bad credentials, invalid input or non-local user
            if is_rate_limit_activated and ip_address is not None:
                try:
                    create_audit_log = get_ban_cache().register_failed_login(
                        ip_address, email
                    )
                    if create_audit_log:
                        user = (
                            User.objects.filter(email=email).first() if email else None
                        )
                        create_ip_ban_audit_log(ip_address, user)
                except Exception as e:
                    logger.error("Failed to log rate limited IP", exc_info=e)

            return None

    def reauthenticate(self, user, password):
        from allauth.mfa.utils import is_mfa_enabled

        if is_mfa_enabled(user):
            raise ValidationError(
                _("Confirm with your second factor instead of your password."),
                code="mfa_required",
            )
        return super().reauthenticate(user, password)


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
    def _extract_claim_values(extra, claim_names):
        if not claim_names:
            return []
        sources = [
            extra,
            extra.get("userinfo", {}) or {},
            extra.get("id_token", {}) or {},
        ]
        values = []
        for claim in claim_names:
            for source in sources:
                value = source.get(claim)
                if isinstance(value, str) and value:
                    values.append(value)
                elif isinstance(value, list):
                    values.extend(v for v in value if isinstance(v, str) and v)
        return values

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
        # Fallback: check preferred_username / upn (common in Entra ID / Azure AD)
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

        from global_settings.utils import ff_is_enabled
        from .sso.models import SSOSettings
        from .utils import sync_user_idp_groups

        try:
            sso_settings = SSOSettings.objects.get()
        except SSOSettings.DoesNotExist:
            sso_settings = None
        jit_provisioning_active = (
            bool(sso_settings)
            and sso_settings.jit_provisioning_enabled
            and ff_is_enabled("jit_provisioning")
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
        except User.DoesNotExist:
            if not jit_provisioning_active:
                logger.error(
                    "pre_social_login: user not found",
                    provider=sociallogin.account.provider,
                )
                logger.debug(
                    "pre_social_login: user not found - check DB for this email",
                    idp_email=email_address,
                    idp_email_repr=repr(email_address),
                    provider=sociallogin.account.provider,
                )
                return Response(
                    {"message": "User not found."}, status=HTTP_401_UNAUTHORIZED
                )

            user = User.objects.create_user(
                email=email_address,
                password=None,
                first_name=sociallogin.user.first_name,
                last_name=sociallogin.user.last_name,
                user_groups=sso_settings.default_user_groups,
                is_jit_provisioned=True,
            )
            logger.info(
                "pre_social_login: user auto-provisioned via JIT",
                provider=sociallogin.account.provider,
                user_id=str(user.id),
            )
            sociallogin.user = user
            sociallogin.connect(request, user)

        if jit_provisioning_active:
            group_claims = (sso_settings.settings or {}).get(
                "attribute_mapping", {}
            ).get("groups") or DEFAULT_ATTRIBUTE_MAPPING_GROUPS
            if group_claims:
                group_names = self._extract_claim_values(extra, group_claims)
                sync_user_idp_groups(user, group_names)

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
