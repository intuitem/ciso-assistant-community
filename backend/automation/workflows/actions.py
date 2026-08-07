"""Built-in action registry.

One class per action type. `execute` receives the node's action_config and the
running instance; whatever dict it returns is fed through the node's
output_mapping into instance variables. String config values support
`{{variable}}` templating with dotted-path lookup (`{{payload.vendor.name}}`).
"""

import datetime
import re
import uuid
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.db.models import Q

from core.models import (
    AppliedControl,
    RequirementAssessment,
    Asset,
    ComplianceAssessment,
    Evidence,
    Finding,
    FindingsAssessment,
    Framework,
    Incident,
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    SecurityException,
    Vulnerability,
)
from tprm.models import Entity, EntityAssessment

TEMPLATE_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


class ActionError(Exception):
    pass


def dig(data, path):
    """Dotted-path lookup into nested dicts and lists (numeric segments index
    into lists: `body.severity.0.score`); None when the path breaks."""
    current = data
    for part in str(path).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def render(value, variables):
    """Replace {{path}} placeholders in strings; leave other types alone.
    Objects and lists serialize as JSON so whole-object references
    ({{nodes.fetch.body}}) compose into request bodies and fields."""
    if isinstance(value, str):

        def substitute(match):
            resolved = dig(variables, match.group(1))
            if resolved is None:
                return ""
            if isinstance(resolved, (dict, list)):
                import json

                return json.dumps(resolved, default=str)
            return str(resolved)

        return TEMPLATE_RE.sub(substitute, value)
    if isinstance(value, dict):
        return {k: render(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, variables) for v in value]
    return value


def _render_context(instance):
    """Template context: instance variables plus the node-output namespace
    ({{nodes.<ref>.<path>}}). Inside a loop body the
    engine sets a transient instance-local overlay from the current token's
    iteration stack, adding {{item}}/{{index}} (shadowing same-named
    variables); never persisted."""
    overlay = getattr(instance, "_iteration_context", None) or {}
    return {**instance.variables, "nodes": instance.node_outputs, **overlay}


ACTION_REGISTRY = {}


def register(cls):
    ACTION_REGISTRY[cls.action_type] = cls()
    return cls


class BaseAction:
    action_type = ""

    def execute(self, config: dict, instance) -> dict:
        raise NotImplementedError


@register
class LogAction(BaseAction):
    action_type = "log"

    def execute(self, config, instance):
        return {"message": render(config.get("message", ""), _render_context(instance))}


@register
class SetVariablesAction(BaseAction):
    action_type = "set_variables"

    def execute(self, config, instance):
        # In-memory update only; the engine flushes variables + node_outputs in
        # one write via _persist_node_output right after every action runs.
        values = render(config.get("variables", {}), _render_context(instance))
        instance.variables.update(values)
        return values


