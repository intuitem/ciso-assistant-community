"""
OpenControl Converter Service

Converts between OpenControl and OSCAL formats for legacy compatibility.

OpenControl is a YAML-based compliance-as-code format that predates OSCAL.
This service enables bidirectional conversion for migration and interoperability.

Inspired by GoComply's conversion tools.
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of a format conversion"""
    success: bool
    output: Dict[str, Any]
    source_format: str
    target_format: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class OpenControlComponent:
    """OpenControl component representation"""
    name: str
    key: str
    schema_version: str
    documentation_complete: bool
    references: List[Dict[str, str]]
    satisfies: List[Dict[str, Any]]
    responsible_role: str = ""


@dataclass
class OpenControlStandard:
    """OpenControl standard representation"""
    name: str
    controls: Dict[str, Dict[str, Any]]


class OpenControlConverter:
    """
    Converter between OpenControl and OSCAL formats.

    Supports:
    - OpenControl component.yaml → OSCAL Component Definition
    - OpenControl standard.yaml → OSCAL Catalog
    - OpenControl opencontrol.yaml → OSCAL Profile
    - OSCAL → OpenControl (reverse conversion)
    """

    # OpenControl to OSCAL status mapping
    STATUS_MAP = {
        'complete': 'implemented',
        'partial': 'partially-implemented',
        'planned': 'planned',
        'none': 'not-applicable',
        'not applicable': 'not-applicable',
    }

    # Reverse mapping
    OSCAL_TO_OC_STATUS = {v: k for k, v in STATUS_MAP.items()}

    def __init__(self):
        """Initialize the converter"""
        self.oscal_version = "1.1.2"

    # =========================================================================
    # OpenControl to OSCAL
    # =========================================================================

    def opencontrol_component_to_oscal(
        self,
        opencontrol_yaml: str
    ) -> ConversionResult:
        """
        Convert OpenControl component.yaml to OSCAL Component Definition.

        Args:
            opencontrol_yaml: OpenControl component YAML content

        Returns:
            ConversionResult with OSCAL component definition
        """
        if not YAML_AVAILABLE:
            return ConversionResult(
                success=False,
                output={},
                source_format='opencontrol',
                target_format='oscal',
                errors=['PyYAML library not installed. Run: pip install pyyaml']
            )

        try:
            oc_data = yaml.safe_load(opencontrol_yaml)
            warnings = []

            # Extract component info
            name = oc_data.get('name', 'Unknown Component')
            key = oc_data.get('key', name.lower().replace(' ', '-'))
            schema_version = oc_data.get('schema_version', '3.0.0')

            # Create OSCAL component definition
            oscal_comp_def = {
                "oscal-version": self.oscal_version,
                "component-definition": {
                    "uuid": str(uuid.uuid4()),
                    "metadata": {
                        "title": f"Component Definition: {name}",
                        "last-modified": datetime.now().isoformat(),
                        "version": schema_version,
                        "oscal-version": self.oscal_version,
                        "props": [
                            {
                                "name": "opencontrol-key",
                                "value": key
                            }
                        ]
                    },
                    "components": [
                        self._convert_oc_component(oc_data)
                    ]
                }
            }

            # Add back-matter with references
            references = oc_data.get('references', [])
            if references:
                oscal_comp_def["component-definition"]["back-matter"] = {
                    "resources": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "title": ref.get('name', 'Reference'),
                            "rlinks": [{"href": ref.get('path', ref.get('url', ''))}]
                        }
                        for ref in references
                    ]
                }

            return ConversionResult(
                success=True,
                output=oscal_comp_def,
                source_format="opencontrol-component",
                target_format="oscal-component-definition",
                warnings=warnings
            )

        except yaml.YAMLError as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="opencontrol-component",
                target_format="oscal-component-definition",
                errors=[f"Invalid YAML: {str(e)}"]
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="opencontrol-component",
                target_format="oscal-component-definition",
                errors=[str(e)]
            )

    def _convert_oc_component(self, oc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenControl component to OSCAL component"""
        name = oc_data.get('name', 'Unknown Component')
        key = oc_data.get('key', name.lower().replace(' ', '-'))

        component = {
            "uuid": str(uuid.uuid4()),
            "type": "software",  # Default type
            "title": name,
            "description": oc_data.get('documentation_complete', ''),
            "props": [
                {"name": "opencontrol-key", "value": key}
            ],
            "control-implementations": []
        }

        # Convert satisfies to control-implementations
        satisfies = oc_data.get('satisfies', [])
        if satisfies:
            impl = {
                "uuid": str(uuid.uuid4()),
                "source": "unknown",  # Would need to be provided
                "description": f"Control implementations for {name}",
                "implemented-requirements": []
            }

            for satisfy in satisfies:
                impl_req = self._convert_satisfy_to_impl_req(satisfy)
                impl["implemented-requirements"].append(impl_req)

            component["control-implementations"].append(impl)

        return component

    def _convert_satisfy_to_impl_req(self, satisfy: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenControl satisfy entry to OSCAL implemented-requirement"""
        control_key = satisfy.get('control_key', '')
        standard_key = satisfy.get('standard_key', '')

        impl_req = {
            "uuid": str(uuid.uuid4()),
            "control-id": control_key,
            "description": "",
            "props": []
        }

        # Add standard key as prop
        if standard_key:
            impl_req["props"].append({
                "name": "standard-key",
                "value": standard_key
            })

        # Add implementation status
        impl_status = satisfy.get('implementation_status', 'none')
        oscal_status = self.STATUS_MAP.get(impl_status.lower(), 'planned')
        impl_req["props"].append({
            "name": "implementation-status",
            "ns": "https://fedramp.gov/ns/oscal",
            "value": oscal_status
        })

        # Convert narrative to statements
        narrative = satisfy.get('narrative', [])
        if narrative:
            impl_req["statements"] = []
            for idx, narr in enumerate(narrative):
                if isinstance(narr, dict):
                    stmt_text = narr.get('text', '')
                    stmt_key = narr.get('key', f'{control_key}_stmt_{idx}')
                else:
                    stmt_text = str(narr)
                    stmt_key = f'{control_key}_stmt_{idx}'

                impl_req["statements"].append({
                    "statement-id": stmt_key,
                    "uuid": str(uuid.uuid4()),
                    "description": stmt_text
                })

        # Add parameters
        parameters = satisfy.get('parameters', [])
        if parameters:
            impl_req["set-parameters"] = [
                {
                    "param-id": param.get('key', ''),
                    "values": [param.get('text', '')]
                }
                for param in parameters
            ]

        return impl_req

    def opencontrol_standard_to_oscal(
        self,
        standard_yaml: str
    ) -> ConversionResult:
        """
        Convert OpenControl standard to OSCAL Catalog.

        Args:
            standard_yaml: OpenControl standard YAML content

        Returns:
            ConversionResult with OSCAL catalog
        """
        if not YAML_AVAILABLE:
            return ConversionResult(
                success=False,
                output={},
                source_format='opencontrol',
                target_format='oscal',
                errors=['PyYAML library not installed. Run: pip install pyyaml']
            )

        try:
            oc_standard = yaml.safe_load(standard_yaml)
            warnings = []

            name = oc_standard.get('name', 'Unknown Standard')

            # Create OSCAL catalog
            oscal_catalog = {
                "oscal-version": self.oscal_version,
                "catalog": {
                    "uuid": str(uuid.uuid4()),
                    "metadata": {
                        "title": name,
                        "last-modified": datetime.now().isoformat(),
                        "version": "1.0",
                        "oscal-version": self.oscal_version
                    },
                    "controls": []
                }
            }

            # Convert controls
            controls = oc_standard.get('controls', {})
            for control_id, control_data in controls.items():
                oscal_control = self._convert_oc_control(control_id, control_data)
                oscal_catalog["catalog"]["controls"].append(oscal_control)

            return ConversionResult(
                success=True,
                output=oscal_catalog,
                source_format="opencontrol-standard",
                target_format="oscal-catalog",
                warnings=warnings
            )

        except yaml.YAMLError as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="opencontrol-standard",
                target_format="oscal-catalog",
                errors=[f"Invalid YAML: {str(e)}"]
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="opencontrol-standard",
                target_format="oscal-catalog",
                errors=[str(e)]
            )

    def _convert_oc_control(self, control_id: str, control_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenControl control to OSCAL control"""
        control = {
            "id": control_id,
            "title": control_data.get('name', control_id),
            "props": [],
            "parts": []
        }

        # Add family
        family = control_data.get('family', '')
        if family:
            control["props"].append({
                "name": "family",
                "value": family
            })

        # Add description as part
        description = control_data.get('description', '')
        if description:
            control["parts"].append({
                "id": f"{control_id}_stmt",
                "name": "statement",
                "prose": description
            })

        return control

    def opencontrol_system_to_oscal(
        self,
        opencontrol_yaml: str,
        component_yamls: Optional[List[str]] = None
    ) -> ConversionResult:
        """
        Convert OpenControl opencontrol.yaml (system) to OSCAL SSP.

        Args:
            opencontrol_yaml: Main opencontrol.yaml content
            component_yamls: Optional list of component YAML contents

        Returns:
            ConversionResult with OSCAL SSP
        """
        if not YAML_AVAILABLE:
            return ConversionResult(
                success=False,
                output={},
                source_format='opencontrol',
                target_format='oscal',
                errors=['PyYAML library not installed. Run: pip install pyyaml']
            )

        try:
            oc_data = yaml.safe_load(opencontrol_yaml)
            warnings = []

            name = oc_data.get('name', 'Unknown System')
            schema_version = oc_data.get('schema_version', '1.0.0')

            # Create OSCAL SSP
            oscal_ssp = {
                "oscal-version": self.oscal_version,
                "system-security-plan": {
                    "uuid": str(uuid.uuid4()),
                    "metadata": {
                        "title": f"System Security Plan: {name}",
                        "last-modified": datetime.now().isoformat(),
                        "version": schema_version,
                        "oscal-version": self.oscal_version
                    },
                    "system-characteristics": {
                        "system-name": name,
                        "description": oc_data.get('metadata', {}).get('description', ''),
                        "system-ids": [
                            {
                                "id": str(uuid.uuid4()),
                                "identifier-type": "https://ietf.org/rfc/rfc4122"
                            }
                        ],
                        "security-sensitivity-level": "moderate",
                        "system-information": {
                            "information-types": []
                        }
                    },
                    "system-implementation": {
                        "users": [],
                        "components": []
                    },
                    "control-implementation": {
                        "description": "Control implementations",
                        "implemented-requirements": []
                    }
                }
            }

            # Add components from component_yamls
            if component_yamls:
                for comp_yaml in component_yamls:
                    comp_result = self.opencontrol_component_to_oscal(comp_yaml)
                    if comp_result.success:
                        comp_def = comp_result.output.get("component-definition", {})
                        components = comp_def.get("components", [])
                        for comp in components:
                            # Add to system-implementation
                            oscal_ssp["system-security-plan"]["system-implementation"]["components"].append({
                                "uuid": comp.get("uuid"),
                                "type": comp.get("type"),
                                "title": comp.get("title"),
                                "description": comp.get("description", "")
                            })

                            # Add control implementations
                            for ctrl_impl in comp.get("control-implementations", []):
                                for impl_req in ctrl_impl.get("implemented-requirements", []):
                                    oscal_ssp["system-security-plan"]["control-implementation"]["implemented-requirements"].append(impl_req)

            return ConversionResult(
                success=True,
                output=oscal_ssp,
                source_format="opencontrol-system",
                target_format="oscal-ssp",
                warnings=warnings
            )

        except yaml.YAMLError as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="opencontrol-system",
                target_format="oscal-ssp",
                errors=[f"Invalid YAML: {str(e)}"]
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="opencontrol-system",
                target_format="oscal-ssp",
                errors=[str(e)]
            )

    # =========================================================================
    # OSCAL to OpenControl
    # =========================================================================

    def oscal_component_to_opencontrol(
        self,
        oscal_json: str
    ) -> ConversionResult:
        """
        Convert OSCAL Component Definition to OpenControl component.yaml.

        Args:
            oscal_json: OSCAL component definition JSON content

        Returns:
            ConversionResult with OpenControl YAML output
        """
        if not YAML_AVAILABLE:
            return ConversionResult(
                success=False,
                output={},
                source_format='oscal',
                target_format='opencontrol',
                errors=['PyYAML library not installed. Run: pip install pyyaml']
            )

        try:
            oscal_data = json.loads(oscal_json)
            warnings = []

            comp_def = oscal_data.get("component-definition", {})
            components = comp_def.get("components", [])

            if not components:
                return ConversionResult(
                    success=False,
                    output={},
                    source_format="oscal-component-definition",
                    target_format="opencontrol-component",
                    errors=["No components found in OSCAL document"]
                )

            # Convert first component (OpenControl has one component per file)
            component = components[0]
            oc_component = self._convert_oscal_component_to_oc(component)

            # Output as YAML string in the output dict
            yaml_output = yaml.dump(oc_component, default_flow_style=False, allow_unicode=True)

            return ConversionResult(
                success=True,
                output={"yaml_content": yaml_output, "data": oc_component},
                source_format="oscal-component-definition",
                target_format="opencontrol-component",
                warnings=warnings
            )

        except json.JSONDecodeError as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="oscal-component-definition",
                target_format="opencontrol-component",
                errors=[f"Invalid JSON: {str(e)}"]
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="oscal-component-definition",
                target_format="opencontrol-component",
                errors=[str(e)]
            )

    def _convert_oscal_component_to_oc(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSCAL component to OpenControl format"""
        title = component.get("title", "Unknown")

        oc_component = {
            "name": title,
            "key": title.lower().replace(" ", "-"),
            "schema_version": "3.0.0",
            "documentation_complete": True,
            "satisfies": []
        }

        # Convert control implementations to satisfies
        for ctrl_impl in component.get("control-implementations", []):
            for impl_req in ctrl_impl.get("implemented-requirements", []):
                satisfy = self._convert_impl_req_to_satisfy(impl_req)
                oc_component["satisfies"].append(satisfy)

        return oc_component

    def _convert_impl_req_to_satisfy(self, impl_req: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSCAL implemented-requirement to OpenControl satisfy"""
        control_id = impl_req.get("control-id", "")

        satisfy = {
            "standard_key": "NIST-800-53",  # Default, would need to be inferred
            "control_key": control_id,
            "narrative": []
        }

        # Convert statements to narrative
        for statement in impl_req.get("statements", []):
            satisfy["narrative"].append({
                "key": statement.get("statement-id", ""),
                "text": statement.get("description", "")
            })

        # Get implementation status from props
        for prop in impl_req.get("props", []):
            if prop.get("name") == "implementation-status":
                oscal_status = prop.get("value", "planned")
                oc_status = self.OSCAL_TO_OC_STATUS.get(oscal_status, "partial")
                satisfy["implementation_status"] = oc_status

        # Convert set-parameters to parameters
        set_params = impl_req.get("set-parameters", [])
        if set_params:
            satisfy["parameters"] = [
                {
                    "key": param.get("param-id", ""),
                    "text": param.get("values", [""])[0] if param.get("values") else ""
                }
                for param in set_params
            ]

        return satisfy

    def oscal_catalog_to_opencontrol(
        self,
        oscal_json: str
    ) -> ConversionResult:
        """
        Convert OSCAL Catalog to OpenControl standard.yaml.

        Args:
            oscal_json: OSCAL catalog JSON content

        Returns:
            ConversionResult with OpenControl YAML output
        """
        if not YAML_AVAILABLE:
            return ConversionResult(
                success=False,
                output={},
                source_format='oscal',
                target_format='opencontrol',
                errors=['PyYAML library not installed. Run: pip install pyyaml']
            )

        try:
            oscal_data = json.loads(oscal_json)
            warnings = []

            catalog = oscal_data.get("catalog", {})
            metadata = catalog.get("metadata", {})

            oc_standard = {
                "name": metadata.get("title", "Unknown Standard"),
                "controls": {}
            }

            # Convert controls
            for control in catalog.get("controls", []):
                control_id = control.get("id", "")
                oc_standard["controls"][control_id] = self._convert_oscal_control_to_oc(control)

            # Also process controls within groups
            for group in catalog.get("groups", []):
                self._process_group_controls(group, oc_standard["controls"])

            yaml_output = yaml.dump(oc_standard, default_flow_style=False, allow_unicode=True)

            return ConversionResult(
                success=True,
                output={"yaml_content": yaml_output, "data": oc_standard},
                source_format="oscal-catalog",
                target_format="opencontrol-standard",
                warnings=warnings
            )

        except json.JSONDecodeError as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="oscal-catalog",
                target_format="opencontrol-standard",
                errors=[f"Invalid JSON: {str(e)}"]
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                output={},
                source_format="oscal-catalog",
                target_format="opencontrol-standard",
                errors=[str(e)]
            )

    def _convert_oscal_control_to_oc(self, control: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSCAL control to OpenControl format"""
        oc_control = {
            "name": control.get("title", control.get("id", "")),
            "description": ""
        }

        # Extract family from props
        for prop in control.get("props", []):
            if prop.get("name") == "family":
                oc_control["family"] = prop.get("value", "")

        # Extract description from parts
        for part in control.get("parts", []):
            if part.get("name") == "statement":
                oc_control["description"] = part.get("prose", "")
                break

        return oc_control

    def _process_group_controls(self, group: Dict[str, Any], controls_dict: Dict[str, Any]):
        """Recursively process controls within groups"""
        family_id = group.get("id", "")

        for control in group.get("controls", []):
            control_id = control.get("id", "")
            oc_control = self._convert_oscal_control_to_oc(control)
            oc_control["family"] = family_id
            controls_dict[control_id] = oc_control

        # Process nested groups
        for nested_group in group.get("groups", []):
            self._process_group_controls(nested_group, controls_dict)

    # =========================================================================
    # Batch conversion
    # =========================================================================

    def convert_opencontrol_project(
        self,
        project_path: str
    ) -> Dict[str, ConversionResult]:
        """
        Convert an entire OpenControl project directory to OSCAL.

        Args:
            project_path: Path to OpenControl project

        Returns:
            Dict of conversion results by file type
        """
        results = {}
        project = Path(project_path)

        # Convert main opencontrol.yaml
        main_file = project / "opencontrol.yaml"
        if main_file.exists():
            with open(main_file, 'r') as f:
                result = self.opencontrol_system_to_oscal(f.read())
                results["system"] = result

        # Convert standards
        standards_dir = project / "standards"
        if standards_dir.exists():
            for std_file in standards_dir.glob("*.yaml"):
                with open(std_file, 'r') as f:
                    result = self.opencontrol_standard_to_oscal(f.read())
                    results[f"standard_{std_file.stem}"] = result

        # Convert components
        components_dir = project / "components"
        if components_dir.exists():
            for comp_dir in components_dir.iterdir():
                if comp_dir.is_dir():
                    comp_file = comp_dir / "component.yaml"
                    if comp_file.exists():
                        with open(comp_file, 'r') as f:
                            result = self.opencontrol_component_to_oscal(f.read())
                            results[f"component_{comp_dir.name}"] = result

        return results
