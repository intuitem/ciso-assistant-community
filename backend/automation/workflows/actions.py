"""Built-in action registry.

One class per action type. `execute` receives the node's action_config and the
running instance; whatever dict it returns is fed through the node's
output_mapping into instance variables. String config values support
`{{variable}}` templating with dotted-path lookup (`{{payload.vendor.name}}`).
"""

import datetime
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from email.utils import parseaddr
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import (
    BooleanField,
    DateField,
    DecimalField,
    Field,
    FloatField,
    ForeignKey,
    IntegerField,
    Model,
    Q,
    UUIDField,
)

from core.models import (
    Actor,
    AppliedControl,
    RequirementAssessment,
    Asset,
    ComplianceAssessment,
    Evidence,
    FilteringLabel,
    Finding,
    FindingsAssessment,
    Framework,
    Incident,
    Perimeter,
    RiskAcceptance,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    SecurityException,
    ValidationFlow,
    Vulnerability,
)
from core.tasks import get_missing_email_settings
from tprm.models import Entity, EntityAssessment

from .context import RESERVED_VARIABLE_KEYS, VARIABLE_KEY_RE, temporal_seeds
from .models import WorkflowToken
from .tasks import send_email_task

TEMPLATE_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


class ActionError(Exception):
    """Deliberate action failure, routed through the node's retry policy."""


class FatalActionError(ActionError):
    """Permanent action failure (static config, validation) that no retry can
    change: the engine fails the node immediately instead of burning the
    retry schedule."""


class DeferredTask:
    """Returned by an action's execute() instead of an output dict when its
    side effect must run outside the engine transaction (network I/O must not
    hold the instance-tree locks). dispatch() parks the token and enqueues
    `task`; the task hands the token back through
    engine.complete_deferred_action / engine.fail_deferred_action."""

    def __init__(self, task: Callable[..., None], **kwargs):
        """`task` is a huey task called after commit with `kwargs` plus the
        parked token's id as `token_id` and its claim as `dispatch_id`."""
        self.task = task
        self.kwargs = kwargs

    def dispatch(self, token: WorkflowToken) -> None:
        """Park `token` WAITING and enqueue the task after commit. If the
        worker dies before the task reports back, the token stays WAITING
        until the run's TTL reaper collects it — the same exposure as an
        async subprocess wait. No dedicated log row (a new event type would
        cost a migration): NODE_ENTERED is already written, and the
        ACTION_EXECUTED/ERROR row lands when the task reports."""
        dispatch_id = uuid.uuid4()
        token.status = WorkflowToken.Status.WAITING
        # dispatch_id is the claim the task CASes on: only the delivery that
        # clears it runs the side effect, so a duplicate huey delivery is a
        # no-op rather than a second send.
        token.dispatch_id = dispatch_id
        token.save(update_fields=["status", "dispatch_id", "updated_at"])
        # on_commit: the WAITING row must be visible before the consumer
        # runs, or a fast worker finds an ACTIVE token and drops the dispatch.
        task = self.task
        kwargs = {
            "token_id": str(token.id),
            "dispatch_id": str(dispatch_id),
            **self.kwargs,
        }
        transaction.on_commit(lambda: task(**kwargs))


class DeferredSendEmailTask(DeferredTask):
    def __init__(self, subject: str, body: str, recipients: list[str]):
        """Deliver `subject`/`body` to each address in `recipients` over one
        SMTP session, then resume or fail the parked token."""
        super().__init__(
            send_email_task, subject=subject, body=body, recipients=recipients
        )


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
        reserved = RESERVED_VARIABLE_KEYS & values.keys()
        if reserved:
            raise FatalActionError(
                f"set_variables: {', '.join(sorted(reserved))} is set by the engine"
            )
        instance.variables.update(values)
        return values


