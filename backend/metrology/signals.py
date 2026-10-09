"""Marking metric formulas for recomputation when what they read changes.

A sample written, edited or deleted marks the formulas reading its metric,
from that sample's period on. An instance appearing, disappearing or moving
changes what an input resolves to, so it marks them whole, as does editing a
formula. Marks are applied after commit and only recorded: the sweep
recomputes, never the request. The series engine writes in bulk, which sends
no signal, and marks its own dependents.
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
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
        # The instance is being deleted with its samples: its own signal
        # marks the readers whole.
        return
    _after_commit(row[0], row[1], min(moments))


# ---------- instances ----------


@receiver(pre_save, sender=MetricInstance)
def remember_instance_scope(sender, instance, **kwargs):
    instance._previous_scope = None
    if not instance._state.adding:
        instance._previous_scope = (
            MetricInstance.objects.filter(pk=instance.pk)
            .values_list("metric_definition_id", "folder_id")
            .first()
        )


@receiver(post_save, sender=MetricInstance)
def instance_saved(sender, instance, created, update_fields=None, **kwargs):
    from .series import FULL

    if update_fields is not None and set(update_fields) <= _BOOKKEEPING:
        return
    scope = (instance.metric_definition_id, instance.folder_id)
    previous = getattr(instance, "_previous_scope", None)
    if not created and previous == scope:
        return
    if not _has_readers():
        return
    _after_commit(*scope, FULL)
    if previous is not None and previous != scope:
        _after_commit(*previous, FULL)


@receiver(post_delete, sender=MetricInstance)
def instance_deleted(sender, instance, **kwargs):
    from .series import FULL

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
