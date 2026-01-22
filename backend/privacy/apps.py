"""
Django app configuration for Privacy bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class PrivacyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'privacy'
    verbose_name = 'Privacy Bounded Context'

    def ready(self):
        """Initialize event handlers when Django starts"""
        from .projections import register_projections

        event_bus = get_event_bus()
        register_projections(event_bus)