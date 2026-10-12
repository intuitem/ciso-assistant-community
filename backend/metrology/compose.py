"""A computed metric started from instances, not from a definition.

The author picks metric instances and writes a formula over them; out come a
metric definition and an instance of it. The definition is an ordinary metric
formula: one 'one value' input per picked instance, on that instance's metric
and named after it, so it can be reused anywhere. The instance pins each input
to the instance the author picked, and lives in a domain holding them all.
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Terminology
from iam.models import Folder, RoleAssignment

from .models import MetricDefinition, MetricInstance
from .series import MAX_INPUTS, validate_inputs, validate_series_expression

# From the most to the least frequent: a computed metric defaults to the
# frequency of its least frequent input, so no period repeats a value.
FREQUENCY_ORDER = [value for value, _label in MetricInstance.Frequency.choices]
CREATE = ["add_metricinstance", "add_metricdefinition"]


class CompositionError(Exception):
    """What the author must fix, by field, as the modal shows it."""

    def __init__(self, errors):
        super().__init__(errors)
        self.errors = errors


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except ValueError, TypeError, AttributeError:
        return None


def common_domain(folders):
    """The lowest folder holding every one of ``folders`` in its subtree:
    the lowest a computed metric reading them may live, since an input never
    reads outside the instance's tree."""
    paths = [folder.get_folder_full_path(include_root=True) for folder in folders]
    if not paths:
        return None
    common = None
    for level in zip(*paths):
        if any(folder.id != level[0].id for folder in level):
            break
        common = level[0]
    return common


def least_frequent(frequencies):
    known = [f for f in frequencies if f in FREQUENCY_ORDER]
    if not known:
        return MetricInstance.Frequency.MONTHLY
    return max(known, key=FREQUENCY_ORDER.index)


def readable_instances(user, ids):
    """The instances among ``ids`` the user may read. One that does not
    exist and one the user may not see look alike to the caller."""
    found = MetricInstance.objects.filter(id__in=ids).select_related(
        "folder", "metric_definition"
    )
    return {
        instance.id: instance
        for instance in found
        if RoleAssignment.is_object_readable(user, MetricInstance, instance.id)
    }


def unreadable_picks(user, choices, previous=None):
    """Picks in ``choices`` naming an instance the user may not read: a
    formula would show them its values. Picks already in ``previous`` were
    someone else's to make and stay."""

    def picks(value):
        if not isinstance(value, dict):
            return set()
        return {
            str(choice.get("pick"))
            for choice in value.values()
            if isinstance(choice, dict) and choice.get("pick")
        }

    new = sorted(picks(choices) - picks(previous))
    ids = [_as_uuid(pick) for pick in new]
    readable = readable_instances(user, [i for i in ids if i is not None])
    return [pick for pick, i in zip(new, ids) if i not in readable]


def creatable_in(user, folder):
    """Whether the user may create both the definition and the instance in
    ``folder``."""
    from django.contrib.auth.models import Permission

    permissions = list(Permission.objects.filter(codename__in=CREATE))
    return len(permissions) == len(CREATE) and all(
        RoleAssignment.is_access_allowed(user=user, perm=permission, folder=folder)
        for permission in permissions
    )


def _clean_inputs(user, raw, folder):
    """The picked instances as (key, instance) pairs, and the errors."""
    if not isinstance(raw, list) or not raw:
        return [], ["Pick at least one metric instance"]
    if len(raw) > MAX_INPUTS:
        return [], [f"At most {MAX_INPUTS} metric instances"]
    ids = [
        _as_uuid(item.get("instance")) if isinstance(item, dict) else None
        for item in raw
    ]
    readable = readable_instances(user, [i for i in ids if i is not None])
    subtree = set(
        folder.get_sub_folders(include_self=True).values_list("id", flat=True)
    )
    pairs, errors, seen = [], [], set()
    for item, instance_id in zip(raw, ids):
        key = item.get("key") if isinstance(item, dict) else None
        picked = readable.get(instance_id)
        if picked is None:
            errors.append(f"'{key}': no such metric instance")
            continue
        if instance_id in seen:
            errors.append(f"'{picked.name}' is picked twice")
            continue
        seen.add(instance_id)
        if picked.status == MetricInstance.Status.DEPRECATED:
            errors.append(f"'{key}': '{picked.name}' is deprecated")
        elif picked.folder_id not in subtree:
            errors.append(
                f"'{key}': '{picked.name}' is outside {folder.name}; "
                "choose a domain that holds every picked instance"
            )
        pairs.append((key, picked))
    return pairs, errors


