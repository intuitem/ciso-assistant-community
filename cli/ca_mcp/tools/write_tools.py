"""Write/Create MCP tools for CISO Assistant"""

from ..client import make_post_request
from ..resolvers import (
    resolve_folder_id,
    resolve_perimeter_id,
    resolve_risk_matrix_id,
    resolve_framework_id,
    resolve_risk_assessment_id,
)
from ..config import GLOBAL_FOLDER_ID


async def create_folder(
    name: str,
    description: str = "",
    parent_folder_id: str = None,
) -> str:
    """Create a new folder (domain) in CISO Assistant

    Args:
        name: Name of the folder
        description: Optional description of the folder
        parent_folder_id: Optional parent folder ID or name (can use folder name instead of UUID)
    """
    try:
        payload = {
            "name": name,
            "description": description,
        }

        # Resolve parent folder name to ID if needed
        if parent_folder_id:
            parent_folder_id = resolve_folder_id(parent_folder_id)
            payload["parent_folder"] = parent_folder_id

        res = make_post_request("/folders/", payload)

        if res.status_code == 201:
            folder = res.json()
            return f"✅ Folder created successfully: {folder.get('name')} (ID: {folder.get('id')})"
        else:
            return f"Error creating folder: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_folder: {str(e)}"


async def create_perimeter(
    name: str,
    description: str = "",
    folder_id: str = None,
) -> str:
    """Create a new perimeter in CISO Assistant

    Args:
        name: Name of the perimeter
        description: Optional description of the perimeter
        folder_id: Optional folder/domain ID or name where to create the perimeter (can use folder name instead of UUID)
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
        }

        if folder_id:
            payload["folder"] = folder_id

        res = make_post_request("/perimeters/", payload)

        if res.status_code == 201:
            perimeter = res.json()
            return f"✅ Perimeter created successfully: {perimeter.get('name')} (ID: {perimeter.get('id')})"
        else:
            return f"Error creating perimeter: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_perimeter: {str(e)}"


async def create_asset(
    name: str,
    description: str = "",
    asset_type: str = "PR",
    folder_id: str = None,
) -> str:
    """Create a new asset in CISO Assistant

    Args:
        name: Name of the asset
        description: Optional description of the asset
        asset_type: Type of asset - "PR" for Primary or "SP" for Supporting (defaults to "PR")
        folder_id: Optional folder/domain ID or name where to create the asset (can use folder name instead of UUID)
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
            "type": asset_type,
        }

        if folder_id:
            payload["folder"] = folder_id

        res = make_post_request("/assets/", payload)

        if res.status_code == 201:
            asset = res.json()
            return f"✅ Asset created successfully: {asset.get('name')} (ID: {asset.get('id')})"
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
    """Create a new threat in CISO Assistant

    Args:
        name: Name of the threat
        description: Optional description of the threat
        provider: Optional provider/source of the threat (e.g., "MITRE ATT&CK", "Custom")
        ref_id: Optional reference ID for the threat
        folder_id: Optional folder/domain ID or name where to create the threat (can use folder name instead of UUID)
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
            return f"✅ Threat created successfully: {threat.get('name')} (ID: {threat.get('id')})"
        else:
            return f"Error creating threat: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_threat: {str(e)}"


async def create_applied_control(
    name: str,
    description: str = "",
    eta: str = None,
    folder_id: str = None,
    category: str = "technical",
    status: str = "planned",
) -> str:
    """Create a new applied control (security measure) in CISO Assistant

    Args:
        name: Name of the control
        description: Optional description of what the control does
        eta: Optional estimated completion date (format: YYYY-MM-DD)
        folder_id: Optional folder/domain ID or name where to create the control (can use folder name instead of UUID)
        category: Control category (technical, physical, organizational, or procedural) - defaults to "technical"
        status: Control status (planned, active, or inactive) - defaults to "planned"
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
            "status": status,
        }

        if folder_id:
            payload["folder"] = folder_id

        if eta:
            payload["eta"] = eta

        res = make_post_request("/applied-controls/", payload)

        if res.status_code == 201:
            control = res.json()
            return f"✅ Applied control created successfully: {control.get('name')} (ID: {control.get('id')})"
        else:
            return f"Error creating applied control: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_applied_control: {str(e)}"


