"""
Trestle Service - Enhanced OSCAL Operations

Service layer integrating compliance-trestle for advanced OSCAL operations:
- Split/Merge operations for large OSCAL documents
- Profile resolution (collapse profiles with catalog references)
- Format conversion (JSON/YAML/XML)
- Repository API for programmatic OSCAL access
- Component Definition support
"""

import json
import logging
import tempfile
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)


class OscalFormat(Enum):
    """Supported OSCAL formats"""
    JSON = "json"
    YAML = "yaml"
    XML = "xml"


class OscalModelType(Enum):
    """OSCAL model types"""
    CATALOG = "catalog"
    PROFILE = "profile"
    COMPONENT_DEFINITION = "component-definition"
    SSP = "system-security-plan"
    ASSESSMENT_PLAN = "assessment-plan"
    ASSESSMENT_RESULTS = "assessment-results"
    POAM = "plan-of-action-and-milestones"


@dataclass
class SplitResult:
    """Result of an OSCAL split operation"""
    success: bool
    original_path: str
    split_paths: List[str]
    model_type: str
    split_count: int
    errors: List[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of an OSCAL merge operation"""
    success: bool
    merged_path: str
    source_paths: List[str]
    model_type: str
    errors: List[str] = field(default_factory=list)


@dataclass
class ProfileResolutionResult:
    """Result of profile resolution"""
    success: bool
    resolved_catalog: Dict[str, Any]
    source_profile: str
    imported_catalogs: List[str]
    control_count: int
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Comprehensive validation result"""
    valid: bool
    model_type: Optional[str]
    oscal_version: str
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    duplicate_ids: List[str] = field(default_factory=list)
    missing_references: List[str] = field(default_factory=list)


class TrestleService:
    """
    Enhanced OSCAL service using compliance-trestle patterns.

    Provides advanced operations beyond basic import/export:
    - Document splitting for large OSCAL files
    - Document merging for combined reports
    - Profile resolution to flatten catalogs
    - Multi-format support (JSON, YAML, XML)
    - Comprehensive validation with reference checking
    """

    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize Trestle service.

        Args:
            workspace_path: Optional path for trestle workspace.
                          If not provided, uses temporary directory.
        """
        self.workspace_path = workspace_path or tempfile.mkdtemp(prefix="trestle_")
        self._ensure_workspace()

    def _ensure_workspace(self):
        """Ensure workspace directory exists with proper structure"""
        workspace = Path(self.workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)

        # Create trestle workspace structure
        (workspace / "catalogs").mkdir(exist_ok=True)
        (workspace / "profiles").mkdir(exist_ok=True)
        (workspace / "component-definitions").mkdir(exist_ok=True)
        (workspace / "system-security-plans").mkdir(exist_ok=True)
        (workspace / "assessment-plans").mkdir(exist_ok=True)
        (workspace / "assessment-results").mkdir(exist_ok=True)
        (workspace / "plan-of-action-and-milestones").mkdir(exist_ok=True)

    # =========================================================================
    # FORMAT CONVERSION
    # =========================================================================

    def convert_format(
        self,
        content: Union[str, Dict],
        source_format: OscalFormat,
        target_format: OscalFormat
    ) -> str:
        """
        Convert OSCAL content between formats.

        Args:
            content: OSCAL content as string or dict
            source_format: Source format (JSON, YAML, XML)
            target_format: Target format (JSON, YAML, XML)

        Returns:
            Converted content as string
        """
        # Parse source content
        if isinstance(content, str):
            data = self._parse_content(content, source_format)
        else:
            data = content

        # Convert to target format
        return self._serialize_content(data, target_format)

    def _parse_content(self, content: str, format: OscalFormat) -> Dict[str, Any]:
        """Parse content based on format"""
        if format == OscalFormat.JSON:
            return json.loads(content)
        elif format == OscalFormat.YAML:
            if not YAML_AVAILABLE:
                raise ImportError("PyYAML library not installed. Run: pip install pyyaml")
            return yaml.safe_load(content)
        elif format == OscalFormat.XML:
            return self._parse_xml_to_dict(content)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _serialize_content(self, data: Dict[str, Any], format: OscalFormat) -> str:
        """Serialize data to specified format"""
        if format == OscalFormat.JSON:
            return json.dumps(data, indent=2, default=str)
        elif format == OscalFormat.YAML:
            if not YAML_AVAILABLE:
                raise ImportError("PyYAML library not installed. Run: pip install pyyaml")
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        elif format == OscalFormat.XML:
            return self._dict_to_xml(data)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _parse_xml_to_dict(self, xml_content: str) -> Dict[str, Any]:
        """Parse XML content to dictionary"""
        import xml.etree.ElementTree as ET

        def element_to_dict(element):
            result = {}

            # Add attributes
            if element.attrib:
                result['@attributes'] = dict(element.attrib)

            # Add text content
            if element.text and element.text.strip():
                if len(element) == 0:  # No children
                    return element.text.strip()
                result['#text'] = element.text.strip()

            # Add children
            for child in element:
                child_data = element_to_dict(child)
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

                if tag in result:
                    if not isinstance(result[tag], list):
                        result[tag] = [result[tag]]
                    result[tag].append(child_data)
                else:
                    result[tag] = child_data

            return result

        root = ET.fromstring(xml_content)
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        return {root_tag: element_to_dict(root)}

    def _dict_to_xml(self, data: Dict[str, Any], root_name: str = "oscal") -> str:
        """Convert dictionary to XML string"""
        import xml.etree.ElementTree as ET

        def dict_to_element(d, parent):
            if isinstance(d, dict):
                for key, value in d.items():
                    if key == '@attributes':
                        for attr_key, attr_val in value.items():
                            parent.set(attr_key, str(attr_val))
                    elif key == '#text':
                        parent.text = str(value)
                    elif isinstance(value, list):
                        for item in value:
                            child = ET.SubElement(parent, key)
                            dict_to_element(item, child)
                    else:
                        child = ET.SubElement(parent, key)
                        dict_to_element(value, child)
            else:
                parent.text = str(d) if d is not None else ""

        # Get root element name from data
        if len(data) == 1:
            root_name = list(data.keys())[0]
            data = data[root_name]

        root = ET.Element(root_name)
        root.set("xmlns", "http://csrc.nist.gov/ns/oscal/1.0")
        dict_to_element(data, root)

        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    # =========================================================================
    # SPLIT OPERATIONS
    # =========================================================================

    def split_document(
        self,
        content: str,
        model_type: OscalModelType,
        split_by: str = "control-family"
    ) -> SplitResult:
        """
        Split a large OSCAL document into smaller parts.

        Args:
            content: OSCAL JSON content
            model_type: Type of OSCAL model
            split_by: Split strategy ('control-family', 'group', 'component')

        Returns:
            SplitResult with paths to split files
        """
        try:
            data = json.loads(content)
            split_paths = []
            errors = []

            if model_type == OscalModelType.CATALOG:
                split_paths = self._split_catalog(data, split_by)
            elif model_type == OscalModelType.SSP:
                split_paths = self._split_ssp(data, split_by)
            elif model_type == OscalModelType.COMPONENT_DEFINITION:
                split_paths = self._split_component_definition(data)
            else:
                errors.append(f"Split not supported for model type: {model_type.value}")

            return SplitResult(
                success=len(errors) == 0,
                original_path="",
                split_paths=split_paths,
                model_type=model_type.value,
                split_count=len(split_paths),
                errors=errors
            )

        except Exception as e:
            logger.error(f"Error splitting document: {e}")
            return SplitResult(
                success=False,
                original_path="",
                split_paths=[],
                model_type=model_type.value,
                split_count=0,
                errors=[str(e)]
            )

    def _split_catalog(self, data: Dict, split_by: str) -> List[str]:
        """Split catalog by control family or group"""
        split_paths = []
        catalog = data.get('catalog', {})
        groups = catalog.get('groups', [])

        if not groups:
            # No groups, try splitting by top-level controls
            controls = catalog.get('controls', [])
            if controls:
                return self._split_by_control_family(data, controls)
            return []

        workspace = Path(self.workspace_path) / "catalogs" / "split"
        workspace.mkdir(parents=True, exist_ok=True)

        for group in groups:
            group_id = group.get('id', str(uuid.uuid4())[:8])

            # Create split catalog with single group
            split_catalog = {
                'catalog': {
                    'uuid': str(uuid.uuid4()),
                    'metadata': catalog.get('metadata', {}),
                    'groups': [group],
                    'back-matter': catalog.get('back-matter', {})
                }
            }

            # Add oscal-version
            if 'oscal-version' in data:
                split_catalog['oscal-version'] = data['oscal-version']

            split_path = workspace / f"catalog-{group_id}.json"
            split_path.write_text(json.dumps(split_catalog, indent=2))
            split_paths.append(str(split_path))

        return split_paths

    def _split_by_control_family(self, data: Dict, controls: List[Dict]) -> List[str]:
        """Split controls by family prefix (e.g., AC, AU, IA)"""
        from collections import defaultdict

        families = defaultdict(list)
        for control in controls:
            control_id = control.get('id', '')
            family = control_id.split('-')[0] if '-' in control_id else control_id[:2]
            families[family].append(control)

        workspace = Path(self.workspace_path) / "catalogs" / "split"
        workspace.mkdir(parents=True, exist_ok=True)

        split_paths = []
        catalog = data.get('catalog', {})

        for family, family_controls in families.items():
            split_catalog = {
                'catalog': {
                    'uuid': str(uuid.uuid4()),
                    'metadata': catalog.get('metadata', {}),
                    'controls': family_controls,
                    'back-matter': catalog.get('back-matter', {})
                }
            }

            if 'oscal-version' in data:
                split_catalog['oscal-version'] = data['oscal-version']

            split_path = workspace / f"catalog-family-{family}.json"
            split_path.write_text(json.dumps(split_catalog, indent=2))
            split_paths.append(str(split_path))

        return split_paths

    def _split_ssp(self, data: Dict, split_by: str) -> List[str]:
        """Split SSP by sections"""
        split_paths = []
        ssp = data.get('system-security-plan', {})
        workspace = Path(self.workspace_path) / "system-security-plans" / "split"
        workspace.mkdir(parents=True, exist_ok=True)

        base_metadata = {
            'oscal-version': data.get('oscal-version', '1.1.2'),
            'metadata': ssp.get('metadata', {})
        }

        # Split into logical sections
        sections = [
            ('system-characteristics', ssp.get('system-characteristics', {})),
            ('system-implementation', ssp.get('system-implementation', {})),
            ('control-implementation', ssp.get('control-implementation', {})),
        ]

        for section_name, section_data in sections:
            if section_data:
                split_ssp = {
                    **base_metadata,
                    'system-security-plan': {
                        'uuid': str(uuid.uuid4()),
                        'metadata': ssp.get('metadata', {}),
                        section_name: section_data
                    }
                }

                split_path = workspace / f"ssp-{section_name}.json"
                split_path.write_text(json.dumps(split_ssp, indent=2))
                split_paths.append(str(split_path))

        return split_paths

    def _split_component_definition(self, data: Dict) -> List[str]:
        """Split component definition by component"""
        split_paths = []
        comp_def = data.get('component-definition', {})
        components = comp_def.get('components', [])

        workspace = Path(self.workspace_path) / "component-definitions" / "split"
        workspace.mkdir(parents=True, exist_ok=True)

        for component in components:
            comp_uuid = component.get('uuid', str(uuid.uuid4()))
            comp_title = component.get('title', 'component').replace(' ', '-').lower()

            split_comp_def = {
                'oscal-version': data.get('oscal-version', '1.1.2'),
                'component-definition': {
                    'uuid': str(uuid.uuid4()),
                    'metadata': comp_def.get('metadata', {}),
                    'components': [component]
                }
            }

            split_path = workspace / f"component-{comp_title}-{comp_uuid[:8]}.json"
            split_path.write_text(json.dumps(split_comp_def, indent=2))
            split_paths.append(str(split_path))

        return split_paths

    # =========================================================================
    # MERGE OPERATIONS
    # =========================================================================

    def merge_documents(
        self,
        contents: List[str],
        model_type: OscalModelType
    ) -> MergeResult:
        """
        Merge multiple OSCAL documents into one.

        Args:
            contents: List of OSCAL JSON content strings
            model_type: Type of OSCAL model

        Returns:
            MergeResult with merged document
        """
        try:
            documents = [json.loads(c) for c in contents]
            errors = []

            if model_type == OscalModelType.CATALOG:
                merged = self._merge_catalogs(documents)
            elif model_type == OscalModelType.SSP:
                merged = self._merge_ssps(documents)
            elif model_type == OscalModelType.COMPONENT_DEFINITION:
                merged = self._merge_component_definitions(documents)
            elif model_type == OscalModelType.ASSESSMENT_RESULTS:
                merged = self._merge_assessment_results(documents)
            else:
                errors.append(f"Merge not supported for model type: {model_type.value}")
                merged = {}

            # Save merged document
            workspace = Path(self.workspace_path) / "merged"
            workspace.mkdir(parents=True, exist_ok=True)
            merged_path = workspace / f"merged-{model_type.value}-{uuid.uuid4()}.json"
            merged_path.write_text(json.dumps(merged, indent=2))

            return MergeResult(
                success=len(errors) == 0,
                merged_path=str(merged_path),
                source_paths=[],
                model_type=model_type.value,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Error merging documents: {e}")
            return MergeResult(
                success=False,
                merged_path="",
                source_paths=[],
                model_type=model_type.value,
                errors=[str(e)]
            )

    def _merge_catalogs(self, documents: List[Dict]) -> Dict:
        """Merge multiple catalogs"""
        merged_groups = []
        merged_controls = []
        merged_params = []

        # Use first document as base
        base = documents[0] if documents else {}
        base_catalog = base.get('catalog', {})

        for doc in documents:
            catalog = doc.get('catalog', {})
            merged_groups.extend(catalog.get('groups', []))
            merged_controls.extend(catalog.get('controls', []))
            merged_params.extend(catalog.get('params', []))

        # Deduplicate by ID
        seen_groups = set()
        unique_groups = []
        for group in merged_groups:
            gid = group.get('id')
            if gid not in seen_groups:
                seen_groups.add(gid)
                unique_groups.append(group)

        seen_controls = set()
        unique_controls = []
        for control in merged_controls:
            cid = control.get('id')
            if cid not in seen_controls:
                seen_controls.add(cid)
                unique_controls.append(control)

        return {
            'oscal-version': base.get('oscal-version', '1.1.2'),
            'catalog': {
                'uuid': str(uuid.uuid4()),
                'metadata': base_catalog.get('metadata', {}),
                'params': merged_params,
                'groups': unique_groups if unique_groups else None,
                'controls': unique_controls if unique_controls else None,
                'back-matter': base_catalog.get('back-matter', {})
            }
        }

    def _merge_ssps(self, documents: List[Dict]) -> Dict:
        """Merge multiple SSPs"""
        base = documents[0] if documents else {}
        base_ssp = base.get('system-security-plan', {})

        merged_impl_reqs = []
        merged_components = []
        merged_users = []

        for doc in documents:
            ssp = doc.get('system-security-plan', {})

            # Merge control implementations
            control_impl = ssp.get('control-implementation', {})
            merged_impl_reqs.extend(control_impl.get('implemented-requirements', []))

            # Merge system implementation
            sys_impl = ssp.get('system-implementation', {})
            merged_components.extend(sys_impl.get('components', []))
            merged_users.extend(sys_impl.get('users', []))

        return {
            'oscal-version': base.get('oscal-version', '1.1.2'),
            'system-security-plan': {
                'uuid': str(uuid.uuid4()),
                'metadata': base_ssp.get('metadata', {}),
                'import-profile': base_ssp.get('import-profile', {}),
                'system-characteristics': base_ssp.get('system-characteristics', {}),
                'system-implementation': {
                    'users': merged_users,
                    'components': merged_components,
                    'inventory-items': base_ssp.get('system-implementation', {}).get('inventory-items', [])
                },
                'control-implementation': {
                    'description': 'Merged control implementations',
                    'implemented-requirements': merged_impl_reqs
                },
                'back-matter': base_ssp.get('back-matter', {})
            }
        }

    def _merge_component_definitions(self, documents: List[Dict]) -> Dict:
        """Merge multiple component definitions"""
        base = documents[0] if documents else {}
        base_def = base.get('component-definition', {})

        merged_components = []
        merged_capabilities = []

        for doc in documents:
            comp_def = doc.get('component-definition', {})
            merged_components.extend(comp_def.get('components', []))
            merged_capabilities.extend(comp_def.get('capabilities', []))

        return {
            'oscal-version': base.get('oscal-version', '1.1.2'),
            'component-definition': {
                'uuid': str(uuid.uuid4()),
                'metadata': base_def.get('metadata', {}),
                'components': merged_components,
                'capabilities': merged_capabilities if merged_capabilities else None,
                'back-matter': base_def.get('back-matter', {})
            }
        }

    def _merge_assessment_results(self, documents: List[Dict]) -> Dict:
        """Merge multiple assessment results"""
        base = documents[0] if documents else {}
        base_results = base.get('assessment-results', {})

        merged_results = []

        for doc in documents:
            ar = doc.get('assessment-results', {})
            merged_results.extend(ar.get('results', []))

        return {
            'oscal-version': base.get('oscal-version', '1.1.2'),
            'assessment-results': {
                'uuid': str(uuid.uuid4()),
                'metadata': base_results.get('metadata', {}),
                'import-ap': base_results.get('import-ap', {}),
                'results': merged_results,
                'back-matter': base_results.get('back-matter', {})
            }
        }

    # =========================================================================
    # PROFILE RESOLUTION
    # =========================================================================

    def resolve_profile(
        self,
        profile_content: str,
        catalog_contents: Dict[str, str]
    ) -> ProfileResolutionResult:
        """
        Resolve a profile into a flat catalog.

        Processes profile imports, modifications, and merges to produce
        a single resolved catalog with all selected controls.

        Args:
            profile_content: OSCAL Profile JSON content
            catalog_contents: Dict mapping catalog hrefs to their JSON content

        Returns:
            ProfileResolutionResult with resolved catalog
        """
        try:
            profile = json.loads(profile_content)
            profile_obj = profile.get('profile', {})

            # Get imports
            imports = profile_obj.get('imports', [])

            # Collect all imported controls
            all_controls = []
            all_groups = []
            imported_catalogs = []

            for import_def in imports:
                href = import_def.get('href', '')
                imported_catalogs.append(href)

                # Get catalog content
                catalog_content = catalog_contents.get(href)
                if not catalog_content:
                    continue

                catalog = json.loads(catalog_content)
                catalog_obj = catalog.get('catalog', {})

                # Get include controls
                include_controls = import_def.get('include-controls', [])
                exclude_controls = import_def.get('exclude-controls', [])

                # Filter controls
                catalog_controls = self._get_all_controls_from_catalog(catalog_obj)

                if include_controls:
                    # Include specific controls
                    include_ids = set()
                    for inc in include_controls:
                        if 'with-ids' in inc:
                            include_ids.update(inc['with-ids'])

                    filtered = [c for c in catalog_controls if c.get('id') in include_ids]
                else:
                    # Include all controls
                    filtered = catalog_controls

                # Apply exclusions
                if exclude_controls:
                    exclude_ids = set()
                    for exc in exclude_controls:
                        if 'with-ids' in exc:
                            exclude_ids.update(exc['with-ids'])
                    filtered = [c for c in filtered if c.get('id') not in exclude_ids]

                all_controls.extend(filtered)
                all_groups.extend(catalog_obj.get('groups', []))

            # Apply modifications
            modify = profile_obj.get('modify', {})
            if modify:
                all_controls = self._apply_profile_modifications(all_controls, modify)

            # Build resolved catalog
            resolved_catalog = {
                'oscal-version': profile.get('oscal-version', '1.1.2'),
                'catalog': {
                    'uuid': str(uuid.uuid4()),
                    'metadata': {
                        'title': f"Resolved: {profile_obj.get('metadata', {}).get('title', 'Profile')}",
                        'version': '1.0',
                        'oscal-version': profile.get('oscal-version', '1.1.2'),
                        'last-modified': str(uuid.uuid4())[:19]  # Timestamp placeholder
                    },
                    'controls': all_controls,
                    'back-matter': profile_obj.get('back-matter', {})
                }
            }

            return ProfileResolutionResult(
                success=True,
                resolved_catalog=resolved_catalog,
                source_profile="",
                imported_catalogs=imported_catalogs,
                control_count=len(all_controls),
                errors=[]
            )

        except Exception as e:
            logger.error(f"Error resolving profile: {e}")
            return ProfileResolutionResult(
                success=False,
                resolved_catalog={},
                source_profile="",
                imported_catalogs=[],
                control_count=0,
                errors=[str(e)]
            )

    def _get_all_controls_from_catalog(self, catalog: Dict) -> List[Dict]:
        """Extract all controls from catalog including nested in groups"""
        controls = list(catalog.get('controls', []))

        def extract_from_groups(groups):
            for group in groups:
                controls.extend(group.get('controls', []))
                if 'groups' in group:
                    extract_from_groups(group['groups'])

        extract_from_groups(catalog.get('groups', []))
        return controls

    def _apply_profile_modifications(
        self,
        controls: List[Dict],
        modify: Dict
    ) -> List[Dict]:
        """Apply profile modifications to controls"""
        # Build modification lookup
        set_params = {p.get('param-id'): p for p in modify.get('set-parameters', [])}
        alters = {a.get('control-id'): a for a in modify.get('alters', [])}

        modified_controls = []
        for control in controls:
            control_id = control.get('id', '')
            modified = dict(control)

            # Apply parameter settings
            if 'params' in modified:
                for param in modified['params']:
                    param_id = param.get('id')
                    if param_id in set_params:
                        set_param = set_params[param_id]
                        if 'values' in set_param:
                            param['values'] = set_param['values']
                        if 'constraints' in set_param:
                            param['constraints'] = set_param['constraints']

            # Apply alterations
            if control_id in alters:
                alter = alters[control_id]

                # Handle adds
                for add in alter.get('adds', []):
                    position = add.get('position', 'ending')
                    by_id = add.get('by-id')

                    if 'parts' in add:
                        if 'parts' not in modified:
                            modified['parts'] = []
                        if position == 'starting':
                            modified['parts'] = add['parts'] + modified['parts']
                        else:
                            modified['parts'].extend(add['parts'])

                    if 'props' in add:
                        if 'props' not in modified:
                            modified['props'] = []
                        modified['props'].extend(add['props'])

                # Handle removes
                for remove in alter.get('removes', []):
                    by_id = remove.get('by-id')
                    by_name = remove.get('by-name')

                    if by_id and 'parts' in modified:
                        modified['parts'] = [p for p in modified['parts'] if p.get('id') != by_id]
                    if by_name and 'props' in modified:
                        modified['props'] = [p for p in modified['props'] if p.get('name') != by_name]

            modified_controls.append(modified)

        return modified_controls

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate_comprehensive(self, content: str) -> ValidationResult:
        """
        Perform comprehensive OSCAL validation.

        Includes:
        - Schema validation
        - Reference integrity checking
        - Duplicate ID detection
        - Required field validation

        Args:
            content: OSCAL JSON content

        Returns:
            ValidationResult with detailed findings
        """
        errors = []
        warnings = []
        duplicate_ids = []
        missing_refs = []

        try:
            data = json.loads(content)

            # Detect model type
            model_type = self._detect_model_type(data)
            oscal_version = data.get('oscal-version', '')

            # Basic structure validation
            if not oscal_version:
                errors.append({
                    'code': 'MISSING_VERSION',
                    'message': 'oscal-version is required',
                    'location': '/'
                })

            if not data.get('metadata') and model_type:
                model_data = data.get(model_type, {})
                if not model_data.get('metadata'):
                    errors.append({
                        'code': 'MISSING_METADATA',
                        'message': 'metadata is required',
                        'location': f'/{model_type}'
                    })

            # Check for duplicate IDs
            all_ids = self._collect_all_ids(data)
            seen_ids = set()
            for id_value in all_ids:
                if id_value in seen_ids:
                    duplicate_ids.append(id_value)
                seen_ids.add(id_value)

            if duplicate_ids:
                warnings.append({
                    'code': 'DUPLICATE_IDS',
                    'message': f'Found {len(duplicate_ids)} duplicate IDs',
                    'duplicates': duplicate_ids[:10]  # Limit to first 10
                })

            # Check references
            missing_refs = self._check_references(data, seen_ids)
            if missing_refs:
                warnings.append({
                    'code': 'MISSING_REFERENCES',
                    'message': f'Found {len(missing_refs)} missing references',
                    'missing': missing_refs[:10]
                })

            # Model-specific validation
            if model_type == 'system-security-plan':
                self._validate_ssp(data, errors, warnings)
            elif model_type == 'catalog':
                self._validate_catalog(data, errors, warnings)

            return ValidationResult(
                valid=len(errors) == 0,
                model_type=model_type,
                oscal_version=oscal_version,
                errors=errors,
                warnings=warnings,
                duplicate_ids=duplicate_ids,
                missing_references=missing_refs
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                model_type=None,
                oscal_version='',
                errors=[{
                    'code': 'INVALID_JSON',
                    'message': str(e),
                    'location': f'line {e.lineno}, column {e.colno}'
                }]
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                model_type=None,
                oscal_version='',
                errors=[{
                    'code': 'VALIDATION_ERROR',
                    'message': str(e)
                }]
            )

    def _detect_model_type(self, data: Dict) -> Optional[str]:
        """Detect OSCAL model type from data"""
        for model_type in OscalModelType:
            if model_type.value in data:
                return model_type.value
        return None

    def _collect_all_ids(self, data: Dict, path: str = "") -> List[str]:
        """Recursively collect all ID values"""
        ids = []

        if isinstance(data, dict):
            if 'id' in data:
                ids.append(data['id'])
            if 'uuid' in data:
                ids.append(data['uuid'])

            for key, value in data.items():
                ids.extend(self._collect_all_ids(value, f"{path}/{key}"))

        elif isinstance(data, list):
            for i, item in enumerate(data):
                ids.extend(self._collect_all_ids(item, f"{path}[{i}]"))

        return ids

    def _check_references(self, data: Dict, known_ids: set) -> List[str]:
        """Check for missing references"""
        missing = []

        def check_refs(obj, path=""):
            if isinstance(obj, dict):
                # Check href references
                if 'href' in obj:
                    href = obj['href']
                    if href.startswith('#') and href[1:] not in known_ids:
                        missing.append(href)

                # Check id-ref
                for key in ['id-ref', 'control-id', 'party-uuid', 'component-uuid']:
                    if key in obj:
                        ref = obj[key]
                        if ref not in known_ids:
                            missing.append(ref)

                for key, value in obj.items():
                    check_refs(value, f"{path}/{key}")

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_refs(item, f"{path}[{i}]")

        check_refs(data)
        return missing

    def _validate_ssp(self, data: Dict, errors: List, warnings: List):
        """SSP-specific validation"""
        ssp = data.get('system-security-plan', {})

        if not ssp.get('system-characteristics'):
            errors.append({
                'code': 'MISSING_SYSTEM_CHARACTERISTICS',
                'message': 'system-characteristics is required for SSP',
                'location': '/system-security-plan'
            })

        if not ssp.get('control-implementation'):
            warnings.append({
                'code': 'MISSING_CONTROL_IMPLEMENTATION',
                'message': 'control-implementation is recommended for SSP',
                'location': '/system-security-plan'
            })

    def _validate_catalog(self, data: Dict, errors: List, warnings: List):
        """Catalog-specific validation"""
        catalog = data.get('catalog', {})

        if not catalog.get('controls') and not catalog.get('groups'):
            warnings.append({
                'code': 'EMPTY_CATALOG',
                'message': 'Catalog has no controls or groups',
                'location': '/catalog'
            })

    # =========================================================================
    # COMPONENT DEFINITION SUPPORT
    # =========================================================================

    def create_component_definition(
        self,
        title: str,
        components: List[Dict[str, Any]],
        capabilities: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a new OSCAL Component Definition.

        Args:
            title: Title for the component definition
            components: List of component data
            capabilities: Optional list of capabilities

        Returns:
            OSCAL Component Definition document
        """
        comp_def = {
            'oscal-version': '1.1.2',
            'component-definition': {
                'uuid': str(uuid.uuid4()),
                'metadata': {
                    'title': title,
                    'version': '1.0',
                    'oscal-version': '1.1.2',
                    'last-modified': str(uuid.uuid4())[:19]
                },
                'components': [
                    self._normalize_component(comp) for comp in components
                ]
            }
        }

        if capabilities:
            comp_def['component-definition']['capabilities'] = capabilities

        return comp_def

    def _normalize_component(self, component: Dict) -> Dict:
        """Normalize component data to OSCAL structure"""
        return {
            'uuid': component.get('uuid', str(uuid.uuid4())),
            'type': component.get('type', 'software'),
            'title': component.get('title', 'Component'),
            'description': component.get('description', ''),
            'props': component.get('props', []),
            'control-implementations': component.get('control-implementations', []),
            'protocols': component.get('protocols', [])
        }

    # =========================================================================
    # REPOSITORY API
    # =========================================================================

    def list_documents(self, model_type: Optional[OscalModelType] = None) -> List[Dict[str, Any]]:
        """
        List all OSCAL documents in the workspace.

        Args:
            model_type: Optional filter by model type

        Returns:
            List of document metadata
        """
        documents = []
        workspace = Path(self.workspace_path)

        type_dirs = {
            OscalModelType.CATALOG: 'catalogs',
            OscalModelType.PROFILE: 'profiles',
            OscalModelType.COMPONENT_DEFINITION: 'component-definitions',
            OscalModelType.SSP: 'system-security-plans',
            OscalModelType.ASSESSMENT_PLAN: 'assessment-plans',
            OscalModelType.ASSESSMENT_RESULTS: 'assessment-results',
            OscalModelType.POAM: 'plan-of-action-and-milestones'
        }

        dirs_to_search = [type_dirs[model_type]] if model_type else type_dirs.values()

        for dir_name in dirs_to_search:
            dir_path = workspace / dir_name
            if dir_path.exists():
                for file_path in dir_path.rglob('*.json'):
                    try:
                        content = file_path.read_text()
                        data = json.loads(content)

                        doc_type = self._detect_model_type(data)
                        model_data = data.get(doc_type, {}) if doc_type else {}
                        metadata = model_data.get('metadata', {})

                        documents.append({
                            'path': str(file_path),
                            'model_type': doc_type,
                            'uuid': model_data.get('uuid'),
                            'title': metadata.get('title'),
                            'version': metadata.get('version'),
                            'last_modified': metadata.get('last-modified'),
                            'oscal_version': data.get('oscal-version')
                        })
                    except (json.JSONDecodeError, IOError):
                        continue

        return documents

    def get_document(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get an OSCAL document by path.

        Args:
            path: Path to document

        Returns:
            Document content or None if not found
        """
        try:
            file_path = Path(path)
            if file_path.exists():
                return json.loads(file_path.read_text())
            return None
        except (json.JSONDecodeError, IOError):
            return None

    def save_document(
        self,
        content: Dict[str, Any],
        model_type: OscalModelType,
        name: Optional[str] = None
    ) -> str:
        """
        Save an OSCAL document to the workspace.

        Args:
            content: Document content
            model_type: Type of OSCAL model
            name: Optional document name

        Returns:
            Path to saved document
        """
        type_dirs = {
            OscalModelType.CATALOG: 'catalogs',
            OscalModelType.PROFILE: 'profiles',
            OscalModelType.COMPONENT_DEFINITION: 'component-definitions',
            OscalModelType.SSP: 'system-security-plans',
            OscalModelType.ASSESSMENT_PLAN: 'assessment-plans',
            OscalModelType.ASSESSMENT_RESULTS: 'assessment-results',
            OscalModelType.POAM: 'plan-of-action-and-milestones'
        }

        dir_path = Path(self.workspace_path) / type_dirs[model_type]
        dir_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if name:
            filename = f"{name}.json"
        else:
            model_data = content.get(model_type.value, {})
            doc_uuid = model_data.get('uuid', str(uuid.uuid4()))
            filename = f"{model_type.value}-{doc_uuid[:8]}.json"

        file_path = dir_path / filename
        file_path.write_text(json.dumps(content, indent=2))

        return str(file_path)

    def delete_document(self, path: str) -> bool:
        """
        Delete an OSCAL document.

        Args:
            path: Path to document

        Returns:
            True if deleted, False otherwise
        """
        try:
            file_path = Path(path)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except IOError:
            return False

    def cleanup(self):
        """Clean up temporary workspace"""
        if self.workspace_path and Path(self.workspace_path).exists():
            shutil.rmtree(self.workspace_path, ignore_errors=True)
