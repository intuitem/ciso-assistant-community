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

import structlog
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from knox.auth import TokenAuthentication
from rest_framework import views
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import ViewSet

from iam.models import Folder, IdPGroupMapping

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
                "location": request.build_absolute_uri("/api/scim/v2/ServiceProviderConfig"),
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
    permission_classes = [IsSCIMToken]
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def list(self, request):
        filter_str = request.query_params.get("filter", "")
        try:
            start_index = max(int(request.query_params.get("startIndex", 1)), 1)
            count = min(int(request.query_params.get("count", 100)), 200)
        except (TypeError, ValueError):
            start_index, count = 1, 100

        qs = User.objects.all()
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
        page = list(qs[offset: offset + count])
        resources = [scim_user_to_dict(u, request) for u in page]
        return _scim_response(scim_list_response(resources, total, start_index, len(resources)))

    def create(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _scim_error_response("Invalid JSON body", 400)

        user_name = data.get("userName")
        if not user_name:
            return _scim_error_response("userName is required", 400)

        external_id = data.get("externalId")

        # Idempotency: externalId first, then email
        user = None
        if external_id:
            user = User.objects.filter(scim_external_id=external_id).first()
        if user is None:
            user = User.objects.filter(email__iexact=user_name).first()
        if user is not None:
            _update_user_from_scim_data(user, data)
            return _scim_response(scim_user_to_dict(user, request), 200)

        name_data = data.get("name", {})
        first_name = name_data.get("givenName", "")
        last_name = name_data.get("familyName", "")
        is_active = _to_bool(data.get("active", True))

        emails = data.get("emails", [])
        if emails:
            primary = next((e for e in emails if e.get("primary")), emails[0])
            email = primary.get("value", user_name)
        else:
            email = user_name

        try:
            from django.core.validators import validate_email as _ve
            _ve(email)
        except Exception:
            return _scim_error_response(f"Invalid email address: {email}", 400)

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
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_published=True,
            keep_local_login=False,
            folder=Folder.get_root_folder(),
            preferences={"lang": default_lang},
        )
        if external_id:
            user.scim_external_id = external_id
        user.set_unusable_password()
        user.save()

        try:
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(
                user=user, email=user.email, defaults={"verified": True, "primary": True}
            )
        except Exception:
            pass

        logger.info("SCIM: user created", email=user.email, external_id=external_id)
        return _scim_response(scim_user_to_dict(user, request), 201)

    def retrieve(self, request, pk=None):
        user = _get_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        return _scim_response(scim_user_to_dict(user, request))

    def update(self, request, pk=None):
        user = _get_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _scim_error_response("Invalid JSON body", 400)
        _update_user_from_scim_data(user, data)
        return _scim_response(scim_user_to_dict(user, request))

    def partial_update(self, request, pk=None):
        user = _get_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _scim_error_response("Invalid JSON body", 400)

        # Some SCIM clients send "Operations", some send "operations".
        operations = data.get("Operations") or data.get("operations") or []

        logger.info(
            "SCIM: user PATCH received",
            user_id=pk,
            body=data,
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
                if op_type == "replace":
                    if isinstance(value, dict):
                        _apply_user_replace_dict(user, value)
                    elif path:
                        _apply_user_replace_path(user, path, value)

        user.save()
        logger.info(
            "SCIM: user PATCH applied",
            user_id=pk,
            is_active=user.is_active,
            email=user.email,
        )
        return _scim_response(scim_user_to_dict(user, request))

    def destroy(self, request, pk=None):
        user = _get_user_by_pk(pk)
        if user is None:
            return _scim_error_response(f"User {pk} not found", 404)
        user.is_active = False
        user.save(update_fields=["is_active"])
        logger.info("SCIM: user deactivated", user_id=pk)
        return JsonResponse({}, status=204)


# ---------------------------------------------------------------------------
# SCIM Groups
# ---------------------------------------------------------------------------

class SCIMGroupViewSet(ViewSet):
    """
    SCIM Group endpoints. All operations route through IdPGroupMapping —
    SCIM never creates UserGroups directly. The mapping table is the bridge
    between the IdP-side identity and the CISO-side UserGroup; an admin
    must define the mapping before a SCIM client can push the group.
    """

    authentication_classes = [SCIMTokenAuthentication]
    permission_classes = [IsSCIMToken]
    renderer_classes = [SCIMJSONRenderer, JSONRenderer]
    parser_classes = [SCIMJSONParser, JSONParser]

    def list(self, request):
        filter_str = request.query_params.get("filter", "")
        try:
            start_index = max(int(request.query_params.get("startIndex", 1)), 1)
            count = min(int(request.query_params.get("count", 100)), 200)
        except (TypeError, ValueError):
            start_index, count = 1, 100

        # Only mappings actively bound to a SCIM client (scim_external_id set)
        # are visible to SCIM list/read. Unbound mappings are JWT-only.
        qs = IdPGroupMapping.objects.filter(
            scim_external_id__isnull=False
        ).select_related("user_group").prefetch_related("user_group__user_set")

        if filter_str:
            attr, value = parse_filter(filter_str)
            if attr == "displayname":
                qs = qs.filter(external_group_id__iexact=value)
            elif attr == "externalid":
                qs = qs.filter(scim_external_id=value)
            elif attr == "id":
                qs = qs.filter(user_group__id=value)
            else:
                qs = qs.none()

        total = qs.count()
        offset = start_index - 1
        page = list(qs[offset: offset + count])
        resources = [scim_group_to_dict(m, request) for m in page]
        return _scim_response(
            scim_list_response(resources, total, start_index, len(resources))
        )

    def create(self, request):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _scim_error_response("Invalid JSON body", 400, "invalidSyntax")

        display_name = data.get("displayName")
        if not display_name:
            return _scim_error_response(
                "displayName is required", 400, "invalidValue"
            )

        external_id = data.get("externalId")

        # Mapping lookup: stable SCIM ID first (rename-safe), then display name.
        mapping = None
        if external_id:
            mapping = IdPGroupMapping.objects.filter(
                scim_external_id=external_id
            ).first()
        if mapping is None:
            mapping = IdPGroupMapping.objects.filter(
                external_group_id=display_name
            ).first()

        if mapping is None:
            logger.warning(
                "SCIM: group push rejected (no mapping configured)",
                display_name=display_name,
                external_id=external_id,
            )
            return _scim_error_response(
                f"No mapping configured for external group '{display_name}'. "
                f"Create the IdP group mapping in CISO Assistant before "
                f"pushing this group from the IdP.",
                400,
                "invalidValue",
            )

        # Bind the stable SCIM identifier on first contact. From now on the
        # IdP can rename external_group_id freely; the join key won't drift.
        if external_id and not mapping.scim_external_id:
            mapping.scim_external_id = external_id
            mapping.save(update_fields=["scim_external_id"])

        _apply_group_members_add(mapping.user_group, data.get("members", []))
        logger.info(
            "SCIM: group push routed via mapping",
            mapping_id=str(mapping.id),
            external_group_id=mapping.external_group_id,
            user_group_id=str(mapping.user_group.id),
            external_id=external_id,
        )
        # 200 on idempotent hit, 201 if scim_external_id was just bound.
        return _scim_response(scim_group_to_dict(mapping, request), 201)

    def retrieve(self, request, pk=None):
        mapping = _get_scim_mapping_by_group_pk(pk)
        if mapping is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        return _scim_response(scim_group_to_dict(mapping, request))

    def update(self, request, pk=None):
        """PUT — full replace. Members list becomes the new membership."""
        mapping = _get_scim_mapping_by_group_pk(pk)
        if mapping is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _scim_error_response("Invalid JSON body", 400, "invalidSyntax")

        display_name = data.get("displayName")
        if display_name and display_name != mapping.external_group_id:
            mapping.external_group_id = display_name
            mapping.save(update_fields=["external_group_id"])

        group = mapping.user_group
        group.user_set.clear()
        _apply_group_members_add(group, data.get("members", []) or [])
        return _scim_response(scim_group_to_dict(mapping, request))

    def partial_update(self, request, pk=None):
        mapping = _get_scim_mapping_by_group_pk(pk)
        if mapping is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return _scim_error_response("Invalid JSON body", 400, "invalidSyntax")

        # Some SCIM clients send "Operations" (RFC casing), some send lowercase.
        operations = data.get("Operations") or data.get("operations") or []
        logger.info(
            "SCIM: group PATCH received",
            group_id=pk,
            body=data,
            operations_count=len(operations),
        )

        group = mapping.user_group

        for op in operations:
            op_type = op.get("op", "").lower()
            path = op.get("path", "")
            value = op.get("value")

            if op_type == "add" and path == "members":
                _apply_group_members_add(group, value or [])
            elif op_type == "remove":
                if path == "members":
                    # Two flavors per RFC 7644 §3.5.2.2:
                    #   - {"op":"remove","path":"members"} with no value → remove ALL
                    #   - {"op":"remove","path":"members","value":[{"value":"uuid"},...]}
                    #     → remove only the listed members
                    if value:
                        _apply_group_members_remove(group, value)
                    else:
                        group.user_set.clear()
                else:
                    # Filter selector path, e.g. members[value eq "uuid"]
                    uid = _extract_member_filter_id(path)
                    if uid:
                        try:
                            group.user_set.remove(User.objects.get(id=uid))
                        except User.DoesNotExist:
                            pass
            elif op_type == "replace":
                if path == "members":
                    group.user_set.clear()
                    _apply_group_members_add(group, value or [])
                elif path == "displayName" and value:
                    # IdP renamed the group. Update the mapping label;
                    # scim_external_id stays as the stable join key.
                    mapping.external_group_id = value
                    mapping.save(update_fields=["external_group_id"])
                elif isinstance(value, dict):
                    if "displayName" in value:
                        mapping.external_group_id = value["displayName"]
                        mapping.save(update_fields=["external_group_id"])
                    if "members" in value:
                        group.user_set.clear()
                        _apply_group_members_add(group, value["members"] or [])

        return _scim_response(scim_group_to_dict(mapping, request))

    def destroy(self, request, pk=None):
        """
        SCIM DELETE — release the group from SCIM management without
        destroying the CISO-side UserGroup. We null scim_external_id so the
        mapping reverts to JWT-only mode; existing memberships are preserved.
        """
        mapping = _get_scim_mapping_by_group_pk(pk)
        if mapping is None:
            return _scim_error_response(f"Group {pk} not found", 404)
        mapping.scim_external_id = None
        mapping.save(update_fields=["scim_external_id"])
        logger.info(
            "SCIM: group released from SCIM management",
            group_id=pk,
            mapping_id=str(mapping.id),
        )
        return JsonResponse({}, status=204)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_user_by_pk(pk):
    try:
        return User.objects.get(id=pk)
    except (User.DoesNotExist, ValueError):
        return None


def _get_scim_mapping_by_group_pk(pk):
    """
    Resolve the SCIM-active IdPGroupMapping for a given UserGroup primary key.

    A UserGroup may have several mappings, but only one with a non-null
    scim_external_id is SCIM-bound at any time. Returns None if the UserGroup
    is unknown or is not currently managed via SCIM.
    """
    try:
        return (
            IdPGroupMapping.objects.select_related("user_group")
            .prefetch_related("user_group__user_set")
            .filter(user_group_id=pk, scim_external_id__isnull=False)
            .first()
        )
    except (ValueError, IdPGroupMapping.DoesNotExist):
        return None


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
    emails = data.get("emails", [])
    if emails:
        primary = next((e for e in emails if e.get("primary")), emails[0])
        new_email = primary.get("value")
        if new_email:
            user.email = new_email
    user.save()


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
    emails = value_dict.get("emails", [])
    if emails:
        primary = next((e for e in emails if e.get("primary")), emails[0])
        new_email = primary.get("value")
        if new_email:
            user.email = new_email


_EMAILS_VALUE_PATH_RE = re.compile(
    r'^emails(\[[^\]]*\])?\.value$', re.IGNORECASE
)


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
        if isinstance(value, list) and value:
            primary = next((e for e in value if e.get("primary")), value[0])
            new_email = primary.get("value")
            if new_email:
                user.email = new_email
    elif _EMAILS_VALUE_PATH_RE.match(path):
        # IdP-targeted email value update, e.g. emails[type eq "work"].value.
        # Since we only persist one email, any such update writes user.email.
        if value:
            user.email = value


def _apply_group_members_add(group, members):
    for member in members:
        uid = member.get("value")
        if uid:
            try:
                group.user_set.add(User.objects.get(id=uid))
            except (User.DoesNotExist, ValueError):
                pass


def _apply_group_members_remove(group, members):
    for member in members:
        uid = member.get("value") if isinstance(member, dict) else member
        if uid:
            try:
                group.user_set.remove(User.objects.get(id=uid))
            except (User.DoesNotExist, ValueError):
                pass


_MEMBER_FILTER_RE = re.compile(
    r'members\[value\s+eq\s+["\']([^"\']+)["\']\]',
    re.IGNORECASE,
)


def _extract_member_filter_id(path):
    m = _MEMBER_FILTER_RE.search(path)
    return m.group(1) if m else None