# Explicit registry of models workflows may create: each entry
# lists the writable simple fields and the FK fields (target model + the
# frontend endpoint serving its options). Anything else in the config is
# ignored. FK values are UUIDs — templatable, so a previous node's
# created_object_id can feed the next node's FK.
#
# With `upsert: true` in the config, the action matches an existing row by
# the entry's `match_on` field (within the instance's folder) and updates it
# instead of creating a duplicate, which the primitive sync flows need.
# Entries without an explicit `match_on` match on name.
CREATABLE_MODELS = {
    "applied_control": {
        "model": AppliedControl,
        "fields": ["name", "description", "ref_id"],
        "fk_fields": {},
    },
    "evidence": {
        "model": Evidence,
        "fields": ["name", "description"],
        "fk_fields": {},
    },
    "incident": {
        "model": Incident,
        "fields": ["name", "description", "ref_id", "status", "severity", "link"],
        "fk_fields": {},
    },
    "asset": {
        "model": Asset,
        "fields": ["name", "description", "ref_id", "type", "reference_link"],
        "fk_fields": {},
    },
    "vulnerability": {
        "model": Vulnerability,
        "fields": ["name", "description", "ref_id", "status", "severity"],
        "fk_fields": {},
    },
    "security_exception": {
        "model": SecurityException,
        "fields": ["name", "description", "ref_id", "severity", "expiration_date"],
        "fk_fields": {},
    },
    "entity": {
        "model": Entity,
        "fields": ["name", "description", "ref_id", "mission", "reference_link"],
        "fk_fields": {},
    },
    "findings_assessment": {
        "model": FindingsAssessment,
        "fields": ["name", "description", "ref_id"],
        "fk_fields": {},
    },
    "finding": {
        "model": Finding,
        "fields": ["name", "description", "ref_id", "severity", "status"],
        "fk_fields": {
            "findings_assessment": (FindingsAssessment, "findings-assessments")
        },
    },
    "compliance_assessment": {
        "model": ComplianceAssessment,
        "fields": ["name", "description", "ref_id"],
        "fk_fields": {
            "framework": (Framework, "frameworks"),
            "perimeter": (Perimeter, "perimeters"),
        },
    },
    "risk_assessment": {
        "model": RiskAssessment,
        "fields": ["name", "description", "ref_id"],
        "fk_fields": {
            "risk_matrix": (RiskMatrix, "risk-matrices"),
            "perimeter": (Perimeter, "perimeters"),
        },
    },
    "entity_assessment": {
        "model": EntityAssessment,
        "fields": ["name", "description"],
        "fk_fields": {
            "entity": (Entity, "entities"),
            "perimeter": (Perimeter, "perimeters"),
        },
    },
}


def _accessible_folder_ids(folder):
    """The instance folder, its ancestors (global referentials live in root)
    and its subtree. FK targets outside this set are cross-scope writes."""
    ids = {folder.id}
    ids |= {f.id for f in folder.get_parent_folders()}
    ids |= {f.id for f in folder.get_sub_folders()}
    return ids


@register
class CreateObjectAction(BaseAction):
    action_type = "create_object"

    def execute(self, config, instance):
        entry = CREATABLE_MODELS.get(config.get("model"))
        if entry is None:
            raise ActionError(f"create_object: unknown model '{config.get('model')}'")
        fields = render(config.get("fields", {}), _render_context(instance))
        kwargs = {
            key: value
            for key, value in fields.items()
            if key in entry["fields"] and value not in ("", None)
        }
        if not kwargs.get("name") and not config.get("upsert"):
            raise ActionError("create_object: 'name' is required")

        allowed_folders = None
        for fk_name, (fk_model, _endpoint) in entry["fk_fields"].items():
            raw = fields.get(fk_name)
            if not raw:
                continue
            try:
                target = fk_model.objects.filter(id=raw).first()
            except ValueError, ValidationError:
                target = None
            if target is None:
                raise ActionError(f"create_object: {fk_name} '{raw}' does not exist")
            target_folder_id = getattr(target, "folder_id", None)
            if target_folder_id is not None:
                if allowed_folders is None:
                    allowed_folders = _accessible_folder_ids(instance.folder)
                if target_folder_id not in allowed_folders:
                    raise ActionError(
                        f"create_object: {fk_name} is outside this workflow's scope"
                    )
            kwargs[fk_name] = target

        obj = None
        created = True
        if config.get("upsert"):
            match_field = entry.get("match_on", "name")
            match_value = kwargs.get(match_field)
            if match_value in ("", None):
                raise ActionError(f"create_object: upsert requires '{match_field}'")
            obj = (
                entry["model"]
                .objects.filter(folder=instance.folder, **{match_field: match_value})
                .first()
            )

        try:
            if obj is not None:
                created = False
                for key, value in kwargs.items():
                    setattr(obj, key, value)
                obj.save()
            else:
                if not kwargs.get("name"):
                    raise ActionError("create_object: 'name' is required")
                obj = entry["model"].objects.create(folder=instance.folder, **kwargs)
        except ValidationError as e:
            raise ActionError(f"create_object: {'; '.join(e.messages)}")
        return {
            "created_object_id": str(obj.id),
            "created_object_name": obj.name,
            "created_object_model": config.get("model"),
            "created": created,
        }


