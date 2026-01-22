"""
Domain Events for Risk Registers Bounded Context
"""

from core.domain.events import DomainEvent


# AssetRisk Events
class AssetRiskCreated(DomainEvent):
    """Raised when an asset risk is created"""
    pass


class AssetRiskAssessed(DomainEvent):
    """Raised when an asset risk is assessed"""
    pass


class AssetRiskTreated(DomainEvent):
    """Raised when an asset risk is treated"""
    pass


class AssetRiskAccepted(DomainEvent):
    """Raised when an asset risk is accepted"""
    pass


class AssetRiskClosed(DomainEvent):
    """Raised when an asset risk is closed"""
    pass


# ThirdPartyRisk Events
class ThirdPartyRiskCreated(DomainEvent):
    """Raised when a third party risk is created"""
    pass


class ThirdPartyRiskAssessed(DomainEvent):
    """Raised when a third party risk is assessed"""
    pass


class ThirdPartyRiskTreated(DomainEvent):
    """Raised when a third party risk is treated"""
    pass


class ThirdPartyRiskAccepted(DomainEvent):
    """Raised when a third party risk is accepted"""
    pass


class ThirdPartyRiskClosed(DomainEvent):
    """Raised when a third party risk is closed"""
    pass


# BusinessRisk Events
class BusinessRiskCreated(DomainEvent):
    """Raised when a business risk is created"""
    pass


class BusinessRiskAssessed(DomainEvent):
    """Raised when a business risk is assessed"""
    pass


class BusinessRiskTreated(DomainEvent):
    """Raised when a business risk is treated"""
    pass


class BusinessRiskAccepted(DomainEvent):
    """Raised when a business risk is accepted"""
    pass


class BusinessRiskClosed(DomainEvent):
    """Raised when a business risk is closed"""
    pass


# RiskException Events
class RiskExceptionRequested(DomainEvent):
    """Raised when a risk exception is requested"""
    pass


class RiskExceptionApproved(DomainEvent):
    """Raised when a risk exception is approved"""
    pass


class RiskExceptionExpired(DomainEvent):
    """Raised when a risk exception expires"""
    pass


class RiskExceptionRevoked(DomainEvent):
    """Raised when a risk exception is revoked"""
    pass


# RiskTreatmentPlan Events
class RiskTreatmentPlanCreated(DomainEvent):
    """Raised when a risk treatment plan is created"""
    pass


class RiskTreatmentPlanActivated(DomainEvent):
    """Raised when a risk treatment plan is activated"""
    pass


class RiskTreatmentPlanCompleted(DomainEvent):
    """Raised when a risk treatment plan is completed"""
    pass


class RiskTreatmentPlanAbandoned(DomainEvent):
    """Raised when a risk treatment plan is abandoned"""
    pass

