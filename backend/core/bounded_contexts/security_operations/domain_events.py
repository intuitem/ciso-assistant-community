"""
Domain Events for SecurityOperations Bounded Context
"""

from core.domain.events import DomainEvent


# SecurityIncident Events
class SecurityIncidentReported(DomainEvent):
    """Raised when a security incident is reported"""
    pass


class SecurityIncidentTriaged(DomainEvent):
    """Raised when a security incident is triaged"""
    pass


class SecurityIncidentContained(DomainEvent):
    """Raised when a security incident is contained"""
    pass


class SecurityIncidentEradicated(DomainEvent):
    """Raised when a security incident is eradicated"""
    pass


class SecurityIncidentRecovered(DomainEvent):
    """Raised when recovery from a security incident is complete"""
    pass


class SecurityIncidentClosed(DomainEvent):
    """Raised when a security incident is closed"""
    pass


# AwarenessProgram Events
class AwarenessProgramCreated(DomainEvent):
    """Raised when an awareness program is created"""
    pass


class AwarenessProgramActivated(DomainEvent):
    """Raised when an awareness program is activated"""
    pass


class AwarenessProgramPaused(DomainEvent):
    """Raised when an awareness program is paused"""
    pass


class AwarenessProgramRetired(DomainEvent):
    """Raised when an awareness program is retired"""
    pass


# AwarenessCampaign Events
class AwarenessCampaignCreated(DomainEvent):
    """Raised when an awareness campaign is created"""
    pass


class AwarenessCampaignStarted(DomainEvent):
    """Raised when an awareness campaign is started"""
    pass


class AwarenessCampaignCompleted(DomainEvent):
    """Raised when an awareness campaign is completed"""
    pass


class AwarenessCampaignCancelled(DomainEvent):
    """Raised when an awareness campaign is cancelled"""
    pass


# AwarenessCompletion Events
class AwarenessCompletionRecorded(DomainEvent):
    """Raised when a user completes an awareness activity"""
    pass

