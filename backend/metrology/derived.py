"""Derived metrics: a sample computed from the instance's own data.

A derived metric definition carries ``datasets`` (name -> read configuration,
evaluated in aggregate mode through core.reads) and one CEL ``expression``
over the dataset results. The instance binds the formula to a folder: every
dataset reads that folder's subtree, with no identity, so the value is a fact
about the folder and the same for everyone who may view the instance (see
documentation/architecture/decisions/derived-metrics-from-workflow-reads.md).

The expression may also read ``previous`` (the instance's latest sample
value, or null), ``metrics.<ref_id>.value`` (the latest value of other
instances in the same subtree) and ``now`` / ``today``. Dataset filter values
may carry ``{{today}}``, ``{{now}}`` and ``{{today-30d}}``-style offsets.
"""

from __future__ import annotations

import datetime
import math
import re
from dataclasses import dataclass
from dataclasses import field as dataclass_field

import structlog
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from core.expressions import (
    ExpressionError,
    compile_expression,
    evaluate,
    referenced_paths,
)
from core.reads import (
    MODE_AGGREGATE,
    READABLE_MODELS,
    ReadError,
    ReadScope,
    run_aggregate_read,
    subtree_folder_ids,
    validate_read_config,
)

DATASET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_DATASETS = 10
MAX_EXPRESSION_LENGTH = 2000
# Names the expression may read besides the datasets.
CONTEXT_ROOTS = frozenset({"previous", "metrics", "now", "today"})
# A lock outlives any sane computation; a crashed worker frees it by expiry.
LOCK_TTL_SECONDS = 600

logger = structlog.get_logger(__name__)

_TIME_TOKEN_RE = re.compile(r"\{\{\s*(today|now)\s*(?:([+-])\s*(\d+)\s*d)?\s*\}\}")


class DerivedMetricError(Exception):
    """The formula cannot be evaluated for this instance. Author-facing."""

    def __init__(self, message):
        super().__init__(message)
        # What an API response or the instance page may carry: the curated
        # text, never the exception object itself.
        self.message = message


# ---------- the formula ----------


def validate_formula(
    datasets, expression, inputs=None, definition=None
) -> list[tuple[str, str]]:
    """Save-time checks of a definition's formula, as (code, message) tuples.
    An empty expression with no datasets and no inputs is a plain (manual)
    definition. A formula reads datasets (objects, now) or inputs (other
    metrics, period by period), never both: past periods cannot be
    recomputed from present-day objects. ``definition`` is the one being
    saved, when it exists, so a formula cannot read itself."""
    errors = []
    expression = expression or ""
    if not isinstance(expression, str):
        return [("derived_expression_invalid", "The expression must be text")]
    if not expression.strip() and not datasets and not inputs:
        return errors
    if inputs:
        return _validate_metric_formula(datasets, expression, inputs, definition)
    if not isinstance(datasets, dict) or not datasets:
        errors.append(
            ("derived_datasets_missing", "A derived metric needs at least one dataset")
        )
        datasets = {}
    if len(datasets) > MAX_DATASETS:
        errors.append(
            ("derived_datasets_too_many", f"At most {MAX_DATASETS} datasets per metric")
        )
    names = set()
    for name, config in datasets.items():
        if (
            not isinstance(name, str)
            or not DATASET_NAME_RE.match(name)
            or name in CONTEXT_ROOTS
        ):
            errors.append(
                (
                    "derived_dataset_name_invalid",
                    (
                        f"'{name}' is not a valid dataset name (letters, digits, _; "
                        f"not one of {', '.join(sorted(CONTEXT_ROOTS))})"
                    ),
                )
            )
            continue
        names.add(name)
        if not isinstance(config, dict):
            errors.append(
                ("derived_dataset_invalid", f"dataset '{name}' must be a mapping")
            )
            continue
        for code, message in validate_read_config(_aggregate_config(config)):
            errors.append(("derived_dataset_invalid", f"dataset '{name}': {message}"))
        for message in _grouping_errors(config):
            errors.append(("derived_dataset_invalid", f"dataset '{name}': {message}"))
    if not expression.strip():
        errors.append(
            ("derived_expression_missing", "A derived metric needs an expression")
        )
        return errors
    if len(expression) > MAX_EXPRESSION_LENGTH:
        errors.append(("derived_expression_too_long", "The expression is too long"))
        return errors
    try:
        compile_expression(expression)
    except ExpressionError as e:
        errors.append(("derived_expression_invalid", e.message))
        return errors
    roots = {path.split(".")[0] for path in referenced_paths(expression)}
    for root in sorted(roots - names - CONTEXT_ROOTS):
        errors.append(
            (
                "derived_expression_unknown_name",
                f"'{root}' is not a dataset of this metric",
            )
        )
    return errors


