"""Write/Create MCP tools for CISO Assistant"""

from ..client import make_post_request, make_get_request
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
    """Create folder (domain)

    Args:
        name: Folder name
        description: Optional description
        parent_folder_id: Optional parent folder ID or name
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
        description: Optional description
        folder_id: Optional folder ID or name
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
            return f"Created asset: {asset.get('name')} (ID: {asset.get('id')})"
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
            return f"Created threat: {threat.get('name')} (ID: {threat.get('id')})"
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
            return f"Created applied control: {control.get('name')} (ID: {control.get('id')})"
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
            return f"Created risk assessment: {assessment.get('name')} (ID: {assessment.get('id')})"
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
    assets: list = None,
    threats: list = None,
    applied_controls: list = None,
    existing_applied_controls: list = None,
) -> str:
    """Create a new risk scenario in CISO Assistant

    Args:
        name: Name/title of the risk scenario
        description: Description of the risk scenario
        risk_assessment_id: Optional ID or name of the risk assessment to link this scenario to (can use risk assessment name instead of UUID)
        folder_id: Optional folder/domain ID or name where to create the scenario (can use folder name instead of UUID)
        existing_controls: Optional description of existing controls (text field)
        current_proba: Optional current probability level (0-4, where 0=very low, 4=very high)
        current_impact: Optional current impact level (0-4, where 0=very low, 4=very high)
        assets: Optional list of asset IDs or names to link to this scenario (can use asset names instead of UUIDs)
        threats: Optional list of threat IDs or names to link to this scenario (can use threat names instead of UUIDs)
        applied_controls: Optional list of new/planned applied control IDs or names to link (can use control names instead of UUIDs)
        existing_applied_controls: Optional list of existing applied control IDs or names to link (can use control names instead of UUIDs)
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

        # Resolve asset names to IDs if provided
        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        # Resolve threat names to IDs if provided
        if threats:
            from ..resolvers import resolve_id_or_name

            resolved_threats = []
            for threat in threats:
                # Try to resolve as UUID first, otherwise lookup by name
                if "-" in threat and len(threat) == 36:
                    resolved_threats.append(threat)
                else:
                    # Look up threat by name
                    threat_res = make_get_request("/threats/", params={"name": threat})
                    if threat_res.status_code == 200:
                        threat_data = threat_res.json()
                        from ..client import get_paginated_results

                        threat_results = get_paginated_results(threat_data)
                        if threat_results:
                            resolved_threats.append(threat_results[0]["id"])
                        else:
                            raise ValueError(f"Threat '{threat}' not found")
                    else:
                        raise ValueError(f"Failed to look up threat '{threat}'")
            payload["threats"] = resolved_threats

        # Resolve new/planned applied control names to IDs if provided
        if applied_controls:
            resolved_controls = []
            for control in applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_controls.append(resolved_control_id)
            payload["applied_controls"] = resolved_controls

        # Resolve existing applied control names to IDs if provided
        if existing_applied_controls:
            resolved_existing_controls = []
            for control in existing_applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
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
            return message
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
    """Create a new quantitative risk study in CISO Assistant

    Args:
        name: Name of the quantitative risk study
        description: Optional description of the study
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated" (defaults to "planned")
        distribution_model: Distribution model to use (defaults to "lognormal_ci90")
        loss_threshold: Optional loss threshold value (monetary amount)
        risk_tolerance_point1_probability: Optional probability for first risk tolerance point (0.0-1.0, e.g., 0.01 for 1%)
        risk_tolerance_point1_acceptable_loss: Optional acceptable loss for first point (monetary amount)
        risk_tolerance_point2_probability: Optional probability for second risk tolerance point (0.0-1.0, e.g., 0.001 for 0.1%)
        risk_tolerance_point2_acceptable_loss: Optional acceptable loss for second point (monetary amount)
        folder_id: Optional folder/domain ID or name where to create the study (can use folder name instead of UUID)

    Note: Risk tolerance points define your organization's risk appetite curve.
    Example: point1 (1% probability, $100K acceptable loss), point2 (0.1% probability, $1M acceptable loss)
    The curve is automatically generated from these two points.
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
) -> str:
    """Create a new quantitative risk scenario in CISO Assistant

    Args:
        name: Name of the quantitative risk scenario
        quantitative_risk_study_id: ID or name of the quantitative risk study to link this scenario to (required)
        description: Optional description of the scenario
        status: Optional status - "draft", "open", "mitigate", "accept", or "transfer" (defaults to "draft")
        priority: Optional priority (1=P1, 2=P2, 3=P3, 4=P4)
        folder_id: Optional folder/domain ID or name where to create the scenario (can use folder name instead of UUID)
        assets: Optional list of asset IDs or names to link to this scenario (can use asset names instead of UUIDs)
        threats: Optional list of threat IDs or names to link to this scenario (can use threat names instead of UUIDs)
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

        # Resolve asset names to IDs if provided
        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        # Resolve threat names to IDs if provided
        if threats:
            resolved_threats = []
            for threat in threats:
                # Try to resolve as UUID first, otherwise lookup by name
                if "-" in threat and len(threat) == 36:
                    resolved_threats.append(threat)
                else:
                    # Look up threat by name
                    threat_res = make_get_request("/threats/", params={"name": threat})
                    if threat_res.status_code == 200:
                        threat_data = threat_res.json()
                        from ..client import get_paginated_results

                        threat_results = get_paginated_results(threat_data)
                        if threat_results:
                            resolved_threats.append(threat_results[0]["id"])
                        else:
                            raise ValueError(f"Threat '{threat}' not found")
                    else:
                        raise ValueError(f"Failed to look up threat '{threat}'")
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
    """Create a new quantitative risk hypothesis in CISO Assistant

    Args:
        name: Name of the quantitative risk hypothesis
        quantitative_risk_scenario_id: ID or name of the quantitative risk scenario to link this hypothesis to (required)
        risk_stage: Risk stage - "inherent", "current", or "residual" (defaults to "current")
        description: Optional description of the hypothesis
        probability: Optional probability value (0.0 to 1.0)
        impact_lb: Optional impact lower bound value
        impact_ub: Optional impact upper bound value
        impact_distribution: Impact distribution model (defaults to "LOGNORMAL-CI90")
        folder_id: Optional folder/domain ID or name where to create the hypothesis (can use folder name instead of UUID)
        existing_applied_controls: Optional list of existing applied control IDs or names (for residual hypotheses, can use control names)
        added_applied_controls: Optional list of added applied control IDs or names (for residual hypotheses, can use control names)
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

        # Resolve existing applied control names to IDs if provided
        if existing_applied_controls:
            resolved_existing = []
            for control in existing_applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_existing.append(resolved_control_id)
            payload["existing_applied_controls"] = resolved_existing

        # Resolve added applied control names to IDs if provided
        if added_applied_controls:
            resolved_added = []
            for control in added_applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
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
    """Refresh all simulations for a quantitative risk study

    This triggers a complete recalculation of:
    - All hypothesis simulations (Monte Carlo simulations for each hypothesis with valid parameters)
    - Portfolio simulation (combined Annual Loss Expectancy and Loss Exceedance Curves)
    - Risk tolerance curves

    Note: This operation can take some time as it processes multiple simulations.

    Args:
        study_id: ID or name of the quantitative risk study to refresh simulations for
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
