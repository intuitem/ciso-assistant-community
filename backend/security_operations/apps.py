"""
Django app configuration for Security Operations bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class SecurityOperationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'security_operations'
    verbose_name = 'Security Operations Bounded Context'

    def ready(self):
        """Initialize event handlers when Django starts"""
        from .projections import register_projections

        event_bus = get_event_bus()
        register_projections(event_bus)
