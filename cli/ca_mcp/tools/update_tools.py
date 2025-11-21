"""Update MCP tools for CISO Assistant"""

from ..client import make_get_request, make_patch_request, make_delete_request, get_paginated_results
from ..resolvers import (
    resolve_asset_id,
    resolve_risk_scenario_id,
    resolve_risk_assessment_id,
    resolve_folder_id,
    resolve_applied_control_id,
    resolve_requirement_assessment_id,
    resolve_task_template_id,
)


async def update_asset(
    asset_id: str,
    name: str = None,
    description: str = None,
    asset_type: str = None,
    business_value: str = None,
    parent_assets: list = None,
) -> str:
    """Update asset properties

    Args:
        asset_id: Asset ID/name
        name: New name
        description: New description
        asset_type: PR | SP
        business_value: low | medium | high | very_high
        parent_assets: List of parent asset IDs/names
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
    """Update risk scenario properties and ratings

    Args:
        risk_scenario_id: Scenario ID/name
        name: New name
        description: New description
        risk_assessment_id: Risk assessment ID/name
        existing_controls: Existing controls description
        inherent_proba: Inherent probability index (from risk matrix)
        inherent_impact: Inherent impact index (from risk matrix)
        current_proba: Current probability index (from risk matrix)
        current_impact: Current impact index (from risk matrix)
        residual_proba: Residual probability index (from risk matrix)
        residual_impact: Residual impact index (from risk matrix)
        treatment: open | mitigate | accept | avoid | transfer
        strength_of_knowledge: -1 to 2
        justification: Justification text
        ref_id: Reference ID
        assets: List of asset IDs/names (replaces existing)
        threats: List of threat IDs/names (replaces existing)
        applied_controls: List of planned control IDs/names (replaces existing)
        existing_applied_controls: List of existing control IDs/names (replaces existing)
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
    cost: dict = None,
    control_impact: int = None,
    eta: str = None,
    start_date: str = None,
    expiry_date: str = None,
    link: str = None,
    ref_id: str = None,
) -> str:
    """Update applied control properties

    Args:
        control_id: Control ID/name
        name: New name
        description: New description
        status: to_do | in_progress | on_hold | active | deprecated | --
        priority: 1-4 (1=P1, 4=P4)
        category: policy | process | technical | physical
        csf_function: identify | protect | detect | respond | recover | govern
        effort: XS | S | M | L | XL
        cost: is a JSON object composed by follwing keys : 
            currency: € (euros),
            amortization_period (typically 1 year),
            build: One-time implementation costs
                fixed_cost: monetary amount,
                people_days: person-days effort
            run: Annual operational costs
                fixed_cost: monetary amount
                people_days: person-days effort
        control_impact: 1-5 (1=Very Low, 5=Very High)
        eta: ETA date YYYY-MM-DD
        start_date: Start date YYYY-MM-DD
        expiry_date: Expiry date YYYY-MM-DD
        link: External link (e.g. Jira URL)
        ref_id: Reference ID
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
        if cost is not None:
            payload["cost"] = cost
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
    applied_controls: list = None,
) -> str:
    """Update requirement assessment in audit. Use get_requirement_assessments() to find IDs

    Args:
        requirement_assessment_id: Requirement assessment UUID
        status: to_do | in_progress | in_review | done
        result: not_assessed | partially_compliant | non_compliant | compliant | not_applicable
        observation: Observation text
        score: Score value
        is_scored: Scored assessment flag
        eta: ETA date YYYY-MM-DD
        due_date: Due date YYYY-MM-DD
        selected: Applicability flag
        applied_controls: List of applied control IDs/names to associate with this requirement assessment. Can be None to leave unchanged, or empty list to clear associations. Elements should be strings representing control identifiers.
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
        if applied_controls is not None:
            resolved_controls = []
            for control in applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_controls.append(resolved_control_id)
            payload["applied_controls"] = resolved_controls

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
    """Update quantitative risk study. Risk tolerance curve auto-regenerates when points modified

    Args:
        study_id: Study ID/name
        name: New name
        description: New description
        status: planned | in_progress | in_review | done | deprecated
        loss_threshold: Loss threshold (monetary)
        risk_tolerance_point1_probability: Point1 probability (0.0-1.0, e.g. 0.01=1%)
        risk_tolerance_point1_acceptable_loss: Point1 acceptable loss (monetary)
        risk_tolerance_point2_probability: Point2 probability (0.0-1.0, e.g. 0.001=0.1%)
        risk_tolerance_point2_acceptable_loss: Point2 acceptable loss (monetary)
        observation: Observation text
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
    """Update quantitative risk scenario

    Args:
        scenario_id: Scenario ID/name
        name: New name
        description: New description
        status: draft | open | mitigate | accept | transfer
        priority: 1-4 (1=P1, 4=P4)
        observation: Observation text
        assets: List of asset IDs/names (replaces existing)
        threats: List of threat IDs/names (replaces existing)
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
    """Update quantitative risk hypothesis

    Args:
        hypothesis_id: Hypothesis ID/name
        name: New name
        description: New description
        probability: Probability 0.0-1.0
        impact_lb: Impact lower bound
        impact_ub: Impact upper bound
        impact_distribution: Distribution model (e.g. LOGNORMAL-CI90)
        is_selected: Selected flag (for residual scenarios)
        observation: Observation text
        existing_applied_controls: List of existing control IDs/names (replaces existing)
        added_applied_controls: List of added control IDs/names (replaces existing)
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


async def update_task_template(
    task_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    observation: str = None,
    evidences: list = None,
    is_published: bool = None,
    task_date: str = None,
    is_recurrent: bool = None,
    ref_id: str = None,
    schedule: str = None,
    enabled: bool = None,
    link: str = None,
    folder_id: str = None,
    assigned_to: list = None,
    assets: list = None,
    applied_controls: list = None,
    compliance_assessments: list = None,
    risk_assessments: list = None,
    findings_assessment: list = None,
) -> str:
    """Update task template properties

    Args:
        task_id: Task template ID/name (required)
        name: Task template name
        description: Description
        status: Status
        observation: Observation text
        evidences: Array of evidence UUIDs
        is_published: Published flag
        task_date: Task date (YYYY-MM-DD)
        is_recurrent: Recurrent flag
        ref_id: Reference ID
        schedule: Schedule definition
        enabled: Enabled flag
        link: Link to evidence (e.g. Jira ticket)
        folder_id: Folder ID/name
        assigned_to: Array of user UUIDs
        assets: Array of asset UUIDs
        applied_controls: List of applied control IDs/names to associate with this task template. Can be None to leave unchanged, or empty list to clear associations. Elements should be strings representing control identifiers.
        compliance_assessments: Array of compliance assessment UUIDs
        risk_assessments: Array of risk assessment UUIDs
        findings_assessment: Array of finding assessment UUIDs
    """
    try:
        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
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
        if is_published is not None:
            payload["is_published"] = is_published
        if task_date is not None:
            payload["task_date"] = task_date
        if is_recurrent is not None:
            payload["is_recurrent"] = is_recurrent
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if schedule is not None:
            payload["schedule"] = schedule
        if enabled is not None:
            payload["enabled"] = enabled
        if link is not None:
            payload["link"] = link
        if assigned_to is not None:
            payload["assigned_to"] = assigned_to
        if assets is not None:
            payload["assets"] = assets
        if applied_controls is not None:
            resolved_controls = []
            for control in applied_controls:
                resolved_control_id = resolve_applied_control_id(control)
                resolved_controls.append(resolved_control_id)
            payload["applied_controls"] = resolved_controls
        if compliance_assessments is not None:
            payload["compliance_assessments"] = compliance_assessments
        if risk_assessments is not None:
            payload["risk_assessments"] = risk_assessments
        if findings_assessment is not None:
            payload["findings_assessment"] = findings_assessment

        # Resolve folder name to ID if provided
        if folder_id is not None:
            resolved_folder_id = resolve_folder_id(folder_id)
            payload["folder"] = resolved_folder_id

        if not payload:
            return "Error: No fields provided to update"
            
        # Resolve task name to ID if needed
        resolved_task_id = resolve_task_template_id(task_id)

        res = make_patch_request(f"/task-templates/{resolved_task_id}/", payload)

        if res.status_code == 200:
            task = res.json()
            return f"Updated task template: {task.get('name')} (ID: {task.get('id')})"
        else:
            return f"Error updating task template: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_task_template: {str(e)}"


async def delete_task_template(task_id: str) -> str:
    """Delete task template

    Args:
        task_id: Task template ID/name
    """
    try:
        # Resolve task name to ID if needed
        resolved_task_id = resolve_task_template_id(task_id)

        res = make_delete_request(f"/task-templates/{resolved_task_id}/")

        if res.status_code == 204:
            return f"Deleted task template (ID: {resolved_task_id})"
        else:
            return f"Error deleting task template: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in delete_task_template: {str(e)}"
