"""Write/Create MCP tools for CISO Assistant"""

from ..client import make_post_request, make_get_request
from ..resolvers import (
    resolve_ebios_rm_study_id,
    resolve_folder_id,
    resolve_perimeter_id,
    resolve_risk_matrix_id,
    resolve_framework_id,
    resolve_risk_assessment_id,
    resolve_applied_control_id,
    resolve_asset_id,
    resolve_actor_ids,
    resolve_reference_control_id,
    resolve_qualification_ids,
    resolve_risk_level_index,
    parse_duration,
)
from ..config import GLOBAL_FOLDER_ID
from ..utils.response_formatter import (
    success_response,
    error_response,
    http_error_response,
)


# ---------------------------------------------------------------------------
# Asset objectives / capabilities (shared by create_asset and update_asset)
# ---------------------------------------------------------------------------

# Backend Asset.DEFAULT_SECURITY_OBJECTIVES / DEFAULT_DISASTER_RECOVERY_OBJECTIVES
SECURITY_CRITERIA = (
    "confidentiality",
    "integrity",
    "availability",
    "proof",
    "authenticity",
    "privacy",
    "safety",
)
RECOVERY_KEYS = ("rto", "rpo", "mtd")


def _collect_criteria(prefix: str, params: dict) -> dict:
    """Pick the touched criteria among <prefix>_<criterion>[_enabled] params.

    Returns {criterion: (value, enabled)} for every criterion with a value or
    a flag. Values must be integers 0-4 (raises ValueError otherwise).
    """
    touched = {}
    for criterion in SECURITY_CRITERIA:
        value = params.get(f"{prefix}_{criterion}")
        enabled = params.get(f"{prefix}_{criterion}_enabled")
        if value is None and enabled is None:
            continue
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4
        ):
            raise ValueError(
                f"{prefix}_{criterion} must be an integer between 0 and 4, got {value!r}"
            )
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError(
                f"{prefix}_{criterion}_enabled must be a boolean, got {enabled!r}"
            )
        touched[criterion] = (value, enabled)
    return touched


def _collect_durations(prefix: str, params: dict) -> dict:
    """Pick the touched <prefix>_<rto|rpo|mtd> params, parsed to seconds."""
    return {
        key: parse_duration(params[f"{prefix}_{key}"])
        for key in RECOVERY_KEYS
        if params.get(f"{prefix}_{key}") is not None
    }


def _merge_criteria(current: dict, touched: dict) -> dict:
    """Merge touched criteria over the stored ones.

    Every stored key that is not touched is kept as is. A touched value
    without its flag means enabled; a flag alone keeps the stored value.
    """
    merged = {k: dict(v) for k, v in (current or {}).items() if isinstance(v, dict)}
    for criterion, (value, enabled) in touched.items():
        entry = dict(merged.get(criterion) or {"value": 0, "is_enabled": False})
        if value is not None:
            entry["value"] = value
        entry.setdefault("value", 0)
        if enabled is not None:
            entry["is_enabled"] = enabled
        elif value is not None:
            entry["is_enabled"] = True
        else:
            entry.setdefault("is_enabled", False)
        merged[criterion] = entry
    return merged


def _merge_durations(current: dict, touched: dict) -> dict:
    merged = {k: dict(v) for k, v in (current or {}).items() if isinstance(v, dict)}
    for key, seconds in touched.items():
        entry = dict(merged.get(key) or {})
        entry["value"] = seconds
        merged[key] = entry
    return merged


def _collect_asset_objective_changes(params: dict) -> dict:
    """Validate and group the flat objective/capability params of an asset tool.

    Returns {"security_objectives": {...touched}, "security_capabilities": ...,
    "disaster_recovery_objectives": ..., "recovery_capabilities": ...} with
    only the fields that have at least one touched key.
    """
    changes = {
        "security_objectives": _collect_criteria("sec", params),
        "security_capabilities": _collect_criteria("cap", params),
        "disaster_recovery_objectives": _collect_durations("dro", params),
        "recovery_capabilities": _collect_durations("rcap", params),
    }
    return {field: touched for field, touched in changes.items() if touched}


def _build_asset_objectives(changes: dict, current_asset: dict = None) -> dict:
    """Payload fragment for the touched objective/capability fields.

    current_asset is the stored asset as returned by /assets/{id}/object/
    (update); None on create, where only the touched keys are sent.
    """
    payload = {}
    for field, touched in changes.items():
        stored = (current_asset or {}).get(field) or {}
        stored = stored.get("objectives") if isinstance(stored, dict) else {}
        stored = stored if isinstance(stored, dict) else {}
        if field in ("security_objectives", "security_capabilities"):
            merged = _merge_criteria(stored, touched)
        else:
            merged = _merge_durations(stored, touched)
        payload[field] = {"objectives": merged}
    return payload


def _ignored_fields_warning(changes: dict, asset_type: str) -> str:
    """Warning for fields the backend computes (and ignores) for this asset type."""
    if asset_type == "SP":
        ignored = [
            f
            for f in ("security_objectives", "disaster_recovery_objectives")
            if f in changes
        ]
        why = "supporting assets inherit their objectives from their primary parents"
    elif asset_type == "PR":
        ignored = [
            f
            for f in ("security_capabilities", "recovery_capabilities")
            if f in changes
        ]
        why = "primary assets aggregate their capabilities from their supporting assets"
    else:
        return ""
    if not ignored:
        return ""
    return (
        f"\nWARNING: {', '.join(ignored)} stored as asked, but the backend computes "
        f"this for a {asset_type} asset and ignores the stored value ({why})."
    )


