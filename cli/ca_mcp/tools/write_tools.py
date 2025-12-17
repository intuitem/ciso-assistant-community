"""Write/Create MCP tools for CISO Assistant"""

from ..client import make_post_request, make_get_request
from ..resolvers import (
    resolve_folder_id,
    resolve_perimeter_id,
    resolve_risk_matrix_id,
    resolve_framework_id,
    resolve_risk_assessment_id,
    resolve_applied_control_id,
)
from ..config import GLOBAL_FOLDER_ID
from ..utils.response_formatter import (
    success_response,
    error_response,
    http_error_response,
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
) -> str:
    """Create asset in folder

    Args:
        name: Asset name
        description: Description
        asset_type: PR (Primary) | SP (Supporting)
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


async def create_applied_control(
    name: str,
    description: str = "",
    eta: str = None,
    folder_id: str = None,
    category: str = "technical",
    status: str = "planned",
) -> str:
    """Create applied control (security measure)

    Args:
        name: Control name
        description: Description
        eta: Completion date YYYY-MM-DD
        folder_id: Folder ID/name
        category: technical | physical | organizational | procedural
        status: planned | active | inactive
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
    """Create risk assessment with risk matrix and perimeter

    Args:
        name: Assessment name
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
    applied_controls: list = None,
    existing_applied_controls: list = None,
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
        applied_controls: List of planned control IDs/names
        existing_applied_controls: List of existing control IDs/names
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
    is_published: bool = False,
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
        is_published: Published flag
        task_date: Task date (YYYY-MM-DD)
        is_recurrent: Recurrent flag
        ref_id: Reference ID
        schedule: Schedule definition
        enabled: Enabled flag
        link: Link to evidence (e.g. Jira ticket)
        assigned_to: Array of user UUIDs
        assets: Array of asset UUIDs
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
            "is_published": is_published,
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

        res = make_post_request("/task-templates/", payload)

        if res.status_code == 201:
            task = res.json()
            return f"Created task template: {task.get('name')} (ID: {task.get('id')})"
        else:
            return f"Error creating task template: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in create_task_template: {str(e)}"