def _validate_metric_formula(datasets, expression, inputs, definition):
    from .series import validate_inputs, validate_series_expression

    if datasets:
        return [
            (
                "derived_formula_mixed",
                (
                    "A formula reads either datasets or other metrics, not both; "
                    "make the datasets a metric of their own and add it as an input"
                ),
            )
        ]
    errors = validate_inputs(inputs, definition)
    if not expression.strip():
        return errors + [
            ("derived_expression_missing", "A derived metric needs an expression")
        ]
    if len(expression) > MAX_EXPRESSION_LENGTH:
        return errors + [("derived_expression_too_long", "The expression is too long")]
    keys = {
        spec.get("key")
        for spec in inputs
        if isinstance(spec, dict) and isinstance(spec.get("key"), str)
    }
    return errors + validate_series_expression(expression, keys)


def _grouping_errors(config):
    """A derived value is visible to whoever may view the instance, without
    their read rights on the rows: a breakdown may name categories (a status,
    a related object's id) but never row content (a name, a description)."""
    entry = READABLE_MODELS.get(config.get("model"))
    aggregates = config.get("aggregates")
    if entry is None or not isinstance(aggregates, list):
        return []
    categorical = set(entry.categorical_fields())
    return [
        (
            f"'{spec['group_by']}' cannot group a derived metric: only a field "
            "with a fixed set of values (a choice, yes/no, a related object) can"
        )
        for spec in aggregates
        if isinstance(spec, dict)
        and spec.get("group_by")
        and spec["group_by"] not in categorical
    ]


def _aggregate_config(config):
    """A dataset is a read configuration in aggregate mode, whatever the
    stored config says: the metric form never offers the mode."""
    return {**config, "mode": MODE_AGGREGATE}


# ---------- evaluation ----------


def resolve_time_tokens(value, now=None):
    """``{{today}}``, ``{{now}}`` and ``{{today-30d}}`` in a filter value."""
    if not isinstance(value, str) or "{{" not in value:
        return value
    now = now or timezone.now()

    def substitute(match):
        base, sign, days = match.group(1), match.group(2), match.group(3)
        moment = now
        if days:
            delta = datetime.timedelta(days=int(days))
            moment = moment + delta if sign == "+" else moment - delta
        return moment.date().isoformat() if base == "today" else moment.isoformat()

    return _TIME_TOKEN_RE.sub(substitute, value)


@dataclass
class Evaluation:
    """What one evaluation produced, for a sample or for the preview."""

    value: object = None
    datasets: dict = dataclass_field(default_factory=dict)
    context: dict = dataclass_field(default_factory=dict)


