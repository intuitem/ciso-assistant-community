"""
Domain Events for Risk Registers Bounded Context
"""

from core.domain.events import DomainEvent


# Asset Risk Events
class AssetRiskCreated(DomainEvent):
    """Raised when an asset risk is created"""
    pass


class AssetRiskAssessmentUpdated(DomainEvent):
    """Raised when asset risk assessment is updated"""
    pass


class AssetRiskTreatmentPlanDefined(DomainEvent):
    """Raised when asset risk treatment plan is defined"""
    pass


class AssetRiskTreatmentImplemented(DomainEvent):
    """Raised when asset risk treatment is implemented"""
    pass


class AssetRiskResidualUpdated(DomainEvent):
    """Raised when asset risk residual is updated"""
    pass


class AssetRiskMilestoneAdded(DomainEvent):
    """Raised when asset risk milestone is added"""
    pass


class AssetRiskMilestoneUpdated(DomainEvent):
    """Raised when asset risk milestone is updated"""
    pass


class AssetRiskReviewed(DomainEvent):
    """Raised when asset risk is reviewed"""
    pass


class AssetRiskOwnerAssigned(DomainEvent):
    """Raised when asset risk owner is assigned"""
    pass


# Third Party Risk Events
class ThirdPartyRiskCreated(DomainEvent):
    """Raised when a third party risk is created"""
    pass


class ThirdPartyRiskAssessmentUpdated(DomainEvent):
    """Raised when third party risk assessment is updated"""
    pass


class ThirdPartyRiskTreatmentPlanDefined(DomainEvent):
    """Raised when third party risk treatment plan is defined"""
    pass


class ThirdPartyRiskTreatmentImplemented(DomainEvent):
    """Raised when third party risk treatment is implemented"""
    pass


class ThirdPartyRiskResidualUpdated(DomainEvent):
    """Raised when third party risk residual is updated"""
    pass


class ThirdPartyRiskReviewed(DomainEvent):
    """Raised when third party risk is reviewed"""
    pass


class ThirdPartyRiskOwnerAssigned(DomainEvent):
    """Raised when third party risk owner is assigned"""
    pass


# Business Risk Events
class BusinessRiskCreated(DomainEvent):
    """Raised when a business risk is created"""
    pass


class BusinessRiskAssessmentUpdated(DomainEvent):
    """Raised when business risk assessment is updated"""
    pass


class BusinessRiskTreatmentPlanDefined(DomainEvent):
    """Raised when business risk treatment plan is defined"""
    pass


class BusinessRiskTreatmentImplemented(DomainEvent):
    """Raised when business risk treatment is implemented"""
    pass


class BusinessRiskResidualUpdated(DomainEvent):
    """Raised when business risk residual is updated"""
    pass


class BusinessRiskReviewed(DomainEvent):
    """Raised when business risk is reviewed"""
    pass


class BusinessRiskOwnerAssigned(DomainEvent):
    """Raised when business risk owner is assigned"""
    pass


# Risk Scenario Events
class RiskScenarioCreated(DomainEvent):
    """Raised when a risk scenario is created"""
    pass


class RiskScenarioUpdated(DomainEvent):
    """Raised when risk scenario is updated"""
    pass


class RiskScenarioExecuted(DomainEvent):
    """Raised when risk scenario is executed"""
    pass


class RiskScenarioResultsAnalyzed(DomainEvent):
    """Raised when risk scenario results are analyzed"""
    pass


# Risk Register Events
class RiskRegisterCreated(DomainEvent):
    """Raised when a risk register is created"""
    pass


class RiskRegisterUpdated(DomainEvent):
    """Raised when risk register is updated"""
    pass


class RiskRegisterConsolidated(DomainEvent):
    """Raised when risk register is consolidated"""
    pass


class RiskRegisterReported(DomainEvent):
    """Raised when risk register report is generated"""
    pass
