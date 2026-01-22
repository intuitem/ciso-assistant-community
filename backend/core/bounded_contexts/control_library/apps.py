"""
Django app configuration for Control Library bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class ControlLibraryConfig(AppConfig):
    """Configuration for Control Library bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.control_library'
    verbose_name = 'Control Library Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.control_projections import ControlProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers
        event_bus.subscribe("ControlCreated", ControlProjectionHandler())
        event_bus.subscribe("ControlApproved", ControlProjectionHandler())
        event_bus.subscribe("ControlDeprecated", ControlProjectionHandler())
        event_bus.subscribe("ControlImplementationCreated", ControlProjectionHandler())
        event_bus.subscribe("ControlImplementationStatusChanged", ControlProjectionHandler())