async def create_folder(
    name: str,
    description: str = "",
    parent_folder_id: str = None,
) -> str:
    """Create folder (domain)

    Args:
        name: Folder name
        description: Description
        parent_folder_id: Parent folder ID/name
    """
    try:
        payload = {
            "name": name,
            "description": description,
        }

        if parent_folder_id:
            parent_folder_id = resolve_folder_id(parent_folder_id)
            payload["parent_folder"] = parent_folder_id

        res = make_post_request("/folders/", payload)

        if res.status_code == 201:
            folder = res.json()
            return f"Created folder: {folder.get('name')} (ID: {folder.get('id')})"
        else:
            return f"Error creating folder: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_folder: {str(e)}"


async def create_perimeter(
    name: str,
    description: str = "",
    folder_id: str = None,
) -> str:
    """Create perimeter (assessment scope)

    Args:
        name: Perimeter name
        description: Description
        folder_id: Folder ID/name
    """
    try:
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
        }

        if folder_id:
            payload["folder"] = folder_id

        res = make_post_request("/perimeters/", payload)

        if res.status_code == 201:
            perimeter = res.json()
            return f"Created perimeter: {perimeter.get('name')} (ID: {perimeter.get('id')})"
        else:
            return f"Error creating perimeter: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_perimeter: {str(e)}"


async def create_asset(
    name: str,
    description: str = "",
    asset_type: str = "PR",
    folder_id: str = None,
    owner: list = None,
    parent_assets: list = None,
    sec_confidentiality: int = None,
    sec_confidentiality_enabled: bool = None,
    sec_integrity: int = None,
    sec_integrity_enabled: bool = None,
    sec_availability: int = None,
    sec_availability_enabled: bool = None,
    sec_proof: int = None,
    sec_proof_enabled: bool = None,
    sec_authenticity: int = None,
    sec_authenticity_enabled: bool = None,
    sec_privacy: int = None,
    sec_privacy_enabled: bool = None,
    sec_safety: int = None,
    sec_safety_enabled: bool = None,
    dro_rto: int | str = None,
    dro_rpo: int | str = None,
    dro_mtd: int | str = None,
    cap_confidentiality: int = None,
    cap_confidentiality_enabled: bool = None,
    cap_integrity: int = None,
    cap_integrity_enabled: bool = None,
    cap_availability: int = None,
    cap_availability_enabled: bool = None,
    cap_proof: int = None,
    cap_proof_enabled: bool = None,
    cap_authenticity: int = None,
    cap_authenticity_enabled: bool = None,
    cap_privacy: int = None,
    cap_privacy_enabled: bool = None,
    cap_safety: int = None,
    cap_safety_enabled: bool = None,
    rcap_rto: int | str = None,
    rcap_rpo: int | str = None,
    rcap_mtd: int | str = None,
) -> str:
    """Create asset in folder

    Objectives (sec_*, dro_*) are effective on primary assets (supporting ones
    inherit them); capabilities (cap_*, rcap_*) are effective on supporting
    assets (primary ones aggregate them). A value without its _enabled flag
    means enabled.

    Args:
        name: Asset name
        description: Description
        asset_type: PR (Primary) | SP (Supporting)
        folder_id: Folder ID/name
        owner: List of owners as actor UUIDs, emails or names
        parent_assets: List of parent asset IDs/names
        sec_confidentiality: Confidentiality objective 0-4 (0=undefined,1=low,2=med,3=high,4=critical)
        sec_confidentiality_enabled: Enable confidentiality objective
        sec_integrity: Integrity objective 0-4
        sec_integrity_enabled: Enable integrity objective
        sec_availability: Availability objective 0-4
        sec_availability_enabled: Enable availability objective
        sec_proof: Proof (traceability) objective 0-4
        sec_proof_enabled: Enable proof objective
        sec_authenticity: Authenticity objective 0-4
        sec_authenticity_enabled: Enable authenticity objective
        sec_privacy: Privacy objective 0-4
        sec_privacy_enabled: Enable privacy objective
        sec_safety: Safety objective 0-4
        sec_safety_enabled: Enable safety objective
        dro_rto: Recovery Time Objective: seconds or duration ("90s", "30m", "2h", "1d", "1h30m"); 0 = not set
        dro_rpo: Recovery Point Objective: seconds or duration; 0 = not set
        dro_mtd: Maximum Tolerable Downtime: seconds or duration; 0 = not set
        cap_confidentiality: Actual confidentiality capability 0-4
        cap_confidentiality_enabled: Enable confidentiality capability
        cap_integrity: Actual integrity capability 0-4
        cap_integrity_enabled: Enable integrity capability
        cap_availability: Actual availability capability 0-4
        cap_availability_enabled: Enable availability capability
        cap_proof: Actual proof capability 0-4
        cap_proof_enabled: Enable proof capability
        cap_authenticity: Actual authenticity capability 0-4
        cap_authenticity_enabled: Enable authenticity capability
        cap_privacy: Actual privacy capability 0-4
        cap_privacy_enabled: Enable privacy capability
        cap_safety: Actual safety capability 0-4
        cap_safety_enabled: Enable safety capability
        rcap_rto: Actual recovery time: seconds or duration; 0 = not set
        rcap_rpo: Actual recovery point: seconds or duration; 0 = not set
        rcap_mtd: Actual maximum downtime: seconds or duration; 0 = not set
    """
    try:
        # Validate objectives first: a bad value sends nothing
        changes = _collect_asset_objective_changes(locals())

        # If no folder specified, try to get the default folder
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
            "type": asset_type,
        }

        if folder_id:
            payload["folder"] = folder_id

        if owner is not None:
            payload["owner"] = resolve_actor_ids(owner)
        if parent_assets is not None:
            payload["parent_assets"] = [resolve_asset_id(p) for p in parent_assets]

        payload.update(_build_asset_objectives(changes))

        res = make_post_request("/assets/", payload)

        if res.status_code == 201:
            asset = res.json()
            return f"Created asset: {asset.get('name')} (ID: {asset.get('id')})" + (
                _ignored_fields_warning(changes, asset_type)
            )
        else:
            return f"Error creating asset: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_asset: {str(e)}"


