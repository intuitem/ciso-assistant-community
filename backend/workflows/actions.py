"""Built-in action registry (spec D12).

One class per action type. `execute` receives the node's action_config and the
running instance; whatever dict it returns is fed through the node's
output_mapping into instance variables. String config values support
`{{variable}}` templating with dotted-path lookup (`{{payload.vendor.name}}`).
"""

import re

from django.core.exceptions import ValidationError

from core.models import (
    AppliedControl,
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
    """Replace {{path}} placeholders in strings; leave other types alone."""
    if isinstance(value, str):

        def substitute(match):
            resolved = dig(variables, match.group(1))
            return "" if resolved is None else str(resolved)

        return TEMPLATE_RE.sub(substitute, value)
    if isinstance(value, dict):
        return {k: render(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, variables) for v in value]
    return value


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
        return {"message": render(config.get("message", ""), instance.variables)}


@register
class SetVariablesAction(BaseAction):
    action_type = "set_variables"

    def execute(self, config, instance):
        values = render(config.get("variables", {}), instance.variables)
        instance.variables.update(values)
        instance.save(update_fields=["variables", "updated_at"])
        return values


# Explicit registry of models workflows may create (spec D15): each entry
# lists the writable simple fields and the FK fields (target model + the
# frontend endpoint serving its options). Anything else in the config is
# ignored. FK values are UUIDs — templatable, so a previous node's
# created_object_id can feed the next node's FK.
#
# With `upsert: true` in the config, the action matches an existing row by
# the entry's `match_on` field (within the instance's folder) and updates it
# instead of creating a duplicate — the primitive sync flows need (D16).
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
        fields = render(config.get("fields", {}), instance.variables)
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
            except (ValueError, ValidationError):
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


@register
class SendEmailAction(BaseAction):
    action_type = "send_email"

    def execute(self, config, instance):
        from core.tasks import send_notification_email

        recipients = [
            email.strip()
            for email in render(config.get("recipients", ""), instance.variables).split(
                ","
            )
            if email.strip()
        ]
        if not recipients:
            raise ActionError("send_email: no recipients configured")
        subject = render(config.get("subject", ""), instance.variables)
        body = render(config.get("body", ""), instance.variables)
        for email in recipients:
            send_notification_email(subject, body, email)
        return {"recipients": recipients, "subject": subject}


@register
class EmitEventAction(BaseAction):
    action_type = "emit_event"

    def execute(self, config, instance):
        event_key = render(config.get("event_key", ""), instance.variables)
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
        return instance.variables
    from .models import WorkflowSecret

    folder_ids = _accessible_folder_ids(instance.folder)
    secrets = {
        secret.name: secret.value
        for secret in WorkflowSecret.objects.filter(folder_id__in=folder_ids)
    }
    return {**instance.variables, "secrets": secrets}


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
            # DNS failures are transient-adjacent: ActionError keeps them on
            # the node's retry path instead of hard-failing the token.
            raise ActionError(f"http_request: {e}")

        method = (config.get("method") or "GET").upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            raise ActionError(f"http_request: unsupported method '{method}'")
        headers = {
            str(key): render(str(value), context)
            for key, value in (config.get("headers") or {}).items()
        }
        body = render(config.get("body"), context)
        timeout = min(int(config.get("timeout") or 15), 30)

        kwargs = {"headers": headers, "timeout": timeout}
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
        except requests.RequestException as e:
            # Network-level failures raise so the node's retry policy applies.
            raise ActionError(f"http_request: {e}")

        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text[:5000]
        # An error status fails the node right here (and stays retry-eligible)
        # instead of letting downstream nodes run on empty variables. Graphs
        # that want to branch on the status opt in via allow_error_status.
        if response.status_code >= 400 and not config.get("allow_error_status"):
            raise ActionError(
                f"http_request: HTTP {response.status_code} from {url}: "
                f"{str(response_body)[:200]}"
            )
        # Secrets never appear here unless the remote echoes them; request
        # details (headers) are deliberately not logged.
        return {"status": response.status_code, "body": response_body}


def json_loads_or_none(value):
    import json

    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


@register
class ProvisionFolderAction(BaseAction):
    action_type = "provision_folder"

    def execute(self, config, instance):
        from iam.models import Folder

        name = render(config.get("name", ""), instance.variables)
        if not name:
            raise ActionError("provision_folder: 'name' is required")
        parent_id = render(config.get("parent"), instance.variables)
        if parent_id:
            parent = Folder.objects.filter(id=parent_id).first()
            if parent is None or parent.id not in _accessible_folder_ids(
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

        email = render(config.get("email", ""), instance.variables).strip().lower()
        if not email:
            raise ActionError("provision_user: 'email' is required")
        fields = {
            "first_name": render(config.get("first_name", ""), instance.variables),
            "last_name": render(config.get("last_name", ""), instance.variables),
        }
        is_active = _as_bool(render(config.get("is_active", True), instance.variables))

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
        user.is_active = is_active
        user.save()
        return {"user_id": str(user.id), "user_email": user.email, "created": created}


@register
class ManageGroupMembershipAction(BaseAction):
    action_type = "manage_group_membership"

    def execute(self, config, instance):
        from iam.models import Folder, User, UserGroup

        context = instance.variables
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
        if group.folder_id not in _accessible_folder_ids(instance.folder):
            raise ActionError(
                "manage_group_membership: group is outside this workflow's scope"
            )

        operation = config.get("operation", "add")
        if operation == "remove":
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


# Deputization rule (spec D18): publishing a workflow requires the publisher
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
    return {
        "provision_folder": ["add_folder", "change_folder"],
        "provision_user": ["add_user", "change_user"],
        "manage_group_membership": ["change_user", "change_usergroup"],
    }.get(action_type, [])


def execute_action(node, instance):
    config = node.action_config or {}
    action_type = config.get("type")
    action = ACTION_REGISTRY.get(action_type)
    if action is None:
        raise ActionError(f"Unknown action type '{action_type}'")
    return action.execute(config, instance)
