"""Metric formulas: a metric computed from other metrics, period by period.

A definition's ``inputs`` name other metric definitions. On an instance, each
input resolves to that definition's instances in the instance's folder
subtree, taken as one value or combined (sum, avg, min, max, count). The
output's collection frequency cuts time into calendar periods (UTC); each
input contributes its last sample up to the end of a period, unless that
sample is older than the input's staleness threshold. The expression runs
once per period and the result is stored as one sample per instance and
period, replaced when the period is recomputed (see
documentation/architecture/decisions/derived-metrics-from-other-metrics.md).
"""

from __future__ import annotations

import datetime
import uuid
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from core.expressions import ExpressionError, compile_expression, evaluate
from core.expressions import referenced_paths
from core.reads import subtree_folder_ids

from .derived import (
    DATASET_NAME_RE,
    KEEP_EVERY_SAMPLE_DAYS,
    LOCK_TTL_SECONDS,
    DerivedMetricError,
    _lock_key,
    delete_samples_silently,
    is_due,
    shape_value,
)

UTC = datetime.timezone.utc
COMBINES = ("one", "sum", "avg", "min", "max", "count")
# Names the expression may read besides the inputs.
SERIES_ROOTS = frozenset({"previous", "now", "today"})
MAX_INPUTS = 20
# Backfill and recompute never reach further back than this many periods.
MAX_PERIODS = 1000
SUB_DAILY = ("realtime", "hourly")
# recompute_from meaning "the whole series": a formula or an input's set of
# instances changed, so every period may differ.
FULL = datetime.datetime(1970, 1, 1, tzinfo=UTC)


# ---------- calendar periods ----------


def _add_months(moment, months):
    years, month = divmod(moment.month - 1 + months, 12)
    return moment.replace(year=moment.year + years, month=month + 1)


