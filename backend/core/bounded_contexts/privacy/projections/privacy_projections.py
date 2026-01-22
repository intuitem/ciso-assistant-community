"""
Privacy Projection Handlers

Update read models based on Privacy domain events.
"""

from core.domain.events import EventHandler, DomainEvent
from ..read_models.privacy_overview import PrivacyOverview
from ..aggregates.data_asset import DataAsset
from ..aggregates.data_flow import DataFlow


class PrivacyProjectionHandler(EventHandler):
    """
    Handler that updates PrivacyOverview read model from domain events.
    
    This handler listens to privacy-related domain events and updates
    the denormalized PrivacyOverview read model for efficient querying.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        # Update overview for any privacy-related event
        self._update_overview()
    
    def _update_overview(self):
        """Update privacy overview"""
        # Get all data assets
        data_assets = DataAsset.objects.all()
        total_data_assets = data_assets.count()
        active_data_assets = sum(
            1 for da in data_assets if da.lifecycle_state == "active"
        )
        data_assets_with_personal_data = sum(
            1 for da in data_assets if da.contains_personal_data
        )
        
        # Get all data flows
        data_flows = DataFlow.objects.all()
        total_data_flows = data_flows.count()
        active_data_flows = sum(
            1 for df in data_flows if df.lifecycle_state == "active"
        )
        flows_without_encryption = sum(
            1 for df in data_flows if df.encryption_in_transit is False
        )
        
        # Privacy risks would come from RiskRegisters context
        # For now, set to 0 or query from that context if needed
        total_privacy_risks = 0
        open_privacy_risks = 0
        
        # Update or create the overview record
        PrivacyOverview.objects.update_or_create(
            id__isnull=False,  # Use a single record
            defaults={
                "total_data_assets": total_data_assets,
                "active_data_assets": active_data_assets,
                "data_assets_with_personal_data": data_assets_with_personal_data,
                "total_data_flows": total_data_flows,
                "active_data_flows": active_data_flows,
                "flows_without_encryption": flows_without_encryption,
                "total_privacy_risks": total_privacy_risks,
                "open_privacy_risks": open_privacy_risks,
            }
        )