def other_metric_values(folder, exclude_id=None, referenced=()):
    """``metrics.<ref_id>.value`` for the instances of the subtree that carry a
    ref_id: the latest sample's raw value, whatever wrote it. One query for
    the instances and one for their latest samples, whatever the history.

    A ref_id is not unique across a subtree. One that several instances share
    is left out rather than picked arbitrarily, and naming it in
    ``referenced`` (the ref_ids the expression reads) is an error."""
    from .models import CustomMetricSample, MetricInstance

    latest = (
        CustomMetricSample.objects.filter(metric_instance=OuterRef("pk"))
        .order_by("-timestamp")
        .values("id")[:1]
    )
    instances = (
        MetricInstance.objects.filter(folder_id__in=subtree_folder_ids(folder))
        .exclude(ref_id__isnull=True)
        .exclude(ref_id="")
        .annotate(latest_sample_id=Subquery(latest))
    )
    if exclude_id is not None:
        instances = instances.exclude(id=exclude_id)
    rows = list(instances.values_list("ref_id", "latest_sample_id"))
    # raw_value() reads the definition's category: fetched with the samples.
    samples = {
        sample.id: sample
        for sample in CustomMetricSample.objects.filter(
            id__in=[sample_id for _ref, sample_id in rows if sample_id is not None]
        ).select_related("metric_instance__metric_definition")
    }
    counts = {}
    for ref_id, _sample_id in rows:
        counts[ref_id] = counts.get(ref_id, 0) + 1
    for ref_id in sorted(referenced):
        if counts.get(ref_id, 0) > 1:
            raise DerivedMetricError(
                f"metrics.{ref_id}: {counts[ref_id]} instances in this domain "
                "share this reference id"
            )
    values = {}
    for ref_id, sample_id in rows:
        if counts[ref_id] > 1:
            continue
        sample = samples.get(sample_id)
        values[ref_id] = {"value": sample.raw_value() if sample else None}
    return values


def _referenced_metrics(expression):
    """``None`` when the expression never reads ``metrics``, else the ref_ids
    it names (``*`` for an index that is not a string literal)."""
    paths = [path.split(".") for path in referenced_paths(expression)]
    if not any(parts[0] == "metrics" for parts in paths):
        return None
    return {parts[1] for parts in paths if parts[0] == "metrics" and len(parts) > 1}


def evaluate_formula(datasets, expression, folder, *, previous=None, exclude_id=None):
    """Datasets then expression, against ``folder``'s subtree. Raises
    DerivedMetricError with the message an author needs."""
    now = timezone.now()
    scope = ReadScope(folder_ids=subtree_folder_ids(folder))
    evaluation = Evaluation()
    for name, config in (datasets or {}).items():
        # A definition saved before the rule, or written around the
        # serializer, is held to it here too.
        grouping = _grouping_errors(config) if isinstance(config, dict) else []
        if grouping:
            raise DerivedMetricError(f"dataset '{name}': {grouping[0]}")
        try:
            evaluation.datasets[name] = run_aggregate_read(
                _aggregate_config(config),
                scope,
                resolve=lambda value, now=now: resolve_time_tokens(value, now),
            )
        except ReadError as e:
            raise DerivedMetricError(f"dataset '{name}': {e.message}")
        except ValidationError, ValueError, TypeError:
            # A value the column cannot hold, refused by Django or the
            # database while the filter is applied or the query runs. Their
            # wording is theirs, not ours: it goes to the log, not to the
            # author.
            logger.warning(
                "derived metric dataset rejected a filter value",
                dataset=name,
                exc_info=True,
            )
            raise DerivedMetricError(
                f"dataset '{name}': a filter value does not fit its field"
            )
        except IndexError:
            # A library update can shrink a matrix while scenarios keep their
            # old level indices; a computed cell lookup then runs past it.
            raise DerivedMetricError(
                f"dataset '{name}': a stored level no longer exists in the risk matrix"
            )
    referenced = _referenced_metrics(expression)
    evaluation.context = {
        **evaluation.datasets,
        "previous": previous,
        "metrics": (
            {}
            if referenced is None
            else other_metric_values(folder, exclude_id, referenced)
        ),
        "now": now.isoformat(),
        "today": now.date().isoformat(),
    }
    try:
        evaluation.value = evaluate(expression, evaluation.context)
    except ExpressionError as e:
        raise DerivedMetricError(f"expression: {e.message}")
    return evaluation


