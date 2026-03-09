from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import StoredLibrary
from core.mappings.engine import engine

@receiver(post_save, sender=StoredLibrary)
@receiver(post_delete, sender=StoredLibrary)
def update_mapping_engine_cache(sender, instance, **kwargs):
    # Reload RMS data whenever a library is saved (potentially loaded/unloaded) or deleted.
    transaction.on_commit(lambda: engine.load_rms_data())