def period_start(moment, frequency):
    """The start of the calendar period holding ``moment``: quarter hour,
    hour, day, ISO week (Monday), month, quarter or year, in UTC. No
    frequency means daily."""
    moment = moment.astimezone(UTC)
    if frequency == "realtime":
        return moment.replace(
            minute=moment.minute - moment.minute % 15, second=0, microsecond=0
        )
    if frequency == "hourly":
        return moment.replace(minute=0, second=0, microsecond=0)
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if frequency == "weekly":
        return day - datetime.timedelta(days=day.weekday())
    if frequency == "monthly":
        return day.replace(day=1)
    if frequency == "quarterly":
        return day.replace(day=1, month=(day.month - 1) // 3 * 3 + 1)
    if frequency == "yearly":
        return day.replace(day=1, month=1)
    return day


_STEPS = {
    "realtime": datetime.timedelta(minutes=15),
    "hourly": datetime.timedelta(hours=1),
    "weekly": datetime.timedelta(days=7),
}
_MONTH_STEPS = {"monthly": 1, "quarterly": 3, "yearly": 12}


def shift_period(start, frequency, count=1):
    """The period ``count`` periods after (or before) the one at ``start``."""
    if frequency in _MONTH_STEPS:
        return _add_months(start, _MONTH_STEPS[frequency] * count)
    return start + _STEPS.get(frequency, datetime.timedelta(days=1)) * count


# ---------- inputs ----------


def resolve_definition(ref):
    """An input's ``definition``: a definition id (made in the app) or a URN
    (shipped in a library, where ids are not known yet)."""
    from .models import MetricDefinition

    if not isinstance(ref, str) or not ref:
        return None
    try:
        return MetricDefinition.objects.filter(id=uuid.UUID(ref)).first()
    except ValueError:
        return MetricDefinition.objects.filter(urn=ref.lower()).first()


def refers_to(ref, definition):
    """Whether an input's ``definition`` value names ``definition``."""
    if not isinstance(ref, str) or not ref:
        return False
    return ref == str(definition.id) or (
        bool(definition.urn) and ref.lower() == definition.urn.lower()
    )


def _reaches(start, goal_id, seen=None):
    """Whether ``goal_id`` is among ``start``'s inputs, at any depth."""
    seen = seen if seen is not None else set()
    if start.id in seen:
        return False
    seen.add(start.id)
    for spec in start.inputs or []:
        if not isinstance(spec, dict):
            continue
        target = resolve_definition(spec.get("definition"))
        if target is None:
            continue
        if target.id == goal_id or _reaches(target, goal_id, seen):
            return True
    return False


def validate_inputs(inputs, definition=None):
    """Save-time checks of a metric formula's inputs, as (code, message)
    tuples. ``definition`` is the definition being saved, when it exists:
    an input may not read it, directly or through other formulas."""
    from .models import MetricDefinition

    if not isinstance(inputs, list) or not inputs:
        return [("derived_inputs_missing", "A metric formula needs at least one input")]
    if len(inputs) > MAX_INPUTS:
        return [("derived_inputs_too_many", f"At most {MAX_INPUTS} inputs per metric")]
    errors = []
    keys = set()
    for spec in inputs:
        if not isinstance(spec, dict):
            errors.append(("derived_input_invalid", "An input must be a mapping"))
            continue
        key = spec.get("key")
        if (
            not isinstance(key, str)
            or not DATASET_NAME_RE.match(key)
            or key in SERIES_ROOTS
            or key == "metrics"
        ):
            errors.append(
                (
                    "derived_input_key_invalid",
                    (
                        f"'{key}' is not a valid input name (letters, digits, _; "
                        "not previous, now, today or metrics)"
                    ),
                )
            )
            continue
        if key in keys:
            errors.append(("derived_input_key_invalid", f"'{key}' is used twice"))
            continue
        keys.add(key)
        if spec.get("combine", "one") not in COMBINES:
            errors.append(
                (
                    "derived_input_invalid",
                    f"input '{key}': combine must be one of {', '.join(COMBINES)}",
                )
            )
        target = resolve_definition(spec.get("definition"))
        if target is None:
            errors.append(
                ("derived_input_invalid", f"input '{key}': no such metric definition")
            )
        elif target.category != MetricDefinition.Category.QUANTITATIVE:
            errors.append(
                (
                    "derived_input_invalid",
                    f"input '{key}': only quantitative metrics can be inputs",
                )
            )
        elif definition is not None and (
            target.id == definition.id or _reaches(target, definition.id)
        ):
            errors.append(
                (
                    "derived_input_cycle",
                    f"input '{key}': '{target.name}' depends on this metric",
                )
            )
    return errors


def validate_series_expression(expression, keys):
    """The expression of a metric formula reads its inputs, ``previous``,
    ``now`` and ``today``; ``metrics`` would read latest values only."""
    try:
        compile_expression(expression)
    except ExpressionError as e:
        return [("derived_expression_invalid", e.message)]
    errors = []
    roots = {path.split(".")[0] for path in referenced_paths(expression)}
    if "metrics" in roots:
        errors.append(
            (
                "derived_expression_unknown_name",
                "'metrics' reads latest values only; add the metric as an input",
            )
        )
    for root in sorted(roots - keys - SERIES_ROOTS - {"metrics"}):
        errors.append(
            (
                "derived_expression_unknown_name",
                f"'{root}' is not an input of this metric",
            )
        )
    return errors


@dataclass
class ResolvedInput:
    key: str
    combine: str
    definition: object
    instances: list


def input_candidates(target, folder):
    """The instances of ``target`` an input may read from ``folder``: its
    subtree, deprecated ones left out (a replaced instance must not count
    alongside its replacement)."""
    from .models import MetricInstance

    return list(
        MetricInstance.objects.filter(
            metric_definition=target, folder_id__in=subtree_folder_ids(folder)
        )
        .exclude(status=MetricInstance.Status.DEPRECATED)
        .select_related("folder")
        .order_by("name", "id")
    )


def effective_combine(spec, choice):
    """How an input's instances combine on one instance: the instance's own
    choice when it made one, else the definition's."""
    return (choice or {}).get("combine") or spec.get("combine") or "one"


def validate_input_choices(definition, folder, choices):
    """Save-time checks of an instance's ``input_choices``, as messages. An
    instance may change how an input combines (the definition only sets the
    default), pick the instance a one-value input reads, or exclude
    instances from a combined one. A pick names a current instance of the
    input's metric in the instance's domain tree; an exclusion names any
    instance of it there. Nothing ever reaches outside the tree: the same
    boundary as the formula itself."""
    from .models import MetricInstance

    if choices in (None, {}):
        return []
    if not isinstance(choices, dict):
        return ["Input choices must be a mapping of input names"]
    if definition is None or not definition.reads_metrics:
        return ["Only a metric computed from other metrics has input choices"]
    specs = {
        spec.get("key"): spec
        for spec in definition.inputs or []
        if isinstance(spec, dict)
    }
    errors = []
    for key, choice in choices.items():
        spec = specs.get(key)
        if spec is None:
            errors.append(f"'{key}' is not an input of this metric")
            continue
        target = resolve_definition(spec.get("definition"))
        if target is None or not isinstance(choice, dict):
            errors.append(f"input '{key}': invalid choice")
            continue
        if "combine" in choice and choice["combine"] not in COMBINES:
            errors.append(
                f"input '{key}': combine must be one of {', '.join(COMBINES)}"
            )
            continue
        combine = effective_combine(spec, choice)
        allowed = {"combine", "pick" if combine == "one" else "exclude"}
        if not set(choice) <= allowed:
            errors.append(
                f"input '{key}': a 'one value' input takes a pick, not exclusions"
                if combine == "one"
                else f"input '{key}': a combined input takes exclusions, not a pick"
            )
            continue
        in_tree = MetricInstance.objects.filter(
            metric_definition=target, folder_id__in=subtree_folder_ids(folder)
        )
        if combine == "one":
            if "pick" not in choice:
                continue
            if (
                not in_tree.exclude(status=MetricInstance.Status.DEPRECATED)
                .filter(id=_as_uuid(choice["pick"]))
                .exists()
            ):
                errors.append(
                    f"input '{key}': pick an instance of '{target.name}' in this "
                    "domain that is not deprecated"
                )
            continue
        if "exclude" not in choice:
            continue
        excluded = choice["exclude"]
        ids = [_as_uuid(i) for i in excluded] if isinstance(excluded, list) else None
        if (
            ids is None
            or None in ids
            or in_tree.filter(id__in=ids).count() != len(set(ids))
        ):
            errors.append(
                f"input '{key}': exclude only instances of '{target.name}' in this domain"
            )
    return errors


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except ValueError, TypeError, AttributeError:
        return None


def _choice(choices, key):
    choice = (choices or {}).get(key) if isinstance(choices, dict) else None
    return choice if isinstance(choice, dict) else {}


def resolve_inputs(inputs, folder, choices=None):
    """Each input's instances in ``folder``'s subtree, honouring the
    instance's ``choices``: the picked instance of a 'one value' input, the
    instances a combined input excludes. 'one' needs exactly one instance,
    picked or alone; a pick that no longer matches is an error, never a
    fallback. An error names the input so the author can act on it."""
    resolved = []
    for spec in inputs:
        key = spec.get("key")
        target = resolve_definition(spec.get("definition"))
        if target is None:
            raise DerivedMetricError(
                f"input '{key}': the metric it reads no longer exists"
            )
        instances = input_candidates(target, folder)
        choice = _choice(choices, key)
        combine = effective_combine(spec, choice)
        if combine == "one":
            picked = choice.get("pick")
            if picked:
                instances = [i for i in instances if str(i.id) == str(picked)]
                if not instances:
                    raise DerivedMetricError(
                        f"input '{key}': the instance picked for it is no longer "
                        "in this domain, or is deprecated; pick another one"
                    )
            elif len(instances) != 1:
                raise DerivedMetricError(
                    f"input '{key}': {len(instances)} instances of '{target.name}' "
                    "in this domain; pick the one to read in the instance's inputs"
                    if instances
                    else f"input '{key}': no instance of '{target.name}' in this domain"
                )
        else:
            # An exclusion of an instance that has since gone excludes nothing.
            excluded = {str(i) for i in choice.get("exclude") or []}
            instances = [i for i in instances if str(i.id) not in excluded]
        resolved.append(ResolvedInput(key, combine, target, instances))
    return resolved


# ---------- evaluation ----------


def _number(value):
    """A quantitative sample's value, or None: the model's own decoder, on
    the raw column value ``values_list`` hands out."""
    from .models import quantitative_result

    return quantitative_result(value)


class _AsOf:
    """An instance's samples, read in time order: the last value at or
    before a moment, unless older than ``max_age``."""

    def __init__(self, points, max_age):
        self.points = points
        self.max_age = max_age
        self.index = -1

    def at(self, moment):
        while (
            self.index + 1 < len(self.points)
            and self.points[self.index + 1][0] <= moment
        ):
            self.index += 1
        if self.index < 0:
            return None
        stamp, value = self.points[self.index]
        if self.max_age is not None and moment - stamp > self.max_age:
            return None
        return value


def _combine(combine, values):
    present = [value for value in values if value is not None]
    if combine == "one":
        return values[0] if values else None
    if combine == "count":
        return len(present)
    if not present:
        return None
    if combine == "sum":
        return sum(present)
    if combine == "avg":
        return sum(present) / len(present)
    if combine == "min":
        return min(present)
    return max(present)


@dataclass
class PeriodResult:
    start: datetime.datetime
    timestamp: datetime.datetime
    value: object = None
    envelope: dict | None = None
    #: The expression could not run because an input had no value.
    skipped: bool = False
    inputs: dict = dataclass_field(default_factory=dict)


@dataclass
class SeriesEvaluation:
    value: object = None
    periods: list = dataclass_field(default_factory=list)
    resolved: list = dataclass_field(default_factory=list)
    #: Where the recomputed range begins: periods from here on that produced
    #: nothing lose their stored sample.
    start: datetime.datetime | None = None


def _label(start, frequency):
    return start.isoformat() if frequency in SUB_DAILY else start.date().isoformat()


def evaluate_series(
    inputs,
    expression,
    folder,
    frequency,
    shape,
    *,
    since=None,
    previous=None,
    choices=None,
):
    """Every period from the first input sample (or ``since``) to now, capped
    at MAX_PERIODS, and for sub-daily periods at the window downsampling
    keeps. ``shape`` carries the output's category and levels. ``previous``
    is the value of the period before the first one computed. Writes
    nothing. Raises DerivedMetricError naming the input or the period."""
    from .models import STALENESS_THRESHOLDS

    now = timezone.now()
    evaluation = SeriesEvaluation(resolved=resolve_inputs(inputs, folder, choices))
    instance_ids = [
        instance.id for item in evaluation.resolved for instance in item.instances
    ]

    last = period_start(now, frequency)
    floor = shift_period(last, frequency, -(MAX_PERIODS - 1))
    if frequency in SUB_DAILY:
        window = now - datetime.timedelta(days=KEEP_EVERY_SAMPLE_DAYS)
        floor = max(floor, period_start(window, frequency))
    if since is not None and since != FULL:
        floor = max(floor, period_start(since, frequency))
    evaluation.start = floor

    points = defaultdict(list)
    for instance_id, stamp, value in _input_points(instance_ids, floor, now):
        number = _number(value)
        if number is not None:
            points[instance_id].append((stamp, number))
    stamps = [series[0][0] for series in points.values() if series]
    if not stamps:
        return evaluation
    # Computing starts at the first input sample; ``evaluation.start`` stays
    # at the floor so periods before it lose any stale sample. A sample
    # before the floor, when one exists, pulls the start down to the floor.
    start = max(floor, period_start(min(stamps), frequency))

    readers = {
        instance.id: _AsOf(
            points.get(instance.id, []),
            STALENESS_THRESHOLDS.get(instance.collection_frequency),
        )
        for item in evaluation.resolved
        for instance in item.instances
    }
    keys = {item.key for item in evaluation.resolved}
    current = start
    while current <= last:
        end = shift_period(current, frequency)
        # The last moment the period covers; the open period stops at now.
        cutoff = min(end - datetime.timedelta(microseconds=1), now)
        context = {
            item.key: _combine(
                item.combine,
                [readers[instance.id].at(cutoff) for instance in item.instances],
            )
            for item in evaluation.resolved
        }
        period = PeriodResult(start=current, timestamp=cutoff, inputs=dict(context))
        missing = any(context[key] is None for key in keys)
        context.update(
            previous=previous,
            now=cutoff.isoformat(),
            today=cutoff.date().isoformat(),
        )
        try:
            value = evaluate(expression, context)
        except ExpressionError as e:
            if not missing:
                raise DerivedMetricError(
                    f"{_label(current, frequency)}: expression: {e.message}"
                )
            value = None
        if value is None:
            period.skipped = True
        else:
            try:
                period.envelope = shape_value(value, shape)
            except DerivedMetricError as e:
                raise DerivedMetricError(f"{_label(current, frequency)}: {e.message}")
            period.value = value
            evaluation.value = value
        previous = period.value
        evaluation.periods.append(period)
        current = end
    return evaluation


def _input_points(instance_ids, floor, now):
    """The samples the periods from ``floor`` to ``now`` can read, in time
    order: every sample inside that window, plus each instance's last one
    before it, which is what the first periods see. A recompute of the last
    period or two must not stream years of history to find that one row."""
    from django.db.models import OuterRef, Q, Subquery

    from .models import CustomMetricSample, MetricInstance

    last_before = (
        CustomMetricSample.objects.filter(
            metric_instance=OuterRef("pk"), timestamp__lt=floor
        )
        .order_by("-timestamp")
        .values("id")[:1]
    )
    carried = list(
        MetricInstance.objects.filter(id__in=instance_ids)
        .annotate(last_before=Subquery(last_before))
        .exclude(last_before__isnull=True)
        .values_list("last_before", flat=True)
    )
    return (
        CustomMetricSample.objects.filter(
            metric_instance_id__in=instance_ids, timestamp__lte=now
        )
        .filter(Q(timestamp__gte=floor) | Q(id__in=carried))
        .order_by("timestamp")
        .values_list("metric_instance_id", "timestamp", "value")
        .iterator(chunk_size=2000)
    )


# ---------- the sampler ----------


def series_due(instance, now=None):
    return instance.recompute_from is not None or is_due(instance, now)


def _stored_value(instance, start):
    """The stored result of the period starting at ``start``, or None."""
    from .models import CustomMetricSample

    sample = CustomMetricSample.objects.filter(
        metric_instance=instance, period_start=start
    ).first()
    return sample.raw_value() if sample else None


def compute_series(instance, *, write=True, only_if_due=False, full=False):
    """Recompute the instance's series from the earliest period that may have
    changed: the one an input marked, else the one the last run reached.
    Returns the SeriesEvaluation, or None when another worker holds the lock
    or, with ``only_if_due``, when there is nothing to do."""
    definition = instance.metric_definition
    key = _lock_key(instance.id)
    if not cache.add(key, "1", LOCK_TTL_SECONDS):
        return None
    try:
        if only_if_due:
            instance.refresh_from_db(fields=["last_computed_at", "recompute_from"])
            if not series_due(instance):
                return None
        frequency = instance.collection_frequency or "daily"
        since = None
        if not full and instance.last_computed_at is not None:
            since = instance.last_computed_at
            if instance.recompute_from is not None:
                since = min(since, instance.recompute_from)
        previous = None
        if since is not None and since != FULL:
            previous = _stored_value(
                instance, shift_period(period_start(since, frequency), frequency, -1)
            )
        now = timezone.now()
        try:
            evaluation = evaluate_series(
                definition.inputs,
                definition.expression,
                instance.folder,
                frequency,
                definition,
                since=since,
                previous=previous,
                choices=instance.input_choices,
            )
        except DerivedMetricError as e:
            if write:
                instance.last_computed_at = now
                instance.last_computation_error = e.message
                instance.recompute_from = None
                instance.save(
                    update_fields=[
                        "last_computed_at",
                        "last_computation_error",
                        "recompute_from",
                        "updated_at",
                    ]
                )
            raise
        if write:
            changed_from = _store(instance, evaluation)
            instance.last_computed_at = now
            instance.last_computation_error = ""
            instance.recompute_from = None
            instance.save(
                update_fields=[
                    "last_computed_at",
                    "last_computation_error",
                    "recompute_from",
                    "updated_at",
                ]
            )
            instance.__dict__.pop("_latest_sample", None)
            if changed_from is not None:
                # Bulk writes send no signals: formulas reading this one are
                # marked here, once.
                mark_dependents(definition, instance.folder, changed_from)
        return evaluation
    finally:
        cache.delete(key)


def _store(instance, evaluation):
    """One sample per computed period, replaced in place; periods that
    produced nothing lose their sample. Returns the earliest period whose
    value changed, or None."""
    from .models import CustomMetricSample

    now = timezone.now()
    existing = {
        sample.period_start: sample
        for sample in CustomMetricSample.objects.filter(
            metric_instance=instance, period_start__gte=evaluation.start
        )
    }
    to_create, to_update, changed = [], [], []
    for period in evaluation.periods:
        if period.skipped:
            continue
        sample = existing.pop(period.start, None)
        if sample is None:
            to_create.append(
                CustomMetricSample(
                    metric_instance=instance,
                    folder=instance.folder,
                    timestamp=period.timestamp,
                    value=period.envelope,
                    source=CustomMetricSample.Source.DERIVED,
                    period_start=period.start,
                )
            )
            changed.append(period.start)
        elif sample.value != period.envelope or sample.timestamp != period.timestamp:
            if sample.value != period.envelope:
                changed.append(period.start)
            sample.value = period.envelope
            sample.timestamp = period.timestamp
            sample.updated_at = now
            to_update.append(sample)
    changed.extend(existing)
    with transaction.atomic():
        if existing:
            # Signal-free like the bulk writes below: the caller marks the
            # readers once, from the earliest changed period.
            delete_samples_silently(
                CustomMetricSample.objects.filter(
                    id__in=[sample.id for sample in existing.values()]
                )
            )
        CustomMetricSample.objects.bulk_create(to_create, batch_size=500)
        CustomMetricSample.objects.bulk_update(
            to_update, ["value", "timestamp", "updated_at"], batch_size=500
        )
    return min(changed) if changed else None


# ---------- dependencies ----------


def dependents_of(definition):
    """Definitions whose formula reads ``definition``."""
    from .models import MetricDefinition

    return [
        candidate
        for candidate in MetricDefinition.objects.exclude(inputs__isnull=True).exclude(
            expression=""
        )
        if any(
            isinstance(spec, dict) and refers_to(spec.get("definition"), definition)
            for spec in candidate.inputs or []
        )
    ]


def mark(instance_ids, moment):
    """Recompute these instances from ``moment``'s period at the next sweep,
    keeping an earlier mark. ``update()`` sends no signal."""
    from django.db.models import Q

    from .models import MetricInstance

    MetricInstance.objects.filter(id__in=instance_ids).filter(
        Q(recompute_from__isnull=True) | Q(recompute_from__gt=moment)
    ).update(recompute_from=moment)


def mark_dependents(definition, folder, moment):
    """An instance of ``definition`` in ``folder`` changed from ``moment``
    (FULL for its very presence): every formula reading it, in that folder or
    above, recomputes from there."""
    from .models import MetricInstance

    dependents = dependents_of(definition)
    if not dependents:
        return
    ancestors = [f.id for f in folder.get_parent_folders(include_self=True)]
    instance_ids = list(
        MetricInstance.objects.filter(
            metric_definition__in=dependents, folder_id__in=ancestors
        ).values_list("id", flat=True)
    )
    if instance_ids:
        mark(instance_ids, moment)


def input_closure(definitions):
    """The ids of every definition the given formulas read, at any depth."""
    seen = set()
    stack = list(definitions)
    while stack:
        definition = stack.pop()
        for spec in definition.inputs or []:
            if not isinstance(spec, dict):
                continue
            target = resolve_definition(spec.get("definition"))
            if target is not None and target.id not in seen:
                seen.add(target.id)
                stack.append(target)
    return seen


def depth(definition, seen=None):
    """How many formulas stand between ``definition`` and plain metrics: the
    sweep computes shallow ones first, so a formula reads fresh inputs."""
    seen = seen if seen is not None else set()
    if definition.id in seen or not definition.reads_metrics:
        return 0
    seen.add(definition.id)
    targets = [
        resolve_definition(spec.get("definition"))
        for spec in definition.inputs or []
        if isinstance(spec, dict)
    ]
    return 1 + max(
        (depth(target, seen) for target in targets if target is not None), default=0
    )
