"""
Domain Events for Third Party Management Bounded Context
"""

from core.domain.events import DomainEvent


# Third Party Entity Events
class ThirdPartyEntityCreated(DomainEvent):
    """Raised when third party entity is created"""
    pass


class ThirdPartyEntityActivated(DomainEvent):
    """Raised when entity is activated"""
    pass


class ThirdPartyEntityRiskAssessed(DomainEvent):
    """Raised when risk assessment is completed"""
    pass


class ThirdPartyEntityComplianceUpdated(DomainEvent):
    """Raised when compliance status is updated"""
    pass


class ThirdPartyEntityOwnerAssigned(DomainEvent):
    """Raised when owner is assigned"""
    pass


class ThirdPartyEntityReviewed(DomainEvent):
    """Raised when entity is reviewed"""
    pass


class ThirdPartyEntityTerminated(DomainEvent):
    """Raised when relationship is terminated"""
    pass


# Third Party Contract Events
class ThirdPartyContractCreated(DomainEvent):
    """Raised when contract is created"""
    pass


class ThirdPartyContractSigned(DomainEvent):
    """Raised when contract is signed"""
    pass


class ThirdPartyContractRenewed(DomainEvent):
    """Raised when contract is renewed"""
    pass


# Third Party Assessment Events
class ThirdPartyAssessmentCreated(DomainEvent):
    """Raised when assessment is created"""
    pass


class ThirdPartyAssessmentCompleted(DomainEvent):
    """Raised when assessment is completed"""
    pass
