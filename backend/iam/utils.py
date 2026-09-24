from typing import Any, Optional

import structlog
from allauth.headless.tokens.strategies.sessions import SessionTokenStrategy
from django.http import HttpRequest
from knox.models import AuthToken

logger = structlog.get_logger(__name__)


def generate_token(user):
    _auth_token = AuthToken.objects.create(user=user)
    return _auth_token[1]


def revoke_all_user_tokens(user, exclude_token=None) -> int:
    tokens = AuthToken.objects.filter(user=user)
    if exclude_token is not None:
        tokens = tokens.exclude(pk=exclude_token.pk)
    deleted, _ = tokens.delete()
    return deleted


def sync_user_idp_groups(user, group_names) -> None:
    from iam.models import IdPGroup

    # SCIM already owns idp_groups membership for SCIM-managed users
    # (iam/scim/views.py: _resolve_user_ids only ever touches those).
    if user.is_scim_managed:
        return

    names = {
        name.strip() for name in group_names if isinstance(name, str) and name.strip()
    }
    groups = [IdPGroup.objects.get_or_create(name=name)[0] for name in names]
    IdPGroup.objects.filter(id__in=[g.id for g in groups]).exclude(
        source=IdPGroup.Source.SSO
    ).update(source=IdPGroup.Source.SSO)
    user.idp_groups.set(groups)


class KnoxTokenStrategy(SessionTokenStrategy):
    def create_access_token(self, request: HttpRequest) -> str:
        token = generate_token(request.user)
        return token

    def create_access_token_payload(
        self, request: HttpRequest
    ) -> Optional[dict[str, Any]]:
        access_token = self.create_access_token(request)
        if not access_token:
            return None
        return {"access_token": access_token}


def redact_audited_secret(value: str) -> str:
    """Full redaction for auditlog `mask_fields`. Auditlog's default `mask_str`
    only masks the first half of the value, which would still publish most of a
    password hash to anyone holding `view_central_auditlog`."""
    return "**********" if value else value
