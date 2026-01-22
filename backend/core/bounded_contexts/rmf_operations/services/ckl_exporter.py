"""
CKL Exporter Service

Service for exporting STIG checklist data back to CKL (Checklist) XML format.
Supports both CKL v1.0 and v2.0 formats for compatibility with SCAP tools.
"""

import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)


class CKLExporter:
    """
    CKL (Checklist) XML exporter for STIG files.

    Generates CKL XML files that can be imported back into SCAP tools like:
    - SCAP Compliance Checker (SCC)
    - STIG Viewer
    - OpenSCAP
    """

    def __init__(self):
        """Initialize the CKL exporter"""
        self.default_version = '1.0'

    def export_to_ckl(self, checklist_data: Dict[str, Any], version: str = '1.0') -> str:
        """
        Export checklist data to CKL XML format.

        Args:
            checklist_data: Structured checklist data
            version: CKL version to export ('1.0' or '2.0')

        Returns:
            CKL XML content as string
        """
        try:
            if version == '1.0':
                return self._export_ckl_v1(checklist_data)
            elif version == '2.0':
                return self._export_ckl_v2(checklist_data)
            else:
                raise ValueError(f"Unsupported CKL version: {version}")

        except Exception as e:
            logger.error(f"Error exporting CKL: {str(e)}")
            raise

    def _export_ckl_v1(self, checklist_data: Dict[str, Any]) -> str:
        """Export to CKL version 1.0 format"""
        return self._export_ckl_common(checklist_data, '1.0')

    def _export_ckl_v2(self, checklist_data: Dict[str, Any]) -> str:
        """Export to CKL version 2.0 format"""
        # CKL 2.0 has similar structure but may include additional metadata
        return self._export_ckl_common(checklist_data, '2.0')

    def _export_ckl_common(self, checklist_data: Dict[str, Any], version: str) -> str:
        """Common export logic for both CKL versions"""
        # Create root CHECKLIST element
        root = ET.Element('CHECKLIST')

        # Add asset information
        asset_data = checklist_data.get('asset', {})
        asset_elem = self._create_asset_element(asset_data)
        root.append(asset_elem)

        # Add STIG information
        stigs_data = checklist_data.get('stigs', {})
        stigs_elem = self._create_stigs_element(stigs_data, checklist_data.get('vulnerabilities', []))
        root.append(stigs_elem)

        # Convert to string with proper formatting
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)

        # Add XML declaration and format
        xml_str = reparsed.toprettyxml(indent="  ", encoding=None)

        # Clean up extra whitespace
        lines = xml_str.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.strip():
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _create_asset_element(self, asset_data: Dict[str, Any]) -> ET.Element:
        """Create ASSET element from asset data"""
        asset_elem = ET.Element('ASSET')

        # Field mappings from internal data to CKL format
        field_mappings = {
            'host_name': 'HOST_NAME',
            'host_ip': 'HOST_IP',
            'host_mac': 'HOST_MAC',
            'host_fqdn': 'HOST_FQDN',
            'tech_area': 'TECH_AREA',
            'target_key': 'TARGET_KEY',
            'asset_type': 'ASSET_TYPE',
            'role': 'ROLE',
            'web_or_database': 'WEB_OR_DATABASE',
            'web_db_site': 'WEB_DB_SITE',
            'web_db_instance': 'WEB_DB_INSTANCE'
        }

        for internal_field, ckl_field in field_mappings.items():
            value = asset_data.get(internal_field)
            if value is not None:
                # Handle boolean conversion
                if internal_field == 'web_or_database':
                    value = 'true' if value else 'false'
                # Handle list conversion (IP addresses, MAC addresses)
                elif isinstance(value, list):
                    value = ', '.join(str(v) for v in value)

                elem = ET.SubElement(asset_elem, ckl_field)
                elem.text = str(value)

        return asset_elem

    def _create_stigs_element(self, stigs_data: Dict[str, Any], vulnerabilities: List[Dict[str, Any]]) -> ET.Element:
        """Create STIGS element from STIG data and vulnerabilities"""
        stigs_elem = ET.Element('STIGS')

        # Create iSTIG element
        istig_elem = ET.SubElement(stigs_elem, 'iSTIG')

        # Add STIG_INFO
        stig_info_data = stigs_data.get('stig_info', [])
        if stig_info_data:
            stig_info_elem = self._create_stig_info_element(stig_info_data)
            istig_elem.append(stig_info_elem)

        # Add STIG_DATA (vulnerability definitions)
        stig_data_list = stigs_data.get('stig_data', [])
        if stig_data_list:
            stig_data_elem = self._create_stig_data_element(stig_data_list)
            istig_elem.append(stig_data_elem)

        # Add VULN elements
        for vuln_data in vulnerabilities:
            vuln_elem = self._create_vuln_element(vuln_data)
            istig_elem.append(vuln_elem)

        return stigs_elem

    def _create_stig_info_element(self, stig_info_data: List[Dict[str, str]]) -> ET.Element:
        """Create STIG_INFO element"""
        stig_info_elem = ET.Element('STIG_INFO')

        for info_item in stig_info_data:
            si_data_elem = ET.SubElement(stig_info_elem, 'SI_DATA')

            sid_name_elem = ET.SubElement(si_data_elem, 'SID_NAME')
            sid_name_elem.text = info_item.get('sid_name', '')

            sid_data_elem = ET.SubElement(si_data_elem, 'SID_DATA')
            sid_data_elem.text = info_item.get('sid_data', '')

        return stig_info_elem

    def _create_stig_data_element(self, stig_data_list: List[Dict[str, str]]) -> ET.Element:
        """Create STIG_DATA element with vulnerability definitions"""
        stig_data_elem = ET.Element('STIG_DATA')

        for data_item in stig_data_list:
            vuln_data_elem = ET.SubElement(stig_data_elem, 'VULN_DATA')

            vuln_attribute_elem = ET.SubElement(vuln_data_elem, 'VULN_ATTRIBUTE')
            vuln_attribute_elem.text = data_item.get('vuln_attribute', '')

            attribute_data_elem = ET.SubElement(vuln_data_elem, 'ATTRIBUTE_DATA')
            attribute_data_elem.text = data_item.get('attribute_data', '')

        return stig_data_elem

    def _create_vuln_element(self, vuln_data: Dict[str, Any]) -> ET.Element:
        """Create VULN element for a vulnerability finding"""
        vuln_elem = ET.Element('VULN')

        # Add status
        status_elem = ET.SubElement(vuln_elem, 'STATUS')
        status_elem.text = vuln_data.get('status', 'NotReviewed')

        # Add finding details
        finding_details = vuln_data.get('finding_details', '')
        if finding_details:
            finding_elem = ET.SubElement(vuln_elem, 'FINDING_DETAILS')
            finding_elem.text = finding_details

        # Add comments
        comments = vuln_data.get('comments', '')
        if comments:
            comments_elem = ET.SubElement(vuln_elem, 'COMMENTS')
            comments_elem.text = comments

        # Add severity override
        severity_override = vuln_data.get('severity_override', '')
        if severity_override:
            override_elem = ET.SubElement(vuln_elem, 'SEVERITY_OVERRIDE')
            override_elem.text = severity_override

        # Add severity justification
        severity_justification = vuln_data.get('severity_justification', '')
        if severity_justification:
            justification_elem = ET.SubElement(vuln_elem, 'SEVERITY_JUSTIFICATION')
            justification_elem.text = severity_justification

        # Add STIG data
        stig_data = vuln_data.get('stig_data', [])
        if stig_data:
            stig_data_elem = ET.SubElement(vuln_elem, 'STIG_DATA')
            for data_item in stig_data:
                data_elem = ET.SubElement(stig_data_elem, 'DATA')

                vuln_attribute_elem = ET.SubElement(data_elem, 'VULN_ATTRIBUTE')
                vuln_attribute_elem.text = data_item.get('attribute', '')

                attribute_data_elem = ET.SubElement(data_elem, 'ATTRIBUTE_DATA')
                attribute_data_elem.text = data_item.get('data', '')

        return vuln_elem

    def create_sample_ckl_data(self) -> Dict[str, Any]:
        """Create sample CKL data for testing"""
        return {
            'version': '1.0',
            'asset': {
                'host_name': 'sample-server.local',
                'host_ip': '192.168.1.100',
                'host_mac': '00:11:22:33:44:55',
                'host_fqdn': 'sample-server.example.com',
                'tech_area': 'Application Review',
                'asset_type': 'Computing',
                'role': 'Member Server'
            },
            'stigs': {
                'stig_info': [
                    {'sid_name': 'version', 'sid_data': '1.0'},
                    {'sid_name': 'title', 'sid_data': 'Sample STIG'},
                    {'sid_name': 'description', 'sid_data': 'Sample STIG for testing'}
                ],
                'stig_data': [
                    {'vuln_attribute': 'Rule_ID', 'attribute_data': 'SV-12345'},
                    {'vuln_attribute': 'Severity', 'attribute_data': 'medium'},
                    {'vuln_attribute': 'Title', 'attribute_data': 'Sample Rule'}
                ]
            },
            'vulnerabilities': [
                {
                    'status': 'NotAFinding',
                    'finding_details': 'No issues found',
                    'comments': 'System is compliant',
                    'stig_data': [
                        {'attribute': 'Rule_ID', 'data': 'SV-12345'},
                        {'attribute': 'Severity', 'data': 'medium'},
                        {'attribute': 'Title', 'data': 'Sample Rule'}
                    ]
                }
            ]
        }

    def validate_export_data(self, checklist_data: Dict[str, Any]) -> List[str]:
        """Validate data before export"""
        errors = []

        # Check required fields
        if 'asset' not in checklist_data:
            errors.append("Missing asset information")

        if 'stigs' not in checklist_data:
            errors.append("Missing STIG information")

        # Validate asset information
        asset = checklist_data.get('asset', {})
        if not asset.get('host_name'):
            errors.append("Missing host_name in asset information")

        # Validate STIG information
        stigs = checklist_data.get('stigs', {})
        stig_info = stigs.get('stig_info', [])
        if not stig_info:
            errors.append("Missing STIG_INFO data")

        return errors
