"""
Domain Events for Control Library Bounded Context
"""

from core.domain.events import DomainEvent


# Framework Events
class FrameworkCreated(DomainEvent):
    """Raised when a framework is created"""
    pass


class FrameworkPublished(DomainEvent):
    """Raised when a framework is published"""
    pass


class FrameworkDeprecated(DomainEvent):
    """Raised when a framework is deprecated"""
    pass


class FrameworkStructureUpdated(DomainEvent):
    """Raised when framework structure is updated"""
    pass


class FrameworkMappingAdded(DomainEvent):
    """Raised when framework mapping is added"""
    pass


class FrameworkRelationshipAdded(DomainEvent):
    """Raised when framework relationship is added"""
    pass


class FrameworkReviewScheduled(DomainEvent):
    """Raised when framework review is scheduled"""
    pass


class FrameworkReviewed(DomainEvent):
    """Raised when framework is reviewed"""
    pass


# Control Events
class ControlCreated(DomainEvent):
    """Raised when a control is created"""
    pass


class ControlContentUpdated(DomainEvent):
    """Raised when control content is updated"""
    pass


class ControlEnhancementAdded(DomainEvent):
    """Raised when control enhancement is added"""
    pass


class ControlMappingAdded(DomainEvent):
    """Raised when control mapping is added"""
    pass


class ControlRelationshipAdded(DomainEvent):
    """Raised when control relationship is added"""
    pass


class ControlPriorityUpdated(DomainEvent):
    """Raised when control priority is updated"""
    pass


class ControlDeprecated(DomainEvent):
    """Raised when control is deprecated"""
    pass


# Control Implementation Events
class ControlImplementationCreated(DomainEvent):
    """Raised when control implementation is created"""
    pass


class ControlImplementationUpdated(DomainEvent):
    """Raised when control implementation is updated"""
    pass


class ControlImplementationStatusChanged(DomainEvent):
    """Raised when control implementation status changes"""
    pass


class ControlImplementationEvidenceAdded(DomainEvent):
    """Raised when evidence is added to control implementation"""
    pass


class ControlImplementationAssessed(DomainEvent):
    """Raised when control implementation is assessed"""
    pass


class ControlImplementationExceptionRequested(DomainEvent):
    """Raised when exception is requested for control implementation"""
    pass


class ControlImplementationExceptionApproved(DomainEvent):
    """Raised when exception is approved for control implementation"""
    pass


class ControlImplementationExceptionRejected(DomainEvent):
    """Raised when exception is rejected for control implementation"""
    pass


class ControlImplementationReviewScheduled(DomainEvent):
    """Raised when review is scheduled for control implementation"""
    pass


class ControlImplementationReviewed(DomainEvent):
    """Raised when control implementation is reviewed"""
    pass


class ControlImplementationMonitoringUpdated(DomainEvent):
    """Raised when monitoring is updated for control implementation"""
    pass


# Evidence Events
class EvidenceCreated(DomainEvent):
    """Raised when evidence is created"""
    pass


class EvidenceUpdated(DomainEvent):
    """Raised when evidence is updated"""
    pass


class EvidenceReviewed(DomainEvent):
    """Raised when evidence is reviewed"""
    pass


class EvidenceDeprecated(DomainEvent):
    """Raised when evidence is deprecated"""
    pass
