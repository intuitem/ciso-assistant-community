"""Helper functions to resolve names to UUIDs"""

import json
import re
import uuid

from .client import fetch_all_results, make_get_request


def _is_uuid(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def resolve_folder_id(folder_name_or_id: str) -> str:
    """Helper function to resolve folder name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    Returns the UUID string or raises ValueError with a clear message.
    """
    # Check if it's already a UUID (contains hyphens in UUID format)
    if "-" in folder_name_or_id and len(folder_name_or_id) == 36:
        return folder_name_or_id

    # Otherwise, look up by name - return exactly one result
    folders, error = fetch_all_results("/folders/", params={"name": folder_name_or_id})

    if error:
        raise ValueError(f"Folder '{folder_name_or_id}' API error: {error}")

    if not folders or len(folders) == 0:
        raise ValueError(f"Folder '{folder_name_or_id}' not found")

    if len(folders) > 1:
        folder_names = [f["name"] for f in folders[:3]]
        raise ValueError(
            f"Ambiguous folder name '{folder_name_or_id}', found {len(folders)}: {folder_names}"
        )

    # Return exactly one UUID string
    return str(folders[0]["id"])


def resolve_perimeter_id(perimeter_name_or_id: str) -> str:
    """Helper function to resolve perimeter name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    Returns the UUID string or raises ValueError with a clear message.
    """
    # Check if it's already a UUID
    if "-" in perimeter_name_or_id and len(perimeter_name_or_id) == 36:
        return perimeter_name_or_id

    # Otherwise, look up by name - return exactly one result
    perimeters, error = fetch_all_results(
        "/perimeters/", params={"name": perimeter_name_or_id}
    )

    if error:
        raise ValueError(f"Perimeter '{perimeter_name_or_id}' API error: {error}")

    if not perimeters or len(perimeters) == 0:
        raise ValueError(f"Perimeter '{perimeter_name_or_id}' not found")

    if len(perimeters) > 1:
        perimeter_names = [p["name"] for p in perimeters[:3]]
        raise ValueError(
            f"Ambiguous perimeter name '{perimeter_name_or_id}', found {len(perimeters)}: {perimeter_names}"
        )

    # Return exactly one UUID string
    return str(perimeters[0]["id"])


def resolve_risk_matrix_id(matrix_name_or_id: str) -> str:
    """Helper function to resolve risk matrix name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in matrix_name_or_id and len(matrix_name_or_id) == 36:
        return matrix_name_or_id

    # Otherwise, look up by name
    matrices, error = fetch_all_results(
        "/risk-matrices/", params={"name": matrix_name_or_id}
    )

    if error:
        raise ValueError(f"Risk matrix '{matrix_name_or_id}' API error: {error}")

    if not matrices:
        raise ValueError(f"Risk matrix '{matrix_name_or_id}' not found")

    if len(matrices) > 1:
        raise ValueError(
            f"Ambiguous risk matrix name '{matrix_name_or_id}', found {len(matrices)}"
        )

    return matrices[0]["id"]


def resolve_framework_id(framework_name_or_urn_or_id: str) -> str:
    """Helper function to resolve framework name/URN to UUID
    If already a UUID, returns it. If a name or URN, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in framework_name_or_urn_or_id and len(framework_name_or_urn_or_id) == 36:
        return framework_name_or_urn_or_id

    # Try URN search first if it looks like a URN
    if framework_name_or_urn_or_id.startswith("urn:"):
        params = {"urn": framework_name_or_urn_or_id}
    else:
        # Search by name
        params = {"name": framework_name_or_urn_or_id}

    frameworks, error = fetch_all_results("/frameworks/", params=params)

    if error:
        raise ValueError(
            f"Framework '{framework_name_or_urn_or_id}' API error: {error}"
        )

    if not frameworks:
        raise ValueError(f"Framework '{framework_name_or_urn_or_id}' not found")

    if len(frameworks) > 1:
        raise ValueError(
            f"Ambiguous framework name '{framework_name_or_urn_or_id}', found {len(frameworks)}"
        )

    return frameworks[0]["id"]


def resolve_risk_assessment_id(assessment_name_or_id: str) -> str:
    """Helper function to resolve risk assessment name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in assessment_name_or_id and len(assessment_name_or_id) == 36:
        return assessment_name_or_id

    # Otherwise, look up by name
    assessments, error = fetch_all_results(
        "/risk-assessments/", params={"name": assessment_name_or_id}
    )

    if error:
        raise ValueError(
            f"Risk assessment '{assessment_name_or_id}' API error: {error}"
        )

    if not assessments:
        raise ValueError(f"Risk assessment '{assessment_name_or_id}' not found")

    if len(assessments) > 1:
        raise ValueError(
            f"Ambiguous risk assessment name '{assessment_name_or_id}', found {len(assessments)}"
        )

    return assessments[0]["id"]


def resolve_asset_id(asset_name_or_id: str, folder_id: str = None) -> str:
    """Helper function to resolve asset name to UUID
    If already a UUID, returns it. If a name, looks it up via API.

    Args:
        asset_name_or_id: Asset name or UUID
        folder_id: Optional folder UUID to scope the lookup (avoids ambiguity)
    """
    # Check if it's already a UUID
    if "-" in asset_name_or_id and len(asset_name_or_id) == 36:
        return asset_name_or_id

    # Build query params with optional folder scoping
    params = {"name": asset_name_or_id}
    if folder_id:
        params["folder"] = folder_id

    assets, error = fetch_all_results("/assets/", params=params)

    if error:
        raise ValueError(f"Asset '{asset_name_or_id}' API error: {error}")

    if not assets:
        raise ValueError(f"Asset '{asset_name_or_id}' not found")

    if len(assets) > 1:
        raise ValueError(
            f"Ambiguous asset name '{asset_name_or_id}', found {len(assets)}"
        )

    return assets[0]["id"]


def resolve_asset_class_id(asset_class_name_or_id: str) -> str:
    """Helper function to resolve asset class name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in asset_class_name_or_id and len(asset_class_name_or_id) == 36:
        return asset_class_name_or_id

    asset_classes, error = fetch_all_results(
        "/asset-class/", params={"name": asset_class_name_or_id}
    )

    if error:
        raise ValueError(f"Asset class '{asset_class_name_or_id}' API error: {error}")

    if not asset_classes:
        raise ValueError(f"Asset class '{asset_class_name_or_id}' not found")

    if len(asset_classes) > 1:
        class_names = [c["name"] for c in asset_classes[:3]]
        raise ValueError(
            f"Ambiguous asset class name '{asset_class_name_or_id}', found {len(asset_classes)}: {class_names}"
        )

    return str(asset_classes[0]["id"])


def resolve_risk_scenario_id(scenario_name_or_id: str) -> str:
    """Helper function to resolve risk scenario name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in scenario_name_or_id and len(scenario_name_or_id) == 36:
        return scenario_name_or_id

    # Otherwise, look up by name
    scenarios, error = fetch_all_results(
        "/risk-scenarios/", params={"name": scenario_name_or_id}
    )

    if error:
        raise ValueError(f"Risk scenario '{scenario_name_or_id}' API error: {error}")

    if not scenarios:
        raise ValueError(f"Risk scenario '{scenario_name_or_id}' not found")

    if len(scenarios) > 1:
        raise ValueError(
            f"Ambiguous risk scenario name '{scenario_name_or_id}', found {len(scenarios)}"
        )

    return scenarios[0]["id"]


def resolve_applied_control_id(control_name_or_id: str, folder_id: str = None) -> str:
    """Helper function to resolve applied control name to UUID
    If already a UUID, returns it. If a name, looks it up via API.

    Args:
        control_name_or_id: Control name or UUID
        folder_id: Optional folder UUID to scope the lookup (avoids ambiguity)
    """
    # Check if it's already a UUID
    if "-" in control_name_or_id and len(control_name_or_id) == 36:
        return control_name_or_id

    # Build query params with optional folder scoping
    params = {"name": control_name_or_id}
    if folder_id:
        params["folder"] = folder_id

    controls, error = fetch_all_results("/applied-controls/", params=params)

    if error:
        raise ValueError(f"Applied control '{control_name_or_id}' API error: {error}")

    if not controls:
        raise ValueError(f"Applied control '{control_name_or_id}' not found")

    if len(controls) > 1:
        raise ValueError(
            f"Ambiguous applied control name '{control_name_or_id}', found {len(controls)}"
        )

    return controls[0]["id"]


def resolve_requirement_assessment_id(requirement_assessment_id: str) -> str:
    """Validate requirement assessment UUID (only UUIDs accepted, no names)"""
    if "-" in requirement_assessment_id and len(requirement_assessment_id) == 36:
        return requirement_assessment_id

    raise ValueError(
        f"Requirement assessment '{requirement_assessment_id}' is not a valid UUID"
    )


def resolve_compliance_assessment_id(assessment_name_or_id: str) -> str:
    """Helper function to resolve compliance assessment (audit) name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in assessment_name_or_id and len(assessment_name_or_id) == 36:
        return assessment_name_or_id

    # Otherwise, look up by name
    assessments, error = fetch_all_results(
        "/compliance-assessments/", params={"name": assessment_name_or_id}
    )

    if error:
        raise ValueError(
            f"Compliance assessment '{assessment_name_or_id}' API error: {error}"
        )

    if not assessments:
        raise ValueError(f"Compliance assessment '{assessment_name_or_id}' not found")

    if len(assessments) > 1:
        assessment_names = [a["name"] for a in assessments[:3]]
        raise ValueError(
            f"Ambiguous compliance assessment name '{assessment_name_or_id}', found {len(assessments)}: {assessment_names}"
        )

    return assessments[0]["id"]


def resolve_id_or_name(name_or_id: str, endpoint: str) -> str:
    """Generic helper function to resolve name to UUID for any endpoint
    If already a UUID, returns it. If a name, looks it up via API.

    Args:
        name_or_id: Name or UUID to resolve
        endpoint: API endpoint to query (e.g., "/crq/quantitative-risk-studies/")

    Returns:
        UUID of the object
    """
    # Check if it's already a UUID
    if "-" in name_or_id and len(name_or_id) == 36:
        return name_or_id

    # Otherwise, look up by name
    results, error = fetch_all_results(endpoint, params={"name": name_or_id})

    if error:
        raise ValueError(f"'{name_or_id}' at {endpoint} API error: {error}")

    if not results:
        raise ValueError(f"'{name_or_id}' not found at {endpoint}")

    if len(results) > 1:
        raise ValueError(
            f"Ambiguous name '{name_or_id}' at {endpoint}, found {len(results)}"
        )

    return results[0]["id"]


def resolve_threat_id(
    threat_name_or_id: str, library: str = None, folder_id: str = None
) -> str:
    """Helper function to resolve threat name to UUID
    If already a UUID, returns it. If a name, looks it up via API.

    Args:
        threat_name_or_id: Threat name or UUID
        library: Optional library URN/ID to filter threats by specific library
        folder_id: Optional folder UUID to scope the lookup (for custom threats)

    Returns:
        UUID of the threat
    """
    # Check if it's already a UUID
    if "-" in threat_name_or_id and len(threat_name_or_id) == 36:
        return threat_name_or_id

    # Build query params
    params = {"name": threat_name_or_id}
    if library:
        # Resolve library URN to ID if needed
        library_id = resolve_library_id(library)
        params["library"] = library_id
    if folder_id:
        params["folder"] = folder_id

    threats, error = fetch_all_results("/threats/", params=params)

    if error:
        raise ValueError(f"Threat '{threat_name_or_id}' API error: {error}")

    if not threats:
        raise ValueError(f"Threat '{threat_name_or_id}' not found")

    if len(threats) > 1:
        # Provide helpful info about which libraries have matching threats
        threat_info = [
            f"{t['name']} (provider: {t.get('provider', 'unknown')})"
            for t in threats[:3]
        ]
        raise ValueError(
            f"Ambiguous threat name '{threat_name_or_id}', found {len(threats)}: {threat_info}. "
            f"Use the threat UUID or specify a library filter."
        )

    return threats[0]["id"]


def resolve_library_id(library_urn_or_id: str) -> str:
    """Resolve library URN to UUID"""
    if "-" in library_urn_or_id and len(library_urn_or_id) == 36:
        return library_urn_or_id

    libraries, error = fetch_all_results(
        "/loaded-libraries/", params={"urn": library_urn_or_id}
    )

    if error:
        raise ValueError(f"Library '{library_urn_or_id}' API error: {error}")

    if not libraries or len(libraries) == 0:
        raise ValueError(f"Library '{library_urn_or_id}' not found or not loaded")

    if len(libraries) > 1:
        library_names = [lib["name"] for lib in libraries[:3]]
        raise ValueError(
            f"Ambiguous library URN '{library_urn_or_id}', found {len(libraries)}: {library_names}"
        )

    return str(libraries[0]["id"])


def resolve_vulnerability_id(vulnerability_name_or_id: str) -> str:
    """Helper function to resolve vulnerability name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in vulnerability_name_or_id and len(vulnerability_name_or_id) == 36:
        return vulnerability_name_or_id

    # Otherwise, look up by name
    vulnerabilities, error = fetch_all_results(
        "/vulnerabilities/", params={"name": vulnerability_name_or_id}
    )

    if error:
        raise ValueError(
            f"Vulnerability '{vulnerability_name_or_id}' API error: {error}"
        )

    if not vulnerabilities:
        raise ValueError(f"Vulnerability '{vulnerability_name_or_id}' not found")

    if len(vulnerabilities) > 1:
        vuln_names = [v["name"] for v in vulnerabilities[:3]]
        raise ValueError(
            f"Ambiguous vulnerability name '{vulnerability_name_or_id}', found {len(vulnerabilities)}: {vuln_names}"
        )

    return str(vulnerabilities[0]["id"])


def resolve_team_id(team_name_or_id: str) -> str:
    """Helper function to resolve team name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in team_name_or_id and len(team_name_or_id) == 36:
        return team_name_or_id

    teams, error = fetch_all_results("/teams/", params={"name": team_name_or_id})

    if error:
        raise ValueError(f"Team '{team_name_or_id}' API error: {error}")

    if not teams:
        raise ValueError(f"Team '{team_name_or_id}' not found")

    if len(teams) > 1:
        team_names = [t["name"] for t in teams[:3]]
        raise ValueError(
            f"Ambiguous team name '{team_name_or_id}', found {len(teams)}: {team_names}"
        )

    return str(teams[0]["id"])


def resolve_task_template_id(task_name_or_id: str) -> str:
    """Helper function to resolve task template name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in task_name_or_id and len(task_name_or_id) == 36:
        return task_name_or_id

    # Otherwise, look up by name
    tasks, error = fetch_all_results(
        "/task-templates/", params={"name": task_name_or_id}
    )

    if error:
        raise ValueError(f"Task template '{task_name_or_id}' API error: {error}")

    if not tasks:
        raise ValueError(f"Task template '{task_name_or_id}' not found")

    if len(tasks) > 1:
        raise ValueError(
            f"Ambiguous task template name '{task_name_or_id}', found {len(tasks)}"
        )

    return tasks[0]["id"]


# ============================================================================
# TPRM (Third-Party Risk Management) Resolvers
# ============================================================================


def resolve_entity_id(entity_name_or_id: str) -> str:
    """Helper function to resolve entity name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in entity_name_or_id and len(entity_name_or_id) == 36:
        return entity_name_or_id

    entities, error = fetch_all_results(
        "/entities/", params={"name": entity_name_or_id}
    )

    if error:
        raise ValueError(f"Entity '{entity_name_or_id}' API error: {error}")

    if not entities:
        raise ValueError(f"Entity '{entity_name_or_id}' not found")

    if len(entities) > 1:
        raise ValueError(
            f"Ambiguous entity name '{entity_name_or_id}', found {len(entities)}"
        )

    return entities[0]["id"]


def resolve_solution_id(solution_name_or_id: str) -> str:
    """Helper function to resolve solution name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in solution_name_or_id and len(solution_name_or_id) == 36:
        return solution_name_or_id

    solutions, error = fetch_all_results(
        "/solutions/", params={"name": solution_name_or_id}
    )

    if error:
        raise ValueError(f"Solution '{solution_name_or_id}' API error: {error}")

    if not solutions:
        raise ValueError(f"Solution '{solution_name_or_id}' not found")

    if len(solutions) > 1:
        raise ValueError(
            f"Ambiguous solution name '{solution_name_or_id}', found {len(solutions)}"
        )

    return solutions[0]["id"]


def resolve_contract_id(contract_name_or_id: str) -> str:
    """Helper function to resolve contract name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in contract_name_or_id and len(contract_name_or_id) == 36:
        return contract_name_or_id

    contracts, error = fetch_all_results(
        "/contracts/", params={"name": contract_name_or_id}
    )

    if error:
        raise ValueError(f"Contract '{contract_name_or_id}' API error: {error}")

    if not contracts:
        raise ValueError(f"Contract '{contract_name_or_id}' not found")

    if len(contracts) > 1:
        raise ValueError(
            f"Ambiguous contract name '{contract_name_or_id}', found {len(contracts)}"
        )

    return contracts[0]["id"]


def resolve_entity_assessment_id(assessment_name_or_id: str) -> str:
    """Helper function to resolve entity assessment name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in assessment_name_or_id and len(assessment_name_or_id) == 36:
        return assessment_name_or_id

    assessments, error = fetch_all_results(
        "/entity-assessments/", params={"name": assessment_name_or_id}
    )

    if error:
        raise ValueError(
            f"Entity assessment '{assessment_name_or_id}' API error: {error}"
        )

    if not assessments:
        raise ValueError(f"Entity assessment '{assessment_name_or_id}' not found")

    if len(assessments) > 1:
        raise ValueError(
            f"Ambiguous entity assessment name '{assessment_name_or_id}', found {len(assessments)}"
        )

    return assessments[0]["id"]


def resolve_representative_id(representative_email_or_id: str) -> str:
    """Helper function to resolve representative email to UUID
    If already a UUID, returns it. If an email, looks it up via API.
    """
    if "-" in representative_email_or_id and len(representative_email_or_id) == 36:
        return representative_email_or_id

    # Search by email since that's the unique identifier for representatives
    representatives, error = fetch_all_results(
        "/representatives/", params={"search": representative_email_or_id}
    )

    if error:
        raise ValueError(
            f"Representative '{representative_email_or_id}' API error: {error}"
        )

    if not representatives:
        raise ValueError(f"Representative '{representative_email_or_id}' not found")

    if len(representatives) > 1:
        raise ValueError(
            f"Ambiguous representative '{representative_email_or_id}', found {len(representatives)}"
        )

    return representatives[0]["id"]


# ============================================================================
# EBIOS RM (Risk Management) Resolvers
# ============================================================================


def resolve_ebios_rm_study_id(study_name_or_id: str) -> str:
    """Helper function to resolve EBIOS RM study name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in study_name_or_id and len(study_name_or_id) == 36:
        return study_name_or_id

    studies, error = fetch_all_results(
        "/ebios-rm/studies/", params={"name": study_name_or_id}
    )

    if error:
        raise ValueError(f"EBIOS RM Study '{study_name_or_id}' API error: {error}")

    if not studies:
        raise ValueError(f"EBIOS RM Study '{study_name_or_id}' not found")

    if len(studies) > 1:
        raise ValueError(
            f"Ambiguous EBIOS RM Study name '{study_name_or_id}', found {len(studies)}"
        )

    return studies[0]["id"]


def resolve_feared_event_id(feared_event_name_or_id: str) -> str:
    """Helper function to resolve feared event name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in feared_event_name_or_id and len(feared_event_name_or_id) == 36:
        return feared_event_name_or_id

    feared_events, error = fetch_all_results(
        "/ebios-rm/feared-events/", params={"name": feared_event_name_or_id}
    )

    if error:
        raise ValueError(f"Feared event '{feared_event_name_or_id}' API error: {error}")

    if not feared_events:
        raise ValueError(f"Feared event '{feared_event_name_or_id}' not found")

    if len(feared_events) > 1:
        raise ValueError(
            f"Ambiguous feared event name '{feared_event_name_or_id}', found {len(feared_events)}"
        )

    return feared_events[0]["id"]


def resolve_ro_to_id(ro_to_id: str) -> str:
    """Helper function to resolve RoTo couple ID
    RoTo couples don't have names, so only UUIDs are accepted.
    """
    if "-" in ro_to_id and len(ro_to_id) == 36:
        return ro_to_id

    raise ValueError(f"RoTo couple '{ro_to_id}' is not a valid UUID")


def resolve_stakeholder_id(stakeholder_id: str) -> str:
    """Helper function to resolve stakeholder ID
    Stakeholders are identified by entity+category, so only UUIDs are accepted.
    """
    if "-" in stakeholder_id and len(stakeholder_id) == 36:
        return stakeholder_id

    raise ValueError(f"Stakeholder '{stakeholder_id}' is not a valid UUID")


def resolve_strategic_scenario_id(scenario_name_or_id: str) -> str:
    """Helper function to resolve strategic scenario name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in scenario_name_or_id and len(scenario_name_or_id) == 36:
        return scenario_name_or_id

    scenarios, error = fetch_all_results(
        "/ebios-rm/strategic-scenarios/", params={"name": scenario_name_or_id}
    )

    if error:
        raise ValueError(
            f"Strategic scenario '{scenario_name_or_id}' API error: {error}"
        )

    if not scenarios:
        raise ValueError(f"Strategic scenario '{scenario_name_or_id}' not found")

    if len(scenarios) > 1:
        raise ValueError(
            f"Ambiguous strategic scenario name '{scenario_name_or_id}', found {len(scenarios)}"
        )

    return scenarios[0]["id"]


def resolve_attack_path_id(attack_path_name_or_id: str) -> str:
    """Helper function to resolve attack path name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in attack_path_name_or_id and len(attack_path_name_or_id) == 36:
        return attack_path_name_or_id

    attack_paths, error = fetch_all_results(
        "/ebios-rm/attack-paths/", params={"name": attack_path_name_or_id}
    )

    if error:
        raise ValueError(f"Attack path '{attack_path_name_or_id}' API error: {error}")

    if not attack_paths:
        raise ValueError(f"Attack path '{attack_path_name_or_id}' not found")

    if len(attack_paths) > 1:
        raise ValueError(
            f"Ambiguous attack path name '{attack_path_name_or_id}', found {len(attack_paths)}"
        )

    return attack_paths[0]["id"]


def resolve_operational_scenario_id(scenario_id: str) -> str:
    """Helper function to resolve operational scenario ID
    Operational scenarios derive their name from attack paths, so only UUIDs are accepted.
    """
    if "-" in scenario_id and len(scenario_id) == 36:
        return scenario_id

    raise ValueError(f"Operational scenario '{scenario_id}' is not a valid UUID")


def resolve_elementary_action_id(action_name_or_id: str) -> str:
    """Helper function to resolve elementary action name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in action_name_or_id and len(action_name_or_id) == 36:
        return action_name_or_id

    actions, error = fetch_all_results(
        "/ebios-rm/elementary-actions/", params={"name": action_name_or_id}
    )

    if error:
        raise ValueError(f"Elementary action '{action_name_or_id}' API error: {error}")

    if not actions:
        raise ValueError(f"Elementary action '{action_name_or_id}' not found")

    if len(actions) > 1:
        raise ValueError(
            f"Ambiguous elementary action name '{action_name_or_id}', found {len(actions)}"
        )

    return actions[0]["id"]


def resolve_operating_mode_id(mode_name_or_id: str) -> str:
    """Helper function to resolve operating mode name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    if "-" in mode_name_or_id and len(mode_name_or_id) == 36:
        return mode_name_or_id

    modes, error = fetch_all_results(
        "/ebios-rm/operating-modes/", params={"name": mode_name_or_id}
    )

    if error:
        raise ValueError(f"Operating mode '{mode_name_or_id}' API error: {error}")

    if not modes:
        raise ValueError(f"Operating mode '{mode_name_or_id}' not found")

    if len(modes) > 1:
        raise ValueError(
            f"Ambiguous operating mode name '{mode_name_or_id}', found {len(modes)}"
        )

    return modes[0]["id"]


def resolve_kill_chain_id(kill_chain_id: str) -> str:
    """Helper function to resolve kill chain step ID
    Kill chain steps don't have names, so only UUIDs are accepted.
    """
    if "-" in kill_chain_id and len(kill_chain_id) == 36:
        return kill_chain_id

    raise ValueError(f"Kill chain step '{kill_chain_id}' is not a valid UUID")


# ============================================================================
# Terminology matching helpers (shared by EBIOS RM and risk scenario tools)
# ============================================================================


def _normalize_for_matching(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, strip, remove trailing 's' for plurals"""
    normalized = text.lower().strip()
    # Handle common plural forms
    if normalized.endswith("s") and len(normalized) > 2:
        normalized = normalized[:-1]
    # Handle underscores vs spaces
    normalized = normalized.replace("_", " ").replace("-", " ")
    return normalized


def _find_terminology_match(terminologies: list, user_input: str) -> dict | None:
    """Find a terminology that matches the user input.

    Matches against:
    - Base name field (snake_case like "organized_crime")
    - All translations in the translations dict

    Uses case-insensitive, plural-insensitive matching.
    """
    normalized_input = _normalize_for_matching(user_input)

    for term in terminologies:
        # Match against the base name
        if _normalize_for_matching(term.get("name", "")) == normalized_input:
            return term

        # Match against translations
        translations = term.get("translations", {})
        if isinstance(translations, dict):
            for locale, locale_data in translations.items():
                if isinstance(locale_data, dict):
                    translated_name = locale_data.get("name", "")
                    if (
                        translated_name
                        and _normalize_for_matching(translated_name) == normalized_input
                    ):
                        return term
                elif isinstance(locale_data, str):
                    # Some translations might be stored as direct strings
                    if _normalize_for_matching(locale_data) == normalized_input:
                        return term

    return None


# ============================================================================
# Risk review resolvers: actors, reference controls, qualifications, risk levels
# ============================================================================


def _actor_label(actor: dict) -> str:
    return str(
        actor.get("str") or (actor.get("specific") or {}).get("str") or actor.get("id")
    )


def resolve_actor_id(actor_ref: str) -> str:
    """Resolve an Actor (user, team or entity) from a UUID, email or name.

    Owner / assignee fields reference Actor ids, not User ids.
    Matching order: exact email, exact display string (case-insensitive),
    then a single search hit. Raises ValueError naming the candidates.
    """
    if _is_uuid(actor_ref):
        return actor_ref

    ref = str(actor_ref).strip()
    if not ref:
        raise ValueError("Actor reference is empty")
    ref_lower = ref.lower()

    actors, error = fetch_all_results("/actors/", params={"search": ref})
    if error:
        raise ValueError(f"Actor '{ref}' API error: {error}")
    actors = actors or []

    # 1. exact email
    if "@" in ref:
        by_email = [
            a
            for a in actors
            if str((a.get("specific") or {}).get("email") or "").lower() == ref_lower
        ]
        if not by_email:
            # /actors/ does not return the email of the wrapped user: map it
            # through /users/ and match the actor on the user id.
            users, user_error = fetch_all_results(
                "/users/", params={"email__icontains": ref}
            )
            if not user_error and users:
                user_ids = {
                    str(u.get("id"))
                    for u in users
                    if str(u.get("email") or "").lower() == ref_lower
                }
                by_email = [
                    a
                    for a in actors
                    if str((a.get("specific") or {}).get("id")) in user_ids
                ]
        if len(by_email) == 1:
            return str(by_email[0]["id"])

    # 2. exact display string
    exact = [a for a in actors if _actor_label(a).strip().lower() == ref_lower]
    if len(exact) == 1:
        return str(exact[0]["id"])
    if len(exact) > 1:
        labels = [_actor_label(a) for a in exact[:5]]
        raise ValueError(
            f"Ambiguous actor '{ref}', found {len(exact)} exact matches: {labels}. "
            "Use the actor UUID"
        )
    if "@" in ref:
        raise ValueError(f"Actor with email '{ref}' not found")

    # 3. single search hit
    if len(actors) == 1:
        return str(actors[0]["id"])

    if not actors:
        raise ValueError(
            f"Actor '{ref}' not found. Use list_objects('actors') to list actors"
        )

    labels = [_actor_label(a) for a in actors[:5]]
    raise ValueError(
        f"Ambiguous actor '{ref}', found {len(actors)}: {labels}. "
        "Use an exact email, the exact name, or the actor UUID"
    )


def resolve_actor_ids(actor_refs) -> list:
    """Resolve a list of actor references (see resolve_actor_id)."""
    if isinstance(actor_refs, str):
        actor_refs = [actor_refs]
    return [resolve_actor_id(a) for a in actor_refs]


def resolve_user_id(user_ref: str) -> str:
    """Resolve a User (not an Actor) from a UUID, email or name.

    Team.leader/deputies/members are plain User references, unlike
    owner/assignee fields which reference Actor ids (see resolve_actor_id).
    """
    if _is_uuid(user_ref):
        return user_ref

    ref = str(user_ref).strip()
    if not ref:
        raise ValueError("User reference is empty")

    params = {"email": ref} if "@" in ref else {"search": ref}
    users, error = fetch_all_results("/users/", params=params)
    if error:
        raise ValueError(f"User '{ref}' API error: {error}")

    if not users:
        raise ValueError(f"User '{ref}' not found")

    if len(users) > 1:
        needle = ref.lower()
        exact = [
            u
            for u in users
            if needle
            in {
                (u.get("first_name") or "").lower(),
                (u.get("last_name") or "").lower(),
                f"{u.get('first_name') or ''} {u.get('last_name') or ''}".strip().lower(),
            }
        ]
        if len(exact) == 1:
            return str(exact[0]["id"])
        labels = [u.get("email") for u in users[:5]]
        raise ValueError(f"Ambiguous user '{ref}', found {len(users)}: {labels}")

    return str(users[0]["id"])


def resolve_user_ids(user_refs) -> list:
    """Resolve a list of user references (see resolve_user_id)."""
    if isinstance(user_refs, str):
        user_refs = [user_refs]
    return [resolve_user_id(u) for u in user_refs]


def resolve_reference_control_id(ref: str) -> str:
    """Resolve a reference control from a UUID, URN, ref_id or name.

    URN -> ?urn= lookup. Otherwise ?search= then an exact case-insensitive
    match on ref_id, then on name.
    """
    if _is_uuid(ref):
        return ref

    value = str(ref).strip()
    if value.lower().startswith("urn:"):
        controls, error = fetch_all_results(
            "/reference-controls/", params={"urn": value}
        )
        if error:
            raise ValueError(f"Reference control '{value}' API error: {error}")
        if not controls:
            raise ValueError(f"Reference control '{value}' not found")
        if len(controls) > 1:
            raise ValueError(
                f"Ambiguous reference control URN '{value}', found {len(controls)}"
            )
        return str(controls[0]["id"])

    controls, error = fetch_all_results(
        "/reference-controls/", params={"search": value}
    )
    if error:
        raise ValueError(f"Reference control '{value}' API error: {error}")
    controls = controls or []

    def _label(c):
        ref_id = c.get("ref_id") or ""
        return f"{ref_id} {c.get('name') or ''} ({c.get('urn') or c.get('id')})".strip()

    for field in ("ref_id", "name"):
        matches = [
            c
            for c in controls
            if str(c.get(field) or "").strip().lower() == value.lower()
        ]
        if len(matches) == 1:
            return str(matches[0]["id"])
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous reference control '{value}', {len(matches)} match on "
                f"{field}: {[_label(c) for c in matches[:5]]}. Use the URN or UUID"
            )

    if controls:
        raise ValueError(
            f"Reference control '{value}' not found as an exact ref_id or name. "
            f"Candidates: {[_label(c) for c in controls[:5]]}"
        )
    raise ValueError(f"Reference control '{value}' not found")


