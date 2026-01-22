"""
Django app configuration for SecurityOperations bounded context
"""

from django.apps import AppConfig


class SecurityOperationsConfig(AppConfig):
    """Configuration for SecurityOperations bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.security_operations'
    verbose_name = 'SecurityOperations Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers if needed"""
        # Event handlers can be registered here if needed
        pass