def _as_date(value, label):
    """ISO date or ISO datetime; a datetime keeps only its date."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        parsed = datetime.datetime.fromisoformat(str(value).strip())
    except ValueError, TypeError:
        raise FatalActionError(
            f"date_offset: {label} '{value}' is not an ISO date (YYYY-MM-DD)"
        )
    return parsed.date()


def _as_offset(value, label):
    if value in ("", None):
        return 0
    try:
        return int(value)
    except ValueError, TypeError:
        raise FatalActionError(f"date_offset: '{label}' must be a whole number")


@register
class DateOffsetAction(BaseAction):
    action_type = "date_offset"

    def execute(self, config, instance):
        context = _render_context(instance)
        base = render(config.get("base", ""), context)
        if base in ("", None):
            # The run's own today, not the wall clock: retries must not drift.
            base = (
                instance.variables.get("today")
                or temporal_seeds(instance.trigger_registration)["today"]
            )
        base_date = _as_date(base, "base")
        result = base_date + datetime.timedelta(
            days=_as_offset(render(config.get("days"), context), "days"),
            weeks=_as_offset(render(config.get("weeks"), context), "weeks"),
        )
        output = str(config.get("output") or "").strip()
        if output:
            if not VARIABLE_KEY_RE.match(output) or output in RESERVED_VARIABLE_KEYS:
                raise FatalActionError(
                    f"date_offset: '{output}' is not a writable variable name"
                )
            # In-memory like set_variables; _persist_node_output flushes it.
            instance.variables[output] = result.isoformat()
        return {"result": result.isoformat(), "base": base_date.isoformat()}


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


# Columns every readable model exposes, when it has them.
BASE_READ_FIELDS = ["id", "name", "created_at", "updated_at"]


@dataclass(frozen=True)
class ReadEntry:
    """One READABLE_MODELS entry: a model workflows may read, and how its
    rows filter and serialize.

    BASE_READ_FIELDS plus ``fields`` is both the serialized output and the
    filter/order whitelist: concrete columns only, no "__" paths, so filters
    cannot tunnel into other objects. FK fields are listed under their API
    name and filter on the id value — still no join.

    A ``computed`` key may shadow a listed column to reshape its output to
    the API read serializer's shape (display labels, matrix cells, nested FK
    dicts) so workflow rows read like API responses; the column name stays
    the filter/order surface, comparing on the raw stored value.
    """

    model: type[Model]
    #: Readable columns on top of BASE_READ_FIELDS.
    fields: list[str]
    #: Output-only values, key -> callable(row); never filterable/orderable.
    computed: dict[str, Callable] = dataclass_field(default_factory=dict)
    #: Restriction every read of this model must satisfy.
    base_filter: Q | None = None
    #: Integer columns where -1 means "not rated"; range filters skip it.
    skip_unrated: frozenset[str] = frozenset()
    #: Relations the computed callables dereference per row.
    select_related: list[str] = dataclass_field(default_factory=list)

    def readable_fields(self) -> list[str]:
        """Return the field names a read node may output, filter and order
        by: BASE_READ_FIELDS trimmed to columns the model actually has (e.g.
        RequirementAssessment has no name column), plus ``fields``."""
        columns = {field.name for field in self.model._meta.concrete_fields}
        return [field for field in BASE_READ_FIELDS if field in columns] + self.fields


def _requirements_breakdown(assessment):
    """Total assessable requirement assessments and their count per result —
    stable shape: every result key present, zeroes included."""
    by_result = {result: 0 for result in RequirementAssessment.Result.values}
    total = 0
    for count, result in assessment.get_requirements_result_count():
        by_result[result] = count
        total += count
    return {"total": total, **by_result}


READABLE_MODELS: dict[str, ReadEntry] = {
    "applied_control": ReadEntry(
        model=AppliedControl,
        fields=[
            "description",
            "ref_id",
            "status",
            "eta",
            "expiry_date",
            "priority",
            "link",
        ],
        computed={"priority": lambda o: o.get_priority_display()},
    ),
    "evidence": ReadEntry(
        model=Evidence,
        fields=["description", "status"],
        computed={"status": lambda o: o.get_status_display()},
    ),
    "incident": ReadEntry(
        model=Incident,
        fields=["description", "ref_id", "status", "severity", "link"],
        computed={
            "status": lambda o: o.get_status_display(),
            "severity": lambda o: o.get_severity_display(),
        },
    ),
    "asset": ReadEntry(
        model=Asset,
        fields=["description", "ref_id", "type", "reference_link"],
        computed={"type": lambda o: o.get_type_display()},
    ),
    "vulnerability": ReadEntry(
        model=Vulnerability,
        fields=["description", "ref_id", "status", "severity", "eta", "due_date"],
        computed={"severity": lambda o: o.get_severity_display()},
    ),
    "security_exception": ReadEntry(
        model=SecurityException,
        fields=["description", "ref_id", "status", "severity", "expiration_date"],
        computed={"severity": lambda o: o.get_severity_display()},
    ),
    "entity": ReadEntry(
        model=Entity,
        fields=["description", "ref_id", "mission", "reference_link"],
    ),
    "findings_assessment": ReadEntry(
        model=FindingsAssessment,
        fields=["description", "ref_id", "status", "eta", "due_date"],
    ),
    "finding": ReadEntry(
        model=Finding,
        fields=[
            "description",
            "ref_id",
            "status",
            "severity",
            "eta",
            "due_date",
            "priority",
        ],
        computed={
            "severity": lambda o: o.get_severity_display(),
            "priority": lambda o: o.get_priority_display(),
        },
    ),
    "compliance_assessment": ReadEntry(
        model=ComplianceAssessment,
        fields=["description", "ref_id", "status", "eta", "due_date"],
        # Output-only values (never filterable/orderable — they don't exist as
        # queryable columns). Each callable may run its own queries per row,
        # which the list cap bounds.
        computed={
            "computed_outcome": lambda ca: ca.computed_outcome,
            "scores": lambda ca: ca.get_global_score(),
            "requirements": _requirements_breakdown,
        },
    ),
    "risk_assessment": ReadEntry(
        model=RiskAssessment,
        fields=["description", "ref_id", "status", "eta", "due_date"],
    ),
    "entity_assessment": ReadEntry(
        model=EntityAssessment,
        fields=["description", "status", "eta", "due_date"],
    ),
    "requirement_assessment": ReadEntry(
        model=RequirementAssessment,
        # Assessments of non-assessable requirements (section headings)
        # exist in the database; never read them.
        base_filter=Q(requirement__assessable=True),
        fields=[
            "status",
            "result",
            "extended_result",
            "score",
            "is_scored",
            "documentation_score",
            "eta",
            "due_date",
            "compliance_assessment",
        ],
        # Identify the requirement and the audit on every row, under the
        # same keys and shapes as RequirementAssessmentReadSerializer.
        computed={
            "name": str,
            "requirement": lambda ra: {
                "id": str(ra.requirement_id),
                "ref_id": ra.requirement.ref_id,
                "name": ra.requirement.name,
            },
            # Subset of the API's FieldsRelatedField dict.
            "compliance_assessment": lambda ra: {
                "str": str(ra.compliance_assessment),
                "id": str(ra.compliance_assessment_id),
                "name": ra.compliance_assessment.name,
            },
        },
        select_related=["requirement", "compliance_assessment"],
    ),
    "risk_scenario": ReadEntry(
        model=RiskScenario,
        fields=[
            "description",
            "ref_id",
            "treatment",
            "inherent_level",
            "current_level",
            "residual_level",
            "risk_assessment",
        ],
        # The level columns hold -1 until the scenario is rated; range and
        # negated filters must not match those rows (eq -1 still selects them).
        skip_unrated=frozenset({"inherent_level", "current_level", "residual_level"}),
        # Levels serialize as their matrix cell dict, like the API
        # serializer; filters keep comparing the raw integer column.
        computed={
            "inherent_level": lambda s: s.get_inherent_risk(),
            "current_level": lambda s: s.get_current_risk(),
            "residual_level": lambda s: s.get_residual_risk(),
            # Subset of the API's FieldsRelatedField dict.
            "risk_assessment": lambda s: {
                "str": str(s.risk_assessment),
                "id": str(s.risk_assessment_id),
                "name": s.risk_assessment.name,
            },
        },
        select_related=["risk_assessment__risk_matrix"],
    ),
    "risk_acceptance": ReadEntry(
        model=RiskAcceptance,
        fields=["description", "state", "expiry_date", "justification"],
        computed={"state": lambda o: o.get_state_display()},
    ),
    "validation_flow": ReadEntry(
        model=ValidationFlow,
        fields=["ref_id", "status", "validation_deadline"],
        # The API's display key for this nameless model.
        computed={"str": str},
    ),
}

READ_MAX_LIMIT = 100
READ_DEFAULT_LIMIT = 25


def _read_scope_folder_ids(folder):
    """Instance folder + subtree ONLY — deliberately narrower than
    _accessible_folder_ids: reads of ancestor folders would leak parent-domain
    rows into a child-domain workflow's run log."""
    return set(folder.get_sub_folders(include_self=True).values_list("id", flat=True))


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


