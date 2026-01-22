"""
Django app configuration for RMF Operations bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class RmfOperationsConfig(AppConfig):
    """Configuration for RMF Operations bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.rmf_operations'
    verbose_name = 'RMF Operations Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        # Projection handlers will be registered here in later phases
        # For Phase 0, we just ensure the app is loaded
        pass

