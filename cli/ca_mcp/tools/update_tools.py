"""Update MCP tools for CISO Assistant"""

from ..client import make_get_request, make_patch_request, get_paginated_results
from ..resolvers import (
    resolve_asset_id,
    resolve_risk_scenario_id,
    resolve_risk_assessment_id,
    resolve_folder_id,
    resolve_applied_control_id,
    resolve_requirement_assessment_id,
)


async def update_asset(
    asset_id: str,
    name: str = None,
    description: str = None,
    asset_type: str = None,
    business_value: str = None,
    parent_assets: list = None,
) -> str:
    """Update an existing asset in CISO Assistant

    Args:
        asset_id: ID or name of the asset to update
        name: Optional new name for the asset
        description: Optional new description
        asset_type: Optional new type - "PR" for Primary or "SP" for Supporting
        business_value: Optional business value (e.g., "low", "medium", "high", "very_high")
        parent_assets: Optional list of parent asset IDs or names (can use asset names instead of UUIDs)
    """
    try:
        # Resolve asset name to ID if needed
        resolved_asset_id = resolve_asset_id(asset_id)

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if asset_type is not None:
            payload["type"] = asset_type
        if business_value is not None:
            payload["business_value"] = business_value

        # Resolve parent asset names to IDs if provided
        if parent_assets is not None:
            resolved_parents = []
            for parent in parent_assets:
                resolved_parent_id = resolve_asset_id(parent)
                resolved_parents.append(resolved_parent_id)

            payload["parent_assets"] = resolved_parents

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/assets/{resolved_asset_id}/", payload)

        if res.status_code == 200:
            asset = res.json()
            return f"✅ Asset updated successfully: {asset.get('name')} (ID: {asset.get('id')})"
        else:
            return f"Error updating asset: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_asset: {str(e)}"


async def update_risk_scenario(
    risk_scenario_id: str,
    name: str = None,
    description: str = None,
    risk_assessment_id: str = None,
    existing_controls: str = None,
    inherent_proba: int = None,
    inherent_impact: int = None,
    current_proba: int = None,
    current_impact: int = None,
    residual_proba: int = None,
    residual_impact: int = None,
    treatment: str = None,
    strength_of_knowledge: int = None,
    justification: str = None,
    ref_id: str = None,
) -> str:
    """Update an existing risk scenario in CISO Assistant

    Args:
        risk_scenario_id: ID or name of the risk scenario to update
        name: Optional new name for the risk scenario
        description: Optional new description
        risk_assessment_id: Optional ID or name of the risk assessment (can use risk assessment name instead of UUID)
        existing_controls: Optional description of existing controls
        inherent_proba: Optional inherent probability (integer index from risk matrix)
        inherent_impact: Optional inherent impact (integer index from risk matrix)
        current_proba: Optional current probability (integer index from risk matrix)
        current_impact: Optional current impact (integer index from risk matrix)
        residual_proba: Optional residual probability (integer index from risk matrix)
        residual_impact: Optional residual impact (integer index from risk matrix)
        treatment: Optional treatment decision (open, mitigate, accept, avoid, transfer)
        strength_of_knowledge: Optional strength of knowledge (-1 to 2)
        justification: Optional justification text
        ref_id: Optional reference ID
    """
    try:
        # Resolve risk scenario name to ID if needed
        resolved_scenario_id = resolve_risk_scenario_id(risk_scenario_id)

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if existing_controls is not None:
            payload["existing_controls"] = existing_controls
        if inherent_proba is not None:
            payload["inherent_proba"] = inherent_proba
        if inherent_impact is not None:
            payload["inherent_impact"] = inherent_impact
        if current_proba is not None:
            payload["current_proba"] = current_proba
        if current_impact is not None:
            payload["current_impact"] = current_impact
        if residual_proba is not None:
            payload["residual_proba"] = residual_proba
        if residual_impact is not None:
            payload["residual_impact"] = residual_impact
        if treatment is not None:
            payload["treatment"] = treatment
        if strength_of_knowledge is not None:
            payload["strength_of_knowledge"] = strength_of_knowledge
        if justification is not None:
            payload["justification"] = justification
        if ref_id is not None:
            payload["ref_id"] = ref_id

        # Resolve risk assessment name to ID if needed
        if risk_assessment_id is not None:
            resolved_assessment_id = resolve_risk_assessment_id(risk_assessment_id)
            payload["risk_assessment"] = resolved_assessment_id

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/risk-scenarios/{resolved_scenario_id}/", payload)

        if res.status_code == 200:
            scenario = res.json()
            return f"✅ Risk scenario updated successfully: {scenario.get('name')} (ID: {scenario.get('id')})"
        else:
            return f"Error updating risk scenario: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_risk_scenario: {str(e)}"


