"""A computed metric started from instances, not from a definition.

The author picks metric instances and writes a formula over them; out come a
metric definition and an instance of it. The definition is an ordinary metric
formula: one 'one value' input per picked instance, on that instance's metric
and named after it, so it can be reused anywhere. The instance pins each input
to the instance the author picked, and lives in a domain holding them all.

Editing goes through the same path. What belongs to the instance (name,
domain, frequency, target, which instance of a metric a pick reads) changes
on it alone; what belongs to the definition (formula, inputs, result) changes
the definition in place when nothing else uses it, and otherwise moves this
metric to a definition of its own, leaving the others untouched.
"""

from __future__ import annotations

import math
import re
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
# A level's name and reference are what a formula returns: short texts.
MAX_LEVEL_TEXT = 100
# MetricDefinition.name's length.
MAX_NAME_LENGTH = 200
QUALITATIVE = MetricDefinition.Category.QUALITATIVE
QUANTITATIVE = MetricDefinition.Category.QUANTITATIVE
# A CEL string literal, single- or double-quoted, escapes allowed.
STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'')


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


def permitted(user, codenames, folder):
    """Whether the user holds every one of ``codenames`` in ``folder``."""
    from django.contrib.auth.models import Permission

    permissions = list(Permission.objects.filter(codename__in=codenames))
    return len(permissions) == len(codenames) and all(
        RoleAssignment.is_access_allowed(user=user, perm=permission, folder=folder)
        for permission in permissions
    )


def creatable_in(user, folder):
    """Whether the user may create both the definition and the instance in
    ``folder``."""
    return permitted(user, CREATE, folder)


def is_composable(instance):
    """Whether the modal can show the instance's formula: one made of picked
    instances, each input one value pinned to an instance. A combined input
    or a formula over objects is edited on its definition."""
    definition = instance.metric_definition
    if not definition.reads_metrics or definition.datasets:
        return False
    choices = instance.input_choices if isinstance(instance.input_choices, dict) else {}
    for spec in definition.inputs or []:
        if not isinstance(spec, dict) or spec.get("combine", "one") != "one":
            return False
        choice = choices.get(spec.get("key"))
        if not isinstance(choice, dict) or not choice.get("pick"):
            return False
    return True


def _clean_inputs(user, raw, folder, itself=None):
    """The picked instances as (key, instance) pairs, and the errors.
    ``itself`` is the instance being edited: it cannot read itself."""
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
        if itself is not None and picked.id == itself.id:
            errors.append(f"'{key}': a metric cannot read itself")
        elif picked.status == MetricInstance.Status.DEPRECATED:
            errors.append(f"'{key}': '{picked.name}' is deprecated")
        elif picked.folder_id not in subtree:
            errors.append(
                f"'{key}': '{picked.name}' is outside {folder.name}; "
                "choose a domain that holds every picked instance"
            )
        pairs.append((key, picked))
    return pairs, errors


def string_literals(expression):
    """The quoted texts of an expression, in order, each once. Inputs are
    numbers, so in a qualitative formula these are the levels it returns."""
    seen = []
    for match in STRING_LITERAL.finditer(expression or ""):
        text = match.group(1) if match.group(1) is not None else match.group(2)
        if text not in seen:
            seen.append(text)
    return seen


def _clean_levels(raw):
    """A qualitative result's levels as [{ref_id, name}], in order, and the
    errors. Both names and ref_ids are what an expression may return, so
    neither may repeat."""
    if not isinstance(raw, list) or len(raw) < 2:
        return [], ["A level metric needs at least two levels"]
    levels, errors, seen = [], [], set()
    for item in raw:
        ref_id = item.get("ref_id") if isinstance(item, dict) else None
        name = item.get("name") if isinstance(item, dict) else None
        ref_id = ref_id.strip() if isinstance(ref_id, str) else ""
        name = name.strip() if isinstance(name, str) else ""
        if not ref_id or not name:
            errors.append("Each level needs a reference and a name")
            continue
        if len(ref_id) > MAX_LEVEL_TEXT or len(name) > MAX_LEVEL_TEXT:
            errors.append(
                f"A level's reference and name are at most {MAX_LEVEL_TEXT} characters"
            )
            continue
        clashes = {ref_id.lower(), name.lower()} & seen
        if clashes:
            errors.append(f"'{sorted(clashes)[0]}' names two levels")
            continue
        seen |= {ref_id.lower(), name.lower()}
        levels.append({"ref_id": ref_id, "name": name})
    return levels, errors