async def create_threat(
    name: str,
    description: str = "",
    provider: str = "",
    ref_id: str = "",
    folder_id: str = None,
) -> str:
    """Create threat in folder

    Args:
        name: Threat name
        description: Description
        provider: Provider/source (e.g. "MITRE ATT&CK")
        ref_id: Reference ID
        folder_id: Folder ID/name
    """
    try:
        # If no folder specified, try to get the default folder
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
        }

        if provider:
            payload["provider"] = provider

        if ref_id:
            payload["ref_id"] = ref_id

        if folder_id:
            payload["folder"] = folder_id

        res = make_post_request("/threats/", payload)

        if res.status_code == 201:
            threat = res.json()
            return f"Created threat: {threat.get('name')} (ID: {threat.get('id')})"
        else:
            return f"Error creating threat: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_threat: {str(e)}"


APPLIED_CONTROL_STATUSES = [
    "to_do",
    "in_progress",
    "on_hold",
    "active",
    "degraded",
    "deprecated",
    "--",
]
# Values the tool used to advertise, which the backend rejects
LEGACY_APPLIED_CONTROL_STATUSES = {"planned": "to_do", "inactive": "deprecated"}


def _normalize_applied_control_status(status: str) -> str:
    status = LEGACY_APPLIED_CONTROL_STATUSES.get(status, status)
    if status not in APPLIED_CONTROL_STATUSES:
        raise ValueError(
            f"Invalid status. Must be one of: {', '.join(APPLIED_CONTROL_STATUSES)}"
        )
    return status


async def create_applied_control(
    name: str,
    description: str = "",
    eta: str = None,
    folder_id: str = None,
    category: str = "technical",
    status: str = None,
    reference_control: str = None,
    assets: list = None,
    owner: list = None,
    priority: int = None,
    ref_id: str = None,
    csf_function: str = None,
) -> str:
    """Create applied control (security measure)

    Args:
        name: Control name
        description: Description
        eta: Completion date YYYY-MM-DD
        folder_id: Folder ID/name
        category: policy | process | technical | physical | procedure
        status: to_do | in_progress | on_hold | active | degraded | deprecated | --
            (omitted = backend default "--"; legacy planned -> to_do, inactive -> deprecated)
        reference_control: Reference control UUID, URN, ref_id (e.g. "POL.AI") or name
        assets: List of asset IDs/names
        owner: List of owners as actor UUIDs, emails or names (users, teams, entities)
        priority: 1-4 (1=P1, 4=P4)
        ref_id: Reference ID
        csf_function: identify | protect | detect | respond | recover | govern
    """
    try:
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
            "category": category,
        }

        if status is not None:
            payload["status"] = _normalize_applied_control_status(status)

        if folder_id:
            payload["folder"] = folder_id

        if eta:
            payload["eta"] = eta

        if reference_control is not None:
            payload["reference_control"] = resolve_reference_control_id(
                reference_control
            )
        if assets is not None:
            payload["assets"] = [
                resolve_asset_id(asset, folder_id=folder_id) for asset in assets
            ]
        if owner is not None:
            payload["owner"] = resolve_actor_ids(owner)
        if priority is not None:
            payload["priority"] = priority
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if csf_function is not None:
            payload["csf_function"] = csf_function

        res = make_post_request("/applied-controls/", payload)

        if res.status_code == 201:
            control = res.json()
            return f"Created applied control: {control.get('name')} (ID: {control.get('id')})"
        else:
            return f"Error creating applied control: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_applied_control: {str(e)}"