# Fixed letter aliases for the builtin qualifications
QUALIFICATION_LETTERS = {
    "C": "confidentiality",
    "I": "integrity",
    "A": "availability",
    "D": "availability",
    "T": "proof",
    "P": "proof",
}

# French labels of the builtin qualifications. Builtin terminologies carry no
# translations in the database (their labels live in the frontend).
_QUALIFICATION_ALIASES = {
    "confidentialité": "confidentiality",
    "confidentialite": "confidentiality",
    "intégrité": "integrity",
    "integrite": "integrity",
    "disponibilité": "availability",
    "disponibilite": "availability",
    "preuve": "proof",
    "traçabilité": "proof",
    "tracabilite": "proof",
}


def resolve_qualification_ids(qualifications) -> list:
    """Resolve qualification letters/names/UUIDs to Terminology ids.

    Letters: C=confidentiality, I=integrity, A/D=availability, T/P=proof.
    Names match the terminology name or any translation, case-insensitively.
    Never creates a terminology.
    """
    if isinstance(qualifications, str):
        qualifications = [qualifications]

    lookups = []
    for item in qualifications:
        value = str(item).strip()
        lookup = QUALIFICATION_LETTERS.get(value.upper()) if len(value) == 1 else None
        lookups.append(lookup or _QUALIFICATION_ALIASES.get(value.lower()) or item)
    return resolve_terminology_ids(lookups, "qualifications")


