"""
Django app configuration for Compliance bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class ComplianceConfig(AppConfig):
    """Configuration for Compliance bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.compliance'
    verbose_name = 'Compliance Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.compliance_projections import ComplianceProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers for all compliance events
        handler = ComplianceProjectionHandler()
        for event_type in [
            "ComplianceFrameworkCreated", "ComplianceFrameworkActivated", "ComplianceFrameworkRetired",
            "RequirementCreated", "RequirementMappedToControl", "RequirementRetired",
            "ComplianceFindingCreated", "ComplianceFindingStatusChanged",
            "ComplianceExceptionRequested", "ComplianceExceptionApproved", "ComplianceExceptionExpired",
        ]:
            event_bus.subscribe(event_type, handler)

