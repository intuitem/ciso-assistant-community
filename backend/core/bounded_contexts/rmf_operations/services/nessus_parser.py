"""
Nessus Parser Service

Service for parsing Nessus ACAS vulnerability scan XML files.
Extracts scan metadata, host information, and vulnerability findings
for correlation with STIG checklists.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


class NessusParser:
    """
    Parser for Nessus ACAS XML vulnerability scan files.

    Extracts comprehensive scan metadata and vulnerability data
    for integration with RMF compliance workflows.
    """

    def __init__(self):
        """Initialize the Nessus parser"""
        self.supported_versions = ['2.0']  # Nessus XML format version

    def parse_nessus_file(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse Nessus XML file and return structured data.

        Args:
            xml_content: Raw Nessus XML content as string

        Returns:
            Dict containing parsed scan data

        Raises:
            ValidationError: If Nessus file is invalid
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            # Validate Nessus format
            self._validate_nessus_format(root)

            # Extract scan data
            scan_data = {
                'metadata': self._extract_scan_metadata(root),
                'hosts': self._extract_hosts(root),
                'vulnerabilities': self._extract_vulnerabilities(root),
                'statistics': self._calculate_statistics(root),
                'parsing_info': {
                    'parsed_at': timezone.now().isoformat(),
                    'parser_version': '1.0',
                    'xml_size': len(xml_content)
                }
            }

            return scan_data

        except ET.ParseError as e:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Invalid XML format: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing Nessus file: {str(e)}")
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Failed to parse Nessus file: {str(e)}")

    def _validate_nessus_format(self, root: ET.Element) -> None:
        """Validate that this is a proper Nessus file"""
        # Check for root NessusClientData_v2 element
        if root.tag != 'NessusClientData_v2':
            raise ValidationError("Invalid Nessus format: Root element must be 'NessusClientData_v2'")

        # Check for required child elements
        required_elements = ['Policy', 'Report']
        for element in required_elements:
            if root.find(element) is None:
                raise ValidationError(f"Invalid Nessus format: Missing required element '{element}'")

    def _extract_scan_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Extract scan metadata from Nessus file"""
        metadata = {}

        # Policy information
        policy_elem = root.find('Policy')
        if policy_elem is not None:
            metadata['policy_name'] = policy_elem.findtext('policyName', '')
            metadata['policy_comments'] = policy_elem.findtext('policyComments', '')

            # Server preferences
            server_preferences = {}
            for pref in policy_elem.findall('.//preference'):
                name = pref.findtext('name', '')
                value = pref.findtext('value', '')
                if name and value:
                    server_preferences[name] = value
            metadata['server_preferences'] = server_preferences

        # Report information
        report_elem = root.find('Report')
        if report_elem is not None:
            metadata['report_name'] = report_elem.get('name', '')

        # Scanner information (from server preferences or other sources)
        server_prefs = metadata.get('server_preferences', {})
        metadata['scanner_version'] = server_prefs.get('sc_version', '')
        metadata['scanner_build'] = server_prefs.get('sc_build', '')

        # Try to extract scan date from various sources
        scan_date = self._extract_scan_date(root)
        if scan_date:
            metadata['scan_date'] = scan_date.isoformat()

        return metadata

    def _extract_scan_date(self, root: ET.Element) -> Optional[datetime]:
        """Extract scan date from various possible locations"""
        # Try to get from server preferences
        policy_elem = root.find('Policy')
        if policy_elem is not None:
            server_prefs = policy_elem.find('Preferences')
            if server_prefs is not None:
                for pref in server_prefs.findall('ServerPreferences/preference'):
                    name = pref.findtext('name', '')
                    if name == 'scan_start_timestamp':
                        value = pref.findtext('value', '')
                        try:
                            # Nessus timestamp is typically Unix timestamp
                            return datetime.fromtimestamp(int(value))
                        except (ValueError, TypeError):
                            pass

        # Fallback: use current time (scan might be recent)
        return None

    def _extract_hosts(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract host information from Nessus scan"""
        hosts = []

        report_elem = root.find('Report')
        if report_elem is None:
            return hosts

        for host_elem in report_elem.findall('ReportHost'):
            host_data = {
                'name': host_elem.get('name', ''),
                'properties': {},
                'vulnerabilities': []
            }

            # Extract host properties
            for tag_elem in host_elem.findall('HostProperties/tag'):
                name = tag_elem.get('name', '')
                value = tag_elem.text or ''
                host_data['properties'][name] = value

            # Extract vulnerability summaries for this host
            vuln_count = {}
            for item_elem in host_elem.findall('ReportItem'):
                severity = item_elem.get('severity', '0')
                vuln_count[severity] = vuln_count.get(severity, 0) + 1

            host_data['vulnerability_summary'] = vuln_count
            host_data['total_vulnerabilities'] = sum(vuln_count.values())

            hosts.append(host_data)

        return hosts

    def _extract_vulnerabilities(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract vulnerability findings from Nessus scan"""
        vulnerabilities = []

        report_elem = root.find('Report')
        if report_elem is None:
            return vulnerabilities

        for host_elem in report_elem.findall('ReportHost'):
            host_name = host_elem.get('name', '')

            for item_elem in host_elem.findall('ReportItem'):
                vuln_data = {
                    'host_name': host_name,
                    'plugin_id': item_elem.get('pluginID', ''),
                    'plugin_name': item_elem.get('pluginName', ''),
                    'plugin_family': item_elem.get('pluginFamily', ''),
                    'severity': item_elem.get('severity', '0'),
                    'severity_text': self._severity_to_text(item_elem.get('severity', '0')),
                    'protocol': item_elem.get('protocol', ''),
                    'port': item_elem.get('port', ''),
                    'service': item_elem.get('svc_name', ''),
                    'plugin_publication_date': item_elem.findtext('plugin_publication_date', ''),
                    'plugin_modification_date': item_elem.findtext('plugin_modification_date', ''),
                    'cvss_base_score': item_elem.findtext('cvss_base_score', ''),
                    'cvss_temporal_score': item_elem.findtext('cvss_temporal_score', ''),
                    'cvss_vector': item_elem.findtext('cvss_vector', ''),
                    'risk_factor': item_elem.findtext('risk_factor', ''),
                    'synopsis': item_elem.findtext('synopsis', ''),
                    'description': item_elem.findtext('description', ''),
                    'solution': item_elem.findtext('solution', ''),
                    'plugin_output': item_elem.findtext('plugin_output', ''),
                    'see_also': item_elem.findtext('see_also', ''),
                    'cve': self._extract_cve_list(item_elem),
                    'bid': self._extract_bid_list(item_elem),
                    'xref': self._extract_xref_list(item_elem),
                    'tags': {}
                }

                # Extract additional tags
                for tag_elem in item_elem.findall('tag'):
                    key = tag_elem.get('key', '')
                    value = tag_elem.text or ''
                    if key:
                        vuln_data['tags'][key] = value

                vulnerabilities.append(vuln_data)

        return vulnerabilities

    def _severity_to_text(self, severity: str) -> str:
        """Convert Nessus severity number to text"""
        severity_map = {
            '0': 'Info',
            '1': 'Low',
            '2': 'Medium',
            '3': 'High',
            '4': 'Critical'
        }
        return severity_map.get(severity, 'Unknown')

    def _extract_cve_list(self, item_elem: ET.Element) -> List[str]:
        """Extract CVE list from vulnerability item"""
        cves = []
        cve_elem = item_elem.find('cve')
        if cve_elem is not None and cve_elem.text:
            # CVEs might be comma-separated
            cves = [cve.strip() for cve in cve_elem.text.split(',') if cve.strip()]
        return cves

    def _extract_bid_list(self, item_elem: ET.Element) -> List[str]:
        """Extract BID list from vulnerability item"""
        bids = []
        bid_elem = item_elem.find('bid')
        if bid_elem is not None and bid_elem.text:
            bids = [bid.strip() for bid in bid_elem.text.split(',') if bid.strip()]
        return bids

    def _extract_xref_list(self, item_elem: ET.Element) -> List[str]:
        """Extract cross-reference list from vulnerability item"""
        xrefs = []
        xref_elem = item_elem.find('xref')
        if xref_elem is not None and xref_elem.text:
            xrefs = [xref.strip() for xref in xref_elem.text.split(',') if xref.strip()]
        return xrefs

    def _calculate_statistics(self, root: ET.Element) -> Dict[str, Any]:
        """Calculate scan statistics"""
        stats = {
            'total_hosts': 0,
            'total_vulnerabilities': 0,
            'severity_breakdown': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            },
            'plugin_families': {},
            'scan_duration_seconds': None
        }

        report_elem = root.find('Report')
        if report_elem is not None:
            hosts = report_elem.findall('ReportHost')
            stats['total_hosts'] = len(hosts)

            for host_elem in hosts:
                for item_elem in host_elem.findall('ReportItem'):
                    stats['total_vulnerabilities'] += 1

                    severity = item_elem.get('severity', '0')
                    severity_text = self._severity_to_text(severity)
                    severity_key = severity_text.lower()
                    if severity_key in stats['severity_breakdown']:
                        stats['severity_breakdown'][severity_key] += 1

                    # Count plugin families
                    plugin_family = item_elem.get('pluginFamily', 'Unknown')
                    stats['plugin_families'][plugin_family] = stats['plugin_families'].get(plugin_family, 0) + 1

        return stats

    def extract_scan_summary(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary information from parsed scan data"""
        metadata = scan_data.get('metadata', {})
        statistics = scan_data.get('statistics', {})

        summary = {
            'scan_date': metadata.get('scan_date'),
            'scanner_version': metadata.get('scanner_version'),
            'policy_name': metadata.get('policy_name'),
            'total_hosts': statistics.get('total_hosts', 0),
            'total_vulnerabilities': statistics.get('total_vulnerabilities', 0),
            'severity_breakdown': statistics.get('severity_breakdown', {}),
            'top_plugin_families': self._get_top_plugin_families(statistics),
            'risk_score': self._calculate_risk_score(statistics)
        }

        return summary

    def _get_top_plugin_families(self, statistics: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top plugin families by vulnerability count"""
        families = statistics.get('plugin_families', {})
        sorted_families = sorted(families.items(), key=lambda x: x[1], reverse=True)
        return [
            {'family': family, 'count': count}
            for family, count in sorted_families[:limit]
        ]

    def _calculate_risk_score(self, statistics: Dict[str, Any]) -> float:
        """Calculate overall risk score based on vulnerability severities"""
        breakdown = statistics.get('severity_breakdown', {})
        weights = {
            'critical': 4.0,
            'high': 3.0,
            'medium': 2.0,
            'low': 1.0,
            'info': 0.1
        }

        total_weighted_score = 0
        total_vulns = 0

        for severity, count in breakdown.items():
            weight = weights.get(severity, 0)
            total_weighted_score += weight * count
            total_vulns += count

        return total_weighted_score / max(total_vulns, 1)  # Avoid division by zero

    def validate_nessus_data(self, scan_data: Dict[str, Any]) -> List[str]:
        """Validate parsed Nessus scan data"""
        errors = []

        if not scan_data.get('metadata'):
            errors.append("Missing scan metadata")

        if not scan_data.get('hosts'):
            errors.append("No host data found in scan")

        statistics = scan_data.get('statistics', {})
        if statistics.get('total_hosts', 0) == 0:
            errors.append("No hosts detected in scan")

        if statistics.get('total_vulnerabilities', 0) == 0:
            errors.append("No vulnerabilities found (scan may be incomplete)")

        return errors