def get_model_field(model: type[Model], name: str) -> Field | None:
    """Return the concrete column named ``name`` on ``model``, or None."""
    for field in model._meta.concrete_fields:
        if field.name == name:
            return field
    return None


def _allowed_ops(field: Field | None) -> set[str]:
    """Return the operators valid for ``field``'s column type; none for an
    unknown column (fail closed). An untyped op either crashes at query time
    or — worse — compiles on both databases with different rows: 'contains'
    on a boolean LIKEs against 'true'/'false' on PostgreSQL (casts to text)
    but against 0/1 on SQLite."""
    if isinstance(field, BooleanField):
        return {"eq", "neq", "is_null"}
    if isinstance(field, (ForeignKey, UUIDField)):
        return {"eq", "neq", "in", "not_in", "is_null"}
    if isinstance(field, (DateField, IntegerField, FloatField, DecimalField)):
        return set(_READ_OP_LOOKUPS) - {"contains"}
    if isinstance(field, Field):
        return set(_READ_OP_LOOKUPS)
    return set()


_UNRATED_GUARDED_OPS = ("neq", "not_in", "gt", "lt", "gte", "lte")


def _guard_unrated(query, op, field, entry):
    """AND the >= 0 guard AFTER any negation so negating can't flip it into
    'OR level < 0': ranges and negations must not sweep unrated (-1) rows in."""
    if op in _UNRATED_GUARDED_OPS and field in entry.skip_unrated:
        query &= Q(**{f"{field}__gte": 0})
    return query