def _same_formula(definition, specs, expression, shape):
    def normalized(inputs):
        return sorted(
            (spec.get("key"), spec.get("definition"), spec.get("combine", "one"))
            for spec in inputs or []
            if isinstance(spec, dict)
        )

    def levels(choices):
        return [
            (choice.get("ref_id"), choice.get("name"))
            for choice in choices or []
            if isinstance(choice, dict)
        ]

    unit = shape["unit"]
    return (
        definition.expression.strip() == expression.strip()
        and normalized(definition.inputs) == normalized(specs)
        and definition.category == shape["category"]
        and levels(definition.choices_definition) == levels(shape["levels"])
        and definition.unit_id == (unit.id if unit else None)
        and definition.higher_is_better == shape["higher_is_better"]
    )


def _existing_definition(user, folder, specs, expression, shape):
    """A definition the user can read, in the domain or above it, computing
    exactly this formula into the same result: the same metric computed in
    another domain reuses it instead of copying it."""
    candidates = MetricDefinition.objects.filter(
        folder__in=folder.get_parent_folders(include_self=True),
        category=shape["category"],
        expression=expression,
    ).exclude(inputs__isnull=True)
    for definition in candidates.order_by("created_at", "id"):
        if _same_formula(
            definition, specs, expression, shape
        ) and RoleAssignment.is_object_readable(user, MetricDefinition, definition.id):
            return definition
    return None


def _definition_name(name, folder):
    """The metric's name, made unique among the domain's definitions."""
    taken = MetricDefinition.objects.filter(folder=folder)
    candidate, n = name, 2
    while taken.filter(name__iexact=candidate).exists():
        suffix = f" ({n})"
        # Room for the suffix: a name at the limit stays valid.
        candidate = name[: MAX_NAME_LENGTH - len(suffix)] + suffix
        n += 1
    return candidate


def compose(user, data, instance=None):
    """Create a computed metric from ``data``, or edit ``instance``, one the
    modal can show (is_composable). Returns (instance, outcome): "created",
    or "reused" when an identical definition already existed; when editing,
    "unchanged" (the definition stays), "updated" (edited in place) or
    "forked" (this metric moved to a definition of its own, new or
    identical). Raises CompositionError with the errors by field, or
    PermissionError when the user may not write where it would."""
    data = data if isinstance(data, dict) else {}
    errors = {}

    folder = Folder.objects.filter(id=_as_uuid(data.get("folder"))).first()
    if folder is None:
        raise CompositionError({"folder": ["Choose a domain"]})
    if instance is None:
        if not creatable_in(user, folder):
            raise PermissionError
    elif not (
        permitted(user, ["change_metricinstance"], instance.folder)
        and permitted(user, ["change_metricinstance"], folder)
    ):
        raise PermissionError
    current = instance.metric_definition if instance is not None else None

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors["name"] = ["Name the metric"]
    pairs, input_errors = _clean_inputs(user, data.get("inputs"), folder, instance)
    specs = [
        {"key": key, "definition": str(picked.metric_definition_id), "combine": "one"}
        for key, picked in pairs
    ]
    if specs or not input_errors:
        # With nothing usable picked, the pick errors already say why.
        input_errors += [message for _code, message in validate_inputs(specs, current)]
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

    # The result: a number, or one of an ordered list of levels.
    category = data.get("category") or QUANTITATIVE
    levels = []
    if category not in MetricDefinition.Category.values:
        errors["category"] = ["Unknown result type"]
    elif category == QUALITATIVE:
        levels, level_errors = _clean_levels(data.get("choices_definition"))
        if level_errors:
            errors["choices_definition"] = level_errors
        elif isinstance(expression, str) and "expression" not in errors:
            known = {text.lower() for level in levels for text in level.values()}
            unknown = [
                text
                for text in string_literals(expression)
                if text.lower() not in known
            ]
            if unknown:
                errors["expression"] = [
                    f"'{text}' is not one of the levels" for text in unknown
                ]

    frequency = data.get("collection_frequency") or (
        instance.collection_frequency
        if instance is not None
        else least_frequent([picked.collection_frequency for _key, picked in pairs])
    )
    if frequency not in MetricInstance.Frequency.values:
        errors["collection_frequency"] = ["Unknown frequency"]
    unit = None
    if data.get("unit") and category != QUALITATIVE:
        unit = Terminology.objects.filter(
            id=_as_uuid(data.get("unit")),
            field_path=Terminology.FieldPath.METRIC_UNIT,
            is_visible=True,
        ).first()
        if unit is None:
            errors["unit"] = ["Unknown unit"]
    target_value = data.get("target_value")
    if target_value in ("", None) or category == QUALITATIVE:
        target_value = None
    else:
        try:
            target_value = float(target_value)
        except ValueError, TypeError:
            target_value = math.nan
        # inf and nan cannot be stored as JSON: refused, not saved.
        if not math.isfinite(target_value):
            errors["target_value"] = ["The target must be a number"]
    if errors:
        raise CompositionError(errors)

    name = name.strip()
    shape = {
        "category": category,
        "levels": levels,
        "unit": unit,
        "higher_is_better": data.get("higher_is_better", True) is not False,
    }
    picks = {key: {"pick": str(picked.id)} for key, picked in pairs}
    try:
        with transaction.atomic():
            if instance is None:
                definition, outcome = _definition_for(
                    user, folder, name, specs, expression, shape
                )
                instance = MetricInstance.objects.create(
                    name=name,
                    description=data.get("description") or "",
                    folder=folder,
                    metric_definition=definition,
                    status=MetricInstance.Status.ACTIVE,
                    collection_frequency=frequency,
                    target_value=target_value,
                    # Pinned, every one: the author picked these instances, and
                    # a second instance of a metric appearing later in the
                    # domain must not change what this one reads.
                    input_choices=picks,
                )
            else:
                definition, outcome = _definition_after_edit(
                    user, instance, folder, name, specs, expression, shape
                )
                moved = instance.folder_id != folder.id
                instance.name = name
                if "description" in data:
                    instance.description = data.get("description") or ""
                instance.folder = folder
                instance.metric_definition = definition
                instance.collection_frequency = frequency
                instance.target_value = target_value
                instance.input_choices = picks
                instance.save()
                if moved:
                    instance.samples.update(folder=folder)
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
    return instance, outcome


