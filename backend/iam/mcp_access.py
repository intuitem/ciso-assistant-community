"""Who may connect apps: the MCP kill switch and the per-user flag."""

import structlog
from allauth.idp.oidc.models import Token

from iam.oidc_adapter import MCP_SCOPES, mcp_resource

logger = structlog.get_logger(__name__)

MCP_FLAG = "mcp"

MCP_DISABLED = "mcp_disabled"
NOT_ALLOWED = "not_allowed"


def mcp_enabled() -> bool:
    from global_settings.utils import ff_is_enabled

    return ff_is_enabled(MCP_FLAG)


def is_mcp_request(scopes, resources=()) -> bool:
    return bool(set(MCP_SCOPES) & set(scopes or ())) or mcp_resource() in (
        resources or ()
    )


def refusal_reason(user, mcp_request: bool) -> str | None:
    # the kill switch covers MCP only; the per-user flag covers every app
    if mcp_request and not mcp_enabled():
        return MCP_DISABLED
    if not user.can_connect_apps:
        return NOT_ALLOWED
    return None


def revoke_app_tokens(user_ids, client_ids=None) -> int:
    """Delete every token type (a pending code could still be redeemed) and the
    usage rows. Service-account tokens carry no user and are never matched."""
    from iam.models import ConnectedAppUse

    tokens = Token.objects.filter(user_id__in=user_ids, client__isnull=False)
    uses = ConnectedAppUse.objects.filter(user_id__in=user_ids)
    if client_ids is not None:
        tokens = tokens.filter(client_id__in=client_ids)
        uses = uses.filter(client_id__in=client_ids)
    deleted, _ = tokens.delete()
    uses.delete()
    logger.info(
        "app tokens revoked",
        users=[str(u) for u in user_ids],
        clients=client_ids,
        deleted_tokens=deleted,
    )
    return deleted