async def create_risk_assessment(
    name: str,
    risk_matrix_id: str = None,
    perimeter_id: str = None,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
    ebios_rm_study_id: str = None,
    risk_tolerance: int | str = None,
) -> str:
    """Create risk assessment with risk matrix and perimeter

    Args:
        name: Assessment name
        risk_matrix_id: Risk matrix ID/name. Optional with ebios_rm_study_id,
            which supplies the study's own matrix
        perimeter_id: Perimeter ID/name (required)
        description: Description
        version: Version string
        status: planned | in_progress | in_review | done | deprecated
        folder_id: Folder ID/name (inherits from perimeter if not set)
        ebios_rm_study_id: EBIOS RM study ID/name to attach it to (workshop 5).
            Generates one risk scenario per selected operational scenario.
            Refuses if the study already has one; sync that instead.
        risk_tolerance: Risk level index of the matrix (-1 = unset), or a risk
            level name/abbreviation (e.g. "High") resolved against the matrix
    """
    try:
        if ebios_rm_study_id:
            ebios_rm_study_id = resolve_ebios_rm_study_id(ebios_rm_study_id)
            if not risk_matrix_id:
                # the study's scales are what the generated scenarios are scored on
                study = make_get_request(f"/ebios-rm/studies/{ebios_rm_study_id}/")
                if study.status_code == 200:
                    matrix = study.json().get("risk_matrix")
                    risk_matrix_id = (
                        matrix.get("id") if isinstance(matrix, dict) else matrix
                    )

        if ebios_rm_study_id:
            # creating a second one silently detaches the first, so send the
            # caller down the same path the workshop-5 page takes
            existing = make_get_request(
                "/risk-assessments/", params={"ebios_rm_study": ebios_rm_study_id}
            )
            if existing.status_code == 200:
                rows = existing.json().get("results", [])
                if rows:
                    cur = rows[0]
                    label = cur.get("str") or cur.get("name") or cur.get("id")
                    return error_response(
                        "Study already has a risk assessment",
                        f"'{label}' (ID: {cur.get('id')}) is already linked to this "
                        "EBIOS RM study. Creating another would detach it.",
                        "Call sync_risk_assessment_from_ebios_rm with that ID to "
                        "refresh it from the study, or delete it first to start over.",
                        retry_allowed=False,
                    )

        if not risk_matrix_id:
            return error_response(
                "Missing risk matrix",
                "risk_matrix_id is required unless ebios_rm_study_id supplies one.",
                "Pass risk_matrix_id, or an ebios_rm_study_id whose study has a matrix.",
                retry_allowed=True,
            )

        # Resolve risk matrix name to ID if needed
        risk_matrix_id = resolve_risk_matrix_id(risk_matrix_id)

        # Resolve perimeter name to ID if needed
        perimeter_id = resolve_perimeter_id(perimeter_id)

        # Resolve folder name to ID if needed (optional)
        if folder_id:
            folder_id = resolve_folder_id(folder_id)
        elif GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {
            "name": name,
            "risk_matrix": risk_matrix_id,
            "perimeter": perimeter_id,
            "description": description,
            "version": version,
            "status": status,
        }

        # Folder is optional - if not provided, it inherits from perimeter
        if folder_id:
            payload["folder"] = folder_id

        if ebios_rm_study_id:
            payload["ebios_rm_study"] = ebios_rm_study_id

        if risk_tolerance is not None:
            payload["risk_tolerance"] = resolve_risk_level_index(
                risk_tolerance, risk_matrix_id
            )

        res = make_post_request("/risk-assessments/", payload)

        if res.status_code == 201:
            assessment = res.json()
            result = f"Created risk assessment: {assessment.get('name')} (ID: {assessment.get('id')})"
            return success_response(
                result,
                "create_risk_assessment",
                "Risk assessment created successfully. You can now create risk scenarios for this assessment",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def create_risk_scenario(
    name: str,
    description: str = "",
    risk_assessment_id: str = None,
    folder_id: str = None,
    existing_controls: str = "",
    current_proba: int = None,
    current_impact: int = None,
    assets: list = None,
    threats: list = None,
    threat_library: str = None,
    applied_controls: list = None,
    existing_applied_controls: list = None,
    qualifications: list = None,
    owner: list = None,
    inherent_proba: int = None,
    inherent_impact: int = None,
    residual_proba: int = None,
    residual_impact: int = None,
    treatment: str = None,
    ref_id: str = None,
    justification: str = None,
) -> str:
    """Create risk scenario with linked assets/threats/controls

    Args:
        name: Scenario name
        description: Description
        risk_assessment_id: Risk assessment ID/name
        folder_id: Folder ID/name
        existing_controls: Existing controls description
        current_proba: Probability 0-4 (0=very low, 4=very high)
        current_impact: Impact 0-4 (0=very low, 4=very high)
        assets: List of asset IDs/names
        threats: List of threat IDs/names
        threat_library: Library URN to filter threats (e.g. "urn:intuitem:risk:library:intuitem-common-catalog")
        applied_controls: List of planned control IDs/names
        existing_applied_controls: List of existing control IDs/names
        qualifications: List of qualifications: letters C/I/A(D)/T(P)
            (confidentiality/integrity/availability/proof), names or UUIDs
        owner: List of owners as actor UUIDs, emails or names
        inherent_proba: Inherent probability index (from risk matrix)
        inherent_impact: Inherent impact index (from risk matrix)
        residual_proba: Residual probability index (from risk matrix)
        residual_impact: Residual impact index (from risk matrix)
        treatment: open | mitigate | accept | avoid | transfer | cancelled
        ref_id: Reference ID
        justification: Justification text
    """
    try:
        from ..resolvers import resolve_asset_id, resolve_applied_control_id

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        # Resolve risk assessment name to ID if needed
        if risk_assessment_id:
            risk_assessment_id = resolve_risk_assessment_id(risk_assessment_id)

        payload = {
            "name": name,
            "description": description,
        }

        if folder_id:
            payload["folder"] = folder_id

        if risk_assessment_id:
            payload["risk_assessment"] = risk_assessment_id

        if existing_controls:
            payload["existing_controls"] = existing_controls

        if current_proba is not None:
            payload["current_proba"] = current_proba

        if current_impact is not None:
            payload["current_impact"] = current_impact

        for field, value in (
            ("inherent_proba", inherent_proba),
            ("inherent_impact", inherent_impact),
            ("residual_proba", residual_proba),
            ("residual_impact", residual_impact),
            ("treatment", treatment),
            ("ref_id", ref_id),
            ("justification", justification),
        ):
            if value is not None:
                payload[field] = value

        if qualifications is not None:
            payload["qualifications"] = resolve_qualification_ids(qualifications)

        if owner is not None:
            payload["owner"] = resolve_actor_ids(owner)

        # Resolve asset names to IDs if provided (pass folder_id to scope lookup)
        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset, folder_id=folder_id)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        # Resolve threat names to IDs if provided (pass folder_id to scope lookup for custom threats)
        if threats:
            from ..resolvers import resolve_threat_id

            resolved_threats = []
            for threat in threats:
                resolved_threat_id = resolve_threat_id(
                    threat, library=threat_library, folder_id=folder_id
                )
                resolved_threats.append(resolved_threat_id)
            payload["threats"] = resolved_threats

        # Resolve new/planned applied control names to IDs if provided (pass folder_id to scope lookup)
        if applied_controls:
            resolved_controls = []
            for control in applied_controls:
                resolved_control_id = resolve_applied_control_id(
                    control, folder_id=folder_id
                )
                resolved_controls.append(resolved_control_id)
            payload["applied_controls"] = resolved_controls

        # Resolve existing applied control names to IDs if provided (pass folder_id to scope lookup)
        if existing_applied_controls:
            resolved_existing_controls = []
            for control in existing_applied_controls:
                resolved_control_id = resolve_applied_control_id(
                    control, folder_id=folder_id
                )
                resolved_existing_controls.append(resolved_control_id)
            payload["existing_applied_controls"] = resolved_existing_controls

        res = make_post_request("/risk-scenarios/", payload)

        if res.status_code == 201:
            scenario = res.json()
            message = f"Created Risk scenario: {scenario.get('name')} (ID: {scenario.get('id')})"
            if assets:
                message += f"\n   Linked to {len(assets)} asset(s)"
            if threats:
                message += f"\n   Linked to {len(threats)} threat(s)"
            if applied_controls:
                message += (
                    f"\n   Linked to {len(applied_controls)} new/planned control(s)"
                )
            if existing_applied_controls:
                message += f"\n   Linked to {len(existing_applied_controls)} existing control(s)"
            return success_response(
                message,
                "create_risk_scenario",
                "Risk scenario created successfully. You can now update risk ratings or add more scenarios",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def sync_risk_assessment_from_ebios_rm(risk_assessment_id: str) -> str:
    """Refresh a risk assessment from its linked EBIOS RM study (workshop 5)

    Use this instead of creating a second assessment for the same study.
    Scenarios are updated, created, or archived to match the study's current
    selected objects.

    Args:
        risk_assessment_id: Risk assessment ID/name linked to an EBIOS RM study
    """
    try:
        risk_assessment_id = resolve_risk_assessment_id(risk_assessment_id)
        res = make_post_request(
            f"/risk-assessments/{risk_assessment_id}/sync_from_ebios_rm/", {}
        )
        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        result = (
            f"Synchronized from EBIOS RM: {data.get('updated', 0)} updated, "
            f"{data.get('created', 0)} created, {data.get('archived', 0)} archived"
        )
        return success_response(
            result,
            "sync_risk_assessment_from_ebios_rm",
            "Use get_risk_scenarios with this assessment to see the current scenarios.",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def create_business_impact_analysis(
    name: str,
    risk_matrix_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create Business Impact Analysis (BIA)

    Args:
        name: BIA name
        risk_matrix_id: Risk matrix ID/name (required)
        perimeter_id: Perimeter ID/name (required)
        description: Description
        version: Version string
        status: planned | in_progress | in_review | done | deprecated
        folder_id: Folder ID/name (inherits from perimeter if not set)
    """
    try:
        # Resolve risk matrix name to ID if needed
        risk_matrix_id = resolve_risk_matrix_id(risk_matrix_id)

        # Resolve perimeter name to ID if needed
        perimeter_id = resolve_perimeter_id(perimeter_id)

        # Resolve folder name to ID if needed (optional)
        if folder_id:
            folder_id = resolve_folder_id(folder_id)
        elif GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {
            "name": name,
            "risk_matrix": risk_matrix_id,
            "perimeter": perimeter_id,
            "description": description,
            "version": version,
            "status": status,
        }

        # Folder is optional - if not provided, it inherits from perimeter
        if folder_id:
            payload["folder"] = folder_id

        res = make_post_request("/resilience/business-impact-analysis/", payload)

        if res.status_code == 201:
            bia = res.json()
            return f"Created Business Impact Analysis: {bia.get('name')} (ID: {bia.get('id')})"
        else:
            return f"Error creating Business Impact Analysis: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_business_impact_analysis: {str(e)}"


async def create_compliance_assessment(
    name: str,
    framework_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create compliance assessment (audit) for framework

    Args:
        name: Assessment name
        framework_id: Framework ID/URN/name (e.g. "ISO 27001")
        perimeter_id: Perimeter ID/name
        description: Description
        version: Version string
        status: planned | in_progress | in_review | done | deprecated
        folder_id: Folder ID/name (inherits from perimeter if not set)
    """
    try:
        # Resolve framework name/URN to ID if needed
        framework_id = resolve_framework_id(framework_id)

        # Resolve perimeter name to ID if needed
        perimeter_id = resolve_perimeter_id(perimeter_id)

        # Resolve folder name to ID if needed (optional)
        if folder_id:
            folder_id = resolve_folder_id(folder_id)
        elif GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {
            "name": name,
            "framework": framework_id,
            "perimeter": perimeter_id,
            "description": description,
            "version": version,
            "status": status,
        }

        # Folder is optional - if not provided, it inherits from perimeter
        if folder_id:
            payload["folder"] = folder_id

        res = make_post_request("/compliance-assessments/", payload)

        if res.status_code == 201:
            assessment = res.json()
            return f"Created Compliance assessment: {assessment.get('name')} (ID: {assessment.get('id')})"
        else:
            return (
                f"Error creating compliance assessment: {res.status_code} - {res.text}"
            )
    except Exception as e:
        return f"Error in create_compliance_assessment: {str(e)}"


async def create_quantitative_risk_study(
    name: str,
    description: str = "",
    status: str = "planned",
    distribution_model: str = "lognormal_ci90",
    loss_threshold: float = None,
    risk_tolerance_point1_probability: float = None,
    risk_tolerance_point1_acceptable_loss: float = None,
    risk_tolerance_point2_probability: float = None,
    risk_tolerance_point2_acceptable_loss: float = None,
    folder_id: str = None,
) -> str:
    """Create quantitative risk study with risk tolerance curve (2 points define appetite curve)

    Args:
        name: Study name
        description: Description
        status: planned | in_progress | in_review | done | deprecated
        distribution_model: Distribution model (default: lognormal_ci90)
        loss_threshold: Loss threshold (monetary)
        risk_tolerance_point1_probability: Point1 probability (0.0-1.0, e.g. 0.01=1%)
        risk_tolerance_point1_acceptable_loss: Point1 acceptable loss (monetary)
        risk_tolerance_point2_probability: Point2 probability (0.0-1.0, e.g. 0.001=0.1%)
        risk_tolerance_point2_acceptable_loss: Point2 acceptable loss (monetary)
        folder_id: Folder ID/name
    """
    try:
        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "description": description,
            "status": status,
            "distribution_model": distribution_model,
        }

        if folder_id:
            payload["folder"] = folder_id

        if loss_threshold is not None:
            payload["loss_threshold"] = loss_threshold

        # Build risk_tolerance object if points are provided
        if any(
            [
                risk_tolerance_point1_probability is not None,
                risk_tolerance_point1_acceptable_loss is not None,
                risk_tolerance_point2_probability is not None,
                risk_tolerance_point2_acceptable_loss is not None,
            ]
        ):
            risk_tolerance = {"points": {}}

            # Add point1 if any of its values are provided
            if (
                risk_tolerance_point1_probability is not None
                or risk_tolerance_point1_acceptable_loss is not None
            ):
                risk_tolerance["points"]["point1"] = {}
                if risk_tolerance_point1_probability is not None:
                    risk_tolerance["points"]["point1"]["probability"] = (
                        risk_tolerance_point1_probability
                    )
                if risk_tolerance_point1_acceptable_loss is not None:
                    risk_tolerance["points"]["point1"]["acceptable_loss"] = (
                        risk_tolerance_point1_acceptable_loss
                    )

            # Add point2 if any of its values are provided
            if (
                risk_tolerance_point2_probability is not None
                or risk_tolerance_point2_acceptable_loss is not None
            ):
                risk_tolerance["points"]["point2"] = {}
                if risk_tolerance_point2_probability is not None:
                    risk_tolerance["points"]["point2"]["probability"] = (
                        risk_tolerance_point2_probability
                    )
                if risk_tolerance_point2_acceptable_loss is not None:
                    risk_tolerance["points"]["point2"]["acceptable_loss"] = (
                        risk_tolerance_point2_acceptable_loss
                    )

            payload["risk_tolerance"] = risk_tolerance

        res = make_post_request("/crq/quantitative-risk-studies/", payload)

        if res.status_code == 201:
            study = res.json()
            return f"Created Quantitative risk study: {study.get('name')} (ID: {study.get('id')})"
        else:
            return f"Error creating quantitative risk study: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_quantitative_risk_study: {str(e)}"


async def create_quantitative_risk_scenario(
    name: str,
    quantitative_risk_study_id: str,
    description: str = "",
    status: str = "draft",
    priority: int = None,
    folder_id: str = None,
    assets: list = None,
    threats: list = None,
    threat_library: str = None,
) -> str:
    """Create quantitative risk scenario in study

    Args:
        name: Scenario name
        quantitative_risk_study_id: Study ID/name (required)
        description: Description
        status: draft | open | mitigate | accept | transfer
        priority: Priority 1-4 (1=P1, 4=P4)
        folder_id: Folder ID/name
        assets: List of asset IDs/names
        threats: List of threat IDs/names
        threat_library: Library URN to filter threats (e.g. "urn:intuitem:risk:library:intuitem-common-catalog")
    """
    try:
        from ..resolvers import resolve_id_or_name, resolve_asset_id

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        # Resolve study name to ID if needed
        study_id = resolve_id_or_name(
            quantitative_risk_study_id, "/crq/quantitative-risk-studies/"
        )

        payload = {
            "name": name,
            "quantitative_risk_study": study_id,
            "description": description,
            "status": status,
        }

        if folder_id:
            payload["folder"] = folder_id

        if priority is not None:
            payload["priority"] = priority

        # Resolve asset names to IDs if provided (pass folder_id to scope lookup)
        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset, folder_id=folder_id)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        # Resolve threat names to IDs if provided (pass folder_id to scope lookup for custom threats)
        if threats:
            from ..resolvers import resolve_threat_id

            resolved_threats = []
            for threat in threats:
                resolved_threat_id = resolve_threat_id(
                    threat, library=threat_library, folder_id=folder_id
                )
                resolved_threats.append(resolved_threat_id)
            payload["threats"] = resolved_threats

        res = make_post_request("/crq/quantitative-risk-scenarios/", payload)

        if res.status_code == 201:
            scenario = res.json()
            message = f"Created Quantitative risk scenario: {scenario.get('name')} (ID: {scenario.get('id')})"
            if assets:
                message += f"\n   Linked to {len(assets)} asset(s)"
            if threats:
                message += f"\n   Linked to {len(threats)} threat(s)"
            return message
        else:
            return f"Error creating quantitative risk scenario: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_quantitative_risk_scenario: {str(e)}"


async def create_quantitative_risk_hypothesis(
    name: str,
    quantitative_risk_scenario_id: str,
    risk_stage: str = "current",
    description: str = "",
    probability: float = None,
    impact_lb: float = None,
    impact_ub: float = None,
    impact_distribution: str = "LOGNORMAL-CI90",
    folder_id: str = None,
    existing_applied_controls: list = None,
    added_applied_controls: list = None,
) -> str:
    """Create quantitative risk hypothesis for scenario

    Args:
        name: Hypothesis name
        quantitative_risk_scenario_id: Scenario ID/name (required)
        risk_stage: inherent | current | residual
        description: Description
        probability: Probability 0.0-1.0
        impact_lb: Impact lower bound
        impact_ub: Impact upper bound
        impact_distribution: Distribution model (default: LOGNORMAL-CI90)
        folder_id: Folder ID/name
        existing_applied_controls: List of existing control IDs/names
        added_applied_controls: List of added control IDs/names
    """
    try:
        from ..resolvers import resolve_id_or_name, resolve_applied_control_id

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        # Resolve folder name to ID if needed
        if folder_id:
            folder_id = resolve_folder_id(folder_id)

        # Resolve scenario name to ID if needed
        scenario_id = resolve_id_or_name(
            quantitative_risk_scenario_id, "/crq/quantitative-risk-scenarios/"
        )

        payload = {
            "name": name,
            "quantitative_risk_scenario": scenario_id,
            "risk_stage": risk_stage,
            "description": description,
        }

        # Build parameters dict if probability and impact are provided
        if probability is not None or (impact_lb is not None and impact_ub is not None):
            parameters = {}

            if probability is not None:
                parameters["probability"] = probability

            if impact_lb is not None and impact_ub is not None:
                parameters["impact"] = {
                    "lb": impact_lb,
                    "ub": impact_ub,
                    "distribution": impact_distribution,
                }

            payload["parameters"] = parameters

        if folder_id:
            payload["folder"] = folder_id

        # Resolve existing applied control names to IDs if provided (pass folder_id to scope lookup)
        if existing_applied_controls:
            resolved_existing = []
            for control in existing_applied_controls:
                resolved_control_id = resolve_applied_control_id(
                    control, folder_id=folder_id
                )
                resolved_existing.append(resolved_control_id)
            payload["existing_applied_controls"] = resolved_existing

        # Resolve added applied control names to IDs if provided (pass folder_id to scope lookup)
        if added_applied_controls:
            resolved_added = []
            for control in added_applied_controls:
                resolved_control_id = resolve_applied_control_id(
                    control, folder_id=folder_id
                )
                resolved_added.append(resolved_control_id)
            payload["added_applied_controls"] = resolved_added

        res = make_post_request("/crq/quantitative-risk-hypotheses/", payload)

        if res.status_code == 201:
            hypothesis = res.json()
            message = f"Created Quantitative risk hypothesis: {hypothesis.get('name')} (ID: {hypothesis.get('id')})"
            if existing_applied_controls:
                message += f"\n   Linked to {len(existing_applied_controls)} existing control(s)"
            if added_applied_controls:
                message += (
                    f"\n   Linked to {len(added_applied_controls)} added control(s)"
                )
            return message
        else:
            return f"Error creating quantitative risk hypothesis: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_quantitative_risk_hypothesis: {str(e)}"


async def refresh_quantitative_risk_study_simulations(study_id: str) -> str:
    """Refresh all Monte Carlo simulations (hypotheses, portfolio, risk tolerance). May take time

    Args:
        study_id: Study ID/name
    """
    try:
        from ..resolvers import resolve_id_or_name

        # Resolve study name to ID if needed
        resolved_study_id = resolve_id_or_name(
            study_id, "/crq/quantitative-risk-studies/"
        )

        # Call the retrigger-all-simulations endpoint
        res = make_post_request(
            f"/crq/quantitative-risk-studies/{resolved_study_id}/retrigger-all-simulations/",
            {},
        )

        if res.status_code == 200:
            result = res.json()

            # Extract summary information
            success = result.get("success", False)
            message = result.get("message", "")
            sim_results = result.get("simulation_results", {})

            hypothesis_sims = sim_results.get("hypothesis_simulations", {})
            successful_count = len(
                [h for h in hypothesis_sims.values() if h.get("success")]
            )
            failed_sims = sim_results.get("failed_simulations", [])

            response = f"Simulation refresh completed for study {study_id}\n"
            response += f"Hypothesis simulations: {successful_count} successful"
            if failed_sims:
                response += f", {len(failed_sims)} failed"
            response += f"\nPortfolio: {'yes' if sim_results.get('portfolio_generated') else 'no'}"
            response += f"\nRisk tolerance: {'yes' if sim_results.get('risk_tolerance_generated') else 'no'}"
            return response
        else:
            return f"Error refreshing simulations: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in refresh_quantitative_risk_study_simulations: {str(e)}"


async def create_task_template(
    name: str,
    folder_id: str,
    description: str = None,
    status: str = None,
    observation: str = None,
    evidences: list = None,
    task_date: str = None,
    is_recurrent: bool = False,
    ref_id: str = None,
    schedule: str = None,
    enabled: bool = True,
    link: str = None,
    assigned_to: list = None,
    assets: list = None,
    applied_controls: list = None,
    compliance_assessments: list = None,
    risk_assessments: list = None,
    findings_assessment: list = None,
) -> str:
    """Create task template

    Args:
        name: Task template name (required)
        folder_id: Folder ID/name (required)
        description: Description
        status: Status
        observation: Observation text
        evidences: Array of evidence UUIDs
        task_date: Task date (YYYY-MM-DD)
        is_recurrent: Recurrent flag
        ref_id: Reference ID
        schedule: Schedule definition
        enabled: Enabled flag
        link: Link to evidence (e.g. Jira ticket)
        assigned_to: List of assignees as actor UUIDs, emails or names
        assets: List of asset IDs/names
        applied_controls: List of applied control IDs/names
        compliance_assessments: Array of compliance assessment UUIDs
        risk_assessments: Array of risk assessment UUIDs
        findings_assessment: Array of finding assessment UUIDs
    """
    try:
        # Resolve folder name to ID if needed
        folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "folder": folder_id,
            "is_recurrent": is_recurrent,
            "enabled": enabled,
        }

        # Add optional fields if provided
        if description is not None:
            payload["description"] = description
        if status is not None:
            valid_statuses = ["pending", "in_progress", "cancelled", "completed"]
            if status not in valid_statuses:
                return f"Error: Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
            payload["status"] = status
        if observation is not None:
            payload["observation"] = observation
        if evidences is not None:
            payload["evidences"] = evidences
        if task_date is not None:
            payload["task_date"] = task_date
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if schedule is not None:
            payload["schedule"] = schedule
        if link is not None:
            payload["link"] = link
        if assigned_to is not None:
            payload["assigned_to"] = resolve_actor_ids(assigned_to)
        if assets is not None:
            payload["assets"] = [
                resolve_asset_id(asset, folder_id=folder_id) for asset in assets
            ]
        if applied_controls is not None:
            resolved_controls = []
            for control in applied_controls:
                resolved_control_id = resolve_applied_control_id(
                    control, folder_id=folder_id
                )
                resolved_controls.append(resolved_control_id)
            payload["applied_controls"] = resolved_controls
        if compliance_assessments is not None:
            payload["compliance_assessments"] = compliance_assessments
        if risk_assessments is not None:
            payload["risk_assessments"] = risk_assessments
        if findings_assessment is not None:
            payload["findings_assessment"] = findings_assessment

        res = make_post_request("/task-templates/", payload)

        if res.status_code == 201:
            task = res.json()
            return f"Created task template: {task.get('name')} (ID: {task.get('id')})"
        else:
            return f"Error creating task template: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_task_template: {str(e)}"


