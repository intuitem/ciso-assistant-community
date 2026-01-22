"""
Domain Events for ThirdPartyManagement Bounded Context
"""

from core.domain.events import DomainEvent


# ThirdParty Events
class ThirdPartyCreated(DomainEvent):
    """Raised when a third party is created"""
    pass


class ThirdPartyActivated(DomainEvent):
    """Raised when a third party is activated"""
    pass


class ThirdPartyOffboardingStarted(DomainEvent):
    """Raised when offboarding of a third party is started"""
    pass


class ThirdPartyArchived(DomainEvent):
    """Raised when a third party is archived"""
    pass


class ThirdPartyLifecycleChanged(DomainEvent):
    """Raised when a third party lifecycle state changes"""
    pass

