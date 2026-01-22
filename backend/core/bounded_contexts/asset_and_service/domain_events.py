"""
Domain Events for Asset and Service Bounded Context
"""

from core.domain.events import DomainEvent


# Asset Events
class AssetCreated(DomainEvent):
    """Raised when an asset is created"""
    pass


class AssetActivated(DomainEvent):
    """Raised when an asset is activated (moved to InUse)"""
    pass


class AssetArchived(DomainEvent):
    """Raised when an asset is archived"""
    pass


class ControlAssignedToAsset(DomainEvent):
    """Raised when a control is assigned to an asset"""
    pass


class RiskAssignedToAsset(DomainEvent):
    """Raised when a risk is assigned to an asset"""
    pass


class ServiceLinkedToAsset(DomainEvent):
    """Raised when a service is linked to an asset"""
    pass


# Service Events
class ServiceCreated(DomainEvent):
    """Raised when a service is created"""
    pass


class ServiceOperational(DomainEvent):
    """Raised when a service becomes operational"""
    pass


class ServiceRetired(DomainEvent):
    """Raised when a service is retired"""
    pass


# Process Events
class ProcessCreated(DomainEvent):
    """Raised when a process is created"""
    pass


class ProcessActivated(DomainEvent):
    """Raised when a process is activated"""
    pass


class ProcessRetired(DomainEvent):
    """Raised when a process is retired"""
    pass


# ServiceContract Events
class ServiceContractEstablished(DomainEvent):
    """Raised when a service contract is established"""
    pass


class ServiceContractRenewed(DomainEvent):
    """Raised when a service contract is renewed"""
    pass


class ServiceContractExpired(DomainEvent):
    """Raised when a service contract expires"""
    pass

