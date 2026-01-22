"""
Domain Events for Asset and Service Bounded Context
"""

from core.domain.events import DomainEvent


# Asset Events
class AssetCreated(DomainEvent):
    """Raised when an asset is created"""
    pass


class AssetDeployed(DomainEvent):
    """Raised when an asset is deployed"""
    pass


class AssetActivated(DomainEvent):
    """Raised when an asset is activated"""
    pass


class AssetDecommissioned(DomainEvent):
    """Raised when an asset is decommissioned"""
    pass


class AssetDisposed(DomainEvent):
    """Raised when an asset is disposed"""
    pass


class AssetCriticalityUpdated(DomainEvent):
    """Raised when asset criticality is updated"""
    pass


class AssetRelationshipAdded(DomainEvent):
    """Raised when an asset relationship is added"""
    pass


class AssetRelationshipRemoved(DomainEvent):
    """Raised when an asset relationship is removed"""
    pass


class AssetMaintenanceScheduled(DomainEvent):
    """Raised when asset maintenance is scheduled"""
    pass


class AssetMaintenanceCompleted(DomainEvent):
    """Raised when asset maintenance is completed"""
    pass


class AssetRiskUpdated(DomainEvent):
    """Raised when asset risk is updated"""
    pass


class AssetOwnershipTransferred(DomainEvent):
    """Raised when asset ownership is transferred"""
    pass


class AssetServiceDependencyAdded(DomainEvent):
    """Raised when a service dependency is added to an asset"""
    pass


# Service Events
class ServiceCreated(DomainEvent):
    """Raised when a service is created"""
    pass


class ServiceActivated(DomainEvent):
    """Raised when a service is activated"""
    pass


class ServiceStatusUpdated(DomainEvent):
    """Raised when service status is updated"""
    pass


class ServiceDependencyAdded(DomainEvent):
    """Raised when a service dependency is added"""
    pass


class ServiceDependencyRemoved(DomainEvent):
    """Raised when a service dependency is removed"""
    pass


class ServiceMetricsUpdated(DomainEvent):
    """Raised when service metrics are updated"""
    pass


class ServiceIncidentRecorded(DomainEvent):
    """Raised when a service incident is recorded"""
    pass


class ServiceIncidentResolved(DomainEvent):
    """Raised when a service incident is resolved"""
    pass


class ServiceChangeScheduled(DomainEvent):
    """Raised when a service change is scheduled"""
    pass


class ServiceChangeStatusUpdated(DomainEvent):
    """Raised when service change status is updated"""
    pass


class ServiceSLAUpdated(DomainEvent):
    """Raised when service SLA is updated"""
    pass


class ServiceOwnershipTransferred(DomainEvent):
    """Raised when service ownership is transferred"""
    pass


class ServiceReviewScheduled(DomainEvent):
    """Raised when service review is scheduled"""
    pass


class ServiceReviewed(DomainEvent):
    """Raised when service is reviewed"""
    pass
