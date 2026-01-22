"""
Unit tests for CKL Exporter Service
"""

import pytest
from django.core.exceptions import ValidationError

from ..services.ckl_exporter import CKLExporter


class TestCKLExporter:
    """Test CKLExporter service."""

    def setup_method(self):
        """Set up test fixtures"""
        self.exporter = CKLExporter()

    def test_export_ckl_v1(self):
        """Test exporting to CKL v1.0 format"""
        checklist_data = self._get_sample_checklist_data()
        xml_content = self.exporter.export_to_ckl(checklist_data, '1.0')

        assert xml_content.startswith('<?xml')
        assert '<CHECKLIST>' in xml_content
        assert '<ASSET>' in xml_content
        assert '<STIGS>' in xml_content
        assert 'test-server.local' in xml_content

    def test_export_ckl_v2(self):
        """Test exporting to CKL v2.0 format"""
        checklist_data = self._get_sample_checklist_data()
        xml_content = self.exporter.export_to_ckl(checklist_data, '2.0')

        assert xml_content.startswith('<?xml')
        assert '<CHECKLIST>' in xml_content

    def test_export_invalid_version(self):
        """Test exporting with invalid version"""
        checklist_data = self._get_sample_checklist_data()

        with pytest.raises(ValueError, match="Unsupported CKL version"):
            self.exporter.export_to_ckl(checklist_data, '3.0')

    def test_create_sample_data(self):
        """Test creating sample CKL data"""
        sample_data = self.exporter.create_sample_ckl_data()

        assert sample_data['version'] == '1.0'
        assert 'asset' in sample_data
        assert 'stigs' in sample_data
        assert 'vulnerabilities' in sample_data

    def test_validate_export_data(self):
        """Test validating data before export"""
        valid_data = self._get_sample_checklist_data()
        errors = self.exporter.validate_export_data(valid_data)
        assert len(errors) == 0

    def test_validate_invalid_export_data(self):
        """Test validating invalid data before export"""
        invalid_data = {'version': '1.0'}  # Missing required fields

        errors = self.exporter.validate_export_data(invalid_data)
        assert len(errors) > 0
        assert any('asset' in error.lower() for error in errors)

    def test_export_with_minimal_data(self):
        """Test exporting with minimal required data"""
        minimal_data = {
            'version': '1.0',
            'asset': {
                'host_name': 'minimal-server.local'
            },
            'stigs': {
                'stig_info': [
                    {'sid_name': 'version', 'sid_data': '1.0'},
                    {'sid_name': 'title', 'sid_data': 'Minimal STIG'},
                    {'sid_name': 'description', 'sid_data': 'Minimal STIG description'}
                ]
            },
            'vulnerabilities': []
        }

        xml_content = self.exporter.export_to_ckl(minimal_data, '1.0')
        assert xml_content.startswith('<?xml')
        assert 'minimal-server.local' in xml_content

    def test_export_with_vulnerabilities(self):
        """Test exporting with vulnerability findings"""
        data_with_vulns = self._get_sample_checklist_data()

        xml_content = self.exporter.export_to_ckl(data_with_vulns, '1.0')
        assert xml_content.startswith('<?xml')
        assert '<VULN>' in xml_content
        assert 'NotAFinding' in xml_content

    def test_export_with_severity_override(self):
        """Test exporting with severity override"""
        data_with_override = self._get_sample_checklist_data()

        # Add severity override to vulnerability
        data_with_override['vulnerabilities'][0]['severity_override'] = 'high'
        data_with_override['vulnerabilities'][0]['severity_justification'] = 'Business critical'

        xml_content = self.exporter.export_to_ckl(data_with_override, '1.0')
        assert 'high' in xml_content
        assert 'Business critical' in xml_content

    def _get_sample_checklist_data(self):
        """Get sample checklist data for testing"""
        return {
            'version': '1.0',
            'asset': {
                'host_name': 'test-server.local',
                'host_ip': '192.168.1.100',
                'host_mac': '00:11:22:33:44:55',
                'tech_area': 'Application Review',
                'asset_type': 'Computing',
                'role': 'Member Server',
                'web_or_database': True,
                'web_db_site': 'MyApp',
                'web_db_instance': 'Production'
            },
            'stigs': {
                'stig_info': [
                    {'sid_name': 'version', 'sid_data': '1.0'},
                    {'sid_name': 'title', 'sid_data': 'Sample STIG'},
                    {'sid_name': 'description', 'sid_data': 'Sample STIG for testing'},
                    {'sid_name': 'releaseinfo', 'sid_data': 'Release: 2.5'}
                ],
                'stig_data': [
                    {'vuln_attribute': 'Rule_ID', 'attribute_data': 'SV-12345'},
                    {'vuln_attribute': 'Severity', 'attribute_data': 'medium'},
                    {'vuln_attribute': 'Title', 'attribute_data': 'Sample Rule Title'},
                    {'vuln_attribute': 'Discussion', 'attribute_data': 'Sample discussion'},
                    {'vuln_attribute': 'Check_Content', 'attribute_data': 'Sample check content'},
                    {'vuln_attribute': 'Fix_Text', 'attribute_data': 'Sample fix text'}
                ]
            },
            'vulnerabilities': [
                {
                    'status': 'NotAFinding',
                    'finding_details': 'No issues found during assessment',
                    'comments': 'System is compliant with this requirement',
                    'stig_data': [
                        {'attribute': 'Rule_ID', 'data': 'SV-12345'},
                        {'attribute': 'Severity', 'data': 'medium'},
                        {'attribute': 'Title', 'data': 'Sample Rule Title'},
                        {'attribute': 'Discussion', 'data': 'Sample discussion'},
                        {'attribute': 'Check_Content', 'data': 'Sample check content'},
                        {'attribute': 'Fix_Text', 'data': 'Sample fix text'}
                    ]
                },
                {
                    'status': 'Open',
                    'finding_details': 'Configuration does not meet requirements',
                    'comments': 'Need to update system configuration',
                    'severity_override': 'high',
                    'severity_justification': 'Business critical system',
                    'stig_data': [
                        {'attribute': 'Rule_ID', 'data': 'SV-12346'},
                        {'attribute': 'Severity', 'data': 'low'},
                        {'attribute': 'Title', 'data': 'Another Rule Title'}
                    ]
                }
            ]
        }