def _sentinel_fields_in(group, sentinels):
    fields = {
        condition.get("field")
        for condition in group.get("conditions", [])
        if condition.get("field") in sentinels
    }
    for child in group.get("children", []):
        fields |= _sentinel_fields_in(child, sentinels)
    return fields


def _read_condition_to_q(condition, entry, allowed_fields, context):
    field = condition.get("field")
    if field not in allowed_fields:
        raise ActionError(f"read_objects: '{field}' is not a filterable field")
    op = condition.get("op", "eq")
    lookup = _READ_OP_LOOKUPS.get(op)
    if lookup is None:
        raise ActionError(f"read_objects: unknown operator {op!r}")
    if op not in _allowed_ops(get_model_field(entry.model, field)):
        raise ActionError(
            f"read_objects: operator {op!r} is not valid for field {field!r}"
        )
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
        if op == "not_in":
            query = ~query
        return _guard_unrated(query, op, field, entry)
    query = Q(**{f"{field}__{lookup}": value})
    if op == "neq":
        query = ~query
    return _guard_unrated(query, op, field, entry)


def _read_group_to_q(group, entry, allowed_fields, context):
    operator = group.get("operator", "and")
    parts = [
        _read_condition_to_q(condition, entry, allowed_fields, context)
        for condition in group.get("conditions", [])
    ]
    parts += [
        _read_group_to_q(child, entry, allowed_fields, context)
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
    if operator == "not":
        combined = ~combined
        # The negation above just flipped every per-condition guard inside;
        # re-assert it for each sentinel field the subtree touches.
        for field in _sentinel_fields_in(group, entry.skip_unrated):
            combined &= Q(**{f"{field}__gte": 0})
    return combined


def _read_filters_to_q(tree, entry, allowed_fields, context):
    if tree in (None, {}):
        return Q()
    return _read_group_to_q(tree, entry, allowed_fields, context)


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
        fields = entry.readable_fields()
        context = _render_context(instance)
        query = _read_filters_to_q(config.get("filters"), entry, set(fields), context)

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
            entry.model.objects.filter(entry.base_filter or Q())
            .filter(folder_id__in=_read_scope_folder_ids(instance.folder))
            .filter(id__in=authz.viewable_ids(run_identity(instance), entry.model))
            .filter(query)
            .order_by(order_by, "id")  # id tie-break keeps pagination stable
        )
        # Computed callables dereference these per row otherwise.
        if entry.select_related:
            queryset = queryset.select_related(*entry.select_related)
        try:
            if config.get("mode", "list") == "first":
                obj = queryset.first()
                return {
                    "found": obj is not None,
                    "object": _serialize_read_row(obj, fields, entry.computed)
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
                    _serialize_read_row(obj, fields, entry.computed)
                    for obj in queryset[:limit]
                ],
            }
        except (ValidationError, ValueError, TypeError) as e:
            # Type mismatches only surface when the queryset evaluates
            # (e.g. "abc" compared against a date field).
            raise ActionError(f"read_objects: invalid filter value ({e})")
        except IndexError:
            # A library update can shrink a matrix while scenarios keep
            # their old level indices; the computed cell lookups then
            # index past the new lists.
            raise ActionError(
                "read_objects: a stored level no longer exists in the risk matrix"
            )