def shape_value(value, definition):
    """The sample envelope the API validates, from the expression's result:
    a finite number for a quantitative metric, a level (its name, ref_id or
    1-based index) for a qualitative one."""
    from .models import MetricDefinition

    if definition.category == MetricDefinition.Category.QUALITATIVE:
        choices = definition.choices_definition or []
        if isinstance(value, bool) or value is None:
            raise DerivedMetricError(f"'{value}' is not a level of this metric")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            index = int(value)
            if index != value or index < 1 or index > len(choices):
                raise DerivedMetricError(
                    f"level {value} is outside the metric's {len(choices)} options"
                )
            return {"choice_index": index}
        text = str(value).strip().lower()
        for index, choice in enumerate(choices, start=1):
            names = {
                str(choice.get("name", "")).strip().lower(),
                str(choice.get("ref_id", "")).strip().lower(),
            }
            if text in names - {""}:
                return {"choice_index": index}
        raise DerivedMetricError(f"'{value}' is not a level of this metric")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DerivedMetricError(f"the expression must return a number, not {value!r}")
    if not math.isfinite(float(value)):
        raise DerivedMetricError("the expression returned a non-finite number")
    return {"result": float(value)}


# ---------- sampling ----------

FREQUENCY_INTERVALS = {
    "realtime": datetime.timedelta(minutes=15),
    "hourly": datetime.timedelta(hours=1),
    "daily": datetime.timedelta(days=1),
    "weekly": datetime.timedelta(days=7),
    "monthly": datetime.timedelta(days=30),
    "quarterly": datetime.timedelta(days=91),
    "yearly": datetime.timedelta(days=365),
}
DEFAULT_INTERVAL = datetime.timedelta(days=1)
# How often the sweep runs (tasks.compute_due_derived_metrics). The stamp an
# instance carries is written when its task runs, a little after the tick
# that queued it, so a strict comparison would miss the next aligned tick
# and slip every interval by one sweep. Half a sweep of slack: the tick
# nearest the interval picks the instance up, and a duplicate queued seconds
# after a run does not.
SWEEP_INTERVAL = datetime.timedelta(minutes=15)
DUE_TOLERANCE = SWEEP_INTERVAL / 2


def interval_for(instance):
    return FREQUENCY_INTERVALS.get(instance.collection_frequency, DEFAULT_INTERVAL)


def is_due(instance, now=None):
    now = now or timezone.now()
    if instance.last_computed_at is None:
        return True
    return now - instance.last_computed_at >= interval_for(instance) - DUE_TOLERANCE


def due_instances(now=None):
    """Derived instances the sweep should compute now: active or stale (the
    staleness sweep flips those back), with a formula, past their interval."""
    from .models import MetricInstance

    now = now or timezone.now()
    candidates = (
        MetricInstance.objects.filter(
            status__in=[MetricInstance.Status.ACTIVE, MetricInstance.Status.STALE]
        )
        .exclude(metric_definition__expression="")
        .select_related("metric_definition", "folder")
    )
    # A metric formula is also due when an input marked it.
    return [
        instance
        for instance in candidates
        if is_due(instance, now) or instance.recompute_from is not None
    ]


def _lock_key(instance_id):
    return f"metrology:derived-metric-lock:{instance_id}"


