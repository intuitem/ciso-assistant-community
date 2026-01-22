"""
Risk Projection Handlers

Update read models based on Risk domain events.
"""

from core.domain.events import EventHandler, DomainEvent
from ..read_models.risk_register_overview import RiskRegisterOverview
from ..aggregates.asset_risk import AssetRisk
from ..aggregates.third_party_risk import ThirdPartyRisk
from ..aggregates.business_risk import BusinessRisk


class RiskProjectionHandler(EventHandler):
    """
    Handler that updates RiskRegisterOverview read model from domain events.
    
    This handler listens to all risk-related domain events and updates
    the denormalized RiskRegisterOverview read model for efficient querying.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        # Determine which risk type this event belongs to
        if event_type.startswith("AssetRisk"):
            self._update_overview("asset")
        elif event_type.startswith("ThirdPartyRisk"):
            self._update_overview("third_party")
        elif event_type.startswith("BusinessRisk"):
            self._update_overview("business")
    
    def _update_overview(self, risk_type: str):
        """
        Update overview for a specific risk type.
        
        Args:
            risk_type: One of 'asset', 'third_party', or 'business'
        """
        # Get the appropriate model class
        if risk_type == "asset":
            RiskModel = AssetRisk
        elif risk_type == "third_party":
            RiskModel = ThirdPartyRisk
        elif risk_type == "business":
            RiskModel = BusinessRisk
        else:
            return
        
        # Fetch all risks of this type
        risks = list(RiskModel.objects.all())
        
        # Count by lifecycle state
        draft_count = sum(1 for r in risks if r.lifecycle_state == "draft")
        assessed_count = sum(1 for r in risks if r.lifecycle_state == "assessed")
        treated_count = sum(1 for r in risks if r.lifecycle_state == "treated")
        accepted_count = sum(1 for r in risks if r.lifecycle_state == "accepted")
        closed_count = sum(1 for r in risks if r.lifecycle_state == "closed")
        
        # Calculate average scores (only for risks that have been assessed)
        inherent_scores = [
            r.scoring.get("inherent_score", 0)
            for r in risks
            if r.scoring and r.scoring.get("inherent_score")
        ]
        residual_scores = [
            r.scoring.get("residual_score", 0)
            for r in risks
            if r.scoring and r.scoring.get("residual_score")
        ]
        
        avg_inherent = sum(inherent_scores) / len(inherent_scores) if inherent_scores else None
        avg_residual = sum(residual_scores) / len(residual_scores) if residual_scores else None
        
        # Update or create the overview record
        RiskRegisterOverview.objects.update_or_create(
            risk_type=risk_type,
            defaults={
                "draft_count": draft_count,
                "assessed_count": assessed_count,
                "treated_count": treated_count,
                "accepted_count": accepted_count,
                "closed_count": closed_count,
                "average_inherent_score": avg_inherent,
                "average_residual_score": avg_residual,
            }
        )

