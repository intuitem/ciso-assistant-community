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
            return f"Updated Asset: {asset.get('name')} (ID: {asset.get('id')})"
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
    assets: list = None,
    threats: list = None,
    applied_controls: list = None,
    existing_applied_controls: list = None,
) -> str:
    """Update an existing risk scenario in CISO Assistant

    Args:
        risk_scenario_id: ID or name of the risk scenario to update
        name: Optional new name for the risk scenario
        description: Optional new description
        risk_assessment_id: Optional ID or name of the risk assessment (can use risk assessment name instead of UUID)
        existing_controls: Optional description of existing controls (text field)
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
        assets: Optional list of asset IDs or names to update (replaces existing, can use asset names)
        threats: Optional list of threat IDs or names to update (replaces existing, can use threat names)
        applied_controls: Optional list of new/planned applied control IDs or names (replaces existing, can use control names)
        existing_applied_controls: Optional list of existing applied control IDs or names (replaces existing, can use control names)
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

        # Resolve asset names to IDs if provided
        if assets is not None:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        # Resolve threat names to IDs if provided
        if threats is not None:
            from ..client import make_get_request, get_paginated_results

            resolved_threats = []
            for threat in threats:
                if "-" in threat and len(threat) == 36:
                    resolved_threats.append(threat)
                else:
                    threat_res = make_get_request("/threats/", params={"name": threat})
                    if threat_res.status_code == 200:
                        threat_data = threat_res.json()
                        threat_results = get_paginated_results(threat_data)
                        if threat_results:
                            resolved_threats.append(threat_results[0]["id"])
                        else:
                            raise ValueError(f"Threat '{threat}' not found")
                    else:
                        raise ValueError(f"Failed to look up threat '{threat}'")
            payload["threats"] = resolved_threats

        # Resolve applied control names to IDs if provided
        if applied_controls is not None:
            resolved_controls = []
            for control in applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_controls.append(resolved_control_id)
            payload["applied_controls"] = resolved_controls

        # Resolve existing applied control names to IDs if provided
        if existing_applied_controls is not None:
            resolved_existing_controls = []
            for control in existing_applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_existing_controls.append(resolved_control_id)
            payload["existing_applied_controls"] = resolved_existing_controls

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/risk-scenarios/{resolved_scenario_id}/", payload)

        if res.status_code == 200:
            scenario = res.json()
            return f"Updated Risk scenario: {scenario.get('name')} (ID: {scenario.get('id')})"
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
            return f"Updated Applied control: {control.get('name')} (ID: {control.get('id')})"
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
            return f"Updated Requirement assessment: {req_name} (ID: {req_assessment.get('id')})"
        else:
            return (
                f"Error updating requirement assessment: {res.status_code} - {res.text}"
            )
    except Exception as e:
        return f"Error in update_requirement_assessment: {str(e)}"


async def update_quantitative_risk_study(
    study_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    loss_threshold: float = None,
    risk_tolerance_point1_probability: float = None,
    risk_tolerance_point1_acceptable_loss: float = None,
    risk_tolerance_point2_probability: float = None,
    risk_tolerance_point2_acceptable_loss: float = None,
    observation: str = None,
) -> str:
    """Update an existing quantitative risk study in CISO Assistant

    Args:
        study_id: ID or name of the quantitative risk study to update
        name: Optional new name for the study
        description: Optional new description
        status: Optional status - "planned", "in_progress", "in_review", "done", or "deprecated"
        loss_threshold: Optional new loss threshold value (monetary amount)
        risk_tolerance_point1_probability: Optional probability for first risk tolerance point (0.0-1.0, e.g., 0.01 for 1%)
        risk_tolerance_point1_acceptable_loss: Optional acceptable loss for first point (monetary amount)
        risk_tolerance_point2_probability: Optional probability for second risk tolerance point (0.0-1.0, e.g., 0.001 for 0.1%)
        risk_tolerance_point2_acceptable_loss: Optional acceptable loss for second point (monetary amount)
        observation: Optional observation text

    Note: When updating risk tolerance points, you can update individual point values.
    The risk tolerance curve will be automatically regenerated when points are modified.
    """
    try:
        from ..resolvers import resolve_id_or_name

        # Resolve study name to ID if needed
        resolved_study_id = resolve_id_or_name(
            study_id, "/crq/quantitative-risk-studies/"
        )

        # First, get current study to preserve existing risk tolerance if partially updating
        get_res = make_get_request(
            f"/crq/quantitative-risk-studies/{resolved_study_id}/"
        )
        if get_res.status_code != 200:
            return f"Error fetching study: {get_res.status_code} - {get_res.text}"

        current_study = get_res.json()
        current_risk_tolerance = current_study.get("risk_tolerance") or {"points": {}}

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if loss_threshold is not None:
            payload["loss_threshold"] = loss_threshold
        if observation is not None:
            payload["observation"] = observation

        # Handle risk_tolerance updates
        risk_tolerance_updated = False
        if any(
            [
                risk_tolerance_point1_probability is not None,
                risk_tolerance_point1_acceptable_loss is not None,
                risk_tolerance_point2_probability is not None,
                risk_tolerance_point2_acceptable_loss is not None,
            ]
        ):
            # Start with current risk_tolerance
            updated_risk_tolerance = current_risk_tolerance.copy()
            if "points" not in updated_risk_tolerance:
                updated_risk_tolerance["points"] = {}

            # Update point1 values if provided
            if (
                risk_tolerance_point1_probability is not None
                or risk_tolerance_point1_acceptable_loss is not None
            ):
                if "point1" not in updated_risk_tolerance["points"]:
                    updated_risk_tolerance["points"]["point1"] = {}

                if risk_tolerance_point1_probability is not None:
                    updated_risk_tolerance["points"]["point1"]["probability"] = (
                        risk_tolerance_point1_probability
                    )
                    risk_tolerance_updated = True
                if risk_tolerance_point1_acceptable_loss is not None:
                    updated_risk_tolerance["points"]["point1"]["acceptable_loss"] = (
                        risk_tolerance_point1_acceptable_loss
                    )
                    risk_tolerance_updated = True

            # Update point2 values if provided
            if (
                risk_tolerance_point2_probability is not None
                or risk_tolerance_point2_acceptable_loss is not None
            ):
                if "point2" not in updated_risk_tolerance["points"]:
                    updated_risk_tolerance["points"]["point2"] = {}

                if risk_tolerance_point2_probability is not None:
                    updated_risk_tolerance["points"]["point2"]["probability"] = (
                        risk_tolerance_point2_probability
                    )
                    risk_tolerance_updated = True
                if risk_tolerance_point2_acceptable_loss is not None:
                    updated_risk_tolerance["points"]["point2"]["acceptable_loss"] = (
                        risk_tolerance_point2_acceptable_loss
                    )
                    risk_tolerance_updated = True

            if risk_tolerance_updated:
                # Remove curve_data to force regeneration
                if "curve_data" in updated_risk_tolerance:
                    del updated_risk_tolerance["curve_data"]
                payload["risk_tolerance"] = updated_risk_tolerance

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/crq/quantitative-risk-studies/{resolved_study_id}/", payload
        )

        if res.status_code == 200:
            study = res.json()
            return f"Updated Quantitative risk study: {study.get('name')} (ID: {study.get('id')})"
        else:
            return f"Error updating quantitative risk study: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_quantitative_risk_study: {str(e)}"


async def update_quantitative_risk_scenario(
    scenario_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    priority: int = None,
    observation: str = None,
    assets: list = None,
    threats: list = None,
) -> str:
    """Update an existing quantitative risk scenario in CISO Assistant

    Args:
        scenario_id: ID or name of the quantitative risk scenario to update
        name: Optional new name for the scenario
        description: Optional new description
        status: Optional status - "draft", "open", "mitigate", "accept", or "transfer"
        priority: Optional priority (1=P1, 2=P2, 3=P3, 4=P4)
        observation: Optional observation text
        assets: Optional list of asset IDs or names to update (replaces existing, can use asset names)
        threats: Optional list of threat IDs or names to update (replaces existing, can use threat names)
    """
    try:
        from ..resolvers import resolve_id_or_name, resolve_asset_id

        # Resolve scenario name to ID if needed
        resolved_scenario_id = resolve_id_or_name(
            scenario_id, "/crq/quantitative-risk-scenarios/"
        )

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
        if observation is not None:
            payload["observation"] = observation

        # Resolve asset names to IDs if provided
        if assets is not None:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        # Resolve threat names to IDs if provided
        if threats is not None:
            from ..client import make_get_request, get_paginated_results

            resolved_threats = []
            for threat in threats:
                if "-" in threat and len(threat) == 36:
                    resolved_threats.append(threat)
                else:
                    threat_res = make_get_request("/threats/", params={"name": threat})
                    if threat_res.status_code == 200:
                        threat_data = threat_res.json()
                        threat_results = get_paginated_results(threat_data)
                        if threat_results:
                            resolved_threats.append(threat_results[0]["id"])
                        else:
                            raise ValueError(f"Threat '{threat}' not found")
                    else:
                        raise ValueError(f"Failed to look up threat '{threat}'")
            payload["threats"] = resolved_threats

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/crq/quantitative-risk-scenarios/{resolved_scenario_id}/", payload
        )

        if res.status_code == 200:
            scenario = res.json()
            return f"Updated Quantitative risk scenario: {scenario.get('name')} (ID: {scenario.get('id')})"
        else:
            return f"Error updating quantitative risk scenario: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_quantitative_risk_scenario: {str(e)}"


async def update_quantitative_risk_hypothesis(
    hypothesis_id: str,
    name: str = None,
    description: str = None,
    probability: float = None,
    impact_lb: float = None,
    impact_ub: float = None,
    impact_distribution: str = None,
    is_selected: bool = None,
    observation: str = None,
    existing_applied_controls: list = None,
    added_applied_controls: list = None,
) -> str:
    """Update an existing quantitative risk hypothesis in CISO Assistant

    Args:
        hypothesis_id: ID or name of the quantitative risk hypothesis to update
        name: Optional new name for the hypothesis
        description: Optional new description
        probability: Optional new probability value (0.0 to 1.0)
        impact_lb: Optional new impact lower bound value
        impact_ub: Optional new impact upper bound value
        impact_distribution: Optional new impact distribution model (e.g., "LOGNORMAL-CI90")
        is_selected: Optional flag to mark this hypothesis as selected (for residual scenarios)
        observation: Optional observation text
        existing_applied_controls: Optional list of existing applied control IDs or names (replaces existing, can use control names)
        added_applied_controls: Optional list of added applied control IDs or names (replaces existing, can use control names)
    """
    try:
        from ..resolvers import resolve_id_or_name

        # Resolve hypothesis name to ID if needed
        resolved_hypothesis_id = resolve_id_or_name(
            hypothesis_id, "/crq/quantitative-risk-hypotheses/"
        )

        # First, get current hypothesis to preserve existing parameters
        get_res = make_get_request(
            f"/crq/quantitative-risk-hypotheses/{resolved_hypothesis_id}/"
        )
        if get_res.status_code != 200:
            return f"Error fetching hypothesis: {get_res.status_code} - {get_res.text}"

        current_hypothesis = get_res.json()
        current_parameters = current_hypothesis.get("parameters") or {}

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if is_selected is not None:
            payload["is_selected"] = is_selected
        if observation is not None:
            payload["observation"] = observation

        # Handle parameters update
        parameters_updated = False
        updated_parameters = current_parameters.copy()

        if probability is not None:
            updated_parameters["probability"] = probability
            parameters_updated = True

        # Update impact if any impact field is provided
        if (
            impact_lb is not None
            or impact_ub is not None
            or impact_distribution is not None
        ):
            # Get current impact or initialize
            current_impact = updated_parameters.get("impact", {})

            if impact_lb is not None:
                current_impact["lb"] = impact_lb
                parameters_updated = True
            if impact_ub is not None:
                current_impact["ub"] = impact_ub
                parameters_updated = True
            if impact_distribution is not None:
                current_impact["distribution"] = impact_distribution
                parameters_updated = True

            updated_parameters["impact"] = current_impact

        if parameters_updated:
            payload["parameters"] = updated_parameters

        # Resolve existing applied control names to IDs if provided
        if existing_applied_controls is not None:
            from ..resolvers import resolve_applied_control_id

            resolved_existing = []
            for control in existing_applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_existing.append(resolved_control_id)
            payload["existing_applied_controls"] = resolved_existing

        # Resolve added applied control names to IDs if provided
        if added_applied_controls is not None:
            from ..resolvers import resolve_applied_control_id

            resolved_added = []
            for control in added_applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_added.append(resolved_control_id)
            payload["added_applied_controls"] = resolved_added

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/crq/quantitative-risk-hypotheses/{resolved_hypothesis_id}/", payload
        )

        if res.status_code == 200:
            hypothesis = res.json()
            return f"Updated Quantitative risk hypothesis: {hypothesis.get('name')} (ID: {hypothesis.get('id')})"
        else:
            return f"Error updating quantitative risk hypothesis: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_quantitative_risk_hypothesis: {str(e)}"