# Explicit registry of models workflows may read. Each entry lists
# the readable simple fields on top of BASE_READ_FIELDS; the combined set is
# both the serialized output AND the filter/order whitelist — no "__" paths,
# no relations, so filters cannot tunnel into other objects.
BASE_READ_FIELDS = ["id", "name", "created_at", "updated_at"]


def _requirements_breakdown(assessment):
    """Total assessable requirement assessments and their count per result —
    stable shape: every result key present, zeroes included."""
    by_result = {result: 0 for result in RequirementAssessment.Result.values}
    total = 0
    for count, result in assessment.get_requirements_result_count():
        by_result[result] = count
        total += count
    return {"total": total, **by_result}


READABLE_MODELS = {
    "applied_control": {
        "model": AppliedControl,
        "fields": ["description", "ref_id", "status", "eta", "priority", "link"],
    },
    "evidence": {
        "model": Evidence,
        "fields": ["description", "status"],
    },
    "incident": {
        "model": Incident,
        "fields": ["description", "ref_id", "status", "severity", "link"],
    },
    "asset": {
        "model": Asset,
        "fields": ["description", "ref_id", "type", "reference_link"],
    },
    "vulnerability": {
        "model": Vulnerability,
        "fields": ["description", "ref_id", "status", "severity", "eta", "due_date"],
    },
    "security_exception": {
        "model": SecurityException,
        "fields": ["description", "ref_id", "status", "severity", "expiration_date"],
    },
    "entity": {
        "model": Entity,
        "fields": ["description", "ref_id", "mission", "reference_link"],
    },
    "findings_assessment": {
        "model": FindingsAssessment,
        "fields": ["description", "ref_id", "status", "eta", "due_date"],
    },
    "finding": {
        "model": Finding,
        "fields": [
            "description",
            "ref_id",
            "status",
            "severity",
            "eta",
            "due_date",
            "priority",
        ],
    },
    "compliance_assessment": {
        "model": ComplianceAssessment,
        "fields": ["description", "ref_id", "status", "eta", "due_date"],
        # Output-only values (never filterable/orderable — they don't exist as
        # queryable columns). Each callable may run its own queries per row,
        # which the list cap bounds.
        "computed": {
            "computed_outcome": lambda ca: ca.computed_outcome,
            "scores": lambda ca: ca.get_global_score(),
            "requirements": _requirements_breakdown,
        },
    },
    "risk_assessment": {
        "model": RiskAssessment,
        "fields": ["description", "ref_id", "status", "eta", "due_date"],
    },
    "entity_assessment": {
        "model": EntityAssessment,
        "fields": ["description", "status", "eta", "due_date"],
    },
}

READ_MAX_LIMIT = 100
READ_DEFAULT_LIMIT = 25


def _read_scope_folder_ids(folder):
    """Instance folder + subtree ONLY — deliberately narrower than
    _accessible_folder_ids: reads of ancestor folders would leak parent-domain
    rows into a child-domain workflow's run log."""
    return {folder.id, *(f.id for f in folder.get_sub_folders())}


_READ_OP_LOOKUPS = {
    "eq": "exact",
    "neq": "exact",
    "gt": "gt",
    "lt": "lt",
    "gte": "gte",
    "lte": "lte",
    "in": "in",
    "not_in": "in",
    "contains": "icontains",
    "is_null": "isnull",
}


def _read_condition_to_q(condition, allowed_fields, context):
    field = condition.get("field")
    if field not in allowed_fields:
        raise ActionError(f"read_objects: '{field}' is not a filterable field")
    op = condition.get("op", "eq")
    lookup = _READ_OP_LOOKUPS.get(op)
    if lookup is None:
        raise ActionError(f"read_objects: unknown operator '{op}'")
    value = render(condition.get("value"), context)
    if op == "is_null":
        return Q(
            **{f"{field}__isnull": _as_bool(value) if value not in (None, "") else True}
        )
    if op in ("in", "not_in"):
        if isinstance(value, str):
            parsed = json_loads_or_none(value)
            value = (
                parsed
                if isinstance(parsed, list)
                else [item.strip() for item in value.split(",") if item.strip()]
            )
        if not isinstance(value, list):
            raise ActionError(f"read_objects: '{op}' needs a list value")
        query = Q(**{f"{field}__in": value})
        return ~query if op == "not_in" else query
    query = Q(**{f"{field}__{lookup}": value})
    return ~query if op == "neq" else query


