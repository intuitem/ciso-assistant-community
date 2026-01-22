"""
Django app configuration for ThirdPartyManagement bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class ThirdPartyManagementConfig(AppConfig):
    """Configuration for ThirdPartyManagement bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.third_party_management'
    verbose_name = 'ThirdPartyManagement Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.third_party_projections import ThirdPartyProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers for all third party events
        handler = ThirdPartyProjectionHandler()
        for event_type in [
            "ThirdPartyCreated", "ThirdPartyActivated", "ThirdPartyOffboardingStarted",
            "ThirdPartyArchived", "ThirdPartyLifecycleChanged",
        ]:
            event_bus.subscribe(event_type, handler)

