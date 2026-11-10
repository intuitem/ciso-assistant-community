import uuid
from typing import Any, Optional

import structlog
from allauth.headless.tokens.strategies.sessions import SessionTokenStrategy
from django.db.models import Q
from django.http import HttpRequest
from knox.models import AuthToken

logger = structlog.get_logger(__name__)


def generate_token(user):
    _auth_token = AuthToken.objects.create(user=user)
    return _auth_token[1]


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


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


class ViewableFilter:
    """Keeps the linked objects a user may view, with one IAM lookup per model."""

    def __init__(self, user):
        self.user = user
        self._ids = {}

    def ids(self, model) -> set | None:
        """Viewable ids of `model`, or None when it is not filtered: models outside
        IAM, and people, whose names the app shows wherever they are linked."""
        from core.models import Actor, Team
        from iam.models import RoleAssignment, User
        from tprm.models import Entity

        model = model._meta.concrete_model
        if model in (Team, User):
            return None
        if model is Actor and Actor not in self._ids:
            # people stay listed; an actor standing for a third party follows its entity
            self._ids[Actor] = set(
                Actor.objects.filter(
                    Q(entity__isnull=True)
                    | Q(
                        entity_id__in=RoleAssignment.get_viewable_object_ids(
                            self.user, Entity
                        )
                    )
                ).values_list("id", flat=True)
            )
        if model not in self._ids:
            try:
                self._ids[model] = set(
                    RoleAssignment.get_viewable_object_ids(self.user, model)
                )
            except NotImplementedError:
                self._ids[model] = None
        return self._ids[model]

    def allows(self, obj) -> bool:
        ids = self.ids(type(obj))
        return ids is None or obj.pk in ids

    def __call__(self, objs) -> list:
        return [obj for obj in objs if obj is not None and self.allows(obj)]

    def serialized(self, model, items) -> list:
        """Keep the serialized `{"id": ...}` items of `model` the user may view."""
        ids = self.ids(model)
        if ids is None:
            return list(items or [])
        return [item for item in items or [] if _as_uuid(item.get("id")) in ids]
