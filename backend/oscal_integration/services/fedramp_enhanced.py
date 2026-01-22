"""
FedRAMP Enhanced Service

Enhanced FedRAMP support with:
- Control origination tracking (sp-corporate, sp-system, inherited, shared, etc.)
- FedRAMP-specific implementation status
- Responsible roles management
- LI-SaaS baseline support
- XSLT-based validation
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ControlOrigination(Enum):
    """FedRAMP control origination types"""
    SP_CORPORATE = "sp-corporate"  # Service Provider Corporate
    SP_SYSTEM = "sp-system"  # Service Provider System Specific
    CUSTOMER_CONFIGURED = "customer-configured"
    CUSTOMER_PROVIDED = "customer-provided"
    INHERITED = "inherited"
    SHARED = "shared"
    HYBRID = "hybrid"  # Multiple originations


class FedRAMPImplementationStatus(Enum):
    """FedRAMP implementation status values"""
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially-implemented"
    PLANNED = "planned"
    ALTERNATIVE_IMPLEMENTATION = "alternative-implementation"
    NOT_APPLICABLE = "not-applicable"


class FedRAMPBaseline(Enum):
    """FedRAMP baselines"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    LI_SAAS = "li-saas"  # Low Impact SaaS


@dataclass
class ControlOriginationInfo:
    """Control origination information"""
    control_id: str
    originations: List[ControlOrigination]
    description: str = ""
    responsible_roles: List[str] = field(default_factory=list)
    implementation_status: FedRAMPImplementationStatus = FedRAMPImplementationStatus.PLANNED


