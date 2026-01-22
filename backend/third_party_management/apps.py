"""
Django app configuration for Third Party Management bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class ThirdPartyManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'third_party_management'
    verbose_name = 'Third Party Management Bounded Context'

    def ready(self):
        """Initialize event handlers when Django starts"""
        from .projections import register_projections

        event_bus = get_event_bus()
        register_projections(event_bus)
