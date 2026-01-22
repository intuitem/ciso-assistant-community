"""
SSP Generator Service

Service for generating FedRAMP System Security Plan (SSP) Appendix A
Word documents from CISO Assistant compliance assessments.
"""

import logging
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from django.core.files.base import ContentFile

from .oscal_exporter import OSCALExporter
from .ssp_importer import SSPWordImporter

logger = logging.getLogger(__name__)


class SSPGenerator:
    """
    Generates FedRAMP SSP Appendix A Word documents.

    Uses compliance-trestle-fedramp to transform OSCAL SSP JSON
    into formatted Word documents for FedRAMP submission.
    """

    SUPPORTED_BASELINES = ['low', 'moderate', 'high', 'li-saas']

    def __init__(self):
        """Initialize SSP generator"""
        self.exporter = OSCALExporter()
        self.importer = SSPWordImporter()
        self.baselines = self.SUPPORTED_BASELINES

    def generate_appendix_a(self, assessment_id: str, baseline: str = 'moderate') -> bytes:
        """
        Generate FedRAMP SSP Appendix A Word document.

        Args:
            assessment_id: UUID of the compliance assessment
            baseline: FedRAMP baseline ('low', 'moderate', 'high', 'li-saas')

        Returns:
            Word document as bytes
        """
        if baseline not in self.baselines:
            raise ValueError(f"Unsupported baseline: {baseline}. Supported: {self.baselines}")

        try:
            # Export assessment to OSCAL SSP format
            oscal_ssp = self.exporter.export_compliance_assessment(assessment_id)

            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as ssp_file:
                ssp_file.write(oscal_ssp)
                ssp_file_path = ssp_file.name

            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = Path(temp_dir) / f"ssp_appendix_a_{baseline}.docx"

                # Run compliance-trestle-fedramp transform
                result = self._run_ssp_transform(ssp_file_path, baseline, str(output_file))

                if result['success'] and output_file.exists():
                    # Read the generated Word document
                    with open(output_file, 'rb') as f:
                        word_content = f.read()

                    # Clean up temporary files
                    os.unlink(ssp_file_path)

                    return word_content
                else:
                    error_msg = result.get('error', 'Unknown error during SSP generation')
                    raise Exception(f"SSP generation failed: {error_msg}")

        except Exception as e:
            logger.error(f"Error generating SSP Appendix A: {e}")
            raise

    def _run_ssp_transform(self, ssp_path: str, baseline: str, output_path: str) -> Dict[str, Any]:
        """
        Run the compliance-trestle-fedramp transform command.

        Args:
            ssp_path: Path to OSCAL SSP JSON file
            baseline: FedRAMP baseline
            output_path: Path for output Word document

        Returns:
            Command execution results
        """
        try:
            # Construct the transform command
            cmd = [
                'compliance-trestle-fedramp',
                'transform',
                '--ssp-path', ssp_path,
                '--baseline', baseline,
                '--output-path', output_path
            ]

            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for document generation
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'error': result.stderr if result.returncode != 0 else None
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'SSP generation timed out after 10 minutes'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': 'compliance-trestle-fedramp command not found. Please install compliance-trestle-fedramp'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"SSP transform failed: {str(e)}"
            }

    def generate_appendix_a_with_customizations(
        self,
        assessment_id: str,
        baseline: str = 'moderate',
        customizations: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate SSP Appendix A with customizations.

        Args:
            assessment_id: UUID of the compliance assessment
            baseline: FedRAMP baseline
            customizations: Dictionary of customization options

        Returns:
            Customized Word document as bytes
        """
        # First generate the base document
        base_document = self.generate_appendix_a(assessment_id, baseline)

        # Apply customizations if provided
        if customizations:
            return self._apply_customizations(base_document, customizations)

        return base_document

    def _apply_customizations(self, document_bytes: bytes, customizations: Dict[str, Any]) -> bytes:
        """
        Apply customizations to the generated Word document.

        Note: This is a placeholder for document customization logic.
        In practice, this would require a Word document manipulation library
        like python-docx to modify the generated document.
        """
        # Placeholder implementation
        logger.info(f"Applying customizations: {customizations}")

        # For now, return the original document
        # Future implementation would:
        # 1. Parse the Word document
        # 2. Apply custom formatting, headers, footers, etc.
        # 3. Re-save the modified document

        return document_bytes

    def validate_ssp_for_baseline(self, assessment_id: str, baseline: str) -> Dict[str, Any]:
        """
        Validate that an SSP meets baseline requirements before generation.

        Args:
            assessment_id: UUID of the compliance assessment
            baseline: FedRAMP baseline to validate against

        Returns:
            Validation results
        """
        from .fedramp_validator import FedRAMPValidator

        try:
            # Export SSP
            oscal_ssp = self.exporter.export_compliance_assessment(assessment_id)

            # Validate against baseline
            validator = FedRAMPValidator()
            validation_result = validator.validate_ssp(oscal_ssp, baseline)

            return {
                'assessment_id': assessment_id,
                'baseline': baseline,
                'validation_passed': validation_result.get('validation_passed', False),
                'can_generate': validation_result.get('validation_passed', False),
                'validation_errors': validation_result.get('errors', []),
                'validation_warnings': validation_result.get('warnings', []),
                'compliance_percentage': self._calculate_compliance_percentage(validation_result),
                'recommendations': self._generate_generation_recommendations(validation_result)
            }

        except Exception as e:
            logger.error(f"Error validating SSP for generation: {e}")
            return {
                'assessment_id': assessment_id,
                'baseline': baseline,
                'validation_passed': False,
                'can_generate': False,
                'error': str(e)
            }

    def _calculate_compliance_percentage(self, validation_result: Dict[str, Any]) -> float:
        """Calculate compliance percentage from validation results"""
        total_assertions = validation_result.get('total_assertions', 0)
        passed_assertions = validation_result.get('passed_assertions', 0)

        if total_assertions == 0:
            return 0.0

        return round((passed_assertions / total_assertions) * 100, 2)

    def _generate_generation_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for SSP generation"""
        recommendations = []

        if not validation_result.get('validation_passed', False):
            recommendations.append("Address validation failures before generating SSP document")

        compliance_pct = self._calculate_compliance_percentage(validation_result)
        if compliance_pct < 80:
            recommendations.append("Low compliance percentage detected - consider remediation before submission")

        if validation_result.get('errors'):
            recommendations.append("Critical validation errors found - document may not meet FedRAMP requirements")

        if not recommendations:
            recommendations.append("SSP appears ready for FedRAMP submission")

        return recommendations

    def get_supported_baselines(self) -> List[str]:
        """Get list of supported FedRAMP baselines"""
        return self.baselines.copy()

    def get_baseline_info(self, baseline: str) -> Dict[str, Any]:
        """
        Get information about a specific baseline.

        Args:
            baseline: FedRAMP baseline name

        Returns:
            Baseline information dictionary
        """
        baseline_info = {
            'low': {
                'name': 'FedRAMP Low Baseline',
                'description': 'Basic security controls for low-impact systems',
                'impact_level': 'Low',
                'document_sections': ['Executive Summary', 'System Description', 'Control Implementation'],
                'estimated_pages': '25-35'
            },
            'moderate': {
                'name': 'FedRAMP Moderate Baseline',
                'description': 'Enhanced security controls for moderate-impact systems',
                'impact_level': 'Moderate',
                'document_sections': ['Executive Summary', 'System Description', 'Control Implementation', 'Artifact References'],
                'estimated_pages': '45-65'
            },
            'high': {
                'name': 'FedRAMP High Baseline',
                'description': 'Comprehensive security controls for high-impact systems',
                'impact_level': 'High',
                'document_sections': ['Executive Summary', 'System Description', 'Control Implementation', 'Artifact References', 'Security Assessment'],
                'estimated_pages': '65-85'
            },
            'li-saas': {
                'name': 'FedRAMP Low-Impact SaaS Baseline',
                'description': 'Tailored controls for low-impact Software as a Service',
                'impact_level': 'Low (SaaS)',
                'document_sections': ['Executive Summary', 'System Description', 'Control Implementation'],
                'estimated_pages': '20-30'
            }
        }

        return baseline_info.get(baseline, {
            'name': f'Unknown Baseline: {baseline}',
            'description': 'Baseline information not available',
            'impact_level': 'Unknown',
            'document_sections': [],
            'estimated_pages': 'Unknown'
        })

    def preview_ssp_content(self, assessment_id: str, baseline: str) -> Dict[str, Any]:
        """
        Preview SSP content before generation.

        Args:
            assessment_id: UUID of the compliance assessment
            baseline: FedRAMP baseline

        Returns:
            Preview information about the SSP content
        """
        try:
            # Export SSP to get content information
            oscal_ssp = self.exporter.export_compliance_assessment(assessment_id)
            ssp_data = json.loads(oscal_ssp)

            # Extract preview information
            ssp_obj = ssp_data.get('system-security-plan', {})
            control_impl = ssp_obj.get('control-implementation', {})
            implemented_reqs = control_impl.get('implemented-requirements', [])

            preview = {
                'assessment_id': assessment_id,
                'baseline': baseline,
                'system_name': ssp_obj.get('system-characteristics', {}).get('system-name', 'Unknown'),
                'total_controls': len(implemented_reqs),
                'implemented_controls': len([req for req in implemented_reqs if req.get('statements')]),
                'control_families': self._extract_control_families(implemented_reqs),
                'estimated_document_length': self._estimate_document_length(implemented_reqs),
                'content_sections': [
                    'Executive Summary',
                    'System Description',
                    'Control Implementation Details',
                    f'Control Families: {", ".join(self._extract_control_families(implemented_reqs)[:5])}'
                ]
            }

            return preview

        except Exception as e:
            logger.error(f"Error generating SSP preview: {e}")
            return {
                'assessment_id': assessment_id,
                'baseline': baseline,
                'error': str(e)
            }

    def _extract_control_families(self, implemented_reqs: List[Dict[str, Any]]) -> List[str]:
        """Extract unique control families from implemented requirements"""
        families = set()
        for req in implemented_reqs:
            control_id = req.get('control-id', '')
            if '-' in control_id:
                family = control_id.split('-')[0]
                families.add(family)

        return sorted(list(families))

    def _estimate_document_length(self, implemented_reqs: List[Dict[str, Any]]) -> str:
        """Estimate document length based on number of controls"""
        control_count = len(implemented_reqs)

        if control_count < 50:
            return "Short (20-30 pages)"
        elif control_count < 150:
            return "Medium (30-50 pages)"
        elif control_count < 300:
            return "Long (50-70 pages)"
        else:
            return "Very Long (70+ pages)"

    def list_generated_documents(self, assessment_id: str) -> List[Dict[str, Any]]:
        """
        List previously generated SSP documents for an assessment.

        Args:
            assessment_id: UUID of the compliance assessment

        Returns:
            List of generated documents with metadata
        """
        # Placeholder - in practice, this would query a document storage table
        # that tracks generated SSP documents

        return [
            {
                'id': 'placeholder-id',
                'assessment_id': assessment_id,
                'baseline': 'moderate',
                'generated_at': '2024-01-01T00:00:00Z',
                'file_size': 0,
                'status': 'placeholder'
            }
        ]

    def cleanup_generated_documents(self, days_to_keep: int = 90) -> int:
        """
        Clean up old generated documents.

        Args:
            days_to_keep: Number of days to keep documents

        Returns:
            Number of documents cleaned up
        """
        # Placeholder - in practice, this would:
        # 1. Find documents older than days_to_keep
        # 2. Delete physical files
        # 3. Update database records

        logger.info(f"Placeholder: Would clean up documents older than {days_to_keep} days")
        return 0

    # IMPORT FUNCTIONALITY

    def import_ssp_from_docx(self, docx_file_path: str) -> Dict[str, Any]:
        """
        Import SSP from Word document.

        Args:
            docx_file_path: Path to the DOCX file

        Returns:
            Import results with OSCAL SSP and CISO entities
        """
        return self.importer.import_docx_file(docx_file_path)

    def import_ssp_from_upload(self, uploaded_file) -> Dict[str, Any]:
        """
        Import SSP from uploaded Word document.

        Args:
            uploaded_file: Django uploaded file object

        Returns:
            Import results
        """
        return self.importer.import_docx_from_upload(uploaded_file)

    def validate_docx_for_import(self, docx_file_path: str) -> Dict[str, Any]:
        """
        Validate DOCX file for SSP import.

        Args:
            docx_file_path: Path to DOCX file

        Returns:
            Validation results
        """
        try:
            # Try to extract and parse the document
            document_xml = self.importer._extract_document_xml(docx_file_path)
            if not document_xml:
                return {
                    'valid': False,
                    'errors': ['Cannot extract document content from DOCX file'],
                    'warnings': []
                }

            parsed_content = self.importer._parse_document_structure(document_xml)

            # Basic validation
            sections = parsed_content.get('sections', [])
            tables = parsed_content.get('tables', [])

            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'document_info': {
                    'sections_found': len(sections),
                    'tables_found': len(tables),
                    'has_system_info': any('system' in s.get('heading', '').lower() for s in sections),
                    'has_controls': any(re.match(r'^[A-Z]{2}-\d+', s.get('heading', '').upper()) for s in sections)
                }
            }

            # Check for minimum required content
            if len(sections) == 0:
                validation_result['errors'].append('No document sections found')
                validation_result['valid'] = False

            if not validation_result['document_info']['has_system_info']:
                validation_result['warnings'].append('No system information sections detected')

            if not validation_result['document_info']['has_controls']:
                validation_result['warnings'].append('No control implementation sections detected')

            return validation_result

        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation failed: {str(e)}'],
                'warnings': []
            }

    def get_import_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about import capabilities.

        Returns:
            Import capability statistics
        """
        return {
            'capabilities': self.importer.get_import_capabilities(),
            'supported_extensions': ['.docx'],
            'oscal_versions_supported': ['1.1.2'],
            'frameworks_supported': [
                'NIST SP 800-53',
                'ISO 27001',
                'COBIT',
                'PCI DSS',
                'Custom frameworks'
            ],
            'extraction_features': [
                'Document structure parsing',
                'Table extraction',
                'Heading hierarchy',
                'Text content extraction',
                'Basic formatting preservation'
            ],
            'limitations': [
                'Complex nested tables',
                'Embedded images',
                'Advanced formatting',
                'Multi-column layouts'
            ]
        }

    def convert_imported_ssp_to_assessment(self, import_result: Dict[str, Any], assessment_name: str = None) -> Dict[str, Any]:
        """
        Convert imported SSP data to a CISO Assistant compliance assessment.

        Args:
            import_result: Result from SSP import
            assessment_name: Optional name for the assessment

        Returns:
            Assessment creation data
        """
        if not import_result.get('success'):
            return {
                'success': False,
                'error': 'Invalid import result'
            }

        ciso_entities = import_result.get('ciso_entities', {})
        compliance_assessment = ciso_entities.get('compliance_assessment', {})

        # Enhance with import metadata
        assessment_data = {
            'name': assessment_name or f"Imported SSP - {compliance_assessment.get('name', 'Unknown System')}",
            'description': f"Imported from Word document on {import_result.get('import_metadata', {}).get('import_timestamp', 'Unknown date')}",
            'framework': compliance_assessment.get('framework', {}),
            'status': 'draft',
            'controls': compliance_assessment.get('controls', []),
            'assets': ciso_entities.get('assets', []),
            'findings': ciso_entities.get('findings', []),
            'import_metadata': import_result.get('import_metadata', {}),
            'oscal_version': import_result.get('oscal_ssp', {}).get('oscal-version', 'Unknown')
        }

        return {
            'success': True,
            'assessment_data': assessment_data,
            'import_warnings': import_result.get('validation', {}).get('warnings', []),
            'document_info': import_result.get('import_metadata', {})
        }
