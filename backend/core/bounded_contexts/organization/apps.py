"""
Django app configuration for Organization bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class OrganizationConfig(AppConfig):
    """Configuration for Organization bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.organization'
    verbose_name = 'Organization Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.org_unit_projections import OrgUnitProjectionHandler
        from .projections.user_projections import UserProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers
        event_bus.subscribe("OrgUnitCreated", OrgUnitProjectionHandler())
        event_bus.subscribe("OrgUnitActivated", OrgUnitProjectionHandler())
        event_bus.subscribe("OrgUnitRetired", OrgUnitProjectionHandler())
        event_bus.subscribe("ChildOrgUnitAdded", OrgUnitProjectionHandler())
        event_bus.subscribe("OwnerAssignedToOrgUnit", OrgUnitProjectionHandler())
        
        event_bus.subscribe("UserCreated", UserProjectionHandler())
        event_bus.subscribe("UserActivated", UserProjectionHandler())
        event_bus.subscribe("UserDisabled", UserProjectionHandler())
        event_bus.subscribe("UserAssignedToGroup", UserProjectionHandler())
        event_bus.subscribe("UserAssignedToOrgUnit", UserProjectionHandler())

