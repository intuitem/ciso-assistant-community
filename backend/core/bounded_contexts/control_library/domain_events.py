"""
Domain Events for Control Library Bounded Context
"""

from core.domain.events import DomainEvent


# Control Events
class ControlCreated(DomainEvent):
    """Raised when a control is created"""
    pass


class ControlApproved(DomainEvent):
    """Raised when a control is approved"""
    pass


class ControlDeprecated(DomainEvent):
    """Raised when a control is deprecated"""
    pass


# Policy Events
class PolicyCreated(DomainEvent):
    """Raised when a policy is created"""
    pass


class PolicyPublished(DomainEvent):
    """Raised when a policy is published"""
    pass


class PolicyRetired(DomainEvent):
    """Raised when a policy is retired"""
    pass


# EvidenceItem Events
class EvidenceCollected(DomainEvent):
    """Raised when evidence is collected"""
    pass


class EvidenceVerified(DomainEvent):
    """Raised when evidence is verified"""
    pass


class EvidenceExpired(DomainEvent):
    """Raised when evidence expires"""
    pass


# ControlImplementation Events
class ControlImplementationCreated(DomainEvent):
    """Raised when a control implementation is created"""
    pass


class ControlImplementationStatusChanged(DomainEvent):
    """Raised when a control implementation status changes"""
    pass


class ControlImplementationTested(DomainEvent):
    """Raised when a control implementation is tested"""
    pass


# PolicyAcknowledgement Events
class PolicyAcknowledged(DomainEvent):
    """Raised when a policy is acknowledged by a user"""
    pass

