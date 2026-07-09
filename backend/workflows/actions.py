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
    """Dotted-path lookup into nested dicts; None when the path breaks."""
    current = data
    for part in str(path).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
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
        if not kwargs.get("name"):
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

        try:
            obj = entry["model"].objects.create(folder=instance.folder, **kwargs)
        except ValidationError as e:
            raise ActionError(f"create_object: {'; '.join(e.messages)}")
        return {
            "created_object_id": str(obj.id),
            "created_object_name": obj.name,
            "created_object_model": config.get("model"),
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


def execute_action(node, instance):
    config = node.action_config or {}
    action_type = config.get("type")
    action = ACTION_REGISTRY.get(action_type)
    if action is None:
        raise ActionError(f"Unknown action type '{action_type}'")
    return action.execute(config, instance)