def _read_group_to_q(group, allowed_fields, context):
    operator = group.get("operator", "and")
    parts = [
        _read_condition_to_q(condition, allowed_fields, context)
        for condition in group.get("conditions", [])
    ]
    parts += [
        _read_group_to_q(child, allowed_fields, context)
        for child in group.get("children", [])
    ]
    if not parts:
        return Q()
    if operator == "or":
        combined = parts[0]
        for part in parts[1:]:
            combined |= part
        return combined
    combined = parts[0]
    for part in parts[1:]:
        combined &= part
    # Same semantics as event filters: NOT(all(results)).
    return ~combined if operator == "not" else combined


def _read_filters_to_q(tree, allowed_fields, context):
    if tree in (None, {}):
        return Q()
    return _read_group_to_q(tree, allowed_fields, context)


def _serialize_read_row(obj, fields, computed=None):
    row = {}
    for field in fields:
        value = getattr(obj, field, None)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, (datetime.datetime, datetime.date)):
            value = value.isoformat()
        row[field] = value
    if computed:
        import json

        for name, resolve in computed.items():
            row[name] = json.loads(json.dumps(resolve(obj), default=str))
    return row


@register
class ReadObjectsAction(BaseAction):
    action_type = "read_objects"

    def execute(self, config, instance):
        entry = READABLE_MODELS.get(config.get("model"))
        if entry is None:
            raise ActionError(f"read_objects: unknown model '{config.get('model')}'")
        fields = BASE_READ_FIELDS + entry["fields"]
        context = _render_context(instance)
        query = _read_filters_to_q(config.get("filters"), set(fields), context)

        order_by = config.get("order_by") or "-created_at"
        if order_by.lstrip("-") not in fields:
            raise ActionError(f"read_objects: '{order_by}' is not an orderable field")

        # Rows must be BOTH inside the workflow's subtree scope
        # AND visible to the run identity — the identity's view
        # scope is the API's own row-visibility rule, so the run reads
        # exactly what the API would show that user.
        from . import authz
        from .engine import run_identity

        queryset = (
            entry["model"]
            .objects.filter(folder_id__in=_read_scope_folder_ids(instance.folder))
            .filter(id__in=authz.viewable_ids(run_identity(instance), entry["model"]))
            .filter(query)
            .order_by(order_by, "id")  # id tie-break keeps pagination stable
        )
        try:
            if config.get("mode", "list") == "first":
                obj = queryset.first()
                computed = entry.get("computed")
                return {
                    "found": obj is not None,
                    "object": _serialize_read_row(obj, fields, computed)
                    if obj
                    else None,
                }
            limit = min(
                max(int(config.get("limit") or READ_DEFAULT_LIMIT), 1), READ_MAX_LIMIT
            )
            return {
                # Unpaged count so threshold conditions work beyond the page.
                "count": queryset.count(),
                "results": [
                    _serialize_read_row(obj, fields, entry.get("computed"))
                    for obj in queryset[:limit]
                ],
            }
        except (ValidationError, ValueError, TypeError) as e:
            # Type mismatches only surface when the queryset evaluates
            # (e.g. "abc" compared against a date field).
            raise ActionError(f"read_objects: invalid filter value ({e})")


@register
class SendEmailAction(BaseAction):
    action_type = "send_email"

    def execute(self, config, instance):
        from core.tasks import send_notification_email

        recipients = [
            email.strip()
            for email in render(
                config.get("recipients", ""), _render_context(instance)
            ).split(",")
            if email.strip()
        ]
        if not recipients:
            raise ActionError("send_email: no recipients configured")
        subject = render(config.get("subject", ""), _render_context(instance))
        body = render(config.get("body", ""), _render_context(instance))
        for email in recipients:
            send_notification_email(subject, body, email)
        return {"recipients": recipients, "subject": subject}


