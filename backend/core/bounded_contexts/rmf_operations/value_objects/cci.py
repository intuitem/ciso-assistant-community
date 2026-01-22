"""
CCI (Common Control Identifier) Value Object

Represents Common Control Identifiers used in RMF for mapping
controls to technical implementations and assessments.
"""

from typing import Optional, List, Dict, Any
from core.domain.value_object import ValueObject


class CCI(ValueObject):
    """
    Common Control Identifier value object.

    CCIs provide a standardized way to identify and reference
    security control implementations across different frameworks.
    """

    def __init__(self, cci_id: str, definition: Optional[str] = None,
                 control_mappings: Optional[List[str]] = None):
        """
        Initialize CCI value object.

        Args:
            cci_id: The CCI identifier (e.g., "CCI-000001")
            definition: Human-readable definition
            control_mappings: List of control mappings (e.g., ["AC-2", "AC-3"])
        """
        if not self._is_valid_cci_format(cci_id):
            raise ValueError(f"Invalid CCI format: {cci_id}. Expected format: CCI-XXXXXX")

        self.cci_id = cci_id.upper()
        self.definition = definition
        self.control_mappings = control_mappings or []

    @staticmethod
    def _is_valid_cci_format(cci_id: str) -> bool:
        """Validate CCI ID format (CCI-XXXXXX)"""
        import re
        return bool(re.match(r'^CCI-\d{6}$', cci_id.upper()))

    def add_control_mapping(self, control_id: str):
        """Add a control mapping"""
        if control_id not in self.control_mappings:
            self.control_mappings.append(control_id)

    def remove_control_mapping(self, control_id: str):
        """Remove a control mapping"""
        if control_id in self.control_mappings:
            self.control_mappings.remove(control_id)

    def has_control_mapping(self, control_id: str) -> bool:
        """Check if CCI maps to a specific control"""
        return control_id in self.control_mappings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'cci_id': self.cci_id,
            'definition': self.definition,
            'control_mappings': self.control_mappings.copy()
        }

    def __str__(self):
        return f"CCI({self.cci_id})"

    def __eq__(self, other):
        if not isinstance(other, CCI):
            return False
        return self.cci_id == other.cci_id

    def __hash__(self):
        return hash(self.cci_id)
