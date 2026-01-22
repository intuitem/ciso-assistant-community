"""
Example Aggregate Implementation

This file demonstrates how to create aggregates using the DDD infrastructure.
Use this as a reference when creating your own aggregates.
"""

from django.db import models
from core.domain.aggregate import AggregateRoot
from core.domain.events import DomainEvent
from core.domain.fields import EmbeddedIdArrayField
from core.domain.value_object import ValueObject
from dataclasses import dataclass
import uuid


# Domain Events
class AssetCreated(DomainEvent):
    """Event raised when an asset is created"""
    pass


class ControlAssignedToAsset(DomainEvent):
    """Event raised when a control is assigned to an asset"""
    pass


class AssetArchived(DomainEvent):
    """Event raised when an asset is archived"""
    pass


# Value Objects
@dataclass(frozen=True)
class AssetClassification(ValueObject):
    """Asset classification value object"""
    confidentiality: int  # 1-5
    integrity: int  # 1-5
    availability: int  # 1-5
    
    @property
    def cia_score(self) -> int:
        """Calculate CIA score"""
        return self.confidentiality + self.integrity + self.availability


# Aggregate Root
class Asset(AggregateRoot):
    """
    Asset aggregate root example.
    
    This demonstrates:
    - Using AggregateRoot base class
    - Embedded ID arrays for relationships
    - Raising domain events
    - Lifecycle management
    """
    
    # Basic fields
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle state
    LIFECYCLE_CHOICES = [
        ("draft", "Draft"),
        ("in_use", "In Use"),
        ("archived", "Archived"),
    ]
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LIFECYCLE_CHOICES,
        default="draft"
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    controlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control IDs"
    )
    riskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of risk IDs"
    )
    ownerUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of owner user IDs"
    )
    
    # Classification (stored as JSON, used as ValueObject)
    classification = models.JSONField(null=True, blank=True)
    
    class Meta:
        app_label = "core"
        db_table = "example_assets"
    
    def create(self, name: str, description: str = None):
        """
        Create a new asset.
        
        This is a domain method that enforces business rules
        and raises domain events.
        """
        self.name = name
        self.description = description
        self.lifecycle_state = "draft"
        
        # Raise domain event
        self._raise_event(AssetCreated(
            payload={
                "name": name,
                "description": description,
            }
        ))
    
    def assign_control(self, control_id: uuid.UUID):
        """
        Assign a control to this asset.
        
        Args:
            control_id: UUID of the control to assign
        """
        if control_id not in self.controlIds:
            self.controlIds.append(control_id)
            
            # Raise domain event
            self._raise_event(ControlAssignedToAsset(
                payload={
                    "asset_id": str(self.id),
                    "control_id": str(control_id),
                }
            ))
    
    def archive(self):
        """
        Archive this asset.
        
        This changes the lifecycle state and raises an event.
        """
        if self.lifecycle_state != "archived":
            self.lifecycle_state = "archived"
            
            # Raise domain event
            self._raise_event(AssetArchived(
                payload={
                    "asset_id": str(self.id),
                    "name": self.name,
                }
            ))
    
    def set_classification(self, classification: AssetClassification):
        """
        Set the asset classification.
        
        Args:
            classification: AssetClassification value object
        """
        self.classification = classification.to_dict()
    
    def get_classification(self) -> AssetClassification:
        """Get the asset classification as a value object"""
        if self.classification:
            return AssetClassification.from_dict(self.classification)
        return None


# Repository Example
from core.domain.repository import Repository


class AssetRepository(Repository[Asset]):
    """Repository for Asset aggregates"""
    
    def __init__(self):
        super().__init__(Asset)
    
    def find_by_name(self, name: str) -> Asset:
        """Find asset by name"""
        return Asset.objects.filter(name=name).first()
    
    def find_by_control(self, control_id: uuid.UUID) -> list[Asset]:
        """Find all assets with a specific control"""
        return list(
            Asset.objects.filter(controlIds__contains=[control_id])
        )
    
    def find_active(self) -> list[Asset]:
        """Find all active (non-archived) assets"""
        return list(
            Asset.objects.filter(lifecycle_state="in_use")
        )


# Event Handler Example
from core.domain.events import EventHandler, get_event_bus


class AssetCreatedHandler(EventHandler):
    """
    Handler for AssetCreated events.
    
    This could update read models, send notifications, etc.
    """
    
    def handle(self, event: DomainEvent):
        """Handle AssetCreated event"""
        # Example: Update read model
        # Example: Send notification
        # Example: Log to audit trail
        print(f"Asset created: {event.payload.get('name')}")


# Register handler (typically done in app startup)
def register_event_handlers():
    """Register all event handlers"""
    event_bus = get_event_bus()
    event_bus.subscribe("AssetCreated", AssetCreatedHandler())