@dataclass(frozen=True)
class UpdateEntry:
    """One UPDATABLE_MODELS entry, drawn on one line: automation may record
    that time passed and may attach work, but may not render the judgment.

    ``fields`` is what a run may write; ``allowed_values`` narrows a field to
    the values that are facts rather than decisions. Plain columns only —
    anything whose transition lives outside save() stays off the registry.
    """

    model: type[Model]
    #: Never `name`: identity stays stable so create_object's upsert matches.
    fields: list[str]
    allowed_values: dict[str, frozenset] = dataclass_field(default_factory=dict)
    #: name -> (target model, frontend options endpoint)
    m2m_fields: dict[str, tuple[type[Model], str]] = dataclass_field(
        default_factory=dict
    )


_ACTOR = (Actor, "actors")
_LABELS = (FilteringLabel, "filtering-labels")
_CONTROLS = (AppliedControl, "applied-controls")
_EVIDENCES = (Evidence, "evidences")
_ASSETS = (Asset, "assets")
_EXCEPTIONS = (SecurityException, "security-exceptions")

# Lifecycle only; the verdict lives in the results, which are not writable.
_ASSESSMENT_STATUSES = frozenset(
    {"planned", "in_progress", "in_review", "done", "deprecated"}
)

UPDATABLE_MODELS: dict[str, UpdateEntry] = {
    "applied_control": UpdateEntry(
        model=AppliedControl,
        fields=[
            "status",
            "priority",
            "effort",
            "start_date",
            "eta",
            "expiry_date",
            "description",
            "ref_id",
            "link",
            "observation",
        ],
        m2m_fields={
            "owner": _ACTOR,
            "evidences": _EVIDENCES,
            "assets": _ASSETS,
            "filtering_labels": _LABELS,
        },
    ),
    "evidence": UpdateEntry(
        model=Evidence,
        fields=["status", "expiry_date", "description"],
        # A lapsed date and a missing file are facts; approving is not.
        allowed_values={"status": frozenset({"expired", "missing"})},
        m2m_fields={"owner": _ACTOR, "filtering_labels": _LABELS},
    ),
    "incident": UpdateEntry(
        model=Incident,
        # No status/severity: their TimelineEntry is written by the viewset.
        fields=["description", "ref_id", "link"],
        m2m_fields={
            "owners": _ACTOR,
            "assets": _ASSETS,
            "applied_controls": _CONTROLS,
            "filtering_labels": _LABELS,
        },
    ),
    "asset": UpdateEntry(
        model=Asset,
        fields=["description", "ref_id", "reference_link", "observation"],
        m2m_fields={
            "owner": _ACTOR,
            "security_exceptions": _EXCEPTIONS,
            "filtering_labels": _LABELS,
        },
    ),
    "vulnerability": UpdateEntry(
        model=Vulnerability,
        fields=["status", "severity", "description", "ref_id", "eta", "due_date"],
        m2m_fields={
            "applied_controls": _CONTROLS,
            "assets": _ASSETS,
            "security_exceptions": _EXCEPTIONS,
            "filtering_labels": _LABELS,
        },
    ),
    "security_exception": UpdateEntry(
        model=SecurityException,
        fields=[
            "status",
            "severity",
            "description",
            "ref_id",
            "expiration_date",
            "observation",
        ],
        # Granting or refusing an exception stays human; expiring it is a date.
        allowed_values={"status": frozenset({"expired", "deprecated"})},
        m2m_fields={"owners": _ACTOR, "evidences": _EVIDENCES},
    ),
    "entity": UpdateEntry(
        model=Entity,
        fields=["description", "ref_id", "mission", "reference_link"],
        m2m_fields={"filtering_labels": _LABELS},
    ),
    "findings_assessment": UpdateEntry(
        model=FindingsAssessment,
        fields=["status", "eta", "due_date", "description", "ref_id", "observation"],
        allowed_values={"status": _ASSESSMENT_STATUSES},
        m2m_fields={"evidences": _EVIDENCES, "filtering_labels": _LABELS},
    ),
    "finding": UpdateEntry(
        model=Finding,
        fields=[
            "status",
            "severity",
            "priority",
            "eta",
            "due_date",
            "description",
            "ref_id",
            "observation",
        ],
        # All but `dismissed`: that one is a person judging it harmless.
        allowed_values={
            "status": frozenset(
                {
                    "--",
                    "identified",
                    "confirmed",
                    "assigned",
                    "in_progress",
                    "mitigated",
                    "resolved",
                    "closed",
                    "deprecated",
                }
            )
        },
        m2m_fields={
            "owner": _ACTOR,
            "applied_controls": _CONTROLS,
            "evidences": _EVIDENCES,
            "filtering_labels": _LABELS,
        },
    ),
    "compliance_assessment": UpdateEntry(
        model=ComplianceAssessment,
        fields=["status", "eta", "due_date", "description", "ref_id", "observation"],
        allowed_values={"status": _ASSESSMENT_STATUSES},
        m2m_fields={"evidences": _EVIDENCES, "assets": _ASSETS},
    ),
    "risk_assessment": UpdateEntry(
        model=RiskAssessment,
        fields=["status", "eta", "due_date", "description", "ref_id", "observation"],
        allowed_values={"status": _ASSESSMENT_STATUSES},
    ),
    "entity_assessment": UpdateEntry(
        model=EntityAssessment,
        # No `conclusion`: that is the reviewer's verdict on the third party.
        fields=["status", "eta", "due_date", "description", "observation"],
        allowed_values={"status": _ASSESSMENT_STATUSES},
    ),
    "requirement_assessment": UpdateEntry(
        model=RequirementAssessment,
        # Progress and attached work only: a workflow that answers an audit
        # destroys its evidentiary value.
        fields=["status", "eta", "due_date", "observation"],
        m2m_fields={
            "applied_controls": _CONTROLS,
            "evidences": _EVIDENCES,
            "security_exceptions": _EXCEPTIONS,
        },
    ),
    "risk_scenario": UpdateEntry(
        model=RiskScenario,
        # No treatment, no ratings: attach the control, leave the call.
        fields=["description", "ref_id"],
        m2m_fields={
            "applied_controls": _CONTROLS,
            "owner": _ACTOR,
            "assets": _ASSETS,
        },
    ),
}

