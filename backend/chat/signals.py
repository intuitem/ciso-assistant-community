"""
Django signals to trigger incremental re-indexing of model objects
when they are created, updated, or deleted.
"""

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Models to index for RAG
INDEXED_MODELS = [
    "core.AppliedControl",
    "core.RiskScenario",
    "core.Asset",
    "core.Threat",
    "core.ComplianceAssessment",
    "core.RiskAssessment",
]


def _get_model_classes():
    """Lazily resolve model classes from strings."""
    from django.apps import apps

    classes = []
    for model_path in INDEXED_MODELS:
        app_label, model_name = model_path.split(".")
        try:
            classes.append(apps.get_model(app_label, model_name))
        except LookupError:
            logger.warning("Model %s not found, skipping RAG indexing", model_path)
    return classes


_connected = False


def connect_signals():
    """Connect post_save and post_delete signals for indexed models."""
    global _connected
    if _connected:
        return
    _connected = True

    from global_settings.utils import ff_is_enabled

    for model_class in _get_model_classes():

        @receiver(post_save, sender=model_class, weak=False)
        def on_save(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from .tasks import index_model_object

            index_model_object(
                sender._meta.app_label,
                sender.__name__,
                str(instance.id),
            )

        @receiver(post_delete, sender=model_class, weak=False)
        def on_delete(sender, instance, **kwargs):
            if not ff_is_enabled("chat_mode"):
                return
            from .tasks import remove_model_object

            remove_model_object(
                sender._meta.app_label,
                sender.__name__,
                str(instance.id),
            )


# Do NOT call connect_signals() at module level.
# It is called from ChatConfig.ready() in apps.py, which ensures
# all models are fully loaded before we try to resolve them.
