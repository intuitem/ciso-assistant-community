"""
Django app configuration for Risk Registers bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class RiskRegistersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'risk_registers'
    verbose_name = 'Risk Registers Bounded Context'

    def ready(self):
        """Initialize event handlers when Django starts"""
        from .projections import register_projections

        event_bus = get_event_bus()
        register_projections(event_bus)
