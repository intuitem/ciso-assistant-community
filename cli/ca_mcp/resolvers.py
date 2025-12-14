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


def resolve_asset_id(asset_name_or_id: str) -> str:
    """Helper function to resolve asset name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in asset_name_or_id and len(asset_name_or_id) == 36:
        return asset_name_or_id

    # Otherwise, look up by name
    res = make_get_request("/assets/", params={"name": asset_name_or_id})

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


def resolve_applied_control_id(control_name_or_id: str) -> str:
    """Helper function to resolve applied control name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in control_name_or_id and len(control_name_or_id) == 36:
        return control_name_or_id

    # Otherwise, look up by name
    res = make_get_request("/applied-controls/", params={"name": control_name_or_id})

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
