"""
SSP Word Document Importer

Service for importing FedRAMP SSP Word documents back into CISO Assistant.
Converts DOCX files to OSCAL SSP format and imports into the system.
"""

import logging
import zipfile
import xml.etree.ElementTree as ET
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re
import json
from datetime import datetime

from django.utils import timezone
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class SSPWordImporter:
    """
    Imports FedRAMP SSP Word documents into CISO Assistant.

    Parses DOCX files, extracts structured content, converts to OSCAL SSP,
    and imports into CISO Assistant entities.
    """

    def __init__(self):
        """Initialize SSP Word importer"""
        self.namespaces = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }

    def import_docx_file(self, docx_path: str) -> Dict[str, Any]:
        """
        Import SSP from Word document.

        Args:
            docx_path: Path to the DOCX file

        Returns:
            Import results with OSCAL SSP data and CISO Assistant entities
        """
        try:
            # Extract document content
            document_xml = self._extract_document_xml(docx_path)
            if not document_xml:
                raise ValueError("Could not extract document content from DOCX file")

            # Parse document structure
            parsed_content = self._parse_document_structure(document_xml)

            # Convert to OSCAL SSP format
            oscal_ssp = self._convert_to_oscal_ssp(parsed_content)

            # Validate OSCAL structure
            validation_result = self._validate_oscal_ssp(oscal_ssp)

            if not validation_result['valid']:
                logger.warning(f"OSCAL validation issues: {validation_result['errors']}")

            # Convert to CISO Assistant entities
            ciso_entities = self._convert_to_ciso_entities(oscal_ssp)

            return {
                'success': True,
                'oscal_ssp': oscal_ssp,
                'parsed_content': parsed_content,
                'validation': validation_result,
                'ciso_entities': ciso_entities,
                'import_metadata': {
                    'source_file': docx_path,
                    'import_timestamp': timezone.now().isoformat(),
                    'parser_version': '1.0',
                    'document_sections': len(parsed_content.get('sections', []))
                }
            }

        except Exception as e:
            logger.error(f"Error importing SSP Word document {docx_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'docx_path': docx_path
            }

    def _extract_document_xml(self, docx_path: str) -> Optional[str]:
        """
        Extract document.xml from DOCX file.

        Args:
            docx_path: Path to DOCX file

        Returns:
            Document XML content as string
        """
        try:
            with zipfile.ZipFile(docx_path, 'r') as docx:
                # Extract document.xml
                with docx.open('word/document.xml') as f:
                    return f.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error extracting document.xml from {docx_path}: {e}")
            return None

    def _parse_document_structure(self, document_xml: str) -> Dict[str, Any]:
        """
        Parse Word document XML structure into structured content.

        Args:
            document_xml: Raw document XML

        Returns:
            Structured content dictionary
        """
        try:
            root = ET.fromstring(document_xml)

            # Extract document sections
            sections = self._extract_sections(root)

            # Extract headers and footers
            headers = self._extract_headers_and_footers(root)

            # Extract tables
            tables = self._extract_tables(root)

            # Extract lists
            lists = self._extract_lists(root)

            # Extract images and other media (placeholder)
            media = self._extract_media(root)

            return {
                'sections': sections,
                'headers': headers,
                'tables': tables,
                'lists': lists,
                'media': media,
                'metadata': self._extract_metadata(root)
            }

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return {}

    def _extract_sections(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Extract document sections with headings and content.

        Args:
            root: XML root element

        Returns:
            List of sections with headings and content
        """
        sections = []
        current_section = None
        current_content = []

        # Find all paragraphs
        for para in root.findall('.//w:p', self.namespaces):
            text_content = self._extract_paragraph_text(para)

            if not text_content.strip():
                continue

            # Check if this is a heading
            style = self._get_paragraph_style(para)
            if self._is_heading_style(style):
                # Save previous section
                if current_section:
                    current_section['content'] = '\n'.join(current_content)
                    sections.append(current_section)

                # Start new section
                heading_level = self._get_heading_level(style)
                current_section = {
                    'heading': text_content,
                    'level': heading_level,
                    'style': style
                }
                current_content = []
            else:
                # Add to current section content
                if current_section:
                    current_content.append(text_content)

        # Add final section
        if current_section:
            current_section['content'] = '\n'.join(current_content)
            sections.append(current_section)

        return sections

    def _extract_headers_and_footers(self, root: ET.Element) -> Dict[str, Any]:
        """Extract headers and footers"""
        # Placeholder - would need to extract from separate header/footer XML files
        return {
            'header': '',
            'footer': '',
            'first_page_header': '',
            'first_page_footer': ''
        }

    def _extract_tables(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract tables from document"""
        tables = []

        for tbl in root.findall('.//w:tbl', self.namespaces):
            table_data = []
            rows = tbl.findall('.//w:tr', self.namespaces)

            for row in rows:
                row_data = []
                cells = row.findall('.//w:tc', self.namespaces)

                for cell in cells:
                    cell_text = self._extract_cell_text(cell)
                    row_data.append(cell_text)

                table_data.append(row_data)

            tables.append({
                'rows': table_data,
                'row_count': len(table_data),
                'max_columns': max(len(row) for row in table_data) if table_data else 0
            })

        return tables

    def _extract_lists(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract lists from document"""
        lists = []
        # Placeholder - complex list parsing would be implemented here
        return lists

    def _extract_media(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract media references"""
        media = []
        # Placeholder - media extraction would be implemented here
        return media

    def _extract_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Extract document metadata"""
        return {
            'word_count': 0,  # Would need to calculate
            'character_count': 0,
            'paragraph_count': len(root.findall('.//w:p', self.namespaces)),
            'table_count': len(root.findall('.//w:tbl', self.namespaces))
        }

    def _extract_paragraph_text(self, para: ET.Element) -> str:
        """Extract text content from a paragraph"""
        text_parts = []

        for run in para.findall('.//w:r', self.namespaces):
            text_elem = run.find('.//w:t', self.namespaces)
            if text_elem is not None and text_elem.text:
                text_parts.append(text_elem.text)

        return ''.join(text_parts)

    def _extract_cell_text(self, cell: ET.Element) -> str:
        """Extract text content from a table cell"""
        text_parts = []

        for para in cell.findall('.//w:p', self.namespaces):
            text_parts.append(self._extract_paragraph_text(para))

        return '\n'.join(text_parts).strip()

    def _get_paragraph_style(self, para: ET.Element) -> Optional[str]:
        """Get paragraph style"""
        pPr = para.find('.//w:pPr', self.namespaces)
        if pPr is not None:
            style = pPr.find('.//w:pStyle', self.namespaces)
            if style is not None:
                return style.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
        return None

    def _is_heading_style(self, style: Optional[str]) -> bool:
        """Check if style is a heading"""
        if not style:
            return False
        return style.lower().startswith('heading') or style.lower() in ['title', 'subtitle']

    def _get_heading_level(self, style: Optional[str]) -> int:
        """Get heading level from style"""
        if not style:
            return 1

        style_lower = style.lower()
        if style_lower == 'title':
            return 0
        elif 'heading' in style_lower:
            # Extract number from "Heading1", "Heading2", etc.
            match = re.search(r'heading(\d+)', style_lower)
            if match:
                return int(match.group(1))

        return 1

    def _convert_to_oscal_ssp(self, parsed_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert parsed Word document content to OSCAL SSP format.

        Args:
            parsed_content: Parsed document structure

        Returns:
            OSCAL SSP JSON structure
        """
        sections = parsed_content.get('sections', [])

        # Extract system characteristics
        system_characteristics = self._extract_system_characteristics(sections)

        # Extract control implementations
        control_implementations = self._extract_control_implementations(sections)

        # Extract assessment results
        assessment_results = self._extract_assessment_results(sections)

        # Build OSCAL SSP structure
        oscal_ssp = {
            "oscal-version": "1.1.2",
            "metadata": self._create_oscal_metadata(system_characteristics),
            "system-security-plan": {
                "uuid": str(uuid.uuid4()),
                "metadata": self._create_ssp_metadata(system_characteristics),
                "import-profile": self._create_import_profile(sections),
                "system-characteristics": system_characteristics,
                "system-implementation": self._extract_system_implementation(sections),
                "control-implementation": {
                    "description": "Control implementations extracted from SSP document",
                    "implemented-requirements": control_implementations
                }
            }
        }

        # Add assessment results if found
        if assessment_results:
            oscal_ssp["system-security-plan"]["assessment-results"] = assessment_results

        # Add plan of action and milestones if found
        poam = self._extract_poam(sections)
        if poam:
            oscal_ssp["system-security-plan"]["plan-of-action-and-milestones"] = poam

        return oscal_ssp

    def _extract_system_characteristics(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract system characteristics from document sections"""
        # Look for sections containing system information
        system_info = {}

        for section in sections:
            heading = section.get('heading', '').lower()
            content = section.get('content', '')

            if 'system name' in heading or 'system information' in heading:
                # Extract system name
                lines = content.split('\n')
                for line in lines:
                    if 'system name' in line.lower():
                        system_info['system-name'] = line.split(':', 1)[-1].strip()
                    elif 'system id' in line.lower():
                        system_info['system-ids'] = [{
                            "id": line.split(':', 1)[-1].strip(),
                            "identifier-type": "system-id"
                        }]

            elif 'system description' in heading:
                system_info['description'] = content

            elif 'security categorization' in heading:
                system_info['security-impact-level'] = self._parse_security_level(content)

        # Default values if not found
        if 'system-name' not in system_info:
            system_info['system-name'] = 'Imported System'

        if 'system-ids' not in system_info:
            system_info['system-ids'] = [{
                "id": str(uuid.uuid4()),
                "identifier-type": "uuid"
            }]

        if 'description' not in system_info:
            system_info['description'] = 'System imported from Word document'

        return system_info

    def _extract_control_implementations(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract control implementations from document sections"""
        implementations = []

        # Look for control implementation sections
        for section in sections:
            heading = section.get('heading', '').lower()
            content = section.get('content', '')

            # Check if this is a control section (e.g., "AC-2", "IA-5")
            if re.match(r'^[A-Z]{2}-\d+', heading.upper()):
                control_id = heading.upper().split()[0]

                implementation = {
                    "uuid": str(uuid.uuid4()),
                    "control-id": control_id,
                    "description": content[:500],  # Truncate for description
                    "statements": [{
                        "statement-id": "implementation",
                        "description": content,
                        "by-components": []
                    }]
                }

                implementations.append(implementation)

        return implementations

    def _extract_assessment_results(self, sections: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Extract assessment results if present"""
        # Placeholder - would parse assessment results sections
        return None

    def _extract_poam(self, sections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract Plan of Action and Milestones if present"""
        # Placeholder - would parse POA&M sections
        return None

    def _extract_system_implementation(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract system implementation details"""
        return {
            "users": [],
            "components": [],
            "inventory-items": []
        }

    def _create_oscal_metadata(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create OSCAL metadata section"""
        return {
            "title": f"System Security Plan for {system_info.get('system-name', 'Imported System')}",
            "last-modified": timezone.now().isoformat(),
            "version": "1.0",
            "oscal-version": "1.1.2",
            "parties": [],
            "responsible-parties": {}
        }

    def _create_ssp_metadata(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create SSP-specific metadata"""
        return {
            "title": f"System Security Plan for {system_info.get('system-name', 'Imported System')}",
            "published": timezone.now().isoformat(),
            "last-modified": timezone.now().isoformat(),
            "version": "1.0"
        }

    def _create_import_profile(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create import-profile section"""
        # Try to determine which framework this SSP is based on
        framework_ref = "NIST-800-53"  # Default

        for section in sections:
            content = section.get('content', '').lower()
            if 'nist 800-53' in content or 'sp 800-53' in content:
                framework_ref = "NIST-800-53"
                break
            elif 'iso 27001' in content:
                framework_ref = "ISO-27001"
                break

        return {
            "href": f"framework/{framework_ref}",
            "remarks": "Framework reference extracted from SSP document"
        }

    def _parse_security_level(self, content: str) -> Dict[str, Any]:
        """Parse security impact level from content"""
        # Default to moderate
        return {
            "security-objective-confidentiality": "moderate",
            "security-objective-integrity": "moderate",
            "security-objective-availability": "moderate"
        }

    def _validate_oscal_ssp(self, oscal_ssp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate OSCAL SSP structure.

        Args:
            oscal_ssp: OSCAL SSP data

        Returns:
            Validation results
        """
        errors = []
        warnings = []

        # Check required fields
        if 'oscal-version' not in oscal_ssp:
            errors.append("Missing oscal-version")

        if 'metadata' not in oscal_ssp:
            errors.append("Missing metadata")

        ssp = oscal_ssp.get('system-security-plan', {})
        if not ssp:
            errors.append("Missing system-security-plan")
        else:
            if 'system-characteristics' not in ssp:
                errors.append("Missing system-characteristics")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def _convert_to_ciso_entities(self, oscal_ssp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OSCAL SSP to CISO Assistant entities.

        Args:
            oscal_ssp: OSCAL SSP data

        Returns:
            CISO Assistant entity structures
        """
        ssp = oscal_ssp.get('system-security-plan', {})

        # Extract system characteristics for compliance assessment
        system_characteristics = ssp.get('system-characteristics', {})

        # Extract control implementations
        control_implementations = ssp.get('control-implementation', {}).get('implemented-requirements', [])

        # Create compliance assessment structure
        compliance_assessment = {
            'name': system_characteristics.get('system-name', 'Imported SSP'),
            'description': system_characteristics.get('description', ''),
            'framework': self._determine_framework_from_ssp(oscal_ssp),
            'status': 'draft',
            'controls': self._convert_control_implementations(control_implementations)
        }

        return {
            'compliance_assessment': compliance_assessment,
            'assets': self._extract_assets_from_ssp(ssp),
            'findings': self._extract_findings_from_ssp(ssp)
        }

    def _determine_framework_from_ssp(self, oscal_ssp: Dict[str, Any]) -> Dict[str, Any]:
        """Determine framework from SSP data"""
        ssp = oscal_ssp.get('system-security-plan', {})
        import_profile = ssp.get('import-profile', {})

        # Default to NIST 800-53
        return {
            'name': 'NIST SP 800-53',
            'version': 'Rev. 5',
            'reference': import_profile.get('href', 'NIST-800-53')
        }

    def _convert_control_implementations(self, implementations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OSCAL control implementations to CISO format"""
        controls = []

        for impl in implementations:
            control = {
                'control_id': impl.get('control-id', ''),
                'title': f"Control {impl.get('control-id', '')}",
                'description': impl.get('description', ''),
                'status': 'not_implemented',
                'implementation_details': impl.get('statements', [{}])[0].get('description', ''),
                'evidence': []
            }
            controls.append(control)

        return controls

    def _extract_assets_from_ssp(self, ssp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract assets from SSP system implementation"""
        system_implementation = ssp.get('system-implementation', {})
        inventory_items = system_implementation.get('inventory-items', [])

        assets = []
        for item in inventory_items:
            asset = {
                'name': item.get('asset-id', 'Unknown Asset'),
                'asset_id': item.get('asset-id', ''),
                'description': item.get('description', ''),
                'asset_type': 'hardware',  # Default assumption
                'status': 'active'
            }
            assets.append(asset)

        return assets

    def _extract_findings_from_ssp(self, ssp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract findings from SSP assessment results"""
        assessment_results = ssp.get('assessment-results', [])

        findings = []
        for result in assessment_results:
            for finding in result.get('findings', []):
                finding_data = {
                    'title': finding.get('title', ''),
                    'description': finding.get('description', ''),
                    'severity': 'moderate',
                    'status': 'open'
                }
                findings.append(finding_data)

        return findings

    def import_docx_from_upload(self, uploaded_file) -> Dict[str, Any]:
        """
        Import SSP from uploaded DOCX file.

        Args:
            uploaded_file: Django uploaded file object

        Returns:
            Import results
        """
        try:
            # Save uploaded file temporarily
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            try:
                # Import the file
                result = self.import_docx_file(temp_file_path)
                return result

            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Error importing uploaded DOCX file: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': uploaded_file.name
            }

    def get_import_capabilities(self) -> Dict[str, Any]:
        """Get information about import capabilities"""
        return {
            'supported_formats': ['docx'],
            'oscal_version': '1.1.2',
            'capabilities': [
                'SSP document parsing',
                'OSCAL SSP conversion',
                'CISO Assistant entity creation',
                'Validation and error reporting'
            ],
            'limitations': [
                'Complex table structures may not be fully parsed',
                'Embedded images are not extracted',
                'Advanced formatting may be lost'
            ]
        }
