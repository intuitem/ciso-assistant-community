"""
Django app configuration for Privacy bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class PrivacyConfig(AppConfig):
    """Configuration for Privacy bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.privacy'
    verbose_name = 'Privacy Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.privacy_projections import PrivacyProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers for all privacy events
        handler = PrivacyProjectionHandler()
        for event_type in [
            "DataAssetCreated", "DataAssetActivated", "DataAssetRetired",
            "DataFlowEstablished", "DataFlowChanged", "DataFlowActivated", "DataFlowRetired",
        ]:
            event_bus.subscribe(event_type, handler)