@register
class EmitEventAction(BaseAction):
    action_type = "emit_event"

    def execute(self, config, instance):
        event_key = render(config.get("event_key", ""), _render_context(instance))
        if not event_key:
            raise ActionError("emit_event: no event_key configured")
        # Broadcast semantics (spec §7): wake every waiting event token whose
        # key matches, scoped to the same folder. Deferred import: engine
        # imports this module.
        from .engine import broadcast_event

        woken = broadcast_event(event_key, instance)
        return {"event_key": event_key, "woken_tokens": woken}


SECRETS_REFERENCE_RE = re.compile(r"\{\{\s*secrets\.")


def _secrets_context(instance, raw_config):
    """Merge decrypted secrets into a rendering context, only when the config
    actually references {{secrets.*}} and only for http_request."""
    import json

    # Must tolerate the same whitespace TEMPLATE_RE accepts ({{ secrets.x }}).
    if not SECRETS_REFERENCE_RE.search(json.dumps(raw_config)):
        return _render_context(instance)
    from .models import WorkflowSecret

    # Workflow-scoped: an instance resolves ONLY its own workflow's secrets.
    # (workflow, name) is unique, so there is no ambiguity and no cross-workflow
    # or cross-folder read. Mirrored in validation._existing_secret_names.
    secrets = {
        secret.name: secret.value
        for secret in WorkflowSecret.objects.filter(workflow_id=instance.workflow_id)
    }
    return {**_render_context(instance), "secrets": secrets}


@register
class HttpRequestAction(BaseAction):
    action_type = "http_request"

    def execute(self, config, instance):
        import requests
        from core.net_safety import (
            BlockedRequestError,
            DnsLookupError,
            assert_public_url_unless_dev,
        )

        context = _secrets_context(instance, config)
        url = render(config.get("url", ""), context)
        if not url:
            raise ActionError("http_request: no URL configured")
        try:
            assert_public_url_unless_dev(url, allowed_schemes=("https", "http"))
        except (BlockedRequestError, DnsLookupError) as e:
            # Report the host only: the URL may carry a secret in its query
            # string. DNS failures are transient-adjacent, so
            # ActionError keeps them on the node's retry path.
            host = urlsplit(url).hostname or "target"
            raise ActionError(f"http_request: {type(e).__name__} for host '{host}'")

        method = (config.get("method") or "GET").upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            raise ActionError(f"http_request: unsupported method '{method}'")
        headers = {
            str(key): render(str(value), context)
            for key, value in (config.get("headers") or {}).items()
        }
        body = render(config.get("body"), context)
        # Clamp both ends: requests raises ValueError on a negative timeout.
        timeout = min(max(int(config.get("timeout") or 15), 1), 30)

        # Redirects are NOT followed: only the initial URL is SSRF-checked, so
        # following a 3xx Location would reach an internal address the guard
        # never saw. A 3xx is returned as-is for the graph to handle.
        kwargs = {"headers": headers, "timeout": timeout, "allow_redirects": False}
        if body not in (None, ""):
            if isinstance(body, (dict, list)):
                kwargs["json"] = body
            else:
                parsed = json_loads_or_none(body)
                if parsed is not None:
                    kwargs["json"] = parsed
                else:
                    kwargs["data"] = body
        try:
            response = requests.request(method, url, **kwargs)
        except requests.RequestException:
            # requests exceptions stringify with the full URL (possible secret),
            # so report the host only. Network failures stay on the retry path.
            host = urlsplit(url).hostname or "target"
            raise ActionError(f"http_request: request to '{host}' failed")

        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text[:5000]
        # An error status fails the node right here (and stays retry-eligible)
        # instead of letting downstream nodes run on empty variables. Graphs
        # that want to branch on the status opt in via allow_error_status.
        if response.status_code >= 400 and not config.get("allow_error_status"):
            host = urlsplit(url).hostname or "target"
            raise ActionError(
                f"http_request: HTTP {response.status_code} from '{host}': "
                f"{str(response_body)[:200]}"
            )
        # Secrets never appear here unless the remote echoes them; request
        # details (headers) are deliberately not logged.
        return {"status": response.status_code, "body": response_body}


