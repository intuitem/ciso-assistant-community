"""
CKL Parser Service

Service for parsing and validating STIG checklist files in CKL (Checklist) XML format.
Supports both CKL v1.0 and v2.0 formats used by SCAP tools.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger(__name__)


class CKLParser:
    """
    CKL (Checklist) XML parser for STIG files.

    Supports parsing STIG checklists exported from SCAP tools like:
    - SCAP Compliance Checker (SCC)
    - STIG Viewer
    - OpenSCAP
    """

    # CKL XML namespaces
    NAMESPACES = {
        'ckl': 'http://checklists.nist.gov/xccdf/1.1',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

    def __init__(self):
        """Initialize the CKL parser"""
        self.supported_versions = ['1.0', '2.0']

    def parse_ckl_file(self, ckl_content: str) -> Dict[str, Any]:
        """
        Parse CKL file content and return structured data.

        Args:
            ckl_content: Raw CKL XML content as string

        Returns:
            Dict containing parsed checklist data

        Raises:
            ValidationError: If CKL file is invalid or unsupported
        """
        try:
            # Parse XML
            root = ET.fromstring(ckl_content)

            # Validate CKL format
            self._validate_ckl_format(root)

            # Extract version
            version = self._extract_version(root)

            # Parse based on version
            if version == '1.0':
                return self._parse_ckl_v1(root)
            elif version == '2.0':
                return self._parse_ckl_v2(root)
            else:
                raise ValidationError(f"Unsupported CKL version: {version}")

        except ET.ParseError as e:
            raise ValidationError(f"Invalid XML format: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing CKL file: {str(e)}")
            raise ValidationError(f"Failed to parse CKL file: {str(e)}")

    def _validate_ckl_format(self, root: ET.Element) -> None:
        """Validate that this is a proper CKL file"""
        # Check for CHECKLIST root element
        if root.tag != 'CHECKLIST':
            raise ValidationError("Invalid CKL format: Root element must be 'CHECKLIST'")

        # Check for required child elements
        required_elements = ['ASSET', 'STIGS']
        for element in required_elements:
            if root.find(element) is None:
                raise ValidationError(f"Invalid CKL format: Missing required element '{element}'")

    def _extract_version(self, root: ET.Element) -> str:
        """Extract CKL version from the file"""
        # Look for version in STIG_INFO
        stigs_elem = root.find('STIGS')
        if stigs_elem is not None:
            stig_info = stigs_elem.find('iSTIG/STIG_INFO')
            if stig_info is not None:
                for si_data in stig_info.findall('SI_DATA'):
                    sid_name = si_data.find('SID_NAME')
                    sid_data = si_data.find('SID_DATA')

                    if (sid_name is not None and sid_data is not None and
                        sid_name.text == 'version'):
                        return sid_data.text

        # Default to 1.0 if version not found
        logger.warning("CKL version not found, defaulting to 1.0")
        return '1.0'

    def _parse_ckl_v1(self, root: ET.Element) -> Dict[str, Any]:
        """Parse CKL version 1.0 format"""
        return self._parse_ckl_common(root, '1.0')

    def _parse_ckl_v2(self, root: ET.Element) -> Dict[str, Any]:
        """Parse CKL version 2.0 format"""
        # CKL 2.0 has similar structure but may have additional fields
        return self._parse_ckl_common(root, '2.0')

    def _parse_ckl_common(self, root: ET.Element, version: str) -> Dict[str, Any]:
        """Common parsing logic for both CKL versions"""
        checklist_data = {
            'version': version,
            'asset': self._parse_asset_info(root.find('ASSET')),
            'stigs': self._parse_stigs_info(root.find('STIGS')),
            'vulnerabilities': self._parse_vulnerabilities(root.find('STIGS')),
            'metadata': {
                'parsed_at': timezone.now().isoformat(),
                'parser_version': '1.0',
                'ckl_version': version
            }
        }

        return checklist_data

    def _parse_asset_info(self, asset_elem: ET.Element) -> Dict[str, Any]:
        """Parse asset information from CKL"""
        if asset_elem is None:
            return {}

        asset_data = {}

        # Standard asset fields
        field_mappings = {
            'HOST_NAME': 'host_name',
            'HOST_IP': 'host_ip',
            'HOST_MAC': 'host_mac',
            'HOST_FQDN': 'host_fqdn',
            'TECH_AREA': 'tech_area',
            'TARGET_KEY': 'target_key',
            'ASSET_TYPE': 'asset_type',
            'ROLE': 'role',
            'WEB_OR_DATABASE': 'web_or_database',
            'WEB_DB_SITE': 'web_db_site',
            'WEB_DB_INSTANCE': 'web_db_instance'
        }

        for ckl_field, data_field in field_mappings.items():
            elem = asset_elem.find(ckl_field)
            if elem is not None and elem.text:
                asset_data[data_field] = elem.text.strip()

        # Handle special cases
        if 'web_or_database' in asset_data:
            asset_data['web_or_database'] = asset_data['web_or_database'].lower() == 'true'

        # Determine asset type based on ASSET_TYPE, TECH_AREA, and WEB_OR_DATABASE
        asset_type = asset_data.get('asset_type', '').lower()
        tech_area = asset_data.get('tech_area', '').lower()
        is_web_db = asset_data.get('web_or_database', False)

        if is_web_db:
            # Web/database instances get special classification
            if 'web' in tech_area.lower() or 'application' in tech_area.lower():
                asset_data['inferred_asset_type'] = 'web_server'
            elif 'database' in tech_area.lower() or 'db' in tech_area.lower():
                asset_data['inferred_asset_type'] = 'database'
            else:
                asset_data['inferred_asset_type'] = 'application'
        elif asset_type == 'computing':
            if 'server' in tech_area:
                asset_data['inferred_asset_type'] = 'computing'
            elif 'workstation' in tech_area:
                asset_data['inferred_asset_type'] = 'computing'
            else:
                asset_data['inferred_asset_type'] = 'computing'
        elif asset_type == 'network':
            asset_data['inferred_asset_type'] = 'network'
        elif asset_type == 'storage':
            asset_data['inferred_asset_type'] = 'storage'
        else:
            # Default classification based on tech area keywords
            if any(keyword in tech_area for keyword in ['web', 'http', 'apache', 'nginx', 'iis']):
                asset_data['inferred_asset_type'] = 'web_server'
            elif any(keyword in tech_area for keyword in ['database', 'sql', 'oracle', 'mysql', 'postgres']):
                asset_data['inferred_asset_type'] = 'database'
            elif any(keyword in tech_area for keyword in ['network', 'switch', 'router', 'firewall']):
                asset_data['inferred_asset_type'] = 'network'
            elif any(keyword in tech_area for keyword in ['storage', 'nas', 'san']):
                asset_data['inferred_asset_type'] = 'storage'
            else:
                asset_data['inferred_asset_type'] = 'computing'  # Default

        # Handle comma-separated lists
        for field in ['host_ip', 'host_mac']:
            if field in asset_data and ',' in asset_data[field]:
                asset_data[field] = [ip.strip() for ip in asset_data[field].split(',') if ip.strip()]

        return asset_data

    def _parse_stigs_info(self, stigs_elem: ET.Element) -> Dict[str, Any]:
        """Parse STIG information from CKL"""
        if stigs_elem is None:
            return {}

        stigs_data = {}

        # Find iSTIG element
        istig_elem = stigs_elem.find('iSTIG')
        if istig_elem is None:
            return stigs_data

        # Parse STIG_INFO
        stig_info_elem = istig_elem.find('STIG_INFO')
        if stig_info_elem is not None:
            stigs_data['stig_info'] = self._parse_stig_info(stig_info_elem)

        # Parse STIG_DATA (vulnerability definitions)
        stig_data_elem = istig_elem.find('STIG_DATA')
        if stig_data_elem is not None:
            stigs_data['stig_data'] = []
            for vuln_data in stig_data_elem:
                stigs_data['stig_data'].append({
                    'vuln_attribute': vuln_data.find('VULN_ATTRIBUTE').text if vuln_data.find('VULN_ATTRIBUTE') is not None else '',
                    'attribute_data': vuln_data.find('ATTRIBUTE_DATA').text if vuln_data.find('ATTRIBUTE_DATA') is not None else ''
                })

        return stigs_data

    def _parse_stig_info(self, stig_info_elem: ET.Element) -> List[Dict[str, str]]:
        """Parse STIG_INFO section"""
        stig_info = []

        for si_data in stig_info_elem.findall('SI_DATA'):
            sid_name = si_data.find('SID_NAME')
            sid_data = si_data.find('SID_DATA')

            if sid_name is not None and sid_data is not None:
                stig_info.append({
                    'sid_name': sid_name.text or '',
                    'sid_data': sid_data.text or ''
                })

        return stig_info

    def _parse_vulnerabilities(self, stigs_elem: ET.Element) -> List[Dict[str, Any]]:
        """Parse vulnerability findings from CKL"""
        vulnerabilities = []

        if stigs_elem is None:
            return vulnerabilities

        # Find VULN elements
        vuln_elements = stigs_elem.findall('.//VULN')
        for vuln_elem in vuln_elements:
            vuln_data = self._parse_single_vulnerability(vuln_elem)
            if vuln_data:
                vulnerabilities.append(vuln_data)

        return vulnerabilities

    def _parse_single_vulnerability(self, vuln_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a single vulnerability element"""
        try:
            vuln_data = {}

            # Status
            status_elem = vuln_elem.find('STATUS')
            vuln_data['status'] = status_elem.text if status_elem is not None else 'NotReviewed'

            # Finding details
            finding_details_elem = vuln_elem.find('FINDING_DETAILS')
            vuln_data['finding_details'] = finding_details_elem.text if finding_details_elem is not None else ''

            # Comments
            comments_elem = vuln_elem.find('COMMENTS')
            vuln_data['comments'] = comments_elem.text if comments_elem is not None else ''

            # Severity override
            severity_override_elem = vuln_elem.find('SEVERITY_OVERRIDE')
            vuln_data['severity_override'] = severity_override_elem.text if severity_override_elem is not None else ''

            # Severity justification
            severity_justification_elem = vuln_elem.find('SEVERITY_JUSTIFICATION')
            vuln_data['severity_justification'] = severity_justification_elem.text if severity_justification_elem is not None else ''

            # STIG data (vulnerability attributes)
            stig_data = []
            stig_data_elem = vuln_elem.find('STIG_DATA')
            if stig_data_elem is not None:
                for data_elem in stig_data_elem:
                    stig_data.append({
                        'attribute': data_elem.find('VULN_ATTRIBUTE').text if data_elem.find('VULN_ATTRIBUTE') is not None else '',
                        'data': data_elem.find('ATTRIBUTE_DATA').text if data_elem.find('ATTRIBUTE_DATA') is not None else ''
                    })
            vuln_data['stig_data'] = stig_data

            # Extract key fields from STIG data
            vuln_data.update(self._extract_key_fields_from_stig_data(stig_data))

            return vuln_data

        except Exception as e:
            logger.warning(f"Error parsing vulnerability: {str(e)}")
            return None

    def _extract_key_fields_from_stig_data(self, stig_data: List[Dict[str, str]]) -> Dict[str, str]:
        """Extract key vulnerability fields from STIG data"""
        fields = {}

        # Common STIG data indices (these can vary by STIG)
        field_mappings = {
            0: 'version',
            1: 'classification',
            2: 'customname',
            3: 'stigid',
            4: 'severity',
            5: 'weight',
            6: 'title',
            7: 'description',
            8: 'check_content',
            9: 'fix_text',
            10: 'cci_ref'
        }

        for i, data_item in enumerate(stig_data):
            if i in field_mappings and data_item.get('data'):
                fields[field_mappings[i]] = data_item['data']

        # Additional fields that may be at different indices
        for data_item in stig_data:
            attr = data_item.get('attribute', '').lower()
            data = data_item.get('data', '')

            if 'vuln_num' in attr or 'rule_id' in attr:
                fields['rule_id'] = data
            elif 'severity' in attr and 'severity' not in fields:
                fields['severity'] = data
            elif 'title' in attr and 'title' not in fields:
                fields['title'] = data

        return fields

    def validate_ckl_structure(self, checklist_data: Dict[str, Any]) -> List[str]:
        """Validate the structure of parsed CKL data"""
        errors = []

        # Check required fields
        if 'asset' not in checklist_data:
            errors.append("Missing asset information")

        if 'stigs' not in checklist_data:
            errors.append("Missing STIG information")

        if 'vulnerabilities' not in checklist_data:
            errors.append("Missing vulnerabilities")

        # Validate asset information
        asset = checklist_data.get('asset', {})
        if not asset.get('host_name'):
            errors.append("Missing or empty host_name in asset information")

        # Validate STIG information
        stigs = checklist_data.get('stigs', {})
        stig_info = stigs.get('stig_info', [])
        if not stig_info:
            errors.append("Missing STIG_INFO data")

        # Check for required STIG metadata
        required_stig_fields = ['version', 'title', 'description']
        stig_fields_present = {item['sid_name'].lower() for item in stig_info}
        for field in required_stig_fields:
            if field not in stig_fields_present:
                errors.append(f"Missing required STIG field: {field}")

        return errors

    def extract_checklist_summary(self, checklist_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary information from parsed CKL data"""
        summary = {
            'host_name': '',
            'stig_type': '',
            'stig_version': '',
            'total_vulnerabilities': 0,
            'open_findings': 0,
            'severity_breakdown': {'high': 0, 'medium': 0, 'low': 0}
        }

        # Asset information
        asset = checklist_data.get('asset', {})
        summary['host_name'] = asset.get('host_name', '')

        # STIG information
        stigs = checklist_data.get('stigs', {})
        stig_info = stigs.get('stig_info', [])

        for item in stig_info:
            if item['sid_name'].lower() == 'title':
                summary['stig_type'] = item['sid_data']
            elif item['sid_name'].lower() == 'version':
                summary['stig_version'] = item['sid_data']

        # Vulnerability summary
        vulnerabilities = checklist_data.get('vulnerabilities', [])
        summary['total_vulnerabilities'] = len(vulnerabilities)

        for vuln in vulnerabilities:
            if vuln.get('status') == 'Open':
                summary['open_findings'] += 1

            severity = vuln.get('severity', '').lower()
            if severity in ['high', 'cat i']:
                summary['severity_breakdown']['high'] += 1
            elif severity in ['medium', 'cat ii']:
                summary['severity_breakdown']['medium'] += 1
            elif severity in ['low', 'cat iii']:
                summary['severity_breakdown']['low'] += 1

        return summary
