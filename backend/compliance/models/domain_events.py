"""
Domain Events for Compliance Bounded Context
"""

from core.domain.events import DomainEvent


# Compliance Assessment Events
class ComplianceAssessmentCreated(DomainEvent):
    """Raised when a compliance assessment is created"""
    pass


class ComplianceAssessmentStarted(DomainEvent):
    """Raised when a compliance assessment is started"""
    pass


class ComplianceAssessmentProgressUpdated(DomainEvent):
    """Raised when assessment progress is updated"""
    pass


class ComplianceAssessmentRequirementAdded(DomainEvent):
    """Raised when a requirement is added to assessment"""
    pass


class ComplianceAssessmentControlAdded(DomainEvent):
    """Raised when a control is added to assessment"""
    pass


class ComplianceAssessmentFindingAdded(DomainEvent):
    """Raised when a finding is added to assessment"""
    pass


class ComplianceAssessmentExceptionAdded(DomainEvent):
    """Raised when an exception is added to assessment"""
    pass


class ComplianceAssessmentSubmittedForApproval(DomainEvent):
    """Raised when assessment is submitted for approval"""
    pass


class ComplianceAssessmentApproved(DomainEvent):
    """Raised when assessment is approved"""
    pass


class ComplianceAssessmentCompleted(DomainEvent):
    """Raised when assessment is completed"""
    pass


class ComplianceAssessmentReviewed(DomainEvent):
    """Raised when assessment is reviewed"""
    pass


class ComplianceAssessmentCertificationUpdated(DomainEvent):
    """Raised when certification status is updated"""
    pass


# Requirement Assessment Events
class RequirementAssessmentCreated(DomainEvent):
    """Raised when a requirement assessment is created"""
    pass


class RequirementAssessmentUpdated(DomainEvent):
    """Raised when requirement assessment is updated"""
    pass


class RequirementAssessmentStatusChanged(DomainEvent):
    """Raised when requirement assessment status changes"""
    pass


class RequirementAssessmentEvidenceAdded(DomainEvent):
    """Raised when evidence is added to requirement assessment"""
    pass


class RequirementAssessmentApproved(DomainEvent):
    """Raised when requirement assessment is approved"""
    pass


# Compliance Finding Events
class ComplianceFindingCreated(DomainEvent):
    """Raised when a compliance finding is created"""
    pass


class ComplianceFindingUpdated(DomainEvent):
    """Raised when finding is updated"""
    pass


class ComplianceFindingStatusChanged(DomainEvent):
    """Raised when finding status changes"""
    pass


class ComplianceFindingRemediated(DomainEvent):
    """Raised when finding is remediated"""
    pass


class ComplianceFindingClosed(DomainEvent):
    """Raised when finding is closed"""
    pass


# Compliance Exception Events
class ComplianceExceptionCreated(DomainEvent):
    """Raised when a compliance exception is created"""
    pass


class ComplianceExceptionUpdated(DomainEvent):
    """Raised when exception is updated"""
    pass


class ComplianceExceptionApproved(DomainEvent):
    """Raised when exception is approved"""
    pass


class ComplianceExceptionRejected(DomainEvent):
    """Raised when exception is rejected"""
    pass


class ComplianceExceptionExpired(DomainEvent):
    """Raised when exception expires"""
    pass


class ComplianceExceptionExtended(DomainEvent):
    """Raised when exception is extended"""
    pass