async def create_vulnerability(
    name: str,
    description: str = None,
    ref_id: str = None,
    status: str = "--",
    severity: int = -1,
    folder_id: str = None,
    filtering_labels: list = None,
    applied_controls: list = None,
    assets: list = None,
    security_exceptions: list = None,
) -> str:
    """Create a new vulnerability

    Args:
        name: Vulnerability name (required)
        description: Description
        ref_id: Reference ID (e.g. CVE identifier)
        status: -- | potential | exploitable | mitigated | fixed | not_exploitable | unaffected
        severity: -1 (undefined) | 0 (info) | 1 (low) | 2 (medium) | 3 (high) | 4 (critical)
        folder_id: Folder ID/name
        filtering_labels: List of label UUIDs
        applied_controls: List of applied control IDs/names
        assets: List of asset IDs/names
        security_exceptions: List of security exception UUIDs
    """
    try:
        from ..resolvers import resolve_asset_id, resolve_applied_control_id

        if not folder_id and GLOBAL_FOLDER_ID:
            folder_id = GLOBAL_FOLDER_ID

        payload = {"name": name}

        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if status is not None:
            payload["status"] = status
        if severity is not None:
            payload["severity"] = severity

        if folder_id:
            payload["folder"] = resolve_folder_id(folder_id)

        if filtering_labels:
            payload["filtering_labels"] = filtering_labels

        if applied_controls:
            resolved_controls = []
            for control in applied_controls:
                resolved_controls.append(resolve_applied_control_id(control))
            payload["applied_controls"] = resolved_controls

        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_assets.append(resolve_asset_id(asset))
            payload["assets"] = resolved_assets

        if security_exceptions:
            payload["security_exceptions"] = security_exceptions

        res = make_post_request("/vulnerabilities/", payload)

        if res.status_code == 201:
            vuln = res.json()
            return f"Created vulnerability: {vuln.get('name')} (ID: {vuln.get('id')})"
        else:
            return f"Error creating vulnerability: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_vulnerability: {str(e)}"
