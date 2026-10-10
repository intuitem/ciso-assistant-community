"""Marking metric formulas for recomputation when what they read changes.

A sample written, edited or deleted marks the formulas reading its metric,
from that sample's period on. An instance appearing, disappearing, moving or
changing its collection frequency (the staleness threshold a reader aligns
on) changes what an input resolves to, so it marks them whole, as does
editing a formula. Marks are applied after commit and only recorded: the
sweep recomputes, never the request.

The sampler's own bulk writes and deletes send no signal (series._store,
derived.downsample_derived_samples) and mark what they change themselves.
An instance deleted with its samples sends one signal per sample while the
instance row still exists, Django deleting the dependents first: those are
skipped, since the instance's own signal marks the readers whole.
"""

import threading

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import CustomMetricSample, MetricDefinition, MetricInstance

# Saves that are the sampler's own bookkeeping, not a change of what a
# formula reads.
_BOOKKEEPING = {
    "last_computed_at",
    "last_computation_error",
    "recompute_from",
    "updated_at",
    "status",
}

# Instances whose cascade delete is under way on this thread: their samples'
# delete signals carry nothing the instance's own signal does not.
_local = threading.local()


def _deleting():
    if not hasattr(_local, "deleting"):
        _local.deleting = set()
    return _local.deleting


def _after_commit(definition_id, folder_id, moment):
    def apply():
        from iam.models import Folder

        from .series import mark_dependents

        definition = MetricDefinition.objects.filter(id=definition_id).first()
        folder = Folder.objects.filter(id=folder_id).first()
        if definition is not None and folder is not None:
            mark_dependents(definition, folder, moment)

    transaction.on_commit(apply)


def _has_readers():
    """Cheap guard: most deployments have no metric formula at all."""
    return MetricDefinition.objects.exclude(inputs__isnull=True).exists()


# ---------- samples ----------


@receiver(pre_save, sender=CustomMetricSample)
def remember_sample_timestamp(sender, instance, **kwargs):
    instance._previous_timestamp = None
    if not instance._state.adding:
        instance._previous_timestamp = (
            CustomMetricSample.objects.filter(pk=instance.pk)
            .values_list("timestamp", flat=True)
            .first()
        )


@receiver(post_save, sender=CustomMetricSample)
@receiver(post_delete, sender=CustomMetricSample)
def sample_changed(sender, instance, **kwargs):
    if instance.metric_instance_id in _deleting():
        return
    if not _has_readers():
        return
    moments = [instance.timestamp]
    if getattr(instance, "_previous_timestamp", None) is not None:
        moments.append(instance._previous_timestamp)
    metric = MetricInstance.objects.filter(id=instance.metric_instance_id).values_list(
        "metric_definition_id", "folder_id"
    )
    row = metric.first()
    if row is None:
        return
    _after_commit(row[0], row[1], min(moments))


# ---------- instances ----------


@receiver(pre_save, sender=MetricInstance)
def remember_instance_scope(sender, instance, **kwargs):
    instance._previous_scope = None
    instance._previous_choices = None
    if not instance._state.adding:
        row = (
            MetricInstance.objects.filter(pk=instance.pk)
            .values_list(
                "metric_definition_id",
                "folder_id",
                "collection_frequency",
                "input_choices",
            )
            .first()
        )
        if row is not None:
            instance._previous_scope = row[:3]
            instance._previous_choices = row[3]


@receiver(post_save, sender=MetricInstance)
def instance_saved(sender, instance, created, update_fields=None, **kwargs):
    from .series import FULL

    if update_fields is not None and set(update_fields) <= _BOOKKEEPING:
        return
    scope = (
        instance.metric_definition_id,
        instance.folder_id,
        instance.collection_frequency,
    )
    previous = getattr(instance, "_previous_scope", None)
    _own_series_changed(instance, created, previous, scope)
    if not created and previous == scope:
        return
    if not _has_readers():
        return
    # A new frequency changes how old a value may be when a reader aligns
    # on it: every period of every reader may differ.
    _after_commit(scope[0], scope[1], FULL)
    if previous is not None and previous[:2] != scope[:2]:
        _after_commit(previous[0], previous[1], FULL)


def _own_series_changed(instance, created, previous, scope):
    """A metric formula instance whose inputs now resolve differently (other
    picks or exclusions, another folder or frequency) recomputes its whole
    series. A new one has never computed: the sweep backfills it anyway."""
    from .series import FULL, mark

    if created or not instance.metric_definition.reads_metrics:
        return
    choices = getattr(instance, "_previous_choices", None)
    if previous == scope and choices == instance.input_choices:
        return
    instance_id = instance.id
    transaction.on_commit(lambda: mark([instance_id], FULL))


@receiver(pre_delete, sender=MetricInstance)
def instance_deleting(sender, instance, **kwargs):
    _deleting().add(instance.id)


@receiver(post_delete, sender=MetricInstance)
def instance_deleted(sender, instance, **kwargs):
    from .series import FULL

    _deleting().discard(instance.id)
    if _has_readers():
        _after_commit(instance.metric_definition_id, instance.folder_id, FULL)


# ---------- definitions ----------


@receiver(pre_save, sender=MetricDefinition)
def remember_formula(sender, instance, **kwargs):
    instance._previous_formula = None
    if not instance._state.adding:
        instance._previous_formula = (
            MetricDefinition.objects.filter(pk=instance.pk)
            .values_list("inputs", "expression")
            .first()
        )


@receiver(post_save, sender=MetricDefinition)
def formula_saved(sender, instance, created, **kwargs):
    """Editing a metric formula recomputes every instance's whole series."""
    from .series import FULL, mark

    previous = getattr(instance, "_previous_formula", None)
    if created or previous is None or not instance.reads_metrics:
        return
    if previous == (instance.inputs, instance.expression):
        return
    instance_ids = list(instance.metricinstance_set.values_list("id", flat=True))

    transaction.on_commit(lambda: mark(instance_ids, FULL))
