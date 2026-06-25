"""
SCIM 2.0 Views for CISO Assistant.

Endpoints:
  GET/POST                    /api/scim/v2/Users
  GET/PUT/PATCH/DELETE        /api/scim/v2/Users/{id}
  GET/POST                    /api/scim/v2/Groups
  GET/PUT/PATCH/DELETE        /api/scim/v2/Groups/{id}
  GET                         /api/scim/v2/ServiceProviderConfig
"""

import json
import re
import uuid

import structlog
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import JsonResponse
from knox.auth import TokenAuthentication
from rest_framework import views
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import ViewSet

from global_settings.models import GlobalSettings
from iam.models import Folder, IdPGroup

from core.permissions import FeatureFlagRequired
from .permissions import IsSCIMToken
from .schema_definitions import (
    ALL_RESOURCE_TYPES,
    ALL_SCHEMAS,
)
from .serializers import (
    parse_filter,
    scim_error,
    scim_group_to_dict,
    scim_list_response,
    scim_user_to_dict,
)

logger = structlog.get_logger(__name__)
User = get_user_model()
SCIM_CONTENT_TYPE = "application/scim+json"


class SCIMJSONRenderer(JSONRenderer):
    """Renders responses as application/scim+json (RFC 7644)."""

    media_type = "application/scim+json"
    format = "scim+json"


class SCIMJSONParser(JSONParser):
    """Parses request bodies sent with Content-Type: application/scim+json."""

    media_type = "application/scim+json"


class SCIMTokenAuthentication(TokenAuthentication):
    """
    Knox auth that advertises the SCIM-spec `Authorization: Bearer <token>`
    challenge header instead of Knox's default `Authorization: Token <token>`.
    Standard SCIM clients send Bearer per RFC 7644 §2.
    """

    def authenticate_header(self, request):
        return "Bearer"


def _scim_response(data, status_code=200):
    response = JsonResponse(data, status=status_code)
    response["Content-Type"] = SCIM_CONTENT_TYPE
    return response


def _scim_error_response(detail, status_code, scim_type=None):
    return _scim_response(scim_error(detail, status_code, scim_type), status_code)


# ---------------------------------------------------------------------------
# ServiceProviderConfig  (public discovery, no auth required)
# ---------------------------------------------------------------------------


class ServiceProviderConfigView(views.APIView):
    authentication_classes = []
    permission_classes = []
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def get(self, request):
        config = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
            "documentationUri": "",
            "patch": {"supported": True},
            "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
            "filter": {"supported": True, "maxResults": 200},
            "changePassword": {"supported": False},
            "sort": {"supported": False},
            "etag": {"supported": False},
            "authenticationSchemes": [
                {
                    "type": "oauthbearertoken",
                    "name": "OAuth Bearer Token",
                    "description": "Authentication using a Bearer token issued by CISO Assistant",
                }
            ],
            "meta": {
                "resourceType": "ServiceProviderConfig",
                "location": request.build_absolute_uri(
                    "/api/scim/v2/ServiceProviderConfig"
                ),
            },
        }
        response = JsonResponse(config)
        response["Content-Type"] = SCIM_CONTENT_TYPE
        return response


# ---------------------------------------------------------------------------
# Schemas  (public discovery)
# ---------------------------------------------------------------------------


class SchemasView(views.APIView):
    """GET /Schemas — list every schema CISO Assistant supports."""

    authentication_classes = []
    permission_classes = []
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def get(self, request):
        resources = list(ALL_SCHEMAS.values())
        return _scim_response(
            scim_list_response(resources, len(resources), 1, len(resources))
        )


class SchemaDetailView(views.APIView):
    """GET /Schemas/{urn} — single schema definition."""

    authentication_classes = []
    permission_classes = []
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def get(self, request, schema_id):
        schema = ALL_SCHEMAS.get(schema_id)
        if schema is None:
            return _scim_error_response(f"Schema {schema_id} not found", 404)
        return _scim_response(schema)


# ---------------------------------------------------------------------------
# ResourceTypes  (public discovery)
# ---------------------------------------------------------------------------


class ResourceTypesView(views.APIView):
    """GET /ResourceTypes — list every resource type the server exposes."""

    authentication_classes = []
    permission_classes = []
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def get(self, request):
        resources = list(ALL_RESOURCE_TYPES.values())
        return _scim_response(
            scim_list_response(resources, len(resources), 1, len(resources))
        )


