"""
Domain Events for Security Operations Bounded Context
"""

from core.domain.events import DomainEvent


# Security Incident Events
class SecurityIncidentCreated(DomainEvent):
    """Raised when a security incident is created"""
    pass


class SecurityIncidentAssigned(DomainEvent):
    """Raised when incident is assigned to analyst"""
    pass


class SecurityIncidentStatusUpdated(DomainEvent):
    """Raised when incident status is updated"""
    pass


class SecurityIncidentContained(DomainEvent):
    """Raised when incident is contained"""
    pass


class SecurityIncidentEradicated(DomainEvent):
    """Raised when threat is eradicated"""
    pass


class SecurityIncidentRecovered(DomainEvent):
    """Raised when recovery is completed"""
    pass


class SecurityIncidentResolved(DomainEvent):
    """Raised when incident is resolved"""
    pass


class SecurityIncidentClosed(DomainEvent):
    """Raised when incident is closed"""
    pass


class SecurityIncidentImpactAssessed(DomainEvent):
    """Raised when incident impact is assessed"""
    pass


class SecurityIncidentRootCauseAnalyzed(DomainEvent):
    """Raised when root cause analysis is completed"""
    pass


# Awareness Program Events
class AwarenessProgramCreated(DomainEvent):
    """Raised when awareness program is created"""
    pass


class AwarenessProgramActivated(DomainEvent):
    """Raised when program is activated"""
    pass


class AwarenessProgramCompleted(DomainEvent):
    """Raised when program is completed"""
    pass


# Security Training Events
class SecurityTrainingCreated(DomainEvent):
    """Raised when training is created"""
    pass


class SecurityTrainingAssigned(DomainEvent):
    """Raised when training is assigned"""
    pass


class SecurityTrainingCompleted(DomainEvent):
    """Raised when training is completed"""
    pass


# Vulnerability Scan Events
class VulnerabilityScanCreated(DomainEvent):
    """Raised when scan is created"""
    pass


class VulnerabilityScanExecuted(DomainEvent):
    """Raised when scan is executed"""
    pass


class VulnerabilityScanCompleted(DomainEvent):
    """Raised when scan is completed"""
    pass
