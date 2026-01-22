"""
OSCAL Importer Service

Service for importing OSCAL (Open Security Controls Assessment Language) files
into CISO Assistant. Handles SSP (System Security Plan) imports and converts
them to CISO Assistant entities.
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from django.utils import timezone
from compliance_trestle import oscal
from compliance_trestle.oscal import ssp, catalog, profile, assessment_plan, assessment_results, poam

logger = logging.getLogger(__name__)


class OSCALImporter:
    """
    Imports OSCAL files into CISO Assistant.

    Supports multiple OSCAL formats:
    - System Security Plan (SSP)
    - Catalog
    - Profile
    - Assessment Plan
    - Assessment Results
    - Plan of Action and Milestones (POA&M)
    """

    def __init__(self):
        """Initialize OSCAL importer"""
        self.supported_formats = [
            'system-security-plan',
            'catalog',
            'profile',
            'assessment-plan',
            'assessment-results',
            'plan-of-action-and-milestones'
        ]

    def detect_format(self, content: str) -> Optional[str]:
        """
        Detect OSCAL format from content.

        Returns format string or None if not recognized.
        """
        try:
            data = json.loads(content)
            oscal_version = data.get('oscal-version', '')
            if not oscal_version:
                return None

            # Check for specific OSCAL document types
            if 'system-security-plan' in data:
                return 'system-security-plan'
            elif 'catalog' in data:
                return 'catalog'
            elif 'profile' in data:
                return 'profile'
            elif 'assessment-plan' in data:
                return 'assessment-plan'
            elif 'assessment-results' in data:
                return 'assessment-results'
            elif 'plan-of-action-and-milestones' in data:
                return 'plan-of-action-and-milestones'

        except (json.JSONDecodeError, KeyError):
            pass

        return None

    def import_file(self, file_path: str, format_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Import OSCAL file and return structured data.

        Args:
            file_path: Path to OSCAL file (JSON)
            format_hint: Optional format hint

        Returns:
            Dict with import results and metadata
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            format_type = format_hint or self.detect_format(content)
            if not format_type:
                raise ValueError("Unable to detect OSCAL format")

            if format_type == 'system-security-plan':
                return self._import_ssp(content)
            elif format_type == 'catalog':
                return self._import_catalog(content)
            elif format_type == 'profile':
                return self._import_profile(content)
            elif format_type == 'assessment-plan':
                return self._import_assessment_plan(content)
            elif format_type == 'assessment-results':
                return self._import_assessment_results(content)
            elif format_type == 'plan-of-action-and-milestones':
                return self._import_poam(content)
            else:
                raise ValueError(f"Unsupported OSCAL format: {format_type}")

        except Exception as e:
            logger.error(f"Error importing OSCAL file {file_path}: {e}")
            raise

    def _import_ssp(self, content: str) -> Dict[str, Any]:
        """Import System Security Plan"""
        data = json.loads(content)

        ssp_data = {
            'metadata': self._extract_metadata(data),
            'system_characteristics': self._extract_system_characteristics(data),
            'control_implementations': self._extract_control_implementations(data),
            'assessment_results': self._extract_assessment_results(data),
            'plan_of_actions': self._extract_plan_of_actions(data),
            'back_matter': data.get('back-matter', {}),
            'import_info': {
                'format': 'system-security-plan',
                'oscal_version': data.get('oscal-version', ''),
                'imported_at': timezone.now().isoformat(),
                'control_count': len(data.get('control-implementation', {}).get('implemented-requirements', []))
            }
        }

        return ssp_data

    def _import_catalog(self, content: str) -> Dict[str, Any]:
        """Import Control Catalog"""
        data = json.loads(content)

        catalog_data = {
            'metadata': self._extract_metadata(data),
            'groups': self._extract_catalog_groups(data),
            'controls': self._extract_catalog_controls(data),
            'back_matter': data.get('back-matter', {}),
            'import_info': {
                'format': 'catalog',
                'oscal_version': data.get('oscal-version', ''),
                'imported_at': timezone.now().isoformat(),
                'group_count': len(data.get('groups', [])),
                'control_count': len(data.get('controls', []))
            }
        }

        return catalog_data

    def _import_profile(self, content: str) -> Dict[str, Any]:
        """Import Profile"""
        data = json.loads(content)

        profile_data = {
            'metadata': self._extract_metadata(data),
            'imports': self._extract_profile_imports(data),
            'merge': data.get('merge', {}),
            'modify': data.get('modify', {}),
            'back_matter': data.get('back-matter', {}),
            'import_info': {
                'format': 'profile',
                'oscal_version': data.get('oscal-version', ''),
                'imported_at': timezone.now().isoformat(),
                'import_count': len(data.get('imports', []))
            }
        }

        return profile_data

    def _import_assessment_plan(self, content: str) -> Dict[str, Any]:
        """Import Assessment Plan"""
        data = json.loads(content)

        plan_data = {
            'metadata': self._extract_metadata(data),
            'import_ssp': data.get('import-ssp', {}),
            'local_definitions': data.get('local-definitions', {}),
            'terms_and_conditions': data.get('terms-and-conditions', {}),
            'reviewed_controls': data.get('reviewed-controls', {}),
            'assessment_subjects': data.get('assessment-subjects', []),  # Array of subjects
            'assessment_assets': data.get('assessment-assets', {}),
            'assessment_activities': data.get('assessment-activities', []),  # Array of activities
            'back_matter': data.get('back-matter', {}),
            'import_info': {
                'format': 'assessment-plan',
                'oscal_version': data.get('oscal-version', ''),
                'imported_at': timezone.now().isoformat(),
                'activity_count': len(data.get('assessment-activities', [])),
                'subject_count': len(data.get('assessment-subjects', []))
            }
        }

        return plan_data

    def _import_assessment_results(self, content: str) -> Dict[str, Any]:
        """Import Assessment Results"""
        data = json.loads(content)

        results_data = {
            'metadata': self._extract_metadata(data),
            'import_ap': data.get('import-ap', {}),
            'local_definitions': data.get('local-definitions', {}),
            'results': data.get('results', []),  # Array of result objects
            'back_matter': data.get('back-matter', {}),
            'import_info': {
                'format': 'assessment-results',
                'oscal_version': data.get('oscal-version', ''),
                'imported_at': timezone.now().isoformat(),
                'result_count': len(data.get('results', []))
            }
        }

        return results_data

    def _import_poam(self, content: str) -> Dict[str, Any]:
        """Import Plan of Action and Milestones"""
        data = json.loads(content)

        poam_data = {
            'metadata': self._extract_metadata(data),
            'import_ssp': data.get('import-ssp', {}),
            'system_id': data.get('system-id', {}),
            'local_definitions': data.get('local-definitions', {}),
            'observations': data.get('observations', []),  # Array of observations
            'risks': data.get('risks', []),  # Array of risks
            'poam_items': data.get('poam-items', []),  # Array of POA&M items
            'back_matter': data.get('back-matter', {}),
            'import_info': {
                'format': 'plan-of-action-and-milestones',
                'oscal_version': data.get('oscal-version', ''),
                'imported_at': timezone.now().isoformat(),
                'poam_item_count': len(data.get('poam-items', [])),
                'observation_count': len(data.get('observations', [])),
                'risk_count': len(data.get('risks', []))
            }
        }

        return poam_data

    def _extract_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract OSCAL metadata"""
        return data.get('metadata', {})

    def _extract_system_characteristics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract system characteristics from SSP"""
        ssp_obj = data.get('system-security-plan', {})
        return ssp_obj.get('system-characteristics', {})

    def _extract_control_implementations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract control implementations from SSP"""
        ssp_obj = data.get('system-security-plan', {})
        control_impl = ssp_obj.get('control-implementation', {})
        return control_impl.get('implemented-requirements', [])

    def _extract_assessment_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract assessment results from SSP"""
        ssp_obj = data.get('system-security-plan', {})
        return ssp_obj.get('assessment-results', [])

    def _extract_plan_of_actions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract plan of actions from SSP"""
        ssp_obj = data.get('system-security-plan', {})
        return ssp_obj.get('plan-of-action-and-milestones', {})

    def _extract_catalog_groups(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract catalog groups"""
        return data.get('groups', [])

    def _extract_catalog_controls(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract catalog controls"""
        return data.get('controls', {})

    def _extract_profile_imports(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract profile imports"""
        return data.get('imports', [])

    def validate_oscal_content(self, content: str) -> Dict[str, Any]:
        """
        Validate OSCAL content structure.

        Returns validation results with errors and warnings.
        """
        try:
            data = json.loads(content)

            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'oscal_version': data.get('oscal-version', ''),
                'format_detected': self.detect_format(content)
            }

            # Check required fields
            if not data.get('oscal-version'):
                validation_result['errors'].append("Missing oscal-version")
                validation_result['valid'] = False

            if not data.get('metadata'):
                validation_result['errors'].append("Missing metadata")
                validation_result['valid'] = False

            # Format-specific validation
            format_type = validation_result['format_detected']
            if format_type == 'system-security-plan':
                ssp_obj = data.get('system-security-plan', {})
                if not ssp_obj.get('system-characteristics'):
                    validation_result['errors'].append("SSP missing system-characteristics")
                    validation_result['valid'] = False

            elif format_type == 'catalog':
                if not data.get('controls') and not data.get('groups'):
                    validation_result['warnings'].append("Catalog has no controls or groups")

            return validation_result

        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'errors': [f"Invalid JSON: {str(e)}"],
                'warnings': [],
                'oscal_version': '',
                'format_detected': None
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'oscal_version': '',
                'format_detected': None
            }

    def convert_to_ciso_assistant_entities(self, oscal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OSCAL data to CISO Assistant entity structures.

        This method maps OSCAL objects to CISO Assistant models for import.
        """
        format_type = oscal_data.get('import_info', {}).get('format')

        if format_type == 'system-security-plan':
            return self._convert_ssp_to_ciso_entities(oscal_data)
        elif format_type == 'catalog':
            return self._convert_catalog_to_ciso_entities(oscal_data)
        elif format_type == 'assessment-plan':
            return self._convert_assessment_plan_to_ciso_entities(oscal_data)
        elif format_type == 'assessment-results':
            return self._convert_assessment_results_to_ciso_entities(oscal_data)
        elif format_type == 'plan-of-action-and-milestones':
            return self._convert_poam_to_ciso_entities(oscal_data)
        else:
            raise ValueError(f"Unsupported conversion format: {format_type}")

    def _convert_ssp_to_ciso_entities(self, ssp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SSP to CISO Assistant entities"""
        # This would create ComplianceAssessment, ControlImplementation, etc.
        # Implementation would map OSCAL SSP to CISO Assistant models
        return {
            'compliance_assessment': self._create_compliance_assessment_from_ssp(ssp_data),
            'control_implementations': self._create_control_implementations_from_ssp(ssp_data),
            'assets': self._create_assets_from_ssp(ssp_data),
            'findings': self._create_findings_from_ssp(ssp_data)
        }

    def _convert_catalog_to_ciso_entities(self, catalog_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert catalog to CISO Assistant entities"""
        # Convert OSCAL catalog to Framework and Control entities
        return {
            'framework': self._create_framework_from_catalog(catalog_data),
            'controls': self._create_controls_from_catalog(catalog_data)
        }

    def _convert_assessment_plan_to_ciso_entities(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert assessment plan to CISO Assistant entities"""
        return {
            'assessment_plan': self._create_assessment_plan(plan_data),
            'assessment_activities': self._create_assessment_activities(plan_data)
        }

    def _convert_assessment_results_to_ciso_entities(self, results_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert assessment results to CISO Assistant entities"""
        return {
            'assessment_results': self._create_assessment_results(results_data),
            'findings': self._create_findings_from_results(results_data)
        }

    def _convert_poam_to_ciso_entities(self, poam_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert POA&M to CISO Assistant entities"""
        return {
            'poam_items': self._create_poam_items_from_poam(poam_data),
            'risks': self._create_risks_from_poam(poam_data),
            'observations': self._create_observations_from_poam(poam_data)
        }

    # Placeholder methods for entity creation - these would be implemented
    # to actually create CISO Assistant model instances

    def _create_compliance_assessment_from_ssp(self, ssp_data):
        """Placeholder for SSP to ComplianceAssessment conversion"""
        return {'placeholder': 'SSP to ComplianceAssessment mapping'}

    def _create_control_implementations_from_ssp(self, ssp_data):
        """Placeholder for SSP to ControlImplementation conversion"""
        return {'placeholder': 'SSP to ControlImplementation mapping'}

    def _create_assets_from_ssp(self, ssp_data):
        """Placeholder for SSP to Asset conversion"""
        return {'placeholder': 'SSP to Asset mapping'}

    def _create_findings_from_ssp(self, ssp_data):
        """Placeholder for SSP to Finding conversion"""
        return {'placeholder': 'SSP to Finding mapping'}

    def _create_framework_from_catalog(self, catalog_data):
        """Placeholder for catalog to Framework conversion"""
        return {'placeholder': 'Catalog to Framework mapping'}

    def _create_controls_from_catalog(self, catalog_data):
        """Placeholder for catalog to Control conversion"""
        return {'placeholder': 'Catalog to Control mapping'}

    def _create_assessment_plan(self, plan_data):
        """Placeholder for assessment plan creation"""
        return {'placeholder': 'Assessment plan creation'}

    def _create_assessment_activities(self, plan_data):
        """Placeholder for assessment activities creation"""
        return {'placeholder': 'Assessment activities creation'}

    def _create_assessment_results(self, results_data):
        """Placeholder for assessment results creation"""
        return {'placeholder': 'Assessment results creation'}

    def _create_findings_from_results(self, results_data):
        """Placeholder for findings from results creation"""
        return {'placeholder': 'Findings from results creation'}

    def _create_poam_items_from_poam(self, poam_data):
        """Placeholder for POA&M items creation"""
        return {'placeholder': 'POA&M items creation'}

    def _create_risks_from_poam(self, poam_data):
        """Placeholder for risks creation"""
        return {'placeholder': 'Risks creation'}

    def _create_observations_from_poam(self, poam_data):
        """Placeholder for observations creation"""
        return {'placeholder': 'Observations creation'}
