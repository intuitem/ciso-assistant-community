"""
Domain Events for Privacy Bounded Context
"""

from core.domain.events import DomainEvent


# DataAsset Events
class DataAssetCreated(DomainEvent):
    """Raised when a data asset is created"""
    pass


class DataAssetActivated(DomainEvent):
    """Raised when a data asset is activated"""
    pass


class DataAssetRetired(DomainEvent):
    """Raised when a data asset is retired"""
    pass


# DataFlow Events
class DataFlowEstablished(DomainEvent):
    """Raised when a data flow is established"""
    pass


class DataFlowChanged(DomainEvent):
    """Raised when a data flow changes"""
    pass


class DataFlowActivated(DomainEvent):
    """Raised when a data flow is activated"""
    pass


class DataFlowRetired(DomainEvent):
    """Raised when a data flow is retired"""
    pass

