"""
CCI (Common Control Identifier) Management Service

Service for managing Common Control Identifiers and their mappings
to RMF controls and technical implementations.
"""

import json
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

from .cci import CCI

logger = logging.getLogger(__name__)


class CCIService:
    """
    Service for CCI management and control mapping.

    Provides CCI definitions, control mappings, and validation
    for RMF compliance activities.
    """

    def __init__(self):
        """Initialize CCI service"""
        self.cci_definitions: Dict[str, CCI] = {}
        self.control_to_ccis: Dict[str, Set[str]] = {}
        self.cci_to_controls: Dict[str, Set[str]] = {}
        self._loaded = False

    def load_cci_definitions(self, cci_data_file: Optional[str] = None):
        """
        Load CCI definitions from data file.

        Args:
            cci_data_file: Path to CCI data file (JSON format)
        """
        if self._loaded:
            return

        # Default CCI data file (would be part of the application data)
        if not cci_data_file:
            cci_data_file = Path(__file__).parent / "data" / "cci_definitions.json"

        try:
            with open(cci_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for cci_data in data.get('cci_definitions', []):
                cci = CCI(
                    cci_id=cci_data['cci_id'],
                    definition=cci_data.get('definition'),
                    control_mappings=cci_data.get('control_mappings', [])
                )
                self.cci_definitions[cci.cci_id] = cci

                # Build reverse mappings
                for control in cci.control_mappings:
                    if control not in self.control_to_ccis:
                        self.control_to_ccis[control] = set()
                    self.control_to_ccis[control].add(cci.cci_id)

                    if cci.cci_id not in self.cci_to_controls:
                        self.cci_to_controls[cci.cci_id] = set()
                    self.cci_to_controls[cci.cci_id].add(control)

            self._loaded = True
            logger.info(f"Loaded {len(self.cci_definitions)} CCI definitions")

        except FileNotFoundError:
            logger.warning(f"CCI data file not found: {cci_data_file}")
            # Load minimal default definitions
            self._load_default_definitions()
        except Exception as e:
            logger.error(f"Error loading CCI definitions: {e}")
            self._load_default_definitions()

    def _load_default_definitions(self):
        """Load minimal default CCI definitions for basic functionality"""
        # Sample CCI definitions (in practice, this would be much more comprehensive)
        default_ccis = [
            {
                'cci_id': 'CCI-000001',
                'definition': 'The information system enforces approved authorizations for logical access to information and system resources in accordance with applicable access control policies.',
                'control_mappings': ['AC-2', 'AC-3', 'AC-4']
            },
            {
                'cci_id': 'CCI-000002',
                'definition': 'The information system uniquely identifies and authenticates organizational users (or processes acting on behalf of organizational users).',
                'control_mappings': ['IA-2', 'IA-3']
            },
            {
                'cci_id': 'CCI-000003',
                'definition': 'The information system enforces discretionary access control policies over defined subjects and objects.',
                'control_mappings': ['AC-3', 'AC-4']
            }
        ]

        for cci_data in default_ccis:
            cci = CCI(**cci_data)
            self.cci_definitions[cci.cci_id] = cci

            for control in cci.control_mappings:
                if control not in self.control_to_ccis:
                    self.control_to_ccis[control] = set()
                self.control_to_ccis[control].add(cci.cci_id)

                if cci.cci_id not in self.cci_to_controls:
                    self.cci_to_controls[cci.cci_id] = set()
                self.cci_to_controls[cci.cci_id].add(control)

        self._loaded = True
        logger.info(f"Loaded {len(self.cci_definitions)} default CCI definitions")

    def get_cci(self, cci_id: str) -> Optional[CCI]:
        """Get CCI definition by ID"""
        if not self._loaded:
            self.load_cci_definitions()
        return self.cci_definitions.get(cci_id.upper())

    def get_ccis_for_control(self, control_id: str) -> List[CCI]:
        """Get all CCIs mapped to a specific control"""
        if not self._loaded:
            self.load_cci_definitions()

        cci_ids = self.control_to_ccis.get(control_id.upper(), set())
        return [self.cci_definitions[cci_id] for cci_id in cci_ids if cci_id in self.cci_definitions]

    def get_controls_for_cci(self, cci_id: str) -> List[str]:
        """Get all controls mapped to a specific CCI"""
        if not self._loaded:
            self.load_cci_definitions()

        return list(self.cci_to_controls.get(cci_id.upper(), set()))

    def validate_cci_id(self, cci_id: str) -> bool:
        """Validate CCI ID format and existence"""
        if not CCI._is_valid_cci_format(cci_id):
            return False

        if not self._loaded:
            self.load_cci_definitions()

        return cci_id.upper() in self.cci_definitions

    def search_ccis(self, query: str, limit: int = 50) -> List[CCI]:
        """Search CCI definitions by text"""
        if not self._loaded:
            self.load_cci_definitions()

        query_lower = query.lower()
        matches = []

        for cci in self.cci_definitions.values():
            if (query_lower in cci.cci_id.lower() or
                (cci.definition and query_lower in cci.definition.lower())):
                matches.append(cci)
                if len(matches) >= limit:
                    break

        return matches

    def get_all_controls(self) -> List[str]:
        """Get list of all controls that have CCI mappings"""
        if not self._loaded:
            self.load_cci_definitions()
        return sorted(self.control_to_ccis.keys())

    def get_cci_statistics(self) -> Dict[str, int]:
        """Get CCI mapping statistics"""
        if not self._loaded:
            self.load_cci_definitions()

        return {
            'total_ccis': len(self.cci_definitions),
            'total_controls': len(self.control_to_ccis),
            'total_mappings': sum(len(ccis) for ccis in self.control_to_ccis.values())
        }

    def validate_control_mappings(self, cci_list: List[str], control_id: str) -> Dict[str, Any]:
        """
        Validate CCI to control mappings.

        Args:
            cci_list: List of CCI IDs to validate
            control_id: Control ID to validate against

        Returns:
            Validation result with valid/invalid CCIs
        """
        if not self._loaded:
            self.load_cci_definitions()

        valid_ccis = []
        invalid_ccis = []
        expected_ccis = set(self.control_to_ccis.get(control_id.upper(), set()))

        for cci_id in cci_list:
            if not self.validate_cci_id(cci_id):
                invalid_ccis.append({
                    'cci_id': cci_id,
                    'reason': 'Invalid CCI format or not found'
                })
            elif cci_id.upper() not in expected_ccis:
                invalid_ccis.append({
                    'cci_id': cci_id,
                    'reason': f'CCI not mapped to control {control_id}'
                })
            else:
                valid_ccis.append(cci_id.upper())

        return {
            'valid_ccis': valid_ccis,
            'invalid_ccis': invalid_ccis,
            'expected_ccis': list(expected_ccis),
            'is_valid': len(invalid_ccis) == 0
        }

    def get_cci_hierarchy(self, control_id: str) -> Dict[str, Any]:
        """Get CCI hierarchy for a control (for advanced compliance reporting)"""
        if not self._loaded:
            self.load_cci_definitions()

        ccis = self.get_ccis_for_control(control_id)
        return {
            'control_id': control_id,
            'cci_count': len(ccis),
            'ccis': [cci.to_dict() for cci in ccis],
            'categories': self._categorize_ccis(ccis)
        }

    def _categorize_ccis(self, ccis: List[CCI]) -> Dict[str, List[CCI]]:
        """Categorize CCIs by control family"""
        categories = {}

        for cci in ccis:
            for control in cci.control_mappings:
                # Extract control family (e.g., "AC" from "AC-2")
                family = control.split('-')[0] if '-' in control else 'OTHER'
                if family not in categories:
                    categories[family] = []
                categories[family].append(cci)

        return categories

    def export_cci_data(self, format: str = 'json') -> str:
        """Export CCI data in specified format"""
        if not self._loaded:
            self.load_cci_definitions()

        if format.lower() == 'json':
            data = {
                'cci_definitions': [cci.to_dict() for cci in self.cci_definitions.values()],
                'control_mappings': {control: list(ccis) for control, ccis in self.control_to_ccis.items()},
                'statistics': self.get_cci_statistics()
            }
            return json.dumps(data, indent=2)

        # Could add other formats (CSV, XML) as needed
        raise ValueError(f"Unsupported export format: {format}")


# Global CCI service instance
cci_service = CCIService()
