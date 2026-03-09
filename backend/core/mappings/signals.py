from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import StoredLibrary, Framework
from core.mappings.engine import engine


@receiver(post_save, sender=StoredLibrary)
@receiver(post_delete, sender=StoredLibrary)
def update_mapping_engine_cache(sender, instance, **kwargs):
    # Reload RMS data whenever a relevant library is saved (potentially loaded/unloaded) or deleted.
    content = instance.content
    if isinstance(content, dict):
        if any(
            key in content
            for key in [
                "requirement_mapping_set",
                "requirement_mapping_sets",
                "framework",
                "frameworks",
            ]
        ):
            transaction.on_commit(engine.reload_cache)


@receiver(post_delete, sender=Framework)
def update_mapping_engine_cache_on_framework_delete(sender, instance, **kwargs):
    transaction.on_commit(engine.reload_cache)