async def create_risk_assessment(
    name: str,
    risk_matrix_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create a new risk assessment in CISO Assistant

    Args:
        name: Name of the risk assessment
        risk_matrix_id: ID or name of the risk matrix to use (can use risk matrix name instead of UUID; required)
        perimeter_id: ID or name of the perimeter (scope) for this assessment (can use perimeter name instead of UUID; required)
        description: Optional description
        version: Optional version string (defaults to "1.0")
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        folder_id: Optional folder/domain ID or name where to create the assessment (can use folder name instead of UUID; if not provided, inherits from perimeter)
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

        res = make_post_request("/risk-assessments/", payload)

        if res.status_code == 201:
            assessment = res.json()
            return f"✅ Risk assessment created successfully: {assessment.get('name')} (ID: {assessment.get('id')})"
        else:
            return f"Error creating risk assessment: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_risk_assessment: {str(e)}"


async def create_risk_scenario(
    name: str,
    description: str = "",
    risk_assessment_id: str = None,
    folder_id: str = None,
    existing_controls: str = "",
    current_proba: int = None,
    current_impact: int = None,
) -> str:
    """Create a new risk scenario in CISO Assistant

    Args:
        name: Name/title of the risk scenario
        description: Description of the risk scenario
        risk_assessment_id: Optional ID or name of the risk assessment to link this scenario to (can use risk assessment name instead of UUID)
        folder_id: Optional folder/domain ID or name where to create the scenario (can use folder name instead of UUID)
        existing_controls: Optional description of existing controls
        current_proba: Optional current probability level (0-4, where 0=very low, 4=very high)
        current_impact: Optional current impact level (0-4, where 0=very low, 4=very high)
    """
    try:
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

        res = make_post_request("/risk-scenarios/", payload)

        if res.status_code == 201:
            scenario = res.json()
            return f"✅ Risk scenario created successfully: {scenario.get('name')} (ID: {scenario.get('id')})"
        else:
            return f"Error creating risk scenario: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_risk_scenario: {str(e)}"


async def create_business_impact_analysis(
    name: str,
    risk_matrix_id: str,
    perimeter_id: str,
    description: str = "",
    version: str = "1.0",
    status: str = "planned",
    folder_id: str = None,
) -> str:
    """Create a new Business Impact Analysis (BIA) in CISO Assistant

    Args:
        name: Name of the BIA
        risk_matrix_id: ID or name of the risk matrix to use (can use risk matrix name instead of UUID; required)
        perimeter_id: ID or name of the perimeter (scope) for this BIA (can use perimeter name instead of UUID; required)
        description: Optional description
        version: Optional version string (defaults to "1.0")
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        folder_id: Optional folder/domain ID or name where to create the BIA (can use folder name instead of UUID; if not provided, inherits from perimeter)
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
            return f"✅ Business Impact Analysis created successfully: {bia.get('name')} (ID: {bia.get('id')})"
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
    """Create a new compliance assessment (audit) in CISO Assistant

    Args:
        name: Name of the compliance assessment
        framework_id: ID, URN, or name of the framework to use (e.g., "ISO 27001" or "urn:intuitem:risk:library:iso27001-2022")
        perimeter_id: ID or name of the perimeter (scope) for this assessment
        description: Optional description of the assessment
        version: Optional version string (defaults to "1.0")
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        folder_id: Optional folder/domain ID or name where to create the assessment (can use folder name instead of UUID; if not provided, inherits from perimeter)
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
            return f"✅ Compliance assessment created successfully: {assessment.get('name')} (ID: {assessment.get('id')})"
        else:
            return (
                f"Error creating compliance assessment: {res.status_code} - {res.text}"
            )
    except Exception as e:
        return f"Error in create_compliance_assessment: {str(e)}"
