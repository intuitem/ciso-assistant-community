"""
Privacy Projections for read models and event handling
"""

from typing import List
from core.domain.events import DomainEvent
from ..models.domain_events import *


class PrivacyProjectionHandler:
    """Handles domain events and updates privacy-related read models"""

    def __init__(self):
        self.event_handlers = {
            DataAssetCreated: self.handle_data_asset_created,
            DataAssetClassificationUpdated: self.handle_data_asset_updated,
            ConsentRecordCreated: self.handle_consent_created,
            ConsentRecordWithdrawn: self.handle_consent_withdrawn,
            DataSubjectRightRequested: self.handle_dsr_requested,
            DataSubjectRightCompleted: self.handle_dsr_completed,
        }

    def handle(self, event: DomainEvent):
        """Handle a domain event"""
        event_type = type(event)
        if event_type in self.event_handlers:
            self.event_handlers[event_type](event)

    def handle_data_asset_created(self, event: DataAssetCreated):
        """Handle data asset creation"""
        pass

    def handle_data_asset_updated(self, event: DataAssetClassificationUpdated):
        """Handle data asset updates"""
        pass

    def handle_consent_created(self, event: ConsentRecordCreated):
        """Handle consent creation"""
        pass

    def handle_consent_withdrawn(self, event: ConsentRecordWithdrawn):
        """Handle consent withdrawal"""
        pass

    def handle_dsr_requested(self, event: DataSubjectRightRequested):
        """Handle DSR request"""
        pass

    def handle_dsr_completed(self, event: DataSubjectRightCompleted):
        """Handle DSR completion"""
        pass


def register_projections(event_bus):
    """Register projection handlers with the event bus"""
    handler = PrivacyProjectionHandler()

    # Data Asset Events
    event_bus.subscribe("DataAssetCreated", handler)
    event_bus.subscribe("DataAssetClassificationUpdated", handler)
    event_bus.subscribe("DataAssetProcessingUpdated", handler)
    event_bus.subscribe("DataAssetPIACompleted", handler)
    event_bus.subscribe("DataAssetAudited", handler)
    event_bus.subscribe("DataAssetComplianceUpdated", handler)

    # Consent Record Events
    event_bus.subscribe("ConsentRecordCreated", handler)
    event_bus.subscribe("ConsentRecordUpdated", handler)
    event_bus.subscribe("ConsentRecordWithdrawn", handler)
    event_bus.subscribe("ConsentRecordExpired", handler)

    # Data Subject Right Events
    event_bus.subscribe("DataSubjectRightRequested", handler)
    event_bus.subscribe("DataSubjectRightProcessed", handler)
    event_bus.subscribe("DataSubjectRightCompleted", handler)
    event_bus.subscribe("DataSubjectRightRejected", handler)
