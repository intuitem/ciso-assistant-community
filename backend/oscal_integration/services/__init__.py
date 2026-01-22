"""
OSCAL Integration Services

This module provides services for OSCAL document manipulation:
- OSCALImporter: Import OSCAL documents (catalog, profile, SSP, etc.)
- OSCALExporter: Export data to OSCAL format
- SSPGenerator: Generate System Security Plans
- SSPImporter: Import existing SSPs
- FedRAMPValidator: Validate FedRAMP compliance
- TrestleService: OSCAL operations (split/merge, profile resolution, format conversion)
- FedRAMPEnhancedService: Enhanced FedRAMP features (control origination, responsible roles)
- OpenControlConverter: Convert between OpenControl and OSCAL formats
"""


def __getattr__(name):
    """Lazy import to avoid circular dependencies and optional dependency issues"""
    if name == 'OSCALImporter':
        from backend.oscal_integration.services.oscal_importer import OSCALImporter
        return OSCALImporter
    elif name == 'OSCALExporter':
        from backend.oscal_integration.services.oscal_exporter import OSCALExporter
        return OSCALExporter
    elif name == 'SSPGenerator':
        from backend.oscal_integration.services.ssp_generator import SSPGenerator
        return SSPGenerator
    elif name == 'SSPImporter':
        from backend.oscal_integration.services.ssp_importer import SSPImporter
        return SSPImporter
    elif name == 'FedRAMPValidator':
        from backend.oscal_integration.services.fedramp_validator import FedRAMPValidator
        return FedRAMPValidator
    elif name == 'TrestleService':
        from backend.oscal_integration.services.trestle_service import TrestleService
        return TrestleService
    elif name == 'FedRAMPEnhancedService':
        from backend.oscal_integration.services.fedramp_enhanced import FedRAMPEnhancedService
        return FedRAMPEnhancedService
    elif name == 'OpenControlConverter':
        from backend.oscal_integration.services.opencontrol_converter import OpenControlConverter
        return OpenControlConverter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'OSCALImporter',
    'OSCALExporter',
    'SSPGenerator',
    'SSPImporter',
    'FedRAMPValidator',
    'TrestleService',
    'FedRAMPEnhancedService',
    'OpenControlConverter',
]
