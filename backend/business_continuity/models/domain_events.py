"""
Domain Events for Business Continuity Bounded Context
"""

from core.domain.events import DomainEvent


# BCP Plan Events
class BCPPlanCreated(DomainEvent):
    """Raised when BCP plan is created"""
    pass


class BCPPlanBIACompleted(DomainEvent):
    """Raised when Business Impact Analysis is completed"""
    pass


class BCPPlanRecoveryObjectivesDefined(DomainEvent):
    """Raised when recovery objectives are defined"""
    pass


class BCPPlanStrategiesDeveloped(DomainEvent):
    """Raised when recovery strategies are developed"""
    pass


class BCPPlanApproved(DomainEvent):
    """Raised when plan is approved"""
    pass


class BCPPlanActivated(DomainEvent):
    """Raised when plan is activated"""
    pass


class BCPPlanTested(DomainEvent):
    """Raised when plan is tested"""
    pass


class BCPPlanReviewed(DomainEvent):
    """Raised when plan is reviewed"""
    pass


# BCP Test Events
class BCPTestCreated(DomainEvent):
    """Raised when BCP test is created"""
    pass


class BCPTestExecuted(DomainEvent):
    """Raised when test is executed"""
    pass


class BCPTestCompleted(DomainEvent):
    """Raised when test is completed"""
    pass
