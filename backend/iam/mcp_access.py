"""MCP tokens: who may get one, and what one may do."""

from dataclasses import dataclass

import structlog
from allauth.idp.oidc.models import Token
from django.db import transaction

from iam.oidc_adapter import MCP_SCOPES, is_mcp_resource

logger = structlog.get_logger(__name__)

MCP_FLAG = "mcp"
MCP_WRITE_FLAG = "mcp_write"

MCP_DISABLED = "mcp_disabled"
NOT_ALLOWED = "not_allowed"
NO_PROFILE = "no_profile"
NO_SHARED_CACHE = "no_shared_cache"


def mcp_enabled() -> bool:
    from global_settings.utils import ff_is_enabled

    return ff_is_enabled(MCP_FLAG)


def has_shared_cache() -> bool:
    from django.conf import settings

    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    return not backend.endswith(("LocMemCache", "DummyCache"))


def mcp_writes_enabled() -> bool:
    from global_settings.utils import ff_is_enabled

    return mcp_enabled() and ff_is_enabled(MCP_WRITE_FLAG)


def is_mcp_request(scopes, resources=()) -> bool:
    return bool(set(MCP_SCOPES) & set(scopes or ())) or any(
        is_mcp_resource(resource) for resource in resources or ()
    )


def is_mcp_token(token) -> bool:
    """An OAuth token that carries the MCP scope, whoever presents it."""
    return bool(set(MCP_SCOPES) & set(token.get_scopes()))


@dataclass(frozen=True)
class MCPAccess:
    token: object
    user: object
    client: object
    grant: object

    @property
    def actions(self) -> list[str]:
        # writes wait for the organization to allow them
        if not mcp_writes_enabled():
            return ["read"]
        return self.grant.profile.actions

    def claims(self) -> dict:
        return {
            "actions": self.actions,
            "profile": self.grant.profile.name,
            "app": self.client.name,
        }

    def via_app(self) -> dict:
        return {
            "client_id": self.client.id,
            "name": self.client.name,
            "profile": self.grant.profile.name,
        }


def mcp_access(token) -> MCPAccess | None:
    """What a valid MCP access token may do, or None if it may do nothing: MCP
    is off, its user may not connect apps, or no consent stands behind it."""
    from iam.models import AppGrant

    user = token.user
    if (
        token.type != Token.Type.ACCESS_TOKEN
        or user is None
        or not user.is_active
        or not user.can_connect_apps
        or not is_mcp_token(token)
        # a resource indicator, when there is one, must name the MCP resource
        or not all(is_mcp_resource(r) for r in token.get_resources())
        or not mcp_enabled()
    ):
        return None
    grant = (
        AppGrant.objects.select_related("profile")
        .filter(user=user, client_id=token.client_id)
        .first()
    )
    if grant is None:
        return None
    return MCPAccess(token=token, user=user, client=token.client, grant=grant)


def mcp_access_for(raw: str) -> MCPAccess | None:
    token = (
        Token.objects.select_related("user", "client")
        .valid()
        .by_value(raw)
        .filter(type=Token.Type.ACCESS_TOKEN)
        .first()
    )
    return mcp_access(token) if token is not None else None


def refusal_reason(user, mcp_request: bool) -> str | None:
    # other OAuth apps keep today's behaviour
    if not mcp_request:
        return None
    if not mcp_enabled():
        return MCP_DISABLED
    if not has_shared_cache():
        return NO_SHARED_CACHE
    if not user.can_connect_apps:
        return NOT_ALLOWED
    from iam.models import ConnectionProfile

    if not ConnectionProfile.objects.exists():
        return NO_PROFILE
    return None


def revoke_app_tokens(user_ids, client_ids=None) -> int:
    """Delete every token type (a pending code could still be redeemed) and the
    usage and grant rows. `user_ids=None` means every user. Service-account
    tokens carry no user and are never matched."""
    from iam.models import AppGrant, ConnectedAppUse

    tokens = Token.objects.filter(user__isnull=False, client__isnull=False)
    uses = ConnectedAppUse.objects.all()
    grants = AppGrant.objects.all()
    if user_ids is not None:
        tokens = tokens.filter(user_id__in=user_ids)
        uses = uses.filter(user_id__in=user_ids)
        grants = grants.filter(user_id__in=user_ids)
    if client_ids is not None:
        tokens = tokens.filter(client_id__in=client_ids)
        uses = uses.filter(client_id__in=client_ids)
        grants = grants.filter(client_id__in=client_ids)
    with transaction.atomic():
        deleted, _ = tokens.delete()
        uses.delete()
        grants.delete()
    logger.info(
        "app tokens revoked",
        users=None if user_ids is None else [str(u) for u in user_ids],
        clients=client_ids,
        deleted_tokens=deleted,
    )
    return deleted


def revoke_mcp_connections(user_id) -> int:
    """The user's MCP connections only: other OAuth apps keep their tokens."""
    from iam.models import AppGrant

    client_ids = set(
        AppGrant.objects.filter(user_id=user_id).values_list("client_id", flat=True)
    ) | {
        token.client_id
        for token in Token.objects.filter(user_id=user_id, client__isnull=False)
        if is_mcp_token(token)
    }
    return revoke_app_tokens([user_id], sorted(client_ids)) if client_ids else 0
