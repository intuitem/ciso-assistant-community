"""
Unit tests for CKL Parser Service
"""

import pytest
from django.core.exceptions import ValidationError

from ..services.ckl_parser import CKLParser


class TestCKLParser:
    """Test CKLParser service."""

    def setup_method(self):
        """Set up test fixtures"""
        self.parser = CKLParser()

    def test_parse_valid_ckl_v1(self):
        """Test parsing a valid CKL v1.0 file"""
        ckl_content = self._get_sample_ckl_v1()
        result = self.parser.parse_ckl_file(ckl_content)

        assert result['version'] == '1.0'
        assert 'asset' in result
        assert 'stigs' in result
        assert 'vulnerabilities' in result
        assert 'metadata' in result

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML"""
        with pytest.raises(ValidationError, match="Invalid XML format"):
            self.parser.parse_ckl_file("<invalid>xml")

    def test_parse_invalid_ckl_format(self):
        """Test parsing XML that looks like XML but isn't CKL"""
        xml_content = "<root><data>test</data></root>"
        with pytest.raises(ValidationError, match="Invalid CKL format"):
            self.parser.parse_ckl_file(xml_content)

    def test_extract_asset_info(self):
        """Test extracting asset information from CKL"""
        ckl_content = self._get_sample_ckl_v1()
        result = self.parser.parse_ckl_file(ckl_content)

        asset = result['asset']
        assert asset['host_name'] == 'test-server.local'
        assert asset['host_ip'] == ['192.168.1.100', '192.168.1.101']
        assert asset['tech_area'] == 'Application Review'
        assert asset['web_or_database'] is True

    def test_extract_stig_info(self):
        """Test extracting STIG information from CKL"""
        ckl_content = self._get_sample_ckl_v1()
        result = self.parser.parse_ckl_file(ckl_content)

        stigs = result['stigs']
        assert 'stig_info' in stigs
        assert 'stig_data' in stigs

        stig_info = stigs['stig_info']
        assert len(stig_info) > 0

        # Check for required fields
        field_names = {item['sid_name'].lower() for item in stig_info}
        assert 'version' in field_names
        assert 'title' in field_names

    def test_extract_vulnerabilities(self):
        """Test extracting vulnerabilities from CKL"""
        ckl_content = self._get_sample_ckl_v1()
        result = self.parser.parse_ckl_file(ckl_content)

        vulnerabilities = result['vulnerabilities']
        assert isinstance(vulnerabilities, list)
        assert len(vulnerabilities) > 0

        vuln = vulnerabilities[0]
        assert 'status' in vuln
        assert 'stig_data' in vuln

    def test_validate_ckl_structure(self):
        """Test validating CKL structure"""
        ckl_content = self._get_sample_ckl_v1()
        result = self.parser.parse_ckl_file(ckl_content)

        errors = self.parser.validate_ckl_structure(result)
        assert len(errors) == 0  # Should be valid

    def test_validate_invalid_structure(self):
        """Test validating invalid CKL structure"""
        invalid_data = {'version': '1.0'}  # Missing required fields

        errors = self.parser.validate_ckl_structure(invalid_data)
        assert len(errors) > 0
        assert any('asset' in error.lower() for error in errors)

    def test_extract_checklist_summary(self):
        """Test extracting checklist summary"""
        ckl_content = self._get_sample_ckl_v1()
        result = self.parser.parse_ckl_file(ckl_content)

        summary = self.parser.extract_checklist_summary(result)

        assert 'host_name' in summary
        assert 'stig_type' in summary
        assert 'total_vulnerabilities' in summary
        assert 'open_findings' in summary
        assert 'severity_breakdown' in summary

    def _get_sample_ckl_v1(self):
        """Get sample CKL v1.0 content for testing"""
        return '''<?xml version="1.0" encoding="utf-8"?>
<CHECKLIST>
  <ASSET>
    <HOST_NAME>test-server.local</HOST_NAME>
    <HOST_IP>192.168.1.100,192.168.1.101</HOST_IP>
    <HOST_MAC>00:11:22:33:44:55</HOST_MAC>
    <TECH_AREA>Application Review</TECH_AREA>
    <ASSET_TYPE>Computing</ASSET_TYPE>
    <WEB_OR_DATABASE>true</WEB_OR_DATABASE>
    <WEB_DB_SITE>MyApp</WEB_DB_SITE>
    <WEB_DB_INSTANCE>Production</WEB_DB_INSTANCE>
  </ASSET>
  <STIGS>
    <iSTIG>
      <STIG_INFO>
        <SI_DATA>
          <SID_NAME>version</SID_NAME>
          <SID_DATA>1.0</SID_DATA>
        </SI_DATA>
        <SI_DATA>
          <SID_NAME>title</SID_NAME>
          <SID_DATA>Sample STIG</SID_DATA>
        </SI_DATA>
        <SI_DATA>
          <SID_NAME>description</SID_NAME>
          <SID_DATA>Sample STIG for testing</SID_DATA>
        </SI_DATA>
      </STIG_INFO>
      <STIG_DATA>
        <VULN_DATA>
          <VULN_ATTRIBUTE>Rule_ID</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SV-12345</ATTRIBUTE_DATA>
        </VULN_DATA>
        <VULN_DATA>
          <VULN_ATTRIBUTE>Severity</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>medium</ATTRIBUTE_DATA>
        </VULN_DATA>
      </STIG_DATA>
      <VULN>
        <STIG_DATA>
          <DATA>
            <VULN_ATTRIBUTE>Rule_ID</VULN_ATTRIBUTE>
            <ATTRIBUTE_DATA>SV-12345</ATTRIBUTE_DATA>
          </DATA>
          <DATA>
            <VULN_ATTRIBUTE>Severity</VULN_ATTRIBUTE>
            <ATTRIBUTE_DATA>medium</ATTRIBUTE_DATA>
          </DATA>
        </STIG_DATA>
        <STATUS>NotAFinding</STATUS>
        <FINDING_DETAILS>No issues found</FINDING_DETAILS>
        <COMMENTS>System is compliant</COMMENTS>
      </VULN>
    </iSTIG>
  </STIGS>
</CHECKLIST>'''

    def _get_sample_ckl_v2(self):
        """Get sample CKL v2.0 content for testing"""
        # CKL v2.0 has similar structure but may include additional metadata
        return self._get_sample_ckl_v1().replace(
            '<SID_DATA>1.0</SID_DATA>',
            '<SID_DATA>2.0</SID_DATA>'
        )