def _matrix_risk_levels(risk_matrix_id: str) -> list:
    res = make_get_request(f"/risk-matrices/{risk_matrix_id}/")
    if res.status_code != 200:
        raise ValueError(
            f"Risk matrix '{risk_matrix_id}' API error: {res.status_code} - {res.text}"
        )
    json_def = res.json().get("json_definition") or {}
    if isinstance(json_def, str):
        json_def = json.loads(json_def)
    return json_def.get("risk") or []


def resolve_risk_level_index(value, risk_matrix_id: str = None) -> int:
    """Resolve a risk level (e.g. a risk tolerance) to its matrix index.

    An int is returned as is (-1 = unset). A string is matched to the name or
    abbreviation of a risk level of the given matrix.
    """
    if isinstance(value, bool):
        raise ValueError(f"Invalid risk level '{value}'")
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("Risk level is empty")
    try:
        return int(text)
    except ValueError:
        pass

    if not risk_matrix_id:
        raise ValueError(
            f"Cannot resolve risk level '{text}' without a risk matrix; pass an index"
        )

    levels = _matrix_risk_levels(risk_matrix_id)
    for idx, level in enumerate(levels):
        # json_definition is localized: name/abbreviation are in the request
        # locale, the other locales stay in `translations`
        entries = [level]
        translations = level.get("translations")
        if isinstance(translations, dict):
            entries += [t for t in translations.values() if isinstance(t, dict)]
        candidates = {
            str(entry.get(key) or "").strip().lower()
            for entry in entries
            for key in ("name", "abbreviation")
        }
        candidates.discard("")
        if text.lower() in candidates:
            return idx

    labels = [
        f"{idx}={level.get('name')} ({level.get('abbreviation')})"
        for idx, level in enumerate(levels)
    ]
    raise ValueError(f"Risk level '{text}' not found. Valid levels: {labels}")