def json_loads_or_none(value):
    import json

    try:
        return json.loads(value)
    except TypeError, ValueError:
        return None


@register
class ProvisionFolderAction(BaseAction):
    action_type = "provision_folder"

    def execute(self, config, instance):
        from iam.models import Folder

        name = render(config.get("name", ""), _render_context(instance))
        if not name:
            raise ActionError("provision_folder: 'name' is required")
        parent_id = render(config.get("parent"), _render_context(instance))
        if parent_id:
            parent = Folder.objects.filter(id=parent_id).first()
            # Subtree-only: creating a domain under root/an ancestor would let a
            # domain-scoped publisher provision outside their boundary.
            if parent is None or parent.id not in _read_scope_folder_ids(
                instance.folder
            ):
                raise ActionError(
                    "provision_folder: parent is outside this workflow's scope"
                )
        else:
            parent = instance.folder

        create_groups = bool(config.get("create_default_groups"))
        folder = Folder.objects.filter(
            name=name,
            parent_folder=parent,
            content_type=Folder.ContentType.DOMAIN,
        ).first()
        created = folder is None
        if created:
            folder = Folder.objects.create(
                name=name,
                parent_folder=parent,
                content_type=Folder.ContentType.DOMAIN,
                create_iam_groups=create_groups,
            )
            if create_groups:
                Folder.create_default_ug_and_ra(folder)
        elif create_groups and not folder.create_iam_groups:
            folder.create_iam_groups = True
            folder.save(update_fields=["create_iam_groups", "updated_at"])
            Folder.create_default_ug_and_ra(folder)
        return {
            "folder_id": str(folder.id),
            "folder_name": folder.name,
            "created": created,
        }


@register
class ProvisionUserAction(BaseAction):
    action_type = "provision_user"

    def execute(self, config, instance):
        from iam.models import User

        email = (
            render(config.get("email", ""), _render_context(instance)).strip().lower()
        )
        if not email:
            raise ActionError("provision_user: 'email' is required")
        fields = {
            "first_name": render(
                config.get("first_name", ""), _render_context(instance)
            ),
            "last_name": render(config.get("last_name", ""), _render_context(instance)),
        }
        user = User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            if config.get("send_onboarding_email"):
                user = User.objects.create_user(email=email, **fields)
            else:
                # _create_user is the only path that can suppress the welcome
                # mail (create_user always mails when an email host is set).
                user = User.objects._create_user(
                    email, None, mailing=False, initial_group=None, **fields
                )
        else:
            for key, value in fields.items():
                if value:
                    setattr(user, key, value)
        # Only touch activation when the config says so: an omitted key must
        # not re-activate an offboarded account on a routine sync run.
        # (New users are active by default via create_user.)
        if "is_active" in config:
            user.is_active = _as_bool(
                render(config["is_active"], _render_context(instance))
            )
        user.save()
        return {"user_id": str(user.id), "user_email": user.email, "created": created}


