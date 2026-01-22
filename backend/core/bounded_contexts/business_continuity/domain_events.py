"""
Domain Events for BusinessContinuity Bounded Context
"""

from core.domain.events import DomainEvent


# BusinessContinuityPlan Events
class BusinessContinuityPlanCreated(DomainEvent):
    """Raised when a BCP is created"""
    pass


class BusinessContinuityPlanApproved(DomainEvent):
    """Raised when a BCP is approved"""
    pass


class BusinessContinuityPlanExercised(DomainEvent):
    """Raised when a BCP is exercised (tested)"""
    pass


class BusinessContinuityPlanRetired(DomainEvent):
    """Raised when a BCP is retired"""
    pass


# BcpTask Events
class BcpTaskCreated(DomainEvent):
    """Raised when a BCP task is created"""
    pass


class BcpTaskStatusChanged(DomainEvent):
    """Raised when a BCP task status changes"""
    pass


# BcpAudit Events
class BcpAuditCreated(DomainEvent):
    """Raised when a BCP audit is created"""
    pass


class BcpAuditCompleted(DomainEvent):
    """Raised when a BCP audit is completed"""
    pass