def compute_sample(instance, *, write=True, only_if_due=False, full=False):
    """Evaluate the instance's formula and, by default, write the sample.
    Records the failure on the instance instead of a sample when the
    evaluation fails; the error is author-facing and retrying is pointless
    until the formula or the data changes. Returns the Evaluation, or None
    when another worker holds the instance's lock or, with ``only_if_due``,
    when a run queued earlier already computed it. A metric formula
    recomputes its series instead (metrology.series); ``full`` recomputes
    all of it."""
    from .models import CustomMetricSample

    definition = instance.metric_definition
    if not definition.is_derived:
        raise DerivedMetricError("this metric has no formula")
    if definition.reads_metrics:
        from .series import compute_series

        return compute_series(instance, write=write, only_if_due=only_if_due, full=full)
    key = _lock_key(instance.id)
    if not cache.add(key, "1", LOCK_TTL_SECONDS):
        return None
    try:
        if only_if_due:
            # A sweep queues every due instance; when the queue lags behind
            # a sweep interval, the same instance is queued twice. Checked
            # under the lock, against the stored stamp, so the second one
            # finds the first one's sample and stops.
            instance.refresh_from_db(fields=["last_computed_at"])
            if not is_due(instance):
                return None
        now = timezone.now()
        try:
            evaluation = evaluate_formula(
                definition.datasets,
                definition.expression,
                instance.folder,
                previous=instance.raw_value(),
                exclude_id=instance.id,
            )
            envelope = shape_value(evaluation.value, definition)
        except DerivedMetricError as e:
            if write:
                instance.last_computed_at = now
                instance.last_computation_error = e.message
                instance.save(
                    update_fields=[
                        "last_computed_at",
                        "last_computation_error",
                        "updated_at",
                    ]
                )
            raise
        if write:
            with transaction.atomic():
                CustomMetricSample.objects.create(
                    metric_instance=instance,
                    folder=instance.folder,
                    timestamp=now,
                    value=envelope,
                    source=CustomMetricSample.Source.DERIVED,
                )
                instance.last_computed_at = now
                instance.last_computation_error = ""
                instance.save(
                    update_fields=[
                        "last_computed_at",
                        "last_computation_error",
                        "updated_at",
                    ]
                )
            # The memoised latest sample is stale now.
            instance.__dict__.pop("_latest_sample", None)
        return evaluation
    finally:
        cache.delete(key)


# ---------- retention ----------

KEEP_EVERY_SAMPLE_DAYS = 7


def delete_samples_silently(queryset):
    """Delete sample rows without instantiating them or sending signals: the
    sampler's own housekeeping, which either marks what it changes itself
    (series._store) or changes nothing a reader sees (downsampling). The
    signal path would load every row and queue a mark per row."""
    return queryset._raw_delete(queryset.db)


def downsample_derived_samples(now=None):
    """Older than KEEP_EVERY_SAMPLE_DAYS, keep one derived sample per instance
    per UTC day (the last one). Hourly ticks across many instances add up, and
    a trend older than a week does not need the intraday points. Returns the
    number of samples deleted.

    Days are UTC like the series periods, so the sample kept for a day is the
    one a reader's day-end cutoff finds: a formula reading this instance sees
    the same value before and after, and nothing is marked for recompute.
    Sub-daily readers never reach back this far (series.evaluate_series)."""
    from .models import CustomMetricSample

    now = now or timezone.now()
    cutoff = now - datetime.timedelta(days=KEEP_EVERY_SAMPLE_DAYS)
    old = (
        CustomMetricSample.objects.filter(
            source=CustomMetricSample.Source.DERIVED, timestamp__lt=cutoff
        )
        .order_by("metric_instance_id", "timestamp")
        .values_list("id", "metric_instance_id", "timestamp")
    )
    doomed = []
    last_key = None
    last_id = None
    for sample_id, instance_id, stamp in old.iterator(chunk_size=2000):
        key = (instance_id, stamp.astimezone(datetime.timezone.utc).date())
        if key == last_key:
            # The previous one of the same day is superseded by this one.
            doomed.append(last_id)
        last_key, last_id = key, sample_id
    deleted = 0
    for start in range(0, len(doomed), 500):
        deleted += delete_samples_silently(
            CustomMetricSample.objects.filter(id__in=doomed[start : start + 500])
        )
    return deleted
