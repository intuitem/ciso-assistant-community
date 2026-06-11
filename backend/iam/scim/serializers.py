"""
SCIM 2.0 serialization helpers.

All functions return plain dicts — no DRF serializer classes needed.
The views are responsible for wrapping these in JsonResponse with the
correct Content-Type header.
"""

import re

SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


def _format_dt(dt):
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def scim_user_to_dict(user, request):
    base_url = request.build_absolute_uri("/").rstrip("/")
    location = f"{base_url}/api/scim/v2/Users/{user.id}"
    full_name = f"{user.first_name} {user.last_name}".strip()
    return {
        "schemas": [SCIM_USER_SCHEMA],
        "id": str(user.id),
        "externalId": user.scim_external_id or None,
        "userName": user.email,
        "name": {
            "givenName": user.first_name or "",
            "familyName": user.last_name or "",
            "formatted": full_name or user.email,
        },
        "emails": [{"value": user.email, "primary": True, "type": "work"}],
        "active": user.is_active,
        "meta": {
            "resourceType": "User",
            "created": _format_dt(getattr(user, "created_at", None)),
            "lastModified": _format_dt(getattr(user, "updated_at", None)),
            "location": location,
        },
    }


def scim_group_to_dict(mapping, request):
    """
    Serialize a SCIM Group resource from an IdPGroupMapping.

    The mapping is the bridge between the IdP-side identity (external_group_id
    + scim_external_id) and the CISO-side UserGroup. SCIM clients see the
    IdP-side label as displayName, never the local UserGroup.name.
    """
    group = mapping.user_group
    base_url = request.build_absolute_uri("/").rstrip("/")
    location = f"{base_url}/api/scim/v2/Groups/{group.id}"
    members = []
    for user in group.user_set.all():
        user_location = f"{base_url}/api/scim/v2/Users/{user.id}"
        members.append(
            {"value": str(user.id), "display": str(user), "$ref": user_location}
        )
    return {
        "schemas": [SCIM_GROUP_SCHEMA],
        "id": str(group.id),
        "externalId": mapping.scim_external_id or None,
        "displayName": mapping.external_group_id,
        "members": members,
        "meta": {
            "resourceType": "Group",
            "created": _format_dt(getattr(group, "created_at", None)),
            "lastModified": _format_dt(getattr(group, "updated_at", None)),
            "location": location,
        },
    }


def scim_list_response(resources, total, start_index, count):
    return {
        "schemas": [SCIM_LIST_SCHEMA],
        "totalResults": total,
        "startIndex": start_index,
        "itemsPerPage": count,
        "Resources": resources,
    }


def scim_error(detail, status_code, scim_type=None):
    payload = {
        "schemas": [SCIM_ERROR_SCHEMA],
        "detail": detail,
        "status": str(status_code),
    }
    if scim_type:
        payload["scimType"] = scim_type
    return payload


_FILTER_RE = re.compile(
    r'^(?P<attr>[a-zA-Z_][a-zA-Z0-9_.]*)\s+eq\s+["\'](?P<value>[^"\']*)["\']$',
    re.IGNORECASE,
)


def parse_filter(filter_str):
    """Parse a SCIM filter of the form: attr eq "value". Returns (attr_lower, value) or (None, None)."""
    if not filter_str:
        return None, None
    m = _FILTER_RE.match(filter_str.strip())
    if not m:
        return None, None
    return m.group("attr").lower(), m.group("value")
