"""
Django app configuration for Compliance bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class ComplianceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'compliance'
    verbose_name = 'Compliance Bounded Context'

    def ready(self):
        """Initialize event handlers when Django starts"""
        from .projections import register_projections

        event_bus = get_event_bus()
        register_projections(event_bus)
