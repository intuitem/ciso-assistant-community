"""
FedRAMP Validator Service

Service for validating OSCAL SSP files against FedRAMP requirements
using compliance-trestle-fedramp. Provides validation reports and
baseline compliance checking.
"""

import json
import logging
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FedRAMPValidator:
    """
    Validates OSCAL SSP files against FedRAMP baselines.

    Uses compliance-trestle-fedramp to perform validation and
    generate detailed compliance reports.
    """

    SUPPORTED_BASELINES = ['low', 'moderate', 'high', 'li-saas']

    def __init__(self):
        """Initialize FedRAMP validator"""
        self.baselines = self.SUPPORTED_BASELINES

    def validate_ssp(self, ssp_content: str, baseline: str = 'moderate') -> Dict[str, Any]:
        """
        Validate SSP against FedRAMP baseline.

        Args:
            ssp_content: OSCAL SSP JSON content
            baseline: FedRAMP baseline ('low', 'moderate', 'high', 'li-saas')

        Returns:
            Validation results dictionary
        """
        if baseline not in self.baselines:
            raise ValueError(f"Unsupported baseline: {baseline}. Supported: {self.baselines}")

        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as ssp_file:
                ssp_file.write(ssp_content)
                ssp_file_path = ssp_file.name

            with tempfile.TemporaryDirectory() as temp_dir:
                # Run compliance-trestle-fedramp validation
                result = self._run_fedramp_validation(ssp_file_path, baseline, temp_dir)

                # Clean up temporary SSP file
                os.unlink(ssp_file_path)

                return result

        except Exception as e:
            logger.error(f"Error validating SSP: {e}")
            return {
                'valid': False,
                'errors': [str(e)],
                'baseline': baseline,
                'validation_passed': False,
                'svrl_report': None,
                'html_report': None
            }

    def _run_fedramp_validation(self, ssp_path: str, baseline: str, output_dir: str) -> Dict[str, Any]:
        """
        Run the actual compliance-trestle-fedramp validation command.

        Args:
            ssp_path: Path to SSP JSON file
            baseline: FedRAMP baseline
            output_dir: Directory for output files

        Returns:
            Validation results
        """
        try:
            # Construct the validation command
            cmd = [
                'compliance-trestle-fedramp',
                'validate',
                '--ssp-path', ssp_path,
                '--baseline', baseline,
                '--output-dir', output_dir
            ]

            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Check for output files
            svrl_file = Path(output_dir) / f"fedramp_validation_{baseline}.svrl"
            html_file = Path(output_dir) / f"fedramp_validation_{baseline}.html"

            svrl_content = svrl_file.read_text() if svrl_file.exists() else None
            html_content = html_file.read_text() if html_file.exists() else None

            # Parse SVRL for validation results
            validation_results = self._parse_svrl_results(svrl_content or "")

            return {
                'valid': result.returncode == 0,
                'baseline': baseline,
                'validation_passed': result.returncode == 0,
                'command_output': result.stdout,
                'command_error': result.stderr,
                'svrl_report': svrl_content,
                'html_report': html_content,
                'errors': validation_results.get('errors', []),
                'warnings': validation_results.get('warnings', []),
                'failed_assertions': validation_results.get('failed_assertions', []),
                'passed_assertions': validation_results.get('passed_assertions', 0),
                'total_assertions': validation_results.get('total_assertions', 0)
            }

        except subprocess.TimeoutExpired:
            raise Exception("FedRAMP validation timed out after 5 minutes")
        except FileNotFoundError:
            raise Exception("compliance-trestle-fedramp command not found. Please install compliance-trestle-fedramp")
        except Exception as e:
            raise Exception(f"FedRAMP validation failed: {str(e)}")

    def _parse_svrl_results(self, svrl_content: str) -> Dict[str, Any]:
        """
        Parse SVRL (Schematron Validation Report Language) content.

        Args:
            svrl_content: SVRL XML content

        Returns:
            Parsed validation results
        """
        if not svrl_content:
            return {
                'errors': [],
                'warnings': [],
                'failed_assertions': [],
                'passed_assertions': 0,
                'total_assertions': 0
            }

        try:
            # Parse SVRL XML (simplified parsing)
            import xml.etree.ElementTree as ET

            root = ET.fromstring(svrl_content)

            # Extract failed assertions
            failed_assertions = []
            for failed_assert in root.findall(".//{http://purl.oclc.org/dsdl/svrl}failed-assert"):
                assertion = {
                    'id': failed_assert.get('id', ''),
                    'test': failed_assert.get('test', ''),
                    'location': failed_assert.get('location', ''),
                    'text': failed_assert.findtext(".//{http://purl.oclc.org/dsdl/svrl}text", ''),
                    'diagnostic_references': []
                }

                # Add diagnostic references
                for diagnostic in failed_assert.findall(".//{http://purl.oclc.org/dsdl/svrl}diagnostic-reference"):
                    assertion['diagnostic_references'].append({
                        'diagnostic': diagnostic.get('diagnostic', ''),
                        'text': diagnostic.text or ''
                    })

                failed_assertions.append(assertion)

            # Extract successful reports
            successful_reports = len(root.findall(".//{http://purl.oclc.org/dsdl/svrl}successful-report"))

            # Categorize errors and warnings
            errors = []
            warnings = []

            for assertion in failed_assertions:
                error_text = assertion.get('text', '')
                if 'error' in error_text.lower() or 'fatal' in error_text.lower():
                    errors.append(assertion)
                else:
                    warnings.append(assertion)

            return {
                'errors': errors,
                'warnings': warnings,
                'failed_assertions': failed_assertions,
                'passed_assertions': successful_reports,
                'total_assertions': len(failed_assertions) + successful_reports
            }

        except ET.ParseError:
            # If SVRL parsing fails, provide basic error info
            return {
                'errors': [{'text': 'Failed to parse SVRL validation report'}],
                'warnings': [],
                'failed_assertions': [{'text': 'SVRL parsing failed'}],
                'passed_assertions': 0,
                'total_assertions': 1
            }

    def generate_fedramp_report(self, ssp_content: str, baseline: str = 'moderate') -> Dict[str, Any]:
        """
        Generate a comprehensive FedRAMP validation report.

        Args:
            ssp_content: OSCAL SSP JSON content
            baseline: FedRAMP baseline

        Returns:
            Comprehensive validation report
        """
        validation_result = self.validate_ssp(ssp_content, baseline)

        # Enhance with additional metadata
        report = {
            'validation_timestamp': str(datetime.now()),
            'ssp_oscal_version': self._extract_oscal_version(ssp_content),
            'fedramp_baseline': baseline,
            'validator_version': 'compliance-trestle-fedramp',
            'validation_results': validation_result,
            'compliance_summary': self._generate_compliance_summary(validation_result),
            'recommendations': self._generate_recommendations(validation_result)
        }

        return report

    def _extract_oscal_version(self, ssp_content: str) -> str:
        """Extract OSCAL version from SSP content"""
        try:
            data = json.loads(ssp_content)
            return data.get('oscal-version', 'unknown')
        except:
            return 'unknown'

    def _generate_compliance_summary(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate compliance summary from validation results"""
        total_assertions = validation_result.get('total_assertions', 0)
        failed_assertions = len(validation_result.get('failed_assertions', []))
        passed_assertions = validation_result.get('passed_assertions', 0)

        if total_assertions > 0:
            compliance_percentage = (passed_assertions / total_assertions) * 100
        else:
            compliance_percentage = 0

        # Categorize by severity
        critical_failures = 0
        high_failures = 0
        medium_failures = 0

        for failure in validation_result.get('failed_assertions', []):
            text = failure.get('text', '').lower()
            if 'critical' in text or 'cat i' in text:
                critical_failures += 1
            elif 'high' in text or 'cat ii' in text:
                high_failures += 1
            else:
                medium_failures += 1

        return {
            'overall_compliance_percentage': round(compliance_percentage, 2),
            'total_assertions': total_assertions,
            'passed_assertions': passed_assertions,
            'failed_assertions': failed_assertions,
            'critical_failures': critical_failures,
            'high_failures': high_failures,
            'medium_failures': medium_failures,
            'compliance_level': self._determine_compliance_level(compliance_percentage, critical_failures)
        }

    def _determine_compliance_level(self, percentage: float, critical_failures: int) -> str:
        """Determine overall compliance level"""
        if critical_failures > 0:
            return 'non-compliant'
        elif percentage >= 95:
            return 'compliant'
        elif percentage >= 80:
            return 'conditionally-compliant'
        else:
            return 'non-compliant'

    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate remediation recommendations"""
        recommendations = []

        failed_assertions = validation_result.get('failed_assertions', [])
        if not failed_assertions:
            recommendations.append("All FedRAMP validation checks passed!")
            return recommendations

        # Group recommendations by control family
        control_families = {}
        for failure in failed_assertions:
            text = failure.get('text', '')
            # Extract control family from failure text (e.g., "AC-2", "IA-5")
            import re
            controls = re.findall(r'\b[A-Z]{2}-\d+\b', text)
            for control in controls:
                family = control.split('-')[0]
                if family not in control_families:
                    control_families[family] = []
                control_families[family].append(control)

        # Generate family-specific recommendations
        for family, controls in control_families.items():
            unique_controls = list(set(controls))
            recommendations.append(
                f"Review and implement controls in {family} family: {', '.join(unique_controls[:5])}{'...' if len(unique_controls) > 5 else ''}"
            )

        # General recommendations
        if len(failed_assertions) > 10:
            recommendations.append("Consider comprehensive SSP review - multiple validation failures detected")
        if any('documentation' in failure.get('text', '').lower() for failure in failed_assertions):
            recommendations.append("Enhance control implementation documentation")

        return recommendations

    def list_available_baselines(self) -> List[str]:
        """List all available FedRAMP baselines"""
        return self.baselines.copy()

    def get_baseline_requirements(self, baseline: str) -> Dict[str, Any]:
        """
        Get detailed requirements for a specific baseline.

        Args:
            baseline: FedRAMP baseline name

        Returns:
            Baseline requirements and information
        """
        baseline_info = {
            'low': {
                'name': 'FedRAMP Low Baseline',
                'description': 'Basic security controls for low-impact systems',
                'impact_level': 'Low',
                'total_controls': 125,
                'inherited_controls': 72,
                'common_controls': 53
            },
            'moderate': {
                'name': 'FedRAMP Moderate Baseline',
                'description': 'Enhanced security controls for moderate-impact systems',
                'impact_level': 'Moderate',
                'total_controls': 325,
                'inherited_controls': 198,
                'common_controls': 127
            },
            'high': {
                'name': 'FedRAMP High Baseline',
                'description': 'Comprehensive security controls for high-impact systems',
                'impact_level': 'High',
                'total_controls': 421,
                'inherited_controls': 256,
                'common_controls': 165
            },
            'li-saas': {
                'name': 'FedRAMP Low-Impact SaaS Baseline',
                'description': 'Tailored controls for low-impact Software as a Service',
                'impact_level': 'Low (SaaS)',
                'total_controls': 105,
                'inherited_controls': 65,
                'common_controls': 40
            }
        }

        return baseline_info.get(baseline, {
            'name': f'Unknown Baseline: {baseline}',
            'description': 'Baseline information not available',
            'impact_level': 'Unknown',
            'total_controls': 0,
            'inherited_controls': 0,
            'common_controls': 0
        })

    def validate_baseline_compatibility(self, ssp_content: str) -> Dict[str, Any]:
        """
        Validate SSP compatibility across all baselines.

        Args:
            ssp_content: OSCAL SSP JSON content

        Returns:
            Compatibility results for all baselines
        """
        results = {}

        for baseline in self.baselines:
            try:
                validation = self.validate_ssp(ssp_content, baseline)
                results[baseline] = {
                    'compatible': validation.get('validation_passed', False),
                    'error_count': len(validation.get('errors', [])),
                    'warning_count': len(validation.get('warnings', [])),
                    'critical_failures': sum(1 for failure in validation.get('failed_assertions', [])
                                           if 'critical' in failure.get('text', '').lower())
                }
            except Exception as e:
                results[baseline] = {
                    'compatible': False,
                    'error': str(e)
                }

        return results
