from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import RequirementMappingSet, Framework

from core.mappings.engine import engine


@receiver([post_save, post_delete], sender=RequirementMappingSet)
def invalidate_requirement_mapping_set_cache(sender, instance, **kwargs):
    engine.load_rms_data()


@receiver([post_save, post_delete], sender=Framework)
def invalidate_framework_cache(sender, instance, **kwargs):
    engine.load_frameworks()
