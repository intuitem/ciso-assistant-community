"""
Django app configuration for domain module
"""

from django.apps import AppConfig


class DomainConfig(AppConfig):
    """Configuration for domain app"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.domain'
    verbose_name = 'Domain Infrastructure'
    
    def ready(self):
        """Called when Django starts"""
        # Import signal handlers, register event handlers, etc.
        pass

