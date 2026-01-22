"""
Domain Events for POAM Bounded Context
"""

from core.domain.events import DomainEvent


# POAM Item Events
class POAMItemCreated(DomainEvent):
    """Raised when a POA&M item is created"""
    pass


class POAMItemSubmitted(DomainEvent):
    """Raised when a POA&M item is submitted for approval"""
    pass


class POAMItemApproved(DomainEvent):
    """Raised when a POA&M item is approved"""
    pass


class POAMItemRejected(DomainEvent):
    """Raised when a POA&M item is rejected"""
    pass


# Remediation Events
class POAMRemediationStarted(DomainEvent):
    """Raised when remediation work begins"""
    pass


class POAMRemediationCompleted(DomainEvent):
    """Raised when remediation is completed"""
    pass


# Milestone Events
class POAMMilestoneAdded(DomainEvent):
    """Raised when a milestone is added"""
    pass


class POAMMilestoneUpdated(DomainEvent):
    """Raised when a milestone status is updated"""
    pass


# Deviation Events
class POAMDeviationRequested(DomainEvent):
    """Raised when a deviation is requested"""
    pass


class POAMDeviationApproved(DomainEvent):
    """Raised when a deviation is approved"""
    pass


# Evidence Events
class POAMEvidenceAdded(DomainEvent):
    """Raised when evidence is added"""
    pass


# Review Events
class POAMReviewScheduled(DomainEvent):
    """Raised when a review is scheduled"""
    pass


class POAMItemReviewed(DomainEvent):
    """Raised when a POA&M item is reviewed"""
    pass