# RiskAcceptance and ValidationFlow are deliberately absent: their state moves
# through set_state() and the write serializer's transition table + FlowEvent,
# not through save(), so a column write here would skip revoked_at, the
# scenario treatments it reverts, and the flow's own history.

M2M_OPERATIONS = ("add", "remove", "set")


def _writable_values(entry, key):
    """The fence on a field: an explicit allowed_values, else the column's own
    choices. save() enforces max_length and clean() but never choices."""
    if key in entry.allowed_values:
        return entry.allowed_values[key]
    choices = getattr(get_model_field(entry.model, key), "choices", None)
    return frozenset(str(choice[0]) for choice in choices) if choices else None


def _as_id_list(value):
    """A JSON array or a comma-separated string of ids."""
    if isinstance(value, str):
        parsed = json_loads_or_none(value)
        value = (
            parsed
            if isinstance(parsed, list)
            else [item.strip() for item in value.split(",") if item.strip()]
        )
    if not isinstance(value, list):
        return None
    return [str(item).strip() for item in value if str(item).strip()]


@register
class UpdateObjectAction(BaseAction):
    action_type = "update_object"

    def execute(self, config, instance):
        entry = UPDATABLE_MODELS.get(config.get("model"))
        if entry is None:
            raise ActionError(f"update_object: unknown model '{config.get('model')}'")
        context = _render_context(instance)
        target_id = str(render(config.get("id", ""), context) or "").strip()
        if not target_id:
            raise ActionError("update_object: 'id' is required")

        from . import authz
        from .engine import run_identity

        # Subtree AND changeable by the run identity: the same two-part scope
        # as a read, with change instead of view.
        try:
            obj = (
                entry.model.objects.filter(
                    folder_id__in=_read_scope_folder_ids(instance.folder)
                )
                .filter(
                    id__in=authz.changeable_ids(run_identity(instance), entry.model)
                )
                .filter(id=target_id)
                .first()
            )
        except ValueError, ValidationError:
            obj = None
        if obj is None:
            raise ActionError(
                f"update_object: no {config.get('model')} '{target_id}' "
                "in this workflow's scope"
            )

        fields = render(config.get("fields") or {}, context)
        updated = {}
        for key, value in fields.items():
            if key not in entry.fields or value in ("", None):
                continue
            allowed = _writable_values(entry, key)
            if allowed is not None and str(value) not in allowed:
                raise FatalActionError(
                    f"update_object: a workflow may not set {config.get('model')}"
                    f".{key} to '{value}'"
                )
            setattr(obj, key, value)
            updated[key] = value
        if updated:
            try:
                obj.save()
            except ValidationError as e:
                raise ActionError(f"update_object: {'; '.join(e.messages)}")

        relations = {}
        for field_name, spec in (config.get("m2m") or {}).items():
            relations[field_name] = self._apply_m2m(
                entry, obj, field_name, spec or {}, context, instance
            )
        return {
            "object_id": str(obj.id),
            "str": str(obj),
            "updated_fields": sorted(updated),
            "relations": relations,
        }

    def _apply_m2m(self, entry, obj, field_name, spec, context, instance):
        relation = entry.m2m_fields.get(field_name)
        if relation is None:
            raise FatalActionError(
                f"update_object: '{field_name}' is not a writable relation"
            )
        target_model, _endpoint = relation
        operation = spec.get("op", "add")
        if operation not in M2M_OPERATIONS:
            raise FatalActionError(
                f"update_object: unknown relation operation '{operation}'"
            )
        ids = _as_id_list(render(spec.get("values"), context))
        if not ids:
            # `set` would clear the relation, add/remove would no-op.
            raise FatalActionError(f"update_object: '{field_name}' has no values")
        try:
            rows = list(target_model.objects.filter(id__in=ids))
        except ValueError, ValidationError:
            raise FatalActionError(f"update_object: '{field_name}' has invalid ids")
        if len(rows) != len(set(ids)):
            found = {str(row.id) for row in rows}
            missing = ", ".join(sorted(set(ids) - found))
            raise ActionError(f"update_object: {field_name} '{missing}' does not exist")
        # As with create_object's FKs: ancestors allowed, since actors and
        # labels live in root.
        allowed_folders = _accessible_folder_ids(instance.folder)
        for row in rows:
            folder_id = getattr(row, "folder_id", None)
            if folder_id is not None and folder_id not in allowed_folders:
                raise ActionError(
                    f"update_object: {field_name} is outside this workflow's scope"
                )
        manager = getattr(obj, field_name)
        if operation == "add":
            manager.add(*rows)
        elif operation == "remove":
            manager.remove(*rows)
        else:
            # `set` detaches whatever it does not list, which `remove` would
            # have refused when the target sits outside the scope.
            displaced = [
                row
                for row in manager.exclude(id__in=[row.id for row in rows])
                if getattr(row, "folder_id", None) is not None
                and row.folder_id not in allowed_folders
            ]
            if displaced:
                raise ActionError(
                    f"update_object: '{field_name}' would detach objects "
                    "outside this workflow's scope"
                )
            manager.set(rows)
        return {"op": operation, "count": len(rows)}


