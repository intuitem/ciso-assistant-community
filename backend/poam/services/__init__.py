"""
POA&M Services

This module provides services for Plan of Action and Milestones (POA&M) management:
- POAMExportService: Export POA&M data in various formats (FedRAMP XLSX, CSV, OSCAL)
"""


def __getattr__(name):
    """Lazy import to avoid circular dependencies and optional dependency issues"""
    if name == 'POAMExportService':
        from backend.poam.services.poam_export import POAMExportService
        return POAMExportService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'POAMExportService',
]