def _same_formula(definition, specs, expression, unit, higher_is_better):
    def normalized(inputs):
        return sorted(
            (spec.get("key"), spec.get("definition"), spec.get("combine", "one"))
            for spec in inputs or []
            if isinstance(spec, dict)
        )

    return (
        definition.expression.strip() == expression.strip()
        and normalized(definition.inputs) == normalized(specs)
        and definition.unit_id == (unit.id if unit else None)
        and definition.higher_is_better == higher_is_better
    )


def _existing_definition(user, folder, specs, expression, unit, higher_is_better):
    """A definition the user can read, in the domain or above it, computing
    exactly this formula: the same metric computed in another domain reuses
    it instead of copying it."""
    candidates = MetricDefinition.objects.filter(
        folder__in=folder.get_parent_folders(include_self=True),
        category=MetricDefinition.Category.QUANTITATIVE,
        expression=expression,
    ).exclude(inputs__isnull=True)
    for definition in candidates.order_by("created_at", "id"):
        if _same_formula(
            definition, specs, expression, unit, higher_is_better
        ) and RoleAssignment.is_object_readable(user, MetricDefinition, definition.id):
            return definition
    return None


def _definition_name(name, folder):
    """The metric's name, made unique among the domain's definitions."""
    taken = MetricDefinition.objects.filter(folder=folder)
    candidate, n = name, 2
    while taken.filter(name__iexact=candidate).exists():
        candidate = f"{name} ({n})"
        n += 1
    return candidate


def compose(user, data):
    """Create a computed metric from ``data``: (instance, reused), where
    ``reused`` tells whether an identical definition already existed. Raises
    CompositionError with the errors by field, or PermissionError when the
    user may not create metrics in the domain."""
    data = data if isinstance(data, dict) else {}
    errors = {}

    folder = Folder.objects.filter(id=_as_uuid(data.get("folder"))).first()
    if folder is None:
        raise CompositionError({"folder": ["Choose a domain"]})
    if not creatable_in(user, folder):
        raise PermissionError

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors["name"] = ["Name the metric"]
    pairs, input_errors = _clean_inputs(user, data.get("inputs"), folder)
    specs = [
        {"key": key, "definition": str(picked.metric_definition_id), "combine": "one"}
        for key, picked in pairs
    ]
    if specs or not input_errors:
        # With nothing usable picked, the pick errors already say why.
        input_errors += [message for _code, message in validate_inputs(specs)]
    if input_errors:
        errors["inputs"] = input_errors
    expression = data.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        errors["expression"] = ["Write the formula"]
    else:
        expression = expression.strip()
        keys = {key for key, _picked in pairs if isinstance(key, str)}
        expression_errors = validate_series_expression(expression, keys)
        if expression_errors:
            errors["expression"] = [message for _code, message in expression_errors]

    frequency = data.get("collection_frequency") or least_frequent(
        [picked.collection_frequency for _key, picked in pairs]
    )
    if frequency not in MetricInstance.Frequency.values:
        errors["collection_frequency"] = ["Unknown frequency"]
    unit = None
    if data.get("unit"):
        unit = Terminology.objects.filter(
            id=_as_uuid(data.get("unit")),
            field_path=Terminology.FieldPath.METRIC_UNIT,
            is_visible=True,
        ).first()
        if unit is None:
            errors["unit"] = ["Unknown unit"]
    target_value = data.get("target_value")
    if target_value in ("", None):
        target_value = None
    else:
        try:
            target_value = float(target_value)
        except ValueError, TypeError:
            errors["target_value"] = ["The target must be a number"]
    if errors:
        raise CompositionError(errors)

    name = name.strip()
    higher_is_better = data.get("higher_is_better", True) is not False
    try:
        with transaction.atomic():
            definition = _existing_definition(
                user, folder, specs, expression, unit, higher_is_better
            )
            reused = definition is not None
            if definition is None:
                definition = MetricDefinition.objects.create(
                    name=_definition_name(name, folder),
                    folder=folder,
                    category=MetricDefinition.Category.QUANTITATIVE,
                    unit=unit,
                    higher_is_better=higher_is_better,
                    inputs=specs,
                    expression=expression,
                )
            instance = MetricInstance.objects.create(
                name=name,
                description=data.get("description") or "",
                folder=folder,
                metric_definition=definition,
                status=MetricInstance.Status.ACTIVE,
                collection_frequency=frequency,
                target_value=target_value,
                # Pinned, every one: the author picked these instances, and a
                # second instance of a metric appearing later in the domain
                # must not change what this one reads.
                input_choices={key: {"pick": str(picked.id)} for key, picked in pairs},
            )
    except ValidationError as e:
        # A name another instance of the domain already has.
        raise CompositionError(
            {
                field: [str(message) for message in messages]
                for field, messages in e.message_dict.items()
            }
        )

    instance_id = str(instance.id)

    def compute():
        from .tasks import compute_derived_metric_task

        compute_derived_metric_task(instance_id, full=True)

    transaction.on_commit(compute)
    return instance, reused
