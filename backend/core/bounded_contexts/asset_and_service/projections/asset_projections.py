"""
Asset Projection Handlers

Update read models based on Asset domain events.
"""

import uuid
from core.domain.events import EventHandler, DomainEvent
from ..read_models.asset_overview import AssetOverview
from ..aggregates.asset import Asset


class AssetProjectionHandler(EventHandler):
    """
    Handler that updates AssetOverview read model from domain events.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        if event_type == "AssetCreated":
            self._create_overview(event)
        elif event_type == "AssetActivated":
            self._update_overview(event)
        elif event_type == "AssetArchived":
            self._update_overview(event)
        elif event_type == "ControlAssignedToAsset":
            self._update_control_summary(event)
        elif event_type == "RiskAssignedToAsset":
            self._update_risk_summary(event)
        elif event_type == "ServiceLinkedToAsset":
            self._update_service_summary(event)
    
    def _create_overview(self, event: DomainEvent):
        """Create overview when asset is created"""
        asset_id = event.aggregate_id
        
        try:
            asset = Asset.objects.get(id=asset_id)
            self._update_overview_from_asset(asset)
        except Asset.DoesNotExist:
            pass  # Asset not found, skip
    
    def _update_overview(self, event: DomainEvent):
        """Update overview when asset state changes"""
        asset_id = event.aggregate_id
        
        try:
            asset = Asset.objects.get(id=asset_id)
            self._update_overview_from_asset(asset)
        except Asset.DoesNotExist:
            pass
    
    def _update_control_summary(self, event: DomainEvent):
        """Update control summary when control is assigned"""
        asset_id = uuid.UUID(event.payload.get("asset_id"))
        
        try:
            asset = Asset.objects.get(id=asset_id)
            self._update_overview_from_asset(asset)
        except Asset.DoesNotExist:
            pass
    
    def _update_risk_summary(self, event: DomainEvent):
        """Update risk summary when risk is assigned"""
        asset_id = uuid.UUID(event.payload.get("asset_id"))
        
        try:
            asset = Asset.objects.get(id=asset_id)
            self._update_overview_from_asset(asset)
        except Asset.DoesNotExist:
            pass
    
    def _update_service_summary(self, event: DomainEvent):
        """Update service summary when service is linked"""
        asset_id = uuid.UUID(event.payload.get("asset_id"))
        
        try:
            asset = Asset.objects.get(id=asset_id)
            self._update_overview_from_asset(asset)
        except Asset.DoesNotExist:
            pass
    
    def _update_overview_from_asset(self, asset: Asset):
        """Update overview from asset aggregate"""
        # Note: ControlImplementation and Risk aggregates would be queried here
        # For now, we'll just update counts
        
        AssetOverview.objects.update_or_create(
            asset_id=asset.id,
            defaults={
                "name": asset.name,
                "ref_id": asset.ref_id,
                "asset_type": asset.asset_type,
                "lifecycle_state": asset.lifecycle_state,
                "control_count": len(asset.controlIds),
                "risk_count": len(asset.riskIds),
                "third_party_count": len(asset.thirdPartyIds),
                "service_count": len(asset.serviceIds),
                # Status summaries would be populated from related aggregates
                "control_implementation_status_summary": {},
                "risk_residual_score_summary": {},
                "third_party_contract_status_summary": {},
                "third_party_assessment_status_summary": {},
                "service_status_summary": {},
            }
        )

