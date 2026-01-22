"""
Django app configuration for BusinessContinuity bounded context
"""

from django.apps import AppConfig


class BusinessContinuityConfig(AppConfig):
    """Configuration for BusinessContinuity bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.business_continuity'
    verbose_name = 'BusinessContinuity Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers if needed"""
        # Event handlers can be registered here if needed
        pass