async def update_applied_control(
    control_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    priority: int = None,
    category: str = None,
    csf_function: str = None,
    effort: str = None,
    control_impact: int = None,
    eta: str = None,
    start_date: str = None,
    expiry_date: str = None,
    link: str = None,
    ref_id: str = None,
) -> str:
    """Update an existing applied control in CISO Assistant

    Args:
        control_id: ID or name of the applied control to update
        name: Optional new name for the control
        description: Optional new description
        status: Optional status (to_do, in_progress, on_hold, active, deprecated, --)
        priority: Optional priority (1=P1, 2=P2, 3=P3, 4=P4)
        category: Optional category (policy, process, technical, physical)
        csf_function: Optional CSF function (identify, protect, detect, respond, recover, govern)
        effort: Optional effort estimation (XS, S, M, L, XL)
        control_impact: Optional impact rating (1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High)
        eta: Optional ETA date (format: YYYY-MM-DD)
        start_date: Optional start date (format: YYYY-MM-DD)
        expiry_date: Optional expiry date (format: YYYY-MM-DD)
        link: Optional external link (e.g., Jira ticket URL)
        ref_id: Optional reference ID
    """
    try:
        # Resolve control name to ID if needed
        resolved_control_id = resolve_applied_control_id(control_id)

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if priority is not None:
            payload["priority"] = priority
        if category is not None:
            payload["category"] = category
        if csf_function is not None:
            payload["csf_function"] = csf_function
        if effort is not None:
            payload["effort"] = effort
        if control_impact is not None:
            payload["control_impact"] = control_impact
        if eta is not None:
            payload["eta"] = eta
        if start_date is not None:
            payload["start_date"] = start_date
        if expiry_date is not None:
            payload["expiry_date"] = expiry_date
        if link is not None:
            payload["link"] = link
        if ref_id is not None:
            payload["ref_id"] = ref_id

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/applied-controls/{resolved_control_id}/", payload)

        if res.status_code == 200:
            control = res.json()
            return f"✅ Applied control updated successfully: {control.get('name')} (ID: {control.get('id')})"
        else:
            return f"Error updating applied control: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_applied_control: {str(e)}"


async def update_requirement_assessment(
    requirement_assessment_id: str,
    status: str = None,
    result: str = None,
    observation: str = None,
    score: int = None,
    is_scored: bool = None,
    eta: str = None,
    due_date: str = None,
    selected: bool = None,
) -> str:
    """Update a requirement assessment within a compliance assessment (audit)

    Args:
        requirement_assessment_id: UUID of the requirement assessment to update
        status: Optional workflow status (to_do, in_progress, in_review, done)
        result: Optional compliance result (not_assessed, partially_compliant, non_compliant, compliant, not_applicable)
        observation: Optional observation text
        score: Optional score value (if using scored assessment)
        is_scored: Optional flag to indicate if this is a scored assessment
        eta: Optional ETA date (format: YYYY-MM-DD)
        due_date: Optional due date (format: YYYY-MM-DD)
        selected: Optional selection flag (whether requirement is applicable)

    Note: Use get_requirement_assessments() to find requirement assessment IDs
    """
    try:
        # Validate UUID
        resolved_id = resolve_requirement_assessment_id(requirement_assessment_id)

        # Build update payload with only provided fields
        payload = {}

        if status is not None:
            payload["status"] = status
        if result is not None:
            payload["result"] = result
        if observation is not None:
            payload["observation"] = observation
        if score is not None:
            payload["score"] = score
        if is_scored is not None:
            payload["is_scored"] = is_scored
        if eta is not None:
            payload["eta"] = eta
        if due_date is not None:
            payload["due_date"] = due_date
        if selected is not None:
            payload["selected"] = selected

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/requirement-assessments/{resolved_id}/", payload)

        if res.status_code == 200:
            req_assessment = res.json()
            req_name = req_assessment.get("name", "N/A")
            return f"✅ Requirement assessment updated successfully: {req_name} (ID: {req_assessment.get('id')})"
        else:
            return (
                f"Error updating requirement assessment: {res.status_code} - {res.text}"
            )
    except Exception as e:
        return f"Error in update_requirement_assessment: {str(e)}"