@register
class ManageGroupMembershipAction(BaseAction):
    action_type = "manage_group_membership"

    def execute(self, config, instance):
        from iam.models import Folder, User, UserGroup

        context = _render_context(instance)
        user_ref = render(config.get("user", ""), context).strip()
        if not user_ref:
            raise ActionError("manage_group_membership: 'user' is required")
        user = (
            User.objects.filter(id=user_ref).first()
            if UUID_RE.match(user_ref)
            else User.objects.filter(email__iexact=user_ref).first()
        )
        if user is None:
            raise ActionError(f"manage_group_membership: user '{user_ref}' not found")

        group_id = render(config.get("group"), context)
        if group_id:
            group = UserGroup.objects.filter(id=group_id).first()
        else:
            folder_id = render(config.get("folder"), context)
            folder = Folder.objects.filter(id=folder_id).first() if folder_id else None
            codename = config.get("builtin_group", "")
            if folder is None or not codename:
                raise ActionError(
                    "manage_group_membership: set 'group' or 'folder' + 'builtin_group'"
                )
            group = UserGroup.objects.filter(
                folder=folder, name=codename, builtin=True
            ).first()
        if group is None:
            raise ActionError("manage_group_membership: group not found")
        # Subtree-only: an ancestor grant would let a domain admin add a user to
        # the root global-admin group (BI-UG-ADM) via a workflow they publish.
        if group.folder_id not in _read_scope_folder_ids(instance.folder):
            raise ActionError(
                "manage_group_membership: group is outside this workflow's scope"
            )

        operation = config.get("operation", "add")
        if operation == "remove":
            # Last-admin protection (mirrors core remove-members): never strip the
            # final global administrator, or the platform locks out. Only reachable
            # for a root-scoped workflow, since BI-UG-ADM lives at the root folder.
            if group.name == "BI-UG-ADM":
                from django.db import transaction

                with transaction.atomic():
                    UserGroup.objects.select_for_update().filter(
                        name="BI-UG-ADM"
                    ).first()
                    others_remain = (
                        User.objects.filter(user_groups__name="BI-UG-ADM")
                        .exclude(id=user.id)
                        .exists()
                    )
                    if not others_remain:
                        raise ActionError(
                            "manage_group_membership: cannot remove the last "
                            "administrator"
                        )
                    user.user_groups.remove(group)
            else:
                user.user_groups.remove(group)
        else:
            user.user_groups.add(group)
        return {
            "user_id": str(user.id),
            "group_id": str(group.id),
            "group_name": str(group),
            "operation": operation,
        }


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


# Deputization rule: publishing a workflow requires the publisher
# to hold the permissions its actions exercise, checked per action node
# against the workflow's folder.
def required_permissions(action_config):
    action_type = (action_config or {}).get("type")
    if action_type == "create_object":
        entry = CREATABLE_MODELS.get(action_config.get("model"))
        if entry is None:
            return []
        model_name = entry["model"]._meta.model_name
        codenames = [f"add_{model_name}"]
        if action_config.get("upsert"):
            codenames.append(f"change_{model_name}")
        return codenames
    if action_type == "read_objects":
        entry = READABLE_MODELS.get(action_config.get("model"))
        if entry is None:
            return []
        return [f"view_{entry['model']._meta.model_name}"]
    return {
        "provision_folder": ["add_folder", "change_folder"],
        "provision_user": ["add_user", "change_user"],
        # Membership is a M2M-only mutation: the platform authorizes it with
        # change_usergroup on the group's folder (see core add-members/
        # remove-members), NOT change_user — a domain manager manages groups in
        # its subtree without holding the root-scoped change_user.
        "manage_group_membership": ["change_usergroup"],
    }.get(action_type, [])


# User rows are global, not folder-scoped: the platform authorizes user
# create/change/delete at the ROOT folder (core.serializers UserWriteSerializer
# and UserViewSet), so a domain-scoped grant must never let a workflow provision
# or modify users beyond its author's own API authority. Folder and group
# permissions stay folder-scoped — those actions subtree-restrict their targets
# themselves.
ROOT_SCOPED_PERMISSIONS = {"add_user", "change_user", "delete_user"}


def authorization_folder(codename, base_folder):
    """Folder a permission is checked against: root for global user
    permissions, the workflow's own folder for everything else."""
    if codename in ROOT_SCOPED_PERMISSIONS:
        from iam.models import Folder

        return Folder.get_root_folder()
    return base_folder


