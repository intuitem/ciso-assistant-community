"""
Domain Events for RMF Operations Bounded Context
"""

from core.domain.events import DomainEvent


# SystemGroup Events
class SystemGroupCreated(DomainEvent):
    """Raised when a system group is created"""
    pass


class SystemGroupActivated(DomainEvent):
    """Raised when a system group is activated"""
    pass


class SystemGroupArchived(DomainEvent):
    """Raised when a system group is archived"""
    pass


class SystemGroupComplianceChecked(DomainEvent):
    """Raised when a system group compliance is verified"""
    pass


# Nessus Scan Events
class NessusScanUploaded(DomainEvent):
    """Raised when a Nessus scan file is uploaded"""
    pass


class NessusScanProcessingStarted(DomainEvent):
    """Raised when Nessus scan processing begins"""
    pass


class NessusScanProcessingCompleted(DomainEvent):
    """Raised when Nessus scan processing completes successfully"""
    pass


class NessusScanProcessingFailed(DomainEvent):
    """Raised when Nessus scan processing fails"""
    pass


class NessusScanChecklistCorrelated(DomainEvent):
    """Raised when a Nessus scan is correlated with a checklist"""
    pass


# STIG Template Events
class StigTemplateCreated(DomainEvent):
    """Raised when a STIG template is created"""
    pass


class StigTemplateUpdated(DomainEvent):
    """Raised when a STIG template is updated"""
    pass


class StigTemplateActivated(DomainEvent):
    """Raised when a STIG template is activated"""
    pass


class StigTemplateDeactivated(DomainEvent):
    """Raised when a STIG template is deactivated"""
    pass


# Artifact Events
class ArtifactCreated(DomainEvent):
    """Raised when an artifact is created"""
    pass


class ArtifactMetadataUpdated(DomainEvent):
    """Raised when artifact metadata is updated"""
    pass


class ArtifactRelationshipAdded(DomainEvent):
    """Raised when artifact relationships are added"""
    pass


class ArtifactCCIAdded(DomainEvent):
    """Raised when CCI reference is added to artifact"""
    pass


class ArtifactSecurityUpdated(DomainEvent):
    """Raised when artifact security level is updated"""
    pass


class ArtifactDeactivated(DomainEvent):
    """Raised when artifact is deactivated"""
    pass


class ChecklistAddedToSystem(DomainEvent):
    """Raised when a checklist is added to a system group"""
    pass


class AssetAddedToSystem(DomainEvent):
    """Raised when an asset is added to a system group"""
    pass


# StigChecklist Events
class StigChecklistCreated(DomainEvent):
    """Raised when a STIG checklist is created"""
    pass


class StigChecklistImported(DomainEvent):
    """Raised when a STIG checklist is imported from CKL file"""
    pass


class StigChecklistExported(DomainEvent):
    """Raised when a STIG checklist is exported to CKL file"""
    pass


class StigChecklistActivated(DomainEvent):
    """Raised when a STIG checklist is activated"""
    pass


class StigChecklistArchived(DomainEvent):
    """Raised when a STIG checklist is archived"""
    pass


# VulnerabilityFinding Events
class VulnerabilityFindingCreated(DomainEvent):
    """Raised when a vulnerability finding is created"""
    pass


class VulnerabilityFindingStatusChanged(DomainEvent):
    """Raised when a vulnerability finding status changes"""
    pass


class VulnerabilityFindingSeverityOverridden(DomainEvent):
    """Raised when a vulnerability finding severity is overridden"""
    pass


class VulnerabilityFindingsBulkUpdated(DomainEvent):
    """Raised when multiple vulnerability findings are bulk updated"""
    pass


# ChecklistScore Events
class ChecklistScoreCalculated(DomainEvent):
    """Raised when a checklist score is calculated"""
    pass


class ChecklistScoreUpdated(DomainEvent):
    """Raised when a checklist score is updated"""
    pass


class SystemScoreAggregated(DomainEvent):
    """Raised when a system-level score is aggregated"""
    pass


# Additional Events
class ChecklistCreatedFromTemplate(DomainEvent):
    """Raised when a checklist is created from a template"""
    pass

