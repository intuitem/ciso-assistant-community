"""
Django app configuration for Business Continuity bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class BusinessContinuityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'business_continuity'
    verbose_name = 'Business Continuity Bounded Context'

    def ready(self):
        """Initialize event handlers when Django starts"""
        from .projections import register_projections

        event_bus = get_event_bus()
        register_projections(event_bus)
