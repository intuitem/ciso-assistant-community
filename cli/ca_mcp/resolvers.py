"""Helper functions to resolve names to UUIDs"""

from .client import make_get_request, get_paginated_results


def resolve_folder_id(folder_name_or_id: str) -> str:
    """Helper function to resolve folder name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID (contains hyphens in UUID format)
    if "-" in folder_name_or_id and len(folder_name_or_id) == 36:
        return folder_name_or_id

    # Otherwise, look up by name
    res = make_get_request("/folders/", params={"name": folder_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up folder '{folder_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    folders = get_paginated_results(data)

    if not folders:
        raise ValueError(f"Folder '{folder_name_or_id}' not found")

    if len(folders) > 1:
        raise ValueError(
            f"Multiple folders found with name '{folder_name_or_id}'. Please use UUID instead."
        )

    return folders[0]["id"]


def resolve_perimeter_id(perimeter_name_or_id: str) -> str:
    """Helper function to resolve perimeter name to UUID
    If already a UUID, returns it. If a name, looks it up via API.
    """
    # Check if it's already a UUID
    if "-" in perimeter_name_or_id and len(perimeter_name_or_id) == 36:
        return perimeter_name_or_id

    # Otherwise, look up by name
    res = make_get_request("/perimeters/", params={"name": perimeter_name_or_id})

    if res.status_code != 200:
        raise ValueError(
            f"Failed to look up perimeter '{perimeter_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    perimeters = get_paginated_results(data)

    if not perimeters:
        raise ValueError(f"Perimeter '{perimeter_name_or_id}' not found")

    if len(perimeters) > 1:
        raise ValueError(
            f"Multiple perimeters found with name '{perimeter_name_or_id}'. Please use UUID instead."
        )

    return perimeters[0]["id"]


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
            f"Failed to look up risk matrix '{matrix_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    matrices = get_paginated_results(data)

    if not matrices:
        raise ValueError(f"Risk matrix '{matrix_name_or_id}' not found")

    if len(matrices) > 1:
        raise ValueError(
            f"Multiple risk matrices found with name '{matrix_name_or_id}'. Please use UUID instead."
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
            f"Failed to look up framework '{framework_name_or_urn_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    frameworks = get_paginated_results(data)

    if not frameworks:
        raise ValueError(f"Framework '{framework_name_or_urn_or_id}' not found")

    if len(frameworks) > 1:
        raise ValueError(
            f"Multiple frameworks found with name '{framework_name_or_urn_or_id}'. Please use UUID or URN instead."
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
            f"Failed to look up risk assessment '{assessment_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    assessments = get_paginated_results(data)

    if not assessments:
        raise ValueError(f"Risk assessment '{assessment_name_or_id}' not found")

    if len(assessments) > 1:
        raise ValueError(
            f"Multiple risk assessments found with name '{assessment_name_or_id}'. Please use UUID instead."
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
        raise ValueError(
            f"Failed to look up asset '{asset_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    assets = get_paginated_results(data)

    if not assets:
        raise ValueError(f"Asset '{asset_name_or_id}' not found")

    if len(assets) > 1:
        raise ValueError(
            f"Multiple assets found with name '{asset_name_or_id}'. Please use UUID instead."
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
            f"Failed to look up risk scenario '{scenario_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    scenarios = get_paginated_results(data)

    if not scenarios:
        raise ValueError(f"Risk scenario '{scenario_name_or_id}' not found")

    if len(scenarios) > 1:
        raise ValueError(
            f"Multiple risk scenarios found with name '{scenario_name_or_id}'. Please use UUID instead."
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
            f"Failed to look up applied control '{control_name_or_id}': HTTP {res.status_code}"
        )

    data = res.json()
    controls = get_paginated_results(data)

    if not controls:
        raise ValueError(f"Applied control '{control_name_or_id}' not found")

    if len(controls) > 1:
        raise ValueError(
            f"Multiple applied controls found with name '{control_name_or_id}'. Please use UUID instead."
        )

    return controls[0]["id"]


def resolve_requirement_assessment_id(requirement_assessment_id: str) -> str:
    """Helper function to validate requirement assessment UUID
    Requirement assessments don't have names, only UUIDs.
    Use get_audit_gap_analysis() to find requirement assessment IDs.
    """
    # Check if it's a UUID
    if "-" in requirement_assessment_id and len(requirement_assessment_id) == 36:
        return requirement_assessment_id

    raise ValueError(
        f"Requirement assessments can only be identified by UUID. "
        f"Use get_audit_gap_analysis() to find requirement assessment IDs. "
        f"Provided value '{requirement_assessment_id}' is not a valid UUID."
    )