def _definition_for(user, folder, name, specs, expression, shape):
    """An identical definition the user can read, or a new one in
    ``folder``: (definition, "reused" | "created")."""
    definition = _existing_definition(user, folder, specs, expression, shape)
    if definition is not None:
        return definition, "reused"
    definition = MetricDefinition.objects.create(
        name=_definition_name(name, folder),
        folder=folder,
        category=shape["category"],
        choices_definition=shape["levels"] or None,
        unit=shape["unit"],
        higher_is_better=shape["higher_is_better"],
        inputs=specs,
        expression=expression,
    )
    return definition, "created"


def _definition_after_edit(user, instance, folder, name, specs, expression, shape):
    """The definition an edited metric computes with. Unchanged when the
    edit only touched the instance; edited in place when nothing else uses
    it; otherwise this metric moves to a definition of its own, and the
    other metrics using the old one are left exactly as they were. A shared
    definition is never edited from one of its metrics: its other metrics'
    picks are named after its inputs, and their stored history after its
    result."""
    from .series import dependents_of

    current = instance.metric_definition
    if _same_formula(current, specs, expression, shape):
        return current, "unchanged"
    others = current.metricinstance_set.exclude(id=instance.id).exists()
    if not others and permitted(user, ["change_metricdefinition"], current.folder):
        # Formulas reading this metric read numbers: a level result would
        # skip every one of their periods and drop their history.
        if shape["category"] != current.category and dependents_of(current):
            raise CompositionError(
                {
                    "category": [
                        "Other formulas read this metric as a number: its result "
                        "type cannot change while they do"
                    ]
                }
            )
        current.category = shape["category"]
        current.choices_definition = shape["levels"] or None
        current.unit = shape["unit"]
        current.higher_is_better = shape["higher_is_better"]
        current.inputs = specs
        current.expression = expression
        current.save()
        return current, "updated"
    # Moving to another definition: a formula that picked this metric reads
    # it as an instance of the old definition, and would lose it.
    readers = _formulas_picking(instance)
    if readers:
        raise CompositionError(
            {
                "form": [
                    "Other metrics read this one ("
                    + ", ".join(sorted(reader.name for reader in readers)[:5])
                    + "); its definition is shared, so its formula can only "
                    "change once they no longer read it"
                ]
            }
        )
    if not permitted(user, ["add_metricdefinition"], folder):
        raise PermissionError
    definition, _outcome = _definition_for(user, folder, name, specs, expression, shape)
    return definition, "forked"


def _formulas_picking(instance):
    """Metric instances whose formula pins ``instance`` as an input."""
    from .series import dependents_of

    readers = MetricInstance.objects.filter(
        metric_definition__in=dependents_of(instance.metric_definition)
    ).exclude(id=instance.id)
    picked = str(instance.id)
    return [
        reader
        for reader in readers
        if isinstance(reader.input_choices, dict)
        and any(
            isinstance(choice, dict) and str(choice.get("pick")) == picked
            for choice in reader.input_choices.values()
        )
    ]
