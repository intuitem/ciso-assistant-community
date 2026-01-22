"""
Django app configuration for Risk Registers bounded context
"""

from django.apps import AppConfig
from core.domain.events import get_event_bus


class RiskRegistersConfig(AppConfig):
    """Configuration for Risk Registers bounded context"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.bounded_contexts.risk_registers'
    verbose_name = 'Risk Registers Bounded Context'
    
    def ready(self):
        """Called when Django starts - register event handlers"""
        from .projections.risk_projections import RiskProjectionHandler
        
        event_bus = get_event_bus()
        
        # Register projection handlers for all risk events
        for event_type in [
            "AssetRiskCreated", "AssetRiskAssessed", "AssetRiskTreated",
            "AssetRiskAccepted", "AssetRiskClosed",
            "ThirdPartyRiskCreated", "ThirdPartyRiskAssessed", "ThirdPartyRiskTreated",
            "ThirdPartyRiskAccepted", "ThirdPartyRiskClosed",
            "BusinessRiskCreated", "BusinessRiskAssessed", "BusinessRiskTreated",
            "BusinessRiskAccepted", "BusinessRiskClosed",
        ]:
            event_bus.subscribe(event_type, RiskProjectionHandler())

