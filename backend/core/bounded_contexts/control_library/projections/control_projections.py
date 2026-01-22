"""
Control Projection Handlers

Update read models based on Control domain events.
"""

import uuid
from core.domain.events import EventHandler, DomainEvent
from ..read_models.control_overview import ControlOverview
from ..aggregates.control import Control
from ..associations.control_implementation import ControlImplementation


class ControlProjectionHandler(EventHandler):
    """
    Handler that updates ControlOverview read model from domain events.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        if event_type == "ControlCreated":
            self._create_overview(event)
        elif event_type == "ControlApproved":
            self._update_overview(event)
        elif event_type == "ControlDeprecated":
            self._update_overview(event)
        elif event_type == "ControlImplementationCreated":
            self._update_implementation_summary(event)
        elif event_type == "ControlImplementationStatusChanged":
            self._update_implementation_summary(event)
    
    def _create_overview(self, event: DomainEvent):
        """Create overview when control is created"""
        control_id = event.aggregate_id
        
        try:
            control = Control.objects.get(id=control_id)
            self._update_overview_from_control(control)
        except Control.DoesNotExist:
            pass  # Control not found, skip
    
    def _update_overview(self, event: DomainEvent):
        """Update overview when control state changes"""
        control_id = event.aggregate_id
        
        try:
            control = Control.objects.get(id=control_id)
            self._update_overview_from_control(control)
        except Control.DoesNotExist:
            pass
    
    def _update_implementation_summary(self, event: DomainEvent):
        """Update implementation summary when implementation changes"""
        control_id = uuid.UUID(event.payload.get("control_id"))
        
        try:
            control = Control.objects.get(id=control_id)
            self._update_overview_from_control(control)
        except (Control.DoesNotExist, KeyError):
            pass
    
    def _update_overview_from_control(self, control: Control):
        """Update overview from control aggregate"""
        # Get implementation counts by status
        implementations = ControlImplementation.objects.filter(controlId=control.id)
        implementation_count = implementations.count()
        
        # Build status summary
        status_summary = {}
        for impl in implementations:
            state = impl.lifecycle_state
            status_summary[state] = status_summary.get(state, 0) + 1
        
        ControlOverview.objects.update_or_create(
            control_id=control.id,
            defaults={
                "name": control.name,
                "ref_id": control.ref_id,
                "control_type": control.control_type,
                "lifecycle_state": control.lifecycle_state,
                "implementation_count": implementation_count,
                "implementation_status_summary": status_summary,
                "related_control_count": len(control.relatedControlIds),
                "legal_requirement_count": len(control.legalRequirementIds),
                # Evidence count would need to query ControlImplementation.evidenceIds
                "evidence_count": 0,
            }
        )