def validate_read_config(node):
    """Publish-time checks for read_objects nodes: (code, message)
    tuples, same contract as triggers.validate_trigger_config."""
    config = node.action_config or {}
    if config.get("type") != "read_objects":
        return []
    errors = []
    entry = READABLE_MODELS.get(config.get("model"))
    if entry is None:
        return [
            (
                "action_read_unknown_model",
                f"Unknown readable model '{config.get('model')}'",
            )
        ]
    fields = set(BASE_READ_FIELDS) | set(entry["fields"])

    from .events import validate_filter_tree, walk_conditions

    tree = config.get("filters")
    try:
        validate_filter_tree(tree)
    except ValueError as e:
        errors.append(("action_read_invalid_filters", f"Invalid filters: {e}"))
    else:
        for condition in walk_conditions(tree or {}):
            if condition.get("field") not in fields:
                errors.append(
                    (
                        "action_read_invalid_filters",
                        f"'{condition.get('field')}' is not a filterable field of "
                        f"'{config.get('model')}'",
                    )
                )
            if condition.get("changed"):
                errors.append(
                    (
                        "action_read_invalid_filters",
                        "'changed' only applies to event-trigger filters",
                    )
                )

    if config.get("mode", "list") not in ("list", "first"):
        errors.append(
            ("action_read_invalid_mode", f"Unknown mode '{config.get('mode')}'")
        )
    order_by = config.get("order_by") or "-created_at"
    if not isinstance(order_by, str) or order_by.lstrip("-") not in fields:
        errors.append(
            (
                "action_read_invalid_order",
                f"'{order_by}' is not an orderable field of '{config.get('model')}'",
            )
        )
    limit = config.get("limit")
    if limit is not None:
        try:
            valid_limit = 1 <= int(limit) <= READ_MAX_LIMIT
        except TypeError, ValueError:
            valid_limit = False
        if not valid_limit:
            errors.append(
                (
                    "action_read_invalid_limit",
                    f"Limit must be between 1 and {READ_MAX_LIMIT}",
                )
            )
    return errors


def validate_create_config(node):
    """Publish-time checks for create_object nodes, same contract as
    validate_read_config."""
    config = node.action_config or {}
    if config.get("type") != "create_object":
        return []
    entry = CREATABLE_MODELS.get(config.get("model"))
    if entry is None:
        return [
            (
                "action_create_unknown_model",
                f"Unknown creatable model '{config.get('model')}'",
            )
        ]
    fields = config.get("fields") or {}
    errors = []
    for fk_name in entry["fk_fields"]:
        # execute_action skips empty FKs, so a missing non-nullable one only
        # surfaces as an IntegrityError mid-run.
        if entry["model"]._meta.get_field(fk_name).null:
            continue
        if not fields.get(fk_name):
            errors.append(
                (
                    "action_create_missing_fk",
                    f"'{fk_name}' is required to create a '{config.get('model')}'",
                )
            )
    return errors


def authorize_action(node, instance):
    """Runtime half of the deputization promise: before any
    side effect, the run identity must hold every permission the action
    exercises, checked live against the workflow's folder. Refusal is a
    structured, retryable node failure (grant the role, retry the token)."""
    from . import authz
    from .engine import _log, run_identity
    from .models import WorkflowInstanceLog

    codenames = required_permissions(node.action_config)
    if not codenames:
        return
    identity = run_identity(instance)
    denied = (
        codenames
        if identity is None
        else [
            c
            for c in codenames
            if not authz.can(identity, c, authorization_folder(c, instance.folder))
        ]
    )
    if not denied:
        return
    reason = (
        "no run identity (republish the workflow)"
        if identity is None
        else f"'{identity.email}' lacks {', '.join(denied)}"
    )
    _log(
        instance,
        WorkflowInstanceLog.EventType.AUTHORIZATION_DENIED,
        node=node,
        message=f"Authorization denied: {reason}",
        data={
            "codenames": denied,
            "folder": str(instance.folder_id),
            "identity": str(identity.id) if identity else None,
        },
    )
    raise ActionError(f"Authorization denied: {reason}")


def execute_action(node, instance):
    config = node.action_config or {}
    action_type = config.get("type")
    action = ACTION_REGISTRY.get(action_type)
    if action is None:
        raise ActionError(f"Unknown action type '{action_type}'")
    authorize_action(node, instance)
    return action.execute(config, instance)