def resolve_terminology_ids(values, field_path: str) -> list:
    """Resolve terminology names/UUIDs of one field_path to Terminology ids.

    Matches every visible terminology of that field_path, builtin or custom,
    on its name, translated name or any translation (case- and
    plural-insensitive). UUIDs are passed through. Never creates a terminology.
    """
    if isinstance(values, str):
        values = [values]

    terminologies = None
    resolved = []
    for item in values:
        if _is_uuid(item):
            term_id = item
        else:
            value = str(item).strip()
            if not value:
                raise ValueError(f"Empty {field_path} value")
            if terminologies is None:
                terminologies, error = fetch_all_results(
                    "/terminologies/",
                    params={"field_path": field_path, "is_visible": "true"},
                    max_items=None,
                )
                if error:
                    raise ValueError(
                        f"Failed to fetch {field_path} terminologies: {error}"
                    )
                terminologies = terminologies or []

            match = next(
                (
                    t
                    for t in terminologies
                    if str(t.get("name") or "").lower() == value.lower()
                    or str(t.get("translated_name") or "").lower() == value.lower()
                ),
                None,
            ) or _find_terminology_match(terminologies, value)

            if not match:
                names = sorted(
                    {
                        str(t.get("translated_name") or t.get("name"))
                        for t in terminologies
                    }
                )
                raise ValueError(
                    f"'{value}' not found among visible {field_path} terminologies: "
                    f"{names}"
                )
            term_id = str(match["id"])
        if term_id not in resolved:
            resolved.append(term_id)
    return resolved


