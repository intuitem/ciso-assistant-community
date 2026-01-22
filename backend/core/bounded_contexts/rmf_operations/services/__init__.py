"""
RMF Operations Services

Services for CKL parsing, exporting, audit logging, and other RMF operations.
Enhanced with SCAP parsing, RMF document generation, and system scoring.
"""


def __getattr__(name):
    """Lazy import to avoid circular dependencies and optional dependency issues"""
    if name == 'CKLParser':
        from .ckl_parser import CKLParser
        return CKLParser
    elif name == 'CKLExporter':
        from .ckl_exporter import CKLExporter
        return CKLExporter
    elif name == 'BulkOperationsService':
        from .bulk_operations import BulkOperationsService
        return BulkOperationsService
    elif name == 'AuditService':
        from .audit_service import AuditService
        return AuditService
    elif name == 'audit_service':
        from .audit_service import audit_service
        return audit_service
    elif name == 'NessusParser':
        from .nessus_parser import NessusParser
        return NessusParser
    elif name == 'VulnerabilityCorrelationService':
        from .vulnerability_correlation import VulnerabilityCorrelationService
        return VulnerabilityCorrelationService
    elif name == 'SCAPParser':
        from .rmf_enhanced import SCAPParser
        return SCAPParser
    elif name == 'RMFDocumentGenerator':
        from .rmf_enhanced import RMFDocumentGenerator
        return RMFDocumentGenerator
    elif name == 'SystemScoringService':
        from .rmf_enhanced import SystemScoringService
        return SystemScoringService
    elif name == 'AssetMetadataService':
        from .rmf_enhanced import AssetMetadataService
        return AssetMetadataService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'CKLParser',
    'CKLExporter',
    'BulkOperationsService',
    'AuditService',
    'audit_service',
    'NessusParser',
    'VulnerabilityCorrelationService',
    'SCAPParser',
    'RMFDocumentGenerator',
    'SystemScoringService',
    'AssetMetadataService',
]