"""
Domain Events for Compliance Bounded Context
"""

from core.domain.events import DomainEvent


# ComplianceFramework Events
class ComplianceFrameworkCreated(DomainEvent):
    """Raised when a compliance framework is created"""
    pass


class ComplianceFrameworkActivated(DomainEvent):
    """Raised when a compliance framework is activated"""
    pass


class ComplianceFrameworkRetired(DomainEvent):
    """Raised when a compliance framework is retired"""
    pass


# Requirement Events
class RequirementCreated(DomainEvent):
    """Raised when a requirement is created"""
    pass


class RequirementMappedToControl(DomainEvent):
    """Raised when a requirement is mapped to a control"""
    pass


class RequirementRetired(DomainEvent):
    """Raised when a requirement is retired"""
    pass


# OnlineAssessment Events
class OnlineAssessmentCreated(DomainEvent):
    """Raised when an online assessment is created"""
    pass


class OnlineAssessmentPublished(DomainEvent):
    """Raised when an online assessment is published"""
    pass


class OnlineAssessmentRetired(DomainEvent):
    """Raised when an online assessment is retired"""
    pass


# AssessmentRun Events
class AssessmentRunInvited(DomainEvent):
    """Raised when users are invited to an assessment run"""
    pass


class AssessmentRunStarted(DomainEvent):
    """Raised when an assessment run is started"""
    pass


class AssessmentRunSubmitted(DomainEvent):
    """Raised when an assessment run is submitted"""
    pass


class AssessmentRunReviewed(DomainEvent):
    """Raised when an assessment run is reviewed"""
    pass


class AssessmentRunClosed(DomainEvent):
    """Raised when an assessment run is closed"""
    pass


# ComplianceAudit Events
class ComplianceAuditCreated(DomainEvent):
    """Raised when a compliance audit is created"""
    pass


class ComplianceAuditStarted(DomainEvent):
    """Raised when a compliance audit is started"""
    pass


class ComplianceAuditCompleted(DomainEvent):
    """Raised when a compliance audit is completed"""
    pass


class ComplianceAuditClosed(DomainEvent):
    """Raised when a compliance audit is closed"""
    pass


# ComplianceFinding Events
class ComplianceFindingCreated(DomainEvent):
    """Raised when a compliance finding is created"""
    pass


class ComplianceFindingStatusChanged(DomainEvent):
    """Raised when a compliance finding status changes"""
    pass


# ComplianceException Events
class ComplianceExceptionRequested(DomainEvent):
    """Raised when a compliance exception is requested"""
    pass


class ComplianceExceptionApproved(DomainEvent):
    """Raised when a compliance exception is approved"""
    pass


class ComplianceExceptionExpired(DomainEvent):
    """Raised when a compliance exception expires"""
    pass


class ComplianceExceptionRevoked(DomainEvent):
    """Raised when a compliance exception is revoked"""
    pass

