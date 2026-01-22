"""
OSCAL Exporter Service

Service for exporting CISO Assistant data to OSCAL (Open Security Controls Assessment Language) formats.
Converts CISO Assistant entities to OSCAL JSON structures.
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)


class OSCALExporter:
    """
    Exports CISO Assistant data to OSCAL formats.

    Supports multiple OSCAL formats:
    - System Security Plan (SSP)
    - Catalog
    - Profile
    - Assessment Plan
    - Assessment Results
    - Plan of Action and Milestones (POA&M)
    """

    def __init__(self):
        """Initialize OSCAL exporter"""
        self.oscal_version = "1.1.2"  # Current OSCAL version

    def export_compliance_assessment(self, assessment_id: uuid.UUID) -> str:
        """
        Export ComplianceAssessment to OSCAL SSP format.

        Args:
            assessment_id: UUID of the compliance assessment

        Returns:
            OSCAL SSP JSON string
        """
        # Get assessment data from repository
        assessment_data = self._get_assessment_data(assessment_id)

        ssp_data = {
            "oscal-version": self.oscal_version,
            "metadata": self._create_metadata(assessment_data),
            "system-security-plan": {
                "uuid": str(uuid.uuid4()),
                "metadata": self._create_ssp_metadata(assessment_data),
                "import-profile": self._create_import_profile(assessment_data),
                "system-characteristics": self._create_system_characteristics(assessment_data),
                "system-implementation": self._create_system_implementation(assessment_data),
                "control-implementation": self._create_control_implementation(assessment_data)
            }
        }

        # Add optional sections if data exists
        if assessment_data.get('assessment_results'):
            ssp_data["system-security-plan"]["assessment-results"] = self._create_assessment_results(assessment_data)

        if assessment_data.get('plan_of_actions'):
            ssp_data["system-security-plan"]["plan-of-action-and-milestones"] = self._create_plan_of_actions(assessment_data)

        return json.dumps(ssp_data, indent=2)

    def export_framework_as_catalog(self, framework_id: uuid.UUID) -> str:
        """
        Export Framework to OSCAL Catalog format.

        Args:
            framework_id: UUID of the framework

        Returns:
            OSCAL Catalog JSON string
        """
        framework_data = self._get_framework_data(framework_id)

        catalog_data = {
            "oscal-version": self.oscal_version,
            "metadata": self._create_metadata(framework_data),
            "catalog": {
                "uuid": str(uuid.uuid4()),
                "metadata": self._create_catalog_metadata(framework_data),
                "groups": self._create_catalog_groups(framework_data),
                "controls": self._create_catalog_controls(framework_data)
            }
        }

        return json.dumps(catalog_data, indent=2)

    def export_assessment_plan(self, assessment_id: uuid.UUID) -> str:
        """
        Export ComplianceAssessment to OSCAL Assessment Plan format.

        Args:
            assessment_id: UUID of the compliance assessment

        Returns:
            OSCAL Assessment Plan JSON string
        """
        assessment_data = self._get_assessment_data(assessment_id)

        plan_data = {
            "oscal-version": self.oscal_version,
            "metadata": self._create_metadata(assessment_data),
            "assessment-plan": {
                "uuid": str(uuid.uuid4()),
                "metadata": self._create_plan_metadata(assessment_data),
                "import-ssp": self._create_import_ssp(assessment_data),
                "reviewed-controls": self._create_reviewed_controls(assessment_data),
                "assessment-subjects": self._create_assessment_subjects(assessment_data),
                "assessment-assets": self._create_assessment_assets(assessment_data),
                "assessment-activities": self._create_assessment_activities(assessment_data)
            }
        }

        return json.dumps(plan_data, indent=2)

    def export_assessment_results(self, assessment_id: uuid.UUID) -> str:
        """
        Export ComplianceAssessment results to OSCAL Assessment Results format.

        Args:
            assessment_id: UUID of the compliance assessment

        Returns:
            OSCAL Assessment Results JSON string
        """
        assessment_data = self._get_assessment_data(assessment_id)

        results_data = {
            "oscal-version": self.oscal_version,
            "metadata": self._create_metadata(assessment_data),
            "assessment-results": {
                "uuid": str(uuid.uuid4()),
                "metadata": self._create_results_metadata(assessment_data),
                "import-ap": self._create_import_ap(assessment_data),
                "results": self._create_results(assessment_data)
            }
        }

        return json.dumps(results_data, indent=2)

    def export_poam(self, assessment_id: uuid.UUID) -> str:
        """
        Export findings and risks to OSCAL POA&M format.

        Args:
            assessment_id: UUID of the compliance assessment

        Returns:
            OSCAL POA&M JSON string
        """
        assessment_data = self._get_assessment_data(assessment_id)

        poam_data = {
            "oscal-version": self.oscal_version,
            "metadata": self._create_metadata(assessment_data),
            "plan-of-action-and-milestones": {
                "uuid": str(uuid.uuid4()),
                "metadata": self._create_poam_metadata(assessment_data),
                "import-ssp": self._create_import_ssp(assessment_data),
                "system-id": self._create_system_id(assessment_data),
                "observations": self._create_observations(assessment_data),
                "risks": self._create_risks(assessment_data),
                "poam-items": self._create_poam_items(assessment_data)
            }
        }

        return json.dumps(poam_data, indent=2)

    # Helper methods for data retrieval (placeholders - would connect to actual repositories)

    def _get_assessment_data(self, assessment_id: uuid.UUID) -> Dict[str, Any]:
        """Get compliance assessment data"""
        # Placeholder - would query actual repositories
        return {
            'id': assessment_id,
            'name': 'Sample Assessment',
            'framework': {'name': 'NIST SP 800-53', 'version': 'Rev. 5'},
            'organization': {'name': 'Sample Org'},
            'system': {'name': 'Sample System'},
            'controls': [],
            'findings': [],
            'assets': [],
            'created_at': timezone.now(),
            'updated_at': timezone.now()
        }

    def _get_framework_data(self, framework_id: uuid.UUID) -> Dict[str, Any]:
        """Get framework data"""
        # Placeholder - would query actual repositories
        return {
            'id': framework_id,
            'name': 'NIST SP 800-53',
            'version': 'Rev. 5',
            'controls': [],
            'created_at': timezone.now()
        }

    # OSCAL structure creation methods

    def _create_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create OSCAL metadata section"""
        return {
            "title": data.get('name', 'Exported from CISO Assistant'),
            "last-modified": data.get('updated_at', timezone.now()).isoformat(),
            "version": "1.0",
            "oscal-version": self.oscal_version,
            "parties": self._create_parties(data),
            "responsible-parties": self._create_responsible_parties(data)
        }

    def _create_ssp_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create SSP-specific metadata"""
        return {
            "title": f"System Security Plan for {data.get('system', {}).get('name', 'System')}",
            "published": data.get('created_at', timezone.now()).isoformat(),
            "last-modified": data.get('updated_at', timezone.now()).isoformat(),
            "version": "1.0"
        }

    def _create_catalog_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create catalog-specific metadata"""
        return {
            "title": f"Control Catalog: {data.get('name', 'Framework')}",
            "published": data.get('created_at', timezone.now()).isoformat(),
            "last-modified": timezone.now().isoformat(),
            "version": data.get('version', '1.0')
        }

    def _create_plan_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create assessment plan metadata"""
        return {
            "title": f"Assessment Plan for {data.get('name', 'Assessment')}",
            "published": timezone.now().isoformat(),
            "last-modified": timezone.now().isoformat(),
            "version": "1.0"
        }

    def _create_results_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create assessment results metadata"""
        return {
            "title": f"Assessment Results for {data.get('name', 'Assessment')}",
            "published": timezone.now().isoformat(),
            "last-modified": timezone.now().isoformat(),
            "version": "1.0"
        }

    def _create_poam_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create POA&M metadata"""
        return {
            "title": f"Plan of Action and Milestones for {data.get('name', 'Assessment')}",
            "published": timezone.now().isoformat(),
            "last-modified": timezone.now().isoformat(),
            "version": "1.0"
        }

    def _create_parties(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create OSCAL parties section"""
        return [
            {
                "uuid": str(uuid.uuid4()),
                "type": "organization",
                "name": data.get('organization', {}).get('name', 'Organization'),
                "email-addresses": [data.get('organization', {}).get('email', '')]
            }
        ]

    def _create_responsible_parties(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create OSCAL responsible parties section"""
        return {
            "system-owner": [
                {
                    "party-uuid": str(uuid.uuid4()),
                    "role-id": "system-owner"
                }
            ]
        }

    def _create_import_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create import-profile section"""
        return {
            "href": f"framework/{data.get('framework', {}).get('id', 'unknown')}",
            "remarks": f"Profile based on {data.get('framework', {}).get('name', 'Framework')}"
        }

    def _create_system_characteristics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create system characteristics section"""
        return {
            "system-ids": [
                {
                    "id": str(uuid.uuid4()),
                    "identifier-type": "https://ietf.org/rfc/rfc4122"
                }
            ],
            "system-name": data.get('system', {}).get('name', 'System'),
            "description": data.get('system', {}).get('description', ''),
            "security-sensitivity-level": "moderate",
            "system-information": {
                "information-types": []
            },
            "security-impact-level": {
                "security-objective-confidentiality": "moderate",
                "security-objective-integrity": "moderate",
                "security-objective-availability": "moderate"
            }
        }

    def _create_system_implementation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create system implementation section"""
        return {
            "users": [],
            "components": [],
            "inventory-items": []
        }

    def _create_control_implementation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create control implementation section"""
        return {
            "description": "Control implementations from CISO Assistant",
            "implemented-requirements": []
        }

    def _create_assessment_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assessment results section"""
        return []

    def _create_plan_of_actions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create plan of actions section"""
        return {
            "observations": [],
            "risks": [],
            "poam-items": []
        }

    def _create_catalog_groups(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create catalog groups section"""
        return []

    def _create_catalog_controls(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create catalog controls section"""
        return {}

    def _create_import_ssp(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create import-ssp section"""
        return {
            "href": f"assessment/{data.get('id', 'unknown')}",
            "remarks": "Reference to the system security plan"
        }

    def _create_reviewed_controls(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create reviewed controls section"""
        return {
            "control-selections": []
        }

    def _create_assessment_subjects(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assessment subjects section"""
        return []

    def _create_assessment_assets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create assessment assets section"""
        return {
            "assessment-assets": []
        }

    def _create_assessment_activities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assessment activities section"""
        return []

    def _create_import_ap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create import-ap section"""
        return {
            "href": f"assessment-plan/{data.get('id', 'unknown')}",
            "remarks": "Reference to the assessment plan"
        }

    def _create_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create results section"""
        return []

    def _create_system_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create system-id section"""
        return {
            "id": str(uuid.uuid4()),
            "identifier-type": "https://ietf.org/rfc/rfc4122"
        }

    def _create_observations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create observations section"""
        return []

    def _create_risks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create risks section"""
        return []

    def _create_poam_items(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create POA&M items section"""
        return []

    def validate_export(self, oscal_json: str) -> Dict[str, Any]:
        """
        Validate exported OSCAL JSON.

        Returns validation results.
        """
        try:
            data = json.loads(oscal_json)

            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'oscal_version': data.get('oscal-version', ''),
                'format_detected': None
            }

            # Detect format
            if 'system-security-plan' in data:
                validation_result['format_detected'] = 'system-security-plan'
            elif 'catalog' in data:
                validation_result['format_detected'] = 'catalog'
            elif 'assessment-plan' in data:
                validation_result['format_detected'] = 'assessment-plan'
            elif 'assessment-results' in data:
                validation_result['format_detected'] = 'assessment-results'
            elif 'plan-of-action-and-milestones' in data:
                validation_result['format_detected'] = 'plan-of-action-and-milestones'

            # Basic validation
            if not data.get('oscal-version'):
                validation_result['errors'].append("Missing oscal-version")
                validation_result['valid'] = False

            if not data.get('metadata'):
                validation_result['errors'].append("Missing metadata")
                validation_result['valid'] = False

            return validation_result

        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'errors': [f"Invalid JSON: {str(e)}"],
                'warnings': [],
                'oscal_version': '',
                'format_detected': None
            }
