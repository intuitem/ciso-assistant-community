"""
ThirdParty Projection Handlers

Update read models based on ThirdParty domain events.
"""

from core.domain.events import EventHandler, DomainEvent
from ..read_models.third_party_posture import ThirdPartyPosture
from ..aggregates.third_party import ThirdParty


class ThirdPartyProjectionHandler(EventHandler):
    """
    Handler that updates ThirdPartyPosture read model from domain events.
    
    This handler listens to third party-related domain events and updates
    the denormalized ThirdPartyPosture read model for efficient querying.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        # Determine which third party this event relates to
        third_party_id = None
        
        if event_type.startswith("ThirdParty"):
            third_party_id = event.aggregate_id
        
        if third_party_id:
            self._update_posture(third_party_id)
    
    def _update_posture(self, third_party_id):
        """
        Update third party posture for a specific third party.
        
        Args:
            third_party_id: UUID of the third party
        """
        try:
            third_party = ThirdParty.objects.get(id=third_party_id)
        except ThirdParty.DoesNotExist:
            return
        
        # Get contracts (would need to query from AssetAndService context)
        # For now, count from embedded arrays
        active_contracts = len(third_party.contractIds)  # Simplified
        expired_contracts = 0  # Would need to query contract status
        
        # Get assessments (would need to query from Compliance context)
        total_assessments = len(third_party.assessmentRunIds)
        latest_assessment_date = None  # Would need to query assessment dates
        open_findings_count = 0  # Would need to query from Compliance context
        
        # Get risks (would need to query from RiskRegisters context)
        open_risks = len(third_party.riskIds)  # Simplified
        critical_risks = 0  # Would need to query risk severity
        
        # Get exceptions (would need to query from Compliance context)
        active_exceptions = 0  # Would need to query from Compliance context
        
        # Update or create the posture record
        ThirdPartyPosture.objects.update_or_create(
            third_party_id=third_party_id,
            defaults={
                "third_party_name": third_party.name,
                "criticality": third_party.criticality,
                "active_contracts_count": active_contracts,
                "expired_contracts_count": expired_contracts,
                "total_assessments": total_assessments,
                "latest_assessment_date": latest_assessment_date,
                "open_findings_count": open_findings_count,
                "open_risks_count": open_risks,
                "critical_risks_count": critical_risks,
                "active_exceptions_count": active_exceptions,
            }
        )