class ResourceTypeDetailView(views.APIView):
    """GET /ResourceTypes/{id} — single resource type."""

    authentication_classes = []
    permission_classes = []
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def get(self, request, resource_id):
        resource = ALL_RESOURCE_TYPES.get(resource_id)
        if resource is None:
            return _scim_error_response(f"ResourceType {resource_id} not found", 404)
        return _scim_response(resource)


# ---------------------------------------------------------------------------
# SCIM Users
# ---------------------------------------------------------------------------


class SCIMUserViewSet(ViewSet):
    authentication_classes = [SCIMTokenAuthentication]
    permission_classes = [IsSCIMToken, FeatureFlagRequired]
    feature_flag = "idp_groups"
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def list(self, request):
        filter_str = request.query_params.get("filter", "")
        try:
            start_index = max(int(request.query_params.get("startIndex", 1)), 1)
            count = min(max(int(request.query_params.get("count", 100)), 0), 200)
        except TypeError, ValueError:
            start_index, count = 1, 100

        # Only expose users SCIM provisioned/owns; locally-managed accounts are
        # not part of the SCIM directory.
        qs = User.objects.filter(is_scim_managed=True).order_by("date_joined", "id")
        if filter_str:
            attr, value = parse_filter(filter_str)
            if attr == "username":
                qs = qs.filter(email__iexact=value)
            elif attr == "externalid":
                qs = qs.filter(scim_external_id=value)
            else:
                qs = qs.none()

        total = qs.count()
        offset = start_index - 1
        page = list(qs[offset : offset + count])
        resources = [scim_user_to_dict(u, request) for u in page]
        return _scim_response(
            scim_list_response(resources, total, start_index, len(resources))
        )

    def create(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _scim_error_response("Invalid JSON body", 400)

        user_name = data.get("userName")
        if not user_name:
            return _scim_error_response("userName is required", 400)

        external_id = data.get("externalId")

        # Idempotency: externalId first, then email
        user = None
        matched_by_external_id = False
        if external_id:
            user = User.objects.filter(scim_external_id=external_id).first()
            matched_by_external_id = user is not None
        if user is None:
            user = User.objects.filter(email__iexact=user_name).first()
        if user is not None:
            # Adopt-but-protect: SCIM may link a pre-existing non-privileged
            # account by email, but must never silently adopt or rewrite an
            # administrator or a local-login account it does not already own.
            if (
                not matched_by_external_id
                and not _is_scim_managed(user)
                and _is_protected_account(user)
            ):
                return _scim_error_response(
                    "A user with this email already exists and cannot be managed by SCIM",
                    409,
                    "uniqueness",
                )
            user.is_scim_managed = True
            _update_user_from_scim_data(user, data)
            err = _save_user_or_scim_error(user)
            if err:
                return err
            return _scim_response(scim_user_to_dict(user, request), 200)

        name_data = data.get("name", {})
        first_name = name_data.get("givenName", "")
        last_name = name_data.get("familyName", "")
        is_active = _to_bool(data.get("active", True))

        email = _primary_email(data.get("emails", [])) or user_name

        try:
            validate_email(email)
        except DjangoValidationError:
            return _scim_error_response(f"Invalid email address: {email}", 400)

        try:
            general = GlobalSettings.objects.filter(name="general").first()
            default_lang = (
                general.value.get("default_language", "en")
                if general and isinstance(general.value, dict)
                else "en"
            )
        except Exception:
            default_lang = "en"

        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_published=True,
            keep_local_login=False,
            is_scim_managed=True,
            folder=Folder.get_root_folder(),
            preferences={"lang": default_lang},
        )
        if external_id:
            user.scim_external_id = external_id
        user.set_unusable_password()
        try:
            user.save()
        except IntegrityError:
            return _scim_error_response(
                "A user with this email or externalId already exists",
                409,
                "uniqueness",
            )

        try:
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"verified": True, "primary": True},
            )
        except Exception as exc:
            logger.warning(
                "SCIM: failed to create/update EmailAddress for user",
                user_id=str(user.pk),
                email=user.email,
                error=str(exc),
            )

        logger.info("SCIM: user created", email=user.email, external_id=external_id)
        return _scim_response(scim_user_to_dict(user, request), 201)

    def retrieve(self, request, pk=None):
        user = _get_scim_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        return _scim_response(scim_user_to_dict(user, request))

    def update(self, request, pk=None):
        user = _get_scim_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _scim_error_response("Invalid JSON body", 400)
        _update_user_from_scim_data(user, data)
        err = _save_user_or_scim_error(user)
        if err:
            return err
        return _scim_response(scim_user_to_dict(user, request))

    def partial_update(self, request, pk=None):
        user = _get_scim_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _scim_error_response("Invalid JSON body", 400)

        # Some SCIM clients send "Operations", some send "operations".
        operations = data.get("Operations") or data.get("operations") or []

        logger.info(
            "SCIM: user PATCH received",
            user_id=pk,
            top_level_keys=list(data.keys()),
            operations_count=len(operations),
        )

        if not operations:
            # Fallback: some clients send a bare resource document, e.g.
            # {"active": false, "userName": "..."} — treat the whole body as
            # a value-dict replace.
            _apply_user_replace_dict(user, data)
        else:
            for op in operations:
                op_type = op.get("op", "").lower()
                path = op.get("path", "")
                value = op.get("value")
                if op_type in ("replace", "add"):
                    # RFC 7644 §3.5.2.1: on a single-valued attribute, "add"
                    # assigns the value exactly like "replace".
                    if isinstance(value, dict):
                        _apply_user_replace_dict(user, value)
                    elif path:
                        _apply_user_replace_path(user, path, value)
                elif op_type == "remove":
                    # RFC 7644 §3.5.2.2: "path" is REQUIRED for remove.
                    if not path:
                        return _scim_error_response(
                            "remove operation requires a path", 400, "noTarget"
                        )
                    _apply_user_remove_path(user, path)
                else:
                    return _scim_error_response(
                        f"Unsupported PATCH operation '{op.get('op')}'",
                        400,
                        "invalidValue",
                    )

        err = _save_user_or_scim_error(user)
        if err:
            return err
        logger.info(
            "SCIM: user PATCH applied",
            user_id=pk,
            is_active=user.is_active,
            email=user.email,
        )
        return _scim_response(scim_user_to_dict(user, request))

    def destroy(self, request, pk=None):
        user = _get_scim_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        if _would_orphan_admins(user):
            return _scim_error_response(
                "Refusing to deactivate the last active administrator",
                409,
                "mutability",
            )
        user.is_active = False
        user.save(update_fields=["is_active"])
        logger.info("SCIM: user deactivated", user_id=pk)
        return JsonResponse({}, status=204)


