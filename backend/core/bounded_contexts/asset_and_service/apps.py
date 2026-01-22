"""
Django app configuration for Asset and Service bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class AssetAndServiceConfig(AppConfig):
    """Configuration for Asset and Service bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.asset_and_service'
    verbose_name = 'Asset and Service Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.asset_projections import AssetProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers
        event_bus.subscribe("AssetCreated", AssetProjectionHandler())
        event_bus.subscribe("AssetActivated", AssetProjectionHandler())
        event_bus.subscribe("AssetArchived", AssetProjectionHandler())
        event_bus.subscribe("ControlAssignedToAsset", AssetProjectionHandler())
        event_bus.subscribe("RiskAssignedToAsset", AssetProjectionHandler())
        event_bus.subscribe("ServiceLinkedToAsset", AssetProjectionHandler())

