"""Generic list/detail tools over a registry of object types.

The hand-written get_* tools cover the well-trodden objects with tailored
columns. This module covers the long tail: an object type becomes reachable by
adding one line to OBJECTS rather than a new tool per type per verb, which is
what kept ~45 of the API's 76 collections unreachable.

Every path here is verified against a live backend; several apps mount their
routers under a prefix (privacy/, ebios-rm/, ...), so the registry stores the
full relative path rather than assuming /<name>/.
"""

import re

from ..client import make_get_request, get_paginated_results, found_line
from ..utils.response_formatter import (
    success_response,
    error_response,
    empty_response,
    http_error_response,
)

# object_type -> API collection path (relative to API_URL).
# Deliberately excludes credential and session material: workflow-secrets,
# workflow-tokens, sessions, idp-groups, global.
OBJECTS = {
    # core
    "applied_controls": "applied-controls",
    "assets": "assets",
    "compliance_assessments": "compliance-assessments",
    "evidences": "evidences",
    "findings": "findings",
    "folders": "folders",
    "incidents": "incidents",
    "perimeters": "perimeters",
    "policies": "policies",
    "public_documents": "public-documents",
    "requirement_assessments": "requirement-assessments",
    "requirement_nodes": "requirement-nodes",
    "risk_acceptances": "risk-acceptances",
    "risk_assessments": "risk-assessments",
    "risk_scenarios": "risk-scenarios",
    "security_exceptions": "security-exceptions",
    "task_templates": "task-templates",
    "task_nodes": "task-nodes",
    "threats": "threats",
    "timeline_entries": "timeline-entries",
    "vulnerabilities": "vulnerabilities",
    "comments": "comments",
    # third party
    "entities": "entities",
    "entity_assessments": "entity-assessments",
    "solutions": "solutions",
    # questionnaires
    "answers": "answers",
    "questions": "questions",
    "question_choices": "question-choices",
    # privacy (GDPR) — entire app was unreachable before
    "processings": "privacy/processings",
    "personal_data": "privacy/personal-data",
    "purposes": "privacy/purposes",
    "data_subjects": "privacy/data-subjects",
    "data_recipients": "privacy/data-recipients",
    "data_contractors": "privacy/data-contractors",
    "data_transfers": "privacy/data-transfers",
    "data_breaches": "privacy/data-breaches",
    "right_requests": "privacy/right-requests",
    # document management (registers under document-* / managed-*, not "documents")
    "managed_documents": "managed-documents",
    "document_containers": "document-containers",
    "document_templates": "document-templates",
    "document_revisions": "document-revisions",
    # threat modelling / TTP
    "threat_models": "threat-models",
    "ttp_catalogs": "ttp-catalogs",
    "tactics": "tactics",
    "techniques": "techniques",
    "cwes": "cwes",
    # journeys / portals / presets
    "journeys": "journeys",
    "journey_steps": "journey-steps",
    "presets": "presets",
    "portals": "portals",
    "portal_presets": "portal-presets",
    "validation_flows": "validation-flows",
    "library_drafts": "library-drafts",
    # IAM (all RBAC-gated server-side)
    "actors": "actors",
    "teams": "teams",
    "user_groups": "user-groups",
    "role_assignments": "role-assignments",
}

# Field names and ids land in URL paths or are echoed back; keep them boring.
FIELD_NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*")
OBJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")

# Preferred columns, in order, when the caller does not name any.
PREFERRED = [
    "ref_id",
    "name",
    "status",
    "result",
    "severity",
    "treatment",
    "category",
    "folder",
    "description",
]
MAX_CELL = 60


def _flatten(value):
    """Render an API value as one short cell."""
    if value is None:
        return "--"
    if isinstance(value, dict):
        return str(value.get("str") or value.get("name") or value.get("id") or "--")
    if isinstance(value, list):
        return ", ".join(_flatten(v) for v in value[:3]) + (
            "…" if len(value) > 3 else ""
        )
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return text[:MAX_CELL] + "…" if len(text) > MAX_CELL else text


def _columns(rows, fields):
    if fields:
        return [f for f in fields if FIELD_NAME.fullmatch(f)]
    present = {k for row in rows for k in row}
    cols = [c for c in PREFERRED if c in present]
    if not cols:
        # Unknown shape: fall back to the first few scalar-ish keys.
        cols = [k for k in list(rows[0])[:5] if k != "id"]
    return cols


def _unknown_type(object_type):
    return error_response(
        "Unknown object type",
        f"'{object_type}' is not a known object type.",
        "Choose one of: " + ", ".join(sorted(OBJECTS)),
        retry_allowed=True,
    )


async def list_objects(
    object_type: str,
    filters: dict = None,
    limit: int = None,
    offset: int = None,
    fields: list = None,
):
    """List objects of any supported type, as a table. Use when no dedicated get_* tool exists.

    Covers the long tail of object types — privacy/GDPR records, questionnaire
    answers, threat models, TTP catalogs, journeys, portals, IAM groups and more.
    Prefer a dedicated tool (get_assets, get_risk_scenarios, ...) when one exists,
    since those return richer columns.

    For "how many" questions use count_objects instead: this response is capped.

    Args:
        object_type: e.g. processings, personal_data, findings, threat_models, teams
        filters: Query filters as a mapping, e.g. {"status": "to_do"}
        limit: Max rows to return (default 100)
        offset: Row to start from, for paging
        fields: Column names to show, e.g. ["name", "status"]
    """
    try:
        endpoint = OBJECTS.get(object_type)
        if not endpoint:
            return _unknown_type(object_type)

        params = dict(filters or {})
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        res = make_get_request(f"/{endpoint}/", params=params)
        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        rows = get_paginated_results(res.json())
        if not rows:
            return empty_response(object_type, filters)

        cols = _columns(rows, fields)
        out = found_line(rows, object_type, paginated=True, offset=offset or 0)
        if filters:
            out += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        out += "\n\n|id|" + "|".join(cols) + "|\n|" + "---|" * (len(cols) + 1) + "\n"
        for row in rows:
            cells = [_flatten(row.get(c)) for c in cols]
            out += f"|{row.get('id', '--')}|" + "|".join(cells) + "|\n"

        return success_response(
            out,
            "list_objects",
            f"Use get_object(object_type='{object_type}', object_id=<id>) for one record's full detail.",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_object(object_type: str, object_id: str):
    """Get every field of ONE object of any supported type, by its ID.

    Args:
        object_type: e.g. processings, personal_data, findings, threat_models
        object_id: The object's UUID, as shown in the id column of list_objects
    """
    try:
        endpoint = OBJECTS.get(object_type)
        if not endpoint:
            return _unknown_type(object_type)
        # object_id lands in the URL path; keep traversal and separators out.
        if not OBJECT_ID.fullmatch(object_id or ""):
            return error_response(
                "Invalid object id",
                f"'{object_id}' is not a valid identifier.",
                "Pass the id exactly as shown in the id column of list_objects.",
                retry_allowed=True,
            )

        res = make_get_request(f"/{endpoint}/{object_id}/")
        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        obj = res.json()
        if not isinstance(obj, dict):
            return error_response(
                "Unexpected response",
                "The API did not return a single object.",
                "Check the object_type and id.",
                retry_allowed=True,
            )

        title = obj.get("name") or obj.get("ref_id") or object_id
        out = f"## {object_type}: {title}\n\n"
        for key in sorted(obj):
            out += f"**{key}:** {_flatten(obj[key])}\n"

        return success_response(
            out, "get_object", "Use this data to answer the question."
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )
