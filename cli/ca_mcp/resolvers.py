"""Helper functions to resolve names to UUIDs"""

from .client import make_get_request, get_paginated_results


def resolve_folder_id(folder_name_or_id: str) -> str:
    """Helper function to resolve folder name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    Returns the UUID string or raises ValueError with a clear message.
    """
    # Check if it's already a UUID (contains hyphens in UUID format)
    if "-" in folder_name_or_id and len(folder_name_or_id) == 36:
        return folder_name_or_id

    # Otherwise, look up by name - return exactly one result
    res = make_get_request("/folders/", params={"name": folder_name_or_id})

    if res.status_code != 200:
        raise ValueError(f"Folder '{folder_name_or_id}' API error {res.status_code}")

    data = res.json()
    folders = get_paginated_results(data)

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
    res = make_get_request("/perimeters/", params={"name": perimeter_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Perimeter '{perimeter_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    perimeters = get_paginated_results(data)

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
    res = make_get_request("/risk-matrices/", params={"name": matrix_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Risk matrix '{matrix_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    matrices = get_paginated_results(data)

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
        res = make_get_request(
            "/frameworks/", params={"urn": framework_name_or_urn_or_id}
        )
    else:
        # Search by name
        res = make_get_request(
            "/frameworks/", params={"name": framework_name_or_urn_or_id}
        )

    if res.status_code != 200:
        raise ValueError(
            f"Framework '{framework_name_or_urn_or_id}' API error {res.status_code}"
        )

    data = res.json()
    frameworks = get_paginated_results(data)

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
    res = make_get_request("/risk-assessments/", params={"name": assessment_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Risk assessment '{assessment_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    assessments = get_paginated_results(data)

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

    res = make_get_request("/assets/", params=params)

    if res.status_code != 200:
        raise ValueError(f"Asset '{asset_name_or_id}' API error {res.status_code}")

    data = res.json()
    assets = get_paginated_results(data)

    if not assets:
        raise ValueError(f"Asset '{asset_name_or_id}' not found")

    if len(assets) > 1:
        raise ValueError(
            f"Ambiguous asset name '{asset_name_or_id}', found {len(assets)}"
        )

    return assets[0]["id"]


def resolve_risk_scenario_id(scenario_name_or_id: str) -> str:
    """Helper function to resolve risk scenario name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in scenario_name_or_id and len(scenario_name_or_id) == 36:
        return scenario_name_or_id

    # Otherwise, look up by name
    res = make_get_request("/risk-scenarios/", params={"name": scenario_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Risk scenario '{scenario_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    scenarios = get_paginated_results(data)

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

    res = make_get_request("/applied-controls/", params=params)

    if res.status_code != 200:
        raise ValueError(
            f"Applied control '{control_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    controls = get_paginated_results(data)

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
    res = make_get_request(
        "/compliance-assessments/", params={"name": assessment_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Compliance assessment '{assessment_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    assessments = get_paginated_results(data)

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
    res = make_get_request(endpoint, params={"name": name_or_id})

    if res.status_code != 200:
        raise ValueError(f"'{name_or_id}' at {endpoint} API error {res.status_code}")

    data = res.json()
    results = get_paginated_results(data)

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

    res = make_get_request("/threats/", params=params)

    if res.status_code != 200:
        raise ValueError(f"Threat '{threat_name_or_id}' API error {res.status_code}")

    data = res.json()
    threats = get_paginated_results(data)

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

    res = make_get_request("/loaded-libraries/", params={"urn": library_urn_or_id})

    if res.status_code != 200:
        raise ValueError(f"Library '{library_urn_or_id}' API error {res.status_code}")

    data = res.json()
    libraries = get_paginated_results(data)

    if not libraries or len(libraries) == 0:
        raise ValueError(f"Library '{library_urn_or_id}' not found or not loaded")

    if len(libraries) > 1:
        library_names = [lib["name"] for lib in libraries[:3]]
        raise ValueError(
            f"Ambiguous library URN '{library_urn_or_id}', found {len(libraries)}: {library_names}"
        )

    return str(libraries[0]["id"])


def resolve_task_template_id(task_name_or_id: str) -> str:
    """Helper function to resolve task template name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in task_name_or_id and len(task_name_or_id) == 36:
        return task_name_or_id

    # Otherwise, look up by name
    res = make_get_request("/task-templates/", params={"name": task_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Task template '{task_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    tasks = get_paginated_results(data)

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

    res = make_get_request("/entities/", params={"name": entity_name_or_id})

    if res.status_code != 200:
        raise ValueError(f"Entity '{entity_name_or_id}' API error {res.status_code}")

    data = res.json()
    entities = get_paginated_results(data)

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

    res = make_get_request("/solutions/", params={"name": solution_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Solution '{solution_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    solutions = get_paginated_results(data)

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

    res = make_get_request("/contracts/", params={"name": contract_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Contract '{contract_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    contracts = get_paginated_results(data)

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

    res = make_get_request(
        "/entity-assessments/", params={"name": assessment_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Entity assessment '{assessment_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    assessments = get_paginated_results(data)

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
    res = make_get_request(
        "/representatives/", params={"search": representative_email_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Representative '{representative_email_or_id}' API error {res.status_code}"
        )

    data = res.json()
    representatives = get_paginated_results(data)

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

    res = make_get_request("/ebios-rm/studies/", params={"name": study_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"EBIOS RM Study '{study_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    studies = get_paginated_results(data)

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

    res = make_get_request(
        "/ebios-rm/feared-events/", params={"name": feared_event_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Feared event '{feared_event_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    feared_events = get_paginated_results(data)

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

    res = make_get_request(
        "/ebios-rm/strategic-scenarios/", params={"name": scenario_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Strategic scenario '{scenario_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    scenarios = get_paginated_results(data)

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

    res = make_get_request(
        "/ebios-rm/attack-paths/", params={"name": attack_path_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Attack path '{attack_path_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    attack_paths = get_paginated_results(data)

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

    res = make_get_request(
        "/ebios-rm/elementary-actions/", params={"name": action_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Elementary action '{action_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    actions = get_paginated_results(data)

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

    res = make_get_request(
        "/ebios-rm/operating-modes/", params={"name": mode_name_or_id}
    )

    if res.status_code != 200:
        raise ValueError(
            f"Operating mode '{mode_name_or_id}' API error {res.status_code}"
        )

    data = res.json()
    modes = get_paginated_results(data)

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