@register
class SendEmailAction(BaseAction):
    action_type = "send_email"

    def execute(self, config, instance):
        # Config errors fail the node here; delivery happens in a huey task
        # (DeferredSendEmailTask) so SMTP I/O never runs while the engine
        # transaction holds the instance-tree locks. The task resumes or
        # fails the node, so delivery errors still feed the retry policy.

        # No notifications_enable_mailing gate: that toggle governs the
        # digest notifications, not explicit user-authored send_email nodes.
        missing = get_missing_email_settings()
        if missing:
            raise FatalActionError(
                f"send_email: email is not configured (missing {', '.join(missing)})"
            )
        recipients = [
            email.strip()
            for email in render(
                config.get("recipients", ""), _render_context(instance)
            ).split(",")
            if email.strip()
        ]
        if not recipients:
            raise FatalActionError("send_email: no recipients configured")
        for email in recipients:
            # Validate the addr-spec only: display-name recipients
            # ('Jane Doe <jane@x>') are supported. Commas inside quoted
            # display names are not (the comma-split above).
            try:
                validate_email(parseaddr(email)[1])
            except ValidationError:
                raise FatalActionError(f"send_email: invalid recipient '{email}'")
        subject = render(config.get("subject", ""), _render_context(instance))
        body = render(config.get("body", ""), _render_context(instance))
        return DeferredSendEmailTask(subject=subject, body=body, recipients=recipients)


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
    if action_type == "update_object":
        entry = UPDATABLE_MODELS.get(action_config.get("model"))
        if entry is None:
            return []
        return [f"change_{entry.model._meta.model_name}"]
    if action_type == "read_objects":
        entry = READABLE_MODELS.get(action_config.get("model"))
        if entry is None:
            return []
        return [f"view_{entry.model._meta.model_name}"]
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
    fields = set(entry.readable_fields())

    from .events import validate_filter_tree, walk_conditions

    tree = config.get("filters")
    try:
        validate_filter_tree(tree)
    except ValueError as e:
        errors.append(("action_read_invalid_filters", f"Invalid filters: {e}"))
    else:
        for condition in walk_conditions(tree or {}):
            field = condition.get("field")
            op = condition.get("op", "eq")
            if field not in fields:
                errors.append(
                    (
                        "action_read_invalid_filters",
                        f"'{field}' is not a filterable field of "
                        f"'{config.get('model')}'",
                    )
                )
            elif op not in _READ_OP_LOOKUPS:
                errors.append(
                    ("action_read_invalid_filters", f"Unknown operator {op!r}")
                )
            elif op not in _allowed_ops(get_model_field(entry.model, field)):
                errors.append(
                    (
                        "action_read_invalid_filters",
                        f"Operator {op!r} is not valid for {field!r}",
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


def validate_set_variables_config(node):
    config = node.action_config or {}
    if config.get("type") != "set_variables":
        return []
    reserved = RESERVED_VARIABLE_KEYS & (config.get("variables") or {}).keys()
    return [
        ("action_set_variables_reserved", f"'{key}' is set by the engine on every run")
        for key in sorted(reserved)
    ]


def validate_date_offset_config(node):
    """Publish-time checks for date_offset nodes. Templated values are only
    knowable at runtime and pass here."""
    config = node.action_config or {}
    if config.get("type") != "date_offset":
        return []
    errors = []
    output = str(config.get("output") or "").strip()
    if output and (
        not VARIABLE_KEY_RE.match(output) or output in RESERVED_VARIABLE_KEYS
    ):
        errors.append(
            (
                "action_date_offset_bad_output",
                f"'{output}' is not a writable variable name",
            )
        )
    for key in ("days", "weeks"):
        value = config.get(key)
        if value in ("", None) or _is_templated(value):
            continue
        try:
            int(value)
        except ValueError, TypeError:
            errors.append(
                (
                    "action_date_offset_bad_offset",
                    f"'{key}' must be a whole number",
                )
            )
    base = config.get("base")
    if base not in ("", None) and not _is_templated(base):
        try:
            datetime.datetime.fromisoformat(str(base).strip())
        except ValueError, TypeError:
            errors.append(
                (
                    "action_date_offset_bad_base",
                    f"'{base}' is not an ISO date (YYYY-MM-DD)",
                )
            )
    return errors


def validate_update_config(node):
    """Publish-time checks for update_object nodes: what the whitelists would
    refuse mid-run is refused here."""
    config = node.action_config or {}
    if config.get("type") != "update_object":
        return []
    entry = UPDATABLE_MODELS.get(config.get("model"))
    if entry is None:
        return [
            (
                "action_update_unknown_model",
                f"Unknown updatable model '{config.get('model')}'",
            )
        ]
    errors = []
    if not str(config.get("id") or "").strip():
        errors.append(("action_update_missing_id", "Which object to update is not set"))
    fields = {
        key: value
        for key, value in (config.get("fields") or {}).items()
        if value not in ("", None)
    }
    if not fields and not (config.get("m2m") or {}):
        errors.append(("action_update_nothing_to_write", "This step writes nothing"))
    for key, value in fields.items():
        if key not in entry.fields:
            errors.append(
                (
                    "action_update_field_not_writable",
                    f"A workflow may not write '{key}' on '{config.get('model')}'",
                )
            )
            continue
        allowed = _writable_values(entry, key)
        if allowed is not None and not _is_templated(value):
            if str(value) not in allowed:
                errors.append(
                    (
                        "action_update_value_not_allowed",
                        f"'{key}' may only be set to {', '.join(sorted(allowed))}",
                    )
                )
    for field_name, spec in (config.get("m2m") or {}).items():
        if field_name not in entry.m2m_fields:
            errors.append(
                (
                    "action_update_relation_not_writable",
                    f"'{field_name}' is not a writable relation on "
                    f"'{config.get('model')}'",
                )
            )
            continue
        operation = (spec or {}).get("op", "add")
        if operation not in M2M_OPERATIONS:
            errors.append(
                (
                    "action_update_bad_relation_op",
                    f"Unknown relation operation '{operation}'",
                )
            )
        values = (spec or {}).get("values")
        if not _is_templated(values) and not _as_id_list(values):
            errors.append(
                (
                    "action_update_relation_no_values",
                    f"'{field_name}' has no ids to link",
                )
            )
    return errors


def _is_templated(value):
    return isinstance(value, str) and TEMPLATE_RE.search(value) is not None


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