_DURATION_RE = re.compile(
    r"^(?:(?P<d>\d+)d)?(?:(?P<h>\d+)h)?(?:(?P<m>\d+)m)?(?:(?P<s>\d+)s)?$"
)
DURATION_FORMATS = (
    "an integer number of seconds, or a written duration made of "
    "<n>d, <n>h, <n>m, <n>s in that order (e.g. '90s', '30m', '2h', '1d', '1h30m')"
)


def parse_duration(value) -> int:
    """Parse a duration into seconds.

    Accepts a non-negative int (seconds, unchanged), a digit-only string, or a
    written duration such as "90s", "30m", "2h", "1d", "1h30m". Anything else
    raises ValueError naming the accepted formats.
    """
    if isinstance(value, bool):
        raise ValueError(f"Invalid duration {value!r}: expected {DURATION_FORMATS}")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"Invalid duration {value!r}: expected {DURATION_FORMATS}")
        return value
    if isinstance(value, str):
        # "1h 30m" == "1h30m"; "2 hours" still fails the pattern
        text = re.sub(r"\s+", "", value).lower()
        if text.isdigit():
            return int(text)
        match = _DURATION_RE.match(text)
        if text and match:
            parts = match.groupdict()
            return (
                int(parts["d"] or 0) * 86400
                + int(parts["h"] or 0) * 3600
                + int(parts["m"] or 0) * 60
                + int(parts["s"] or 0)
            )
    raise ValueError(f"Invalid duration {value!r}: expected {DURATION_FORMATS}")