@dataclass
class ResponsibleRole:
    """FedRAMP responsible role"""
    role_id: str
    title: str
    party_uuids: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class FedRAMPValidationResult:
    """Enhanced FedRAMP validation result"""
    valid: bool
    baseline: FedRAMPBaseline
    compliance_percentage: float
    total_controls: int
    implemented_controls: int
    partially_implemented: int
    planned_controls: int
    not_applicable: int
    missing_controls: List[str] = field(default_factory=list)
    origination_issues: List[Dict[str, Any]] = field(default_factory=list)
    role_issues: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class FedRAMPEnhancedService:
    """
    Enhanced FedRAMP service with full control origination and role management.

    Provides:
    - Control origination tracking per control
    - FedRAMP-specific implementation status
    - Responsible role assignment
    - Baseline-specific validation
    - SSP enhancement with FedRAMP fields
    """

    # FedRAMP baseline control counts (approximate)
    BASELINE_CONTROLS = {
        FedRAMPBaseline.LOW: {
            'total': 125,
            'families': ['AC', 'AT', 'AU', 'CA', 'CM', 'CP', 'IA', 'IR', 'MA', 'MP', 'PE', 'PL', 'PS', 'RA', 'SA', 'SC', 'SI']
        },
        FedRAMPBaseline.MODERATE: {
            'total': 325,
            'families': ['AC', 'AT', 'AU', 'CA', 'CM', 'CP', 'IA', 'IR', 'MA', 'MP', 'PE', 'PL', 'PM', 'PS', 'RA', 'SA', 'SC', 'SI', 'SR']
        },
        FedRAMPBaseline.HIGH: {
            'total': 421,
            'families': ['AC', 'AT', 'AU', 'CA', 'CM', 'CP', 'IA', 'IR', 'MA', 'MP', 'PE', 'PL', 'PM', 'PS', 'RA', 'SA', 'SC', 'SI', 'SR']
        },
        FedRAMPBaseline.LI_SAAS: {
            'total': 36,  # Reduced control set for LI-SaaS
            'families': ['AC', 'AT', 'AU', 'CA', 'CM', 'IA', 'IR', 'PL', 'PS', 'RA', 'SA', 'SC', 'SI']
        }
    }

    # Standard FedRAMP responsible roles
    STANDARD_ROLES = [
        ResponsibleRole("system-owner", "Information System Owner"),
        ResponsibleRole("authorizing-official", "Authorizing Official"),
        ResponsibleRole("isso", "Information System Security Officer"),
        ResponsibleRole("issm", "Information System Security Manager"),
        ResponsibleRole("security-engineer", "Security Engineer"),
        ResponsibleRole("system-admin", "System Administrator"),
        ResponsibleRole("network-admin", "Network Administrator"),
        ResponsibleRole("database-admin", "Database Administrator"),
        ResponsibleRole("application-admin", "Application Administrator"),
        ResponsibleRole("privacy-officer", "Privacy Officer"),
        ResponsibleRole("configuration-manager", "Configuration Manager"),
        ResponsibleRole("incident-responder", "Incident Responder"),
        ResponsibleRole("risk-executive", "Risk Executive"),
    ]

    def __init__(self):
        """Initialize FedRAMP enhanced service"""
        self.control_originations: Dict[str, ControlOriginationInfo] = {}
        self.responsible_roles: Dict[str, ResponsibleRole] = {
            role.role_id: role for role in self.STANDARD_ROLES
        }

    # =========================================================================
    # CONTROL ORIGINATION
    # =========================================================================

    def set_control_origination(
        self,
        control_id: str,
        originations: List[ControlOrigination],
        description: str = "",
        responsible_roles: Optional[List[str]] = None,
        implementation_status: FedRAMPImplementationStatus = FedRAMPImplementationStatus.PLANNED
    ) -> ControlOriginationInfo:
        """
        Set control origination information for a control.

        Args:
            control_id: Control identifier (e.g., AC-2, IA-5(1))
            originations: List of origination types
            description: Description of origination
            responsible_roles: List of responsible role IDs
            implementation_status: FedRAMP implementation status

        Returns:
            ControlOriginationInfo object
        """
        info = ControlOriginationInfo(
            control_id=control_id.upper(),
            originations=originations,
            description=description,
            responsible_roles=responsible_roles or [],
            implementation_status=implementation_status
        )

        self.control_originations[control_id.upper()] = info
        return info

    def get_control_origination(self, control_id: str) -> Optional[ControlOriginationInfo]:
        """Get control origination information"""
        return self.control_originations.get(control_id.upper())

    def bulk_set_origination(
        self,
        control_ids: List[str],
        origination: ControlOrigination,
        implementation_status: FedRAMPImplementationStatus = FedRAMPImplementationStatus.PLANNED
    ) -> int:
        """
        Set the same origination for multiple controls.

        Args:
            control_ids: List of control IDs
            origination: Origination type to apply
            implementation_status: Implementation status to apply

        Returns:
            Number of controls updated
        """
        count = 0
        for control_id in control_ids:
            self.set_control_origination(
                control_id=control_id,
                originations=[origination],
                implementation_status=implementation_status
            )
            count += 1
        return count

    def get_controls_by_origination(self, origination: ControlOrigination) -> List[str]:
        """Get all controls with a specific origination type"""
        return [
            info.control_id
            for info in self.control_originations.values()
            if origination in info.originations
        ]

    # =========================================================================
    # RESPONSIBLE ROLES
    # =========================================================================

    def add_responsible_role(
        self,
        role_id: str,
        title: str,
        description: str = "",
        party_uuids: Optional[List[str]] = None
    ) -> ResponsibleRole:
        """
        Add a new responsible role.

        Args:
            role_id: Unique role identifier
            title: Role title
            description: Role description
            party_uuids: UUIDs of parties assigned to this role

        Returns:
            ResponsibleRole object
        """
        role = ResponsibleRole(
            role_id=role_id,
            title=title,
            description=description,
            party_uuids=party_uuids or []
        )
        self.responsible_roles[role_id] = role
        return role

    def assign_role_to_control(
        self,
        control_id: str,
        role_ids: List[str]
    ) -> bool:
        """
        Assign responsible roles to a control.

        Args:
            control_id: Control identifier
            role_ids: List of role IDs to assign

        Returns:
            True if successful
        """
        control_id = control_id.upper()
        if control_id not in self.control_originations:
            # Create default origination info
            self.set_control_origination(control_id, [ControlOrigination.SP_SYSTEM])

        info = self.control_originations[control_id]
        info.responsible_roles = list(set(info.responsible_roles + role_ids))
        return True

    def get_roles_for_control(self, control_id: str) -> List[ResponsibleRole]:
        """Get responsible roles for a control"""
        info = self.control_originations.get(control_id.upper())
        if not info:
            return []

        return [
            self.responsible_roles[role_id]
            for role_id in info.responsible_roles
            if role_id in self.responsible_roles
        ]

    def get_controls_by_role(self, role_id: str) -> List[str]:
        """Get all controls assigned to a specific role"""
        return [
            info.control_id
            for info in self.control_originations.values()
            if role_id in info.responsible_roles
        ]

    # =========================================================================
    # SSP ENHANCEMENT
    # =========================================================================

    def enhance_ssp_with_fedramp(
        self,
        ssp_content: str,
        baseline: FedRAMPBaseline = FedRAMPBaseline.MODERATE
    ) -> Dict[str, Any]:
        """
        Enhance an OSCAL SSP with FedRAMP-specific information.

        Args:
            ssp_content: OSCAL SSP JSON content
            baseline: FedRAMP baseline

        Returns:
            Enhanced SSP document
        """
        ssp = json.loads(ssp_content)
        ssp_obj = ssp.get('system-security-plan', {})

        # Add FedRAMP baseline information
        if 'props' not in ssp_obj:
            ssp_obj['props'] = []

        # Add FedRAMP props
        fedramp_props = [
            {
                'name': 'fedramp-baseline',
                'ns': 'https://fedramp.gov/ns/oscal',
                'value': baseline.value
            },
            {
                'name': 'authorization-type',
                'ns': 'https://fedramp.gov/ns/oscal',
                'value': 'fedramp-agency' if baseline != FedRAMPBaseline.LI_SAAS else 'fedramp-li-saas'
            }
        ]

        # Add props if not already present
        existing_prop_names = {p.get('name') for p in ssp_obj.get('props', [])}
        for prop in fedramp_props:
            if prop['name'] not in existing_prop_names:
                ssp_obj['props'].append(prop)

        # Enhance control implementations with origination
        control_impl = ssp_obj.get('control-implementation', {})
        impl_reqs = control_impl.get('implemented-requirements', [])

        for impl_req in impl_reqs:
            control_id = impl_req.get('control-id', '')
            origination_info = self.control_originations.get(control_id.upper())

            if origination_info:
                # Add origination props
                if 'props' not in impl_req:
                    impl_req['props'] = []

                # Add control-origination prop
                impl_req['props'].append({
                    'name': 'control-origination',
                    'ns': 'https://fedramp.gov/ns/oscal',
                    'value': ','.join(o.value for o in origination_info.originations)
                })

                # Add implementation-status prop
                impl_req['props'].append({
                    'name': 'implementation-status',
                    'ns': 'https://fedramp.gov/ns/oscal',
                    'value': origination_info.implementation_status.value
                })

                # Add responsible-roles
                if origination_info.responsible_roles:
                    if 'responsible-roles' not in impl_req:
                        impl_req['responsible-roles'] = []

                    for role_id in origination_info.responsible_roles:
                        impl_req['responsible-roles'].append({
                            'role-id': role_id
                        })

        # Add all responsible roles to metadata
        metadata = ssp_obj.get('metadata', {})
        if 'roles' not in metadata:
            metadata['roles'] = []

        existing_role_ids = {r.get('id') for r in metadata.get('roles', [])}
        for role in self.responsible_roles.values():
            if role.role_id not in existing_role_ids:
                metadata['roles'].append({
                    'id': role.role_id,
                    'title': role.title,
                    'description': role.description
                })

        ssp_obj['metadata'] = metadata
        ssp['system-security-plan'] = ssp_obj

        return ssp

    def extract_fedramp_info_from_ssp(self, ssp_content: str) -> Dict[str, Any]:
        """
        Extract FedRAMP-specific information from an SSP.

        Args:
            ssp_content: OSCAL SSP JSON content

        Returns:
            Dict with FedRAMP information
        """
        ssp = json.loads(ssp_content)
        ssp_obj = ssp.get('system-security-plan', {})

        result = {
            'baseline': None,
            'authorization_type': None,
            'control_originations': {},
            'responsible_roles': [],
            'implementation_summary': {
                'implemented': 0,
                'partially_implemented': 0,
                'planned': 0,
                'alternative': 0,
                'not_applicable': 0
            }
        }

        # Extract baseline from props
        for prop in ssp_obj.get('props', []):
            if prop.get('name') == 'fedramp-baseline':
                result['baseline'] = prop.get('value')
            elif prop.get('name') == 'authorization-type':
                result['authorization_type'] = prop.get('value')

        # Extract control implementations
        control_impl = ssp_obj.get('control-implementation', {})
        for impl_req in control_impl.get('implemented-requirements', []):
            control_id = impl_req.get('control-id', '')

            origination = None
            impl_status = None

            for prop in impl_req.get('props', []):
                if prop.get('name') == 'control-origination':
                    origination = prop.get('value')
                elif prop.get('name') == 'implementation-status':
                    impl_status = prop.get('value')

            if origination or impl_status:
                result['control_originations'][control_id] = {
                    'origination': origination,
                    'implementation_status': impl_status,
                    'responsible_roles': [
                        r.get('role-id') for r in impl_req.get('responsible-roles', [])
                    ]
                }

            # Update summary
            if impl_status == 'implemented':
                result['implementation_summary']['implemented'] += 1
            elif impl_status == 'partially-implemented':
                result['implementation_summary']['partially_implemented'] += 1
            elif impl_status == 'planned':
                result['implementation_summary']['planned'] += 1
            elif impl_status == 'alternative-implementation':
                result['implementation_summary']['alternative'] += 1
            elif impl_status == 'not-applicable':
                result['implementation_summary']['not_applicable'] += 1

        # Extract roles from metadata
        metadata = ssp_obj.get('metadata', {})
        for role in metadata.get('roles', []):
            result['responsible_roles'].append({
                'id': role.get('id'),
                'title': role.get('title')
            })

        return result

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate_fedramp_ssp(
        self,
        ssp_content: str,
        baseline: FedRAMPBaseline = FedRAMPBaseline.MODERATE
    ) -> FedRAMPValidationResult:
        """
        Validate SSP against FedRAMP requirements.

        Args:
            ssp_content: OSCAL SSP JSON content
            baseline: FedRAMP baseline to validate against

        Returns:
            FedRAMPValidationResult
        """
        errors = []
        warnings = []
        origination_issues = []
        role_issues = []

        try:
            ssp = json.loads(ssp_content)
            ssp_obj = ssp.get('system-security-plan', {})

            # Get baseline requirements
            baseline_info = self.BASELINE_CONTROLS[baseline]
            required_families = set(baseline_info['families'])

            # Extract control implementations
            control_impl = ssp_obj.get('control-implementation', {})
            impl_reqs = control_impl.get('implemented-requirements', [])

            # Track implementation status
            implemented = 0
            partially_implemented = 0
            planned = 0
            not_applicable = 0
            missing_controls = []

            # Track which controls are documented
            documented_controls = set()

            for impl_req in impl_reqs:
                control_id = impl_req.get('control-id', '')
                documented_controls.add(control_id.upper())

                # Check for origination
                has_origination = False
                impl_status = None

                for prop in impl_req.get('props', []):
                    if prop.get('name') == 'control-origination':
                        has_origination = True
                    elif prop.get('name') == 'implementation-status':
                        impl_status = prop.get('value')

                if not has_origination:
                    origination_issues.append({
                        'control_id': control_id,
                        'issue': 'Missing control-origination property'
                    })

                # Check for responsible roles on customer/shared controls
                has_roles = bool(impl_req.get('responsible-roles'))
                if not has_roles:
                    role_issues.append({
                        'control_id': control_id,
                        'issue': 'Missing responsible-roles'
                    })

                # Count by status
                if impl_status == 'implemented':
                    implemented += 1
                elif impl_status == 'partially-implemented':
                    partially_implemented += 1
                elif impl_status == 'planned':
                    planned += 1
                elif impl_status == 'not-applicable':
                    not_applicable += 1
                else:
                    planned += 1  # Default to planned if no status

            # Check for required controls (simplified check by family)
            for family in required_families:
                family_controls = [c for c in documented_controls if c.startswith(family + '-')]
                if not family_controls:
                    missing_controls.append(f"{family} family")

            # Calculate compliance
            total_documented = len(documented_controls)
            total_required = baseline_info['total']

            if total_required > 0:
                # Implemented + partially gets partial credit
                effective_implemented = implemented + (partially_implemented * 0.5)
                compliance_percentage = (effective_implemented / total_required) * 100
            else:
                compliance_percentage = 0.0

            # Validation errors
            if compliance_percentage < 100 and not_applicable == 0:
                warnings.append(f"Only {compliance_percentage:.1f}% of {baseline.value} controls documented")

            if origination_issues:
                warnings.append(f"{len(origination_issues)} controls missing origination information")

            if role_issues:
                warnings.append(f"{len(role_issues)} controls missing responsible roles")

            # Check for critical missing elements
            metadata = ssp_obj.get('metadata', {})
            if not metadata.get('roles'):
                errors.append("No roles defined in SSP metadata")

            sys_chars = ssp_obj.get('system-characteristics', {})
            if not sys_chars.get('authorization-boundary'):
                warnings.append("Authorization boundary not defined")

            return FedRAMPValidationResult(
                valid=len(errors) == 0,
                baseline=baseline,
                compliance_percentage=round(compliance_percentage, 2),
                total_controls=total_required,
                implemented_controls=implemented,
                partially_implemented=partially_implemented,
                planned_controls=planned,
                not_applicable=not_applicable,
                missing_controls=missing_controls,
                origination_issues=origination_issues,
                role_issues=role_issues,
                errors=errors,
                warnings=warnings
            )

        except json.JSONDecodeError as e:
            return FedRAMPValidationResult(
                valid=False,
                baseline=baseline,
                compliance_percentage=0.0,
                total_controls=0,
                implemented_controls=0,
                partially_implemented=0,
                planned_controls=0,
                not_applicable=0,
                errors=[f"Invalid JSON: {str(e)}"]
            )
        except Exception as e:
            return FedRAMPValidationResult(
                valid=False,
                baseline=baseline,
                compliance_percentage=0.0,
                total_controls=0,
                implemented_controls=0,
                partially_implemented=0,
                planned_controls=0,
                not_applicable=0,
                errors=[str(e)]
            )

    # =========================================================================
    # LI-SAAS SUPPORT
    # =========================================================================

    def get_li_saas_controls(self) -> List[Dict[str, Any]]:
        """
        Get the list of controls required for FedRAMP LI-SaaS.

        Returns:
            List of control information
        """
        # Core LI-SaaS controls (simplified list - actual FedRAMP LI-SaaS has specific controls)
        li_saas_controls = [
            # Access Control
            {'id': 'AC-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'AC-2', 'title': 'Account Management', 'origination': 'shared'},
            {'id': 'AC-3', 'title': 'Access Enforcement', 'origination': 'sp-system'},
            {'id': 'AC-7', 'title': 'Unsuccessful Logon Attempts', 'origination': 'sp-system'},
            {'id': 'AC-8', 'title': 'System Use Notification', 'origination': 'sp-system'},
            {'id': 'AC-14', 'title': 'Permitted Actions Without Identification', 'origination': 'sp-system'},
            {'id': 'AC-17', 'title': 'Remote Access', 'origination': 'sp-system'},
            {'id': 'AC-20', 'title': 'Use of External Systems', 'origination': 'shared'},

            # Awareness and Training
            {'id': 'AT-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'AT-2', 'title': 'Literacy Training and Awareness', 'origination': 'sp-corporate'},

            # Audit and Accountability
            {'id': 'AU-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'AU-2', 'title': 'Event Logging', 'origination': 'sp-system'},
            {'id': 'AU-3', 'title': 'Content of Audit Records', 'origination': 'sp-system'},
            {'id': 'AU-6', 'title': 'Audit Record Review', 'origination': 'sp-system'},

            # Security Assessment
            {'id': 'CA-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'CA-2', 'title': 'Control Assessments', 'origination': 'sp-corporate'},

            # Configuration Management
            {'id': 'CM-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'CM-2', 'title': 'Baseline Configuration', 'origination': 'sp-system'},
            {'id': 'CM-6', 'title': 'Configuration Settings', 'origination': 'sp-system'},

            # Identification and Authentication
            {'id': 'IA-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'IA-2', 'title': 'Identification and Authentication', 'origination': 'sp-system'},
            {'id': 'IA-5', 'title': 'Authenticator Management', 'origination': 'shared'},
            {'id': 'IA-8', 'title': 'Identification and Authentication (Non-Org Users)', 'origination': 'sp-system'},

            # Incident Response
            {'id': 'IR-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'IR-2', 'title': 'Incident Response Training', 'origination': 'sp-corporate'},
            {'id': 'IR-6', 'title': 'Incident Reporting', 'origination': 'sp-corporate'},

            # Planning
            {'id': 'PL-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},

            # Personnel Security
            {'id': 'PS-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},

            # Risk Assessment
            {'id': 'RA-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'RA-5', 'title': 'Vulnerability Monitoring and Scanning', 'origination': 'sp-system'},

            # System and Services Acquisition
            {'id': 'SA-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},

            # System and Communications Protection
            {'id': 'SC-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'SC-7', 'title': 'Boundary Protection', 'origination': 'sp-system'},
            {'id': 'SC-13', 'title': 'Cryptographic Protection', 'origination': 'sp-system'},

            # System and Information Integrity
            {'id': 'SI-1', 'title': 'Policy and Procedures', 'origination': 'sp-corporate'},
            {'id': 'SI-2', 'title': 'Flaw Remediation', 'origination': 'sp-system'},
            {'id': 'SI-3', 'title': 'Malicious Code Protection', 'origination': 'sp-system'},
        ]

        return li_saas_controls

    def initialize_li_saas_originations(self) -> int:
        """
        Initialize control originations for LI-SaaS baseline.

        Returns:
            Number of controls initialized
        """
        li_saas_controls = self.get_li_saas_controls()

        for control in li_saas_controls:
            origination = ControlOrigination(control['origination'])
            self.set_control_origination(
                control_id=control['id'],
                originations=[origination],
                description=control['title'],
                implementation_status=FedRAMPImplementationStatus.PLANNED
            )

        return len(li_saas_controls)

    # =========================================================================
    # REPORTING
    # =========================================================================

    def generate_control_matrix(self, baseline: FedRAMPBaseline) -> Dict[str, Any]:
        """
        Generate a FedRAMP control responsibility matrix.

        Args:
            baseline: FedRAMP baseline

        Returns:
            Control matrix with origination and role assignments
        """
        matrix = {
            'baseline': baseline.value,
            'generated_at': datetime.now().isoformat(),
            'controls': [],
            'summary': {
                'total': 0,
                'by_origination': {},
                'by_status': {}
            }
        }

        # Group controls
        for control_id, info in sorted(self.control_originations.items()):
            control_entry = {
                'control_id': control_id,
                'originations': [o.value for o in info.originations],
                'implementation_status': info.implementation_status.value,
                'responsible_roles': info.responsible_roles,
                'description': info.description
            }
            matrix['controls'].append(control_entry)

            # Update summary
            matrix['summary']['total'] += 1

            for orig in info.originations:
                orig_key = orig.value
                matrix['summary']['by_origination'][orig_key] = \
                    matrix['summary']['by_origination'].get(orig_key, 0) + 1

            status_key = info.implementation_status.value
            matrix['summary']['by_status'][status_key] = \
                matrix['summary']['by_status'].get(status_key, 0) + 1

        return matrix

    def generate_role_responsibility_report(self) -> Dict[str, Any]:
        """
        Generate a report of responsibilities by role.

        Returns:
            Role responsibility report
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'roles': []
        }

        for role in self.responsible_roles.values():
            controls = self.get_controls_by_role(role.role_id)

            role_entry = {
                'role_id': role.role_id,
                'title': role.title,
                'description': role.description,
                'control_count': len(controls),
                'controls': sorted(controls)
            }
            report['roles'].append(role_entry)

        # Sort by control count descending
        report['roles'].sort(key=lambda r: r['control_count'], reverse=True)

        return report