# ---------------------------------------------------------------------------
# SCIM Groups
# ---------------------------------------------------------------------------


class SCIMGroupViewSet(ViewSet):
    """
    SCIM Group endpoints. A SCIM Group is an IdPGroup: SCIM manages its
    membership (idp_group.users), while an admin decides which CISO user
    groups it grants (idp_group.user_groups). Unknown groups are auto-created
    on first push and grant nothing until an admin wires their user groups.
    The IdPGroup's own UUID is the stable SCIM id, so renames only change the
    displayName.
    """

    authentication_classes = [SCIMTokenAuthentication]
    permission_classes = [IsSCIMToken, FeatureFlagRequired]
    feature_flag = "idp_groups"
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def list(self, request):
        filter_str = request.query_params.get("filter", "")
        try:
            start_index = max(int(request.query_params.get("startIndex", 1)), 1)
            count = min(max(int(request.query_params.get("count", 100)), 0), 200)
        except TypeError, ValueError:
            start_index, count = 1, 100

        qs = IdPGroup.objects.all().order_by("name")

        if filter_str:
            attr, value = parse_filter(filter_str)
            if attr == "displayname":
                qs = qs.filter(name__iexact=value)
            elif attr == "id":
                qs = qs.filter(id=value)
            else:
                qs = qs.none()

        total = qs.count()
        offset = start_index - 1
        page = list(qs[offset : offset + count])
        resources = [scim_group_to_dict(g, request) for g in page]
        return _scim_response(
            scim_list_response(resources, total, start_index, len(resources))
        )

    def create(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _scim_error_response("Invalid JSON body", 400, "invalidSyntax")

        display_name = data.get("displayName")
        if not display_name:
            return _scim_error_response("displayName is required", 400, "invalidValue")

        # Auto-create on first push: the group grants nothing until an admin
        # wires its user_groups, so accepting unknown groups is safe.
        idp_group, created = IdPGroup.objects.get_or_create(name=display_name)
        _add_members(idp_group, _member_ids(data.get("members", [])))
        logger.info(
            "SCIM: group provisioned",
            idp_group_id=str(idp_group.id),
            name=idp_group.name,
            created=created,
        )
        return _scim_response(scim_group_to_dict(idp_group, request), 201)

    def retrieve(self, request, pk=None):
        idp_group = _get_idp_group_by_pk(pk)
        if idp_group is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        return _scim_response(scim_group_to_dict(idp_group, request))

    def update(self, request, pk=None):
        """PUT — full replace. The members list becomes the new membership."""
        idp_group = _get_idp_group_by_pk(pk)
        if idp_group is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _scim_error_response("Invalid JSON body", 400, "invalidSyntax")

        display_name = data.get("displayName")
        if display_name and not _rename_idp_group(idp_group, display_name):
            return _scim_error_response(
                f"A group named '{display_name}' already exists", 409, "uniqueness"
            )

        _set_members(idp_group, _member_ids(data.get("members", []) or []))
        return _scim_response(scim_group_to_dict(idp_group, request))

    def partial_update(self, request, pk=None):
        idp_group = _get_idp_group_by_pk(pk)
        if idp_group is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError, ValueError:
            return _scim_error_response("Invalid JSON body", 400, "invalidSyntax")

        # Some SCIM clients send "Operations" (RFC casing), some send lowercase.
        operations = data.get("Operations") or data.get("operations") or []
        logger.info(
            "SCIM: group PATCH received",
            group_id=pk,
            operations_count=len(operations),
        )

        # RFC 7644 §3.5.2: operations are applied in the order they appear.
        # We build an ordered list of member mutations, merging *consecutive*
        # same-type ops so a PATCH with thousands of single-member "add" ops
        # (one per user, as Okta/Entra send) still applies as one bulk call —
        # without reordering distinct add/remove ops relative to each other.
        segments: list[
            tuple[str, list[str]]
        ] = []  # (action, ids): add|remove|set|clear

        def _push(action: str, ids: list[str]) -> None:
            if action in ("add", "remove") and segments and segments[-1][0] == action:
                segments[-1][1].extend(ids)
            else:
                segments.append((action, list(ids)))

        for op in operations:
            op_type = op.get("op", "").lower()
            path = op.get("path", "")
            value = op.get("value")

            if op_type == "add":
                if path == "members":
                    _push("add", _member_ids(value or []))
                elif isinstance(value, dict) and "members" in value:
                    # Path-less add: members nested under value (Okta/Entra).
                    _push("add", _member_ids(value["members"] or []))
            elif op_type == "remove":
                if path == "members":
                    # RFC 7644 §3.5.2.2: no value → remove ALL (a reset);
                    # with a value → remove only the listed members.
                    if value:
                        _push("remove", _member_ids(value))
                    else:
                        _push("clear", [])
                elif isinstance(value, dict) and "members" in value:
                    # Path-less remove: members nested under value.
                    _push("remove", _member_ids(value["members"] or []))
                else:
                    # Filter selector path, e.g. members[value eq "uuid"]
                    uid = _extract_member_filter_id(path)
                    if uid:
                        _push("remove", [uid])
            elif op_type == "replace":
                if path == "members":
                    _push("set", _member_ids(value or []))
                elif path == "displayName" and value:
                    # IdP renamed the group. Only the label changes; the
                    # IdPGroup PK (the SCIM id) is the stable reference.
                    if not _rename_idp_group(idp_group, value):
                        return _scim_error_response(
                            f"A group named '{value}' already exists", 409, "uniqueness"
                        )
                elif isinstance(value, dict):
                    if "displayName" in value and not _rename_idp_group(
                        idp_group, value["displayName"]
                    ):
                        return _scim_error_response(
                            f"A group named '{value['displayName']}' already exists",
                            409,
                            "uniqueness",
                        )
                    if "members" in value:
                        _push("set", _member_ids(value["members"] or []))

        for action, ids in segments:
            if action == "add":
                _add_members(idp_group, ids)
            elif action == "remove":
                _remove_members(idp_group, ids)
            elif action == "set":
                _set_members(idp_group, ids)
            elif action == "clear":
                idp_group.users.clear()

        return _scim_response(scim_group_to_dict(idp_group, request))

    def destroy(self, request, pk=None):
        """
        SCIM DELETE — remove the IdP group. Members lose the user groups it
        granted (computed), but their direct (manual) memberships are
        unaffected since those live in a separate relation.
        """
        idp_group = _get_idp_group_by_pk(pk)
        if idp_group is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        idp_group.delete()
        logger.info("SCIM: group deleted", group_id=pk)
        return JsonResponse({}, status=204)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _valid_uuid(value):
    """Return the value as a UUID, or None if it is not a valid UUID.

    SCIM path ids and member values come straight from the IdP and may be
    arbitrary strings; a non-UUID would otherwise raise a ValidationError
    inside the ORM and surface as a 500.
    """
    try:
        return uuid.UUID(str(value))
    except ValueError, TypeError, AttributeError:
        return None


def _is_scim_managed(user) -> bool:
    """True if SCIM provisioned/owns this user. SCIM may only read and mutate the
    accounts it owns; locally-managed accounts are not part of the SCIM
    directory. Keyed off an internal marker, not externalId — the latter is
    optional and client-issued (RFC 7643 §3.1), so it cannot define ownership."""
    return user.is_scim_managed


def _is_protected_account(user) -> bool:
    """Accounts SCIM must never silently adopt or take over by email collision:
    administrators and local-login accounts."""
    return user.is_admin() or user.keep_local_login


def _would_orphan_admins(user) -> bool:
    """True if deactivating ``user`` would leave the instance with no other
    active administrator. Mirrors the superuser deactivation guard in
    ``User.save`` for the BI-UG-ADM admin population."""
    if not user.is_admin():
        return False
    return (
        not User.get_admin_users().filter(is_active=True).exclude(pk=user.pk).exists()
    )


def _get_user_by_pk(pk):
    if _valid_uuid(pk) is None:
        return None
    return User.objects.filter(id=pk).first()


def _get_scim_user_by_pk(pk):
    """Resolve a user for SCIM read/modify, restricted to SCIM-managed accounts
    so SCIM can never reach into a locally-managed account it does not own."""
    user = _get_user_by_pk(pk)
    if user is None or not _is_scim_managed(user):
        return None
    return user


def _get_idp_group_by_pk(pk):
    """Resolve the IdPGroup behind a SCIM Group id (the IdPGroup's own PK)."""
    if _valid_uuid(pk) is None:
        return None
    return IdPGroup.objects.filter(id=pk).first()


def _save_user_or_scim_error(user):
    """Persist a SCIM-mutated user, normalizing the email and translating
    storage failures into SCIM responses. Returns None on success, or a SCIM
    error response (400 invalidValue / 409 uniqueness / 409 mutability)."""
    if not user.is_active and _would_orphan_admins(user):
        return _scim_error_response(
            "Refusing to deactivate the last active administrator", 409, "mutability"
        )
    if user.email:
        user.email = user.email.lower()
        try:
            validate_email(user.email)
        except DjangoValidationError:
            return _scim_error_response(
                f"Invalid email address: {user.email}", 400, "invalidValue"
            )
    try:
        user.save()
    except IntegrityError:
        return _scim_error_response(
            "A user with this email or externalId already exists",
            409,
            "uniqueness",
        )
    return None


def _primary_email(emails):
    """Pick the primary (or first) email value from a SCIM emails array.

    SCIM clients may send entries as dicts ({"value": ..., "primary": ...}) or,
    non-conformantly, as bare strings. Non-dict entries are ignored so a bad
    payload yields None instead of raising.
    """
    if not isinstance(emails, list):
        return None
    dicts = [e for e in emails if isinstance(e, dict)]
    if not dicts:
        return None
    primary = next((e for e in dicts if e.get("primary")), dicts[0])
    return primary.get("value")


def _rename_idp_group(idp_group, new_name) -> bool:
    """Rename the IdP group. Returns False on a unique-name collision so the
    SCIM caller can surface it as a 409 instead of a 500."""
    if not new_name or new_name == idp_group.name:
        return True
    idp_group.name = new_name
    try:
        idp_group.save(update_fields=["name"])
    except IntegrityError:
        idp_group.refresh_from_db(fields=["name"])
        return False
    return True


def _member_ids(members):
    """Extract user ids from a SCIM members array ([{"value": "<id>"}, ...])."""
    ids = []
    for member in members:
        uid = member.get("value") if isinstance(member, dict) else member
        if uid:
            ids.append(str(uid))
    return ids


def _resolve_user_ids(ids):
    """Filter SCIM member ids down to existing, SCIM-managed User PKs.

    Non-UUID member values (e.g. an external IdP id) are dropped rather than
    passed into the ORM, which would raise on an invalid UUID. Only SCIM-managed
    users may be members of an IdP group, so a locally-managed account (e.g. a
    hand-created admin) can never be pulled into a role-bearing group via SCIM.
    """
    valid = [v for v in (_valid_uuid(i) for i in ids) if v is not None]
    if not valid:
        return []
    return list(
        User.objects.filter(id__in=valid, is_scim_managed=True).values_list(
            "id", flat=True
        )
    )


def _add_members(idp_group, ids):
    valid = _resolve_user_ids(ids)
    if valid:
        idp_group.users.add(*valid)


def _remove_members(idp_group, ids):
    valid = _resolve_user_ids(ids)
    if valid:
        idp_group.users.remove(*valid)


def _set_members(idp_group, ids):
    resolved = _resolve_user_ids(ids)
    # Guard the wipe footgun: a non-empty members list that resolves to nothing
    # (every id unprovisioned / not SCIM-managed) would otherwise clear the whole
    # group. Treat that as a no-op rather than stripping every member (incl. the
    # groups they inherit). An explicit empty list still clears.
    if ids and not resolved:
        logger.warning(
            "SCIM: ignoring group member replace; no requested members resolved "
            "to SCIM-managed users",
            group_id=str(idp_group.id),
            requested=len(ids),
        )
        return
    idp_group.users.set(resolved)


def _update_user_from_scim_data(user, data):
    name_data = data.get("name", {})
    if "userName" in data:
        user.email = data["userName"]
    if "givenName" in name_data:
        user.first_name = name_data["givenName"]
    if "familyName" in name_data:
        user.last_name = name_data["familyName"]
    if "active" in data:
        user.is_active = _to_bool(data["active"])
    if data.get("externalId"):
        user.scim_external_id = data["externalId"]
    new_email = _primary_email(data.get("emails", []))
    if new_email:
        user.email = new_email


def _apply_user_replace_dict(user, value_dict):
    name_data = value_dict.get("name", {})
    if "active" in value_dict:
        user.is_active = _to_bool(value_dict["active"])
    if "userName" in value_dict:
        user.email = value_dict["userName"]
    if "givenName" in name_data:
        user.first_name = name_data["givenName"]
    if "familyName" in name_data:
        user.last_name = name_data["familyName"]
    if "externalId" in value_dict:
        user.scim_external_id = value_dict["externalId"] or None
    new_email = _primary_email(value_dict.get("emails", []))
    if new_email:
        user.email = new_email


_EMAILS_VALUE_PATH_RE = re.compile(r"^emails(\[[^\]]*\])?\.value$", re.IGNORECASE)


def _to_bool(val):
    """
    SCIM clients are inconsistent about booleans: some send a real bool, some
    send a string like "true"/"false". bool("false") is True in Python, so we
    need explicit coercion.
    """
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on")
    return bool(val)


def _apply_user_replace_path(user, path, value):
    path_lower = path.lower()
    if path_lower == "active":
        user.is_active = _to_bool(value)
    elif path_lower == "username":
        user.email = value
    elif path_lower == "name.givenname":
        user.first_name = value or ""
    elif path_lower == "name.familyname":
        user.last_name = value or ""
    elif path_lower == "externalid":
        user.scim_external_id = value or None
    elif path_lower == "emails":
        # Whole-array replace: pick primary (or first) and store its value.
        new_email = _primary_email(value)
        if new_email:
            user.email = new_email
    elif _EMAILS_VALUE_PATH_RE.match(path):
        # IdP-targeted email value update, e.g. emails[type eq "work"].value.
        # Since we only persist one email, any such update writes user.email.
        if value:
            user.email = value


def _apply_user_remove_path(user, path):
    """Apply a SCIM PATCH 'remove' to a supported single-valued attribute.
    Required attributes (userName/active/emails) cannot be unset and are left
    untouched; unknown paths are ignored (consistent with replace handling)."""
    path_lower = path.lower()
    if path_lower == "externalid":
        user.scim_external_id = None
    elif path_lower == "name.givenname":
        user.first_name = ""
    elif path_lower == "name.familyname":
        user.last_name = ""


_MEMBER_FILTER_RE = re.compile(
    r'members\[value\s+eq\s+["\']([^"\']+)["\']\]',
    re.IGNORECASE,
)


def _extract_member_filter_id(path):
    m = _MEMBER_FILTER_RE.search(path)
    return m.group(1) if m else None
