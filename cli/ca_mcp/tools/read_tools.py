"""Read-only MCP tools for querying CISO Assistant data"""

import sys
from rich import print as rprint
from ..client import make_get_request, get_paginated_results


async def get_risk_scenarios():
    """Get risks scenarios
    Query CISO Assistant Risk Registry
    """
    res = make_get_request("/risk-scenarios/")
    data = res.json()
    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No risk scenarios found", file=sys.stderr)
        return
    scenarios = [
        f"|{rs.get('name')}|{rs.get('description') or ''}|{rs.get('current_level')}|{rs.get('residual_level')}|{(rs.get('folder') or {}).get('str', 'N/A')}|"
        for rs in data["results"]
    ]
    return (
        "|name|description|current_level|residual_level|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(scenarios)
    )


async def get_applied_controls():
    """Get applied controls
    Query CISO Assistant combined action plan
    """
    res = make_get_request("/applied-controls/")
    data = res.json()
    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No applied controls found", file=sys.stderr)
        return
    items = [
        f"|{item.get('name')}|{item.get('description') or ''}|{item.get('status')}|{item.get('eta') or ''}|{(item.get('folder') or {}).get('str', 'N/A')}|"
        for item in data["results"]
    ]
    return (
        "|name|description|status|eta|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(items)
    )


async def get_audits_progress():
    """Get the audits progress
    Query CISO Assistant compliance engine for audits progress
    """
    res = make_get_request("/compliance-assessments/")
    data = res.json()
    if res.status_code != 200:
        rprint(f"Error: check credentials or filename.", file=sys.stderr)
        return
    if not data["results"]:
        rprint(f"Error: No audits found", file=sys.stderr)
        return
    items = [
        f"|{item.get('name')}|{(item.get('framework') or {}).get('str', 'N/A')}|{item.get('status')}|{item.get('progress')}|{(item.get('folder') or {}).get('str', 'N/A')}|"
        for item in data["results"]
    ]
    return (
        "|name|framework|status|progress|domain|"
        + "\n|---|---|---|---|---|\n"
        + "\n".join(items)
    )


async def get_folders():
    """Get all folders (domains) in CISO Assistant
    Returns a list of folders with their IDs and names for reference when creating objects
    """
    try:
        res = make_get_request("/folders/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        folders = get_paginated_results(data)

        if not folders:
            return "No folders found"

        result = "# Folders (Domains)\n\n"
        result += "|ID|Name|Description|Parent Folder|\n"
        result += "|---|---|---|---|\n"

        for folder in folders:
            folder_id = folder.get("id", "N/A")
            name = folder.get("name", "N/A")
            description = (folder.get("description") or "")[
                :50
            ]  # Truncate long descriptions
            parent = folder.get("parent_folder") or {}
            parent_name = parent.get("str", "Root") if parent else "Root"

            result += f"|{folder_id}|{name}|{description}|{parent_name}|\n"

        return result
    except Exception as e:
        return f"Error in get_folders: {str(e)}"


async def get_perimeters():
    """Get all perimeters in CISO Assistant
    Returns a list of perimeters with their IDs and names for reference when creating assessments
    """
    try:
        res = make_get_request("/perimeters/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        perimeters = get_paginated_results(data)

        if not perimeters:
            return "No perimeters found"

        result = "# Perimeters\n\n"
        result += "|ID|Name|Description|Folder|\n"
        result += "|---|---|---|---|\n"

        for perimeter in perimeters:
            perimeter_id = perimeter.get("id", "N/A")
            name = perimeter.get("name", "N/A")
            description = (perimeter.get("description") or "")[:50]
            folder = (perimeter.get("folder") or {}).get("str", "N/A")

            result += f"|{perimeter_id}|{name}|{description}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_perimeters: {str(e)}"


async def get_risk_matrices():
    """Get all risk matrices in CISO Assistant
    Returns a list of risk matrices with their IDs and names for reference when creating risk assessments
    """
    try:
        res = make_get_request("/risk-matrices/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        matrices = get_paginated_results(data)

        if not matrices:
            return "No risk matrices found"

        result = "# Risk Matrices\n\n"
        result += "|ID|Name|Description|Folder|\n"
        result += "|---|---|---|---|\n"

        for matrix in matrices:
            matrix_id = matrix.get("id", "N/A")
            name = matrix.get("name", "N/A")
            description = (matrix.get("description") or "")[:50]
            folder = (matrix.get("folder") or {}).get("str", "N/A")

            result += f"|{matrix_id}|{name}|{description}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_risk_matrices: {str(e)}"


async def get_risk_matrix_details(matrix_id_or_name: str):
    """Get detailed information about a specific risk matrix including probability and impact scales

    Args:
        matrix_id_or_name: ID or name of the risk matrix

    Returns detailed matrix information including:
    - Probability scale with indices and values
    - Impact scale with indices and values
    - Risk level grid

    Use this to determine valid values for inherent_proba, current_proba, etc. when updating risk scenarios
    """
    try:
        from ..resolvers import resolve_risk_matrix_id

        # Resolve matrix name to ID if needed
        matrix_id = resolve_risk_matrix_id(matrix_id_or_name)

        res = make_get_request(f"/risk-matrices/{matrix_id}/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        matrix = res.json()

        result = f"# Risk Matrix: {matrix.get('name', 'N/A')}\n\n"
        result += f"**ID:** {matrix.get('id', 'N/A')}\n"
        result += f"**Description:** {matrix.get('description', 'N/A')}\n\n"

        # Extract JSON definition
        json_def = matrix.get("json_definition", {})

        # Probability scale
        if "probability" in json_def:
            prob = json_def["probability"]
            result += "## Probability Scale\n\n"
            result += "|Index|Abbreviation|Name|Description|\n"
            result += "|---|---|---|---|\n"
            for idx, prob_item in enumerate(prob):
                abbr = prob_item.get("abbreviation", "N/A")
                name = prob_item.get("name", "N/A")
                desc = prob_item.get("description", "")
                result += f"|{idx}|{abbr}|{name}|{desc}|\n"
            result += "\n"

        # Impact scale
        if "impact" in json_def:
            impact = json_def["impact"]
            result += "## Impact Scale\n\n"
            result += "|Index|Abbreviation|Name|Description|\n"
            result += "|---|---|---|---|\n"
            for idx, impact_item in enumerate(impact):
                abbr = impact_item.get("abbreviation", "N/A")
                name = impact_item.get("name", "N/A")
                desc = impact_item.get("description", "")
                result += f"|{idx}|{abbr}|{name}|{desc}|\n"
            result += "\n"

        # Risk levels grid
        if "risk" in json_def:
            risk_levels = json_def["risk"]
            result += "## Risk Levels\n\n"
            result += "|Index|Abbreviation|Name|Description|Hexcolor|\n"
            result += "|---|---|---|---|---|\n"
            for idx, risk_item in enumerate(risk_levels):
                abbr = risk_item.get("abbreviation", "N/A")
                name = risk_item.get("name", "N/A")
                desc = risk_item.get("description", "")
                color = risk_item.get("hexcolor", "N/A")
                result += f"|{idx}|{abbr}|{name}|{desc}|{color}|\n"
            result += "\n"

        # Grid (matrix of probability x impact = risk level)
        if "grid" in json_def:
            grid = json_def["grid"]
            result += "## Risk Assessment Grid\n\n"
            result += "Grid shows risk level index for each probability/impact combination:\n\n"

            # Build grid table
            prob_count = len(json_def.get("probability", []))
            impact_count = len(json_def.get("impact", []))

            # Header row
            result += "| P\\I |"
            for i in range(impact_count):
                result += f" {i} |"
            result += "\n"

            # Separator
            result += "|---|"
            for _ in range(impact_count):
                result += "---|"
            result += "\n"

            # Data rows
            for p_idx in range(prob_count):
                result += f"| {p_idx} |"
                for i_idx in range(impact_count):
                    if p_idx < len(grid) and i_idx < len(grid[p_idx]):
                        result += f" {grid[p_idx][i_idx]} |"
                    else:
                        result += " - |"
                result += "\n"
            result += "\n"

        result += "**Usage:** When updating risk scenarios, use the index values from the Probability and Impact scales.\n"
        result += "Example: `current_proba=2` sets probability to index 2, `current_impact=3` sets impact to index 3.\n"

        return result
    except Exception as e:
        return f"Error in get_risk_matrix_details: {str(e)}"


async def get_risk_assessments():
    """Get all risk assessments in CISO Assistant
    Returns a list of risk assessments with their IDs, names, and status
    Use this to find the risk_assessment_id when creating risk scenarios
    """
    try:
        res = make_get_request("/risk-assessments/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        assessments = get_paginated_results(data)

        if not assessments:
            return "No risk assessments found"

        result = "# Risk Assessments\n\n"
        result += "|ID|Name|Status|Risk Matrix|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for assessment in assessments:
            assessment_id = assessment.get("id", "N/A")
            name = assessment.get("name", "N/A")
            status = assessment.get("status", "N/A")
            risk_matrix = (assessment.get("risk_matrix") or {}).get("str", "N/A")
            folder = (assessment.get("folder") or {}).get("str", "N/A")

            result += f"|{assessment_id}|{name}|{status}|{risk_matrix}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_risk_assessments: {str(e)}"


async def get_threats():
    """Get all threats in CISO Assistant
    Returns a list of threats with their IDs, names, providers, and descriptions
    """
    try:
        res = make_get_request("/threats/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        threats = get_paginated_results(data)

        if not threats:
            return "No threats found"

        result = "# Threats\n\n"
        result += f"Total: {len(threats)}\n\n"
        result += "|ID|Name|Provider|Description|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for threat in threats:
            threat_id = threat.get("id", "N/A")
            name = threat.get("name", "N/A")
            provider = threat.get("provider", "N/A")
            description = threat.get("description") or ""
            folder = (threat.get("folder") or {}).get("str", "N/A")

            result += f"|{threat_id}|{name}|{provider}|{description}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_threats: {str(e)}"


async def get_assets():
    """Get all assets in CISO Assistant
    Returns a list of assets with their IDs, names, types, and other details
    """
    try:
        res = make_get_request("/assets/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        assets = get_paginated_results(data)

        if not assets:
            return "No assets found"

        result = "# Assets\n\n"
        result += "|ID|Name|Type|Business Value|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for asset in assets:
            asset_id = asset.get("id", "N/A")
            name = asset.get("name", "N/A")
            asset_type = asset.get("type", "N/A")
            business_value = asset.get("business_value", "N/A")
            folder = (asset.get("folder") or {}).get("str", "N/A")

            result += f"|{asset_id}|{name}|{asset_type}|{business_value}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_assets: {str(e)}"


async def get_incidents():
    """Get all incidents in CISO Assistant
    Returns a list of incidents with their IDs, names, severity, and status
    """
    try:
        res = make_get_request("/incidents/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        incidents = get_paginated_results(data)

        if not incidents:
            return "No incidents found"

        result = "# Incidents\n\n"
        result += "|ID|Name|Severity|Status|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for incident in incidents:
            incident_id = incident.get("id", "N/A")
            name = incident.get("name", "N/A")
            severity = incident.get("severity", "N/A")
            status = incident.get("status", "N/A")
            folder = (incident.get("folder") or {}).get("str", "N/A")

            result += f"|{incident_id}|{name}|{severity}|{status}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_incidents: {str(e)}"


async def get_security_exceptions():
    """Get all security exceptions in CISO Assistant
    Returns a list of security exceptions with their IDs, names, approval status, and expiry dates
    """
    try:
        res = make_get_request("/security-exceptions/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        exceptions = get_paginated_results(data)

        if not exceptions:
            return "No security exceptions found"

        result = "# Security Exceptions\n\n"
        result += "|ID|Name|State|Expiry Date|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for exception in exceptions:
            exception_id = exception.get("id", "N/A")
            name = exception.get("name", "N/A")
            state = exception.get("state", "N/A")
            expiry_date = exception.get("expiry_date") or "N/A"
            folder = (exception.get("folder") or {}).get("str", "N/A")

            result += f"|{exception_id}|{name}|{state}|{expiry_date}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_security_exceptions: {str(e)}"


async def get_frameworks():
    """Get all frameworks available in CISO Assistant

    Returns a list of frameworks that have been imported/loaded and are available for creating compliance assessments.
    Use this to find framework IDs/URNs/names for creating audits.
    """
    try:
        res = make_get_request("/frameworks/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        frameworks = get_paginated_results(data)

        if not frameworks:
            return "No frameworks found"

        result = "# Frameworks\n\n"
        result += f"Total: {len(frameworks)}\n\n"
        result += "|ID|URN|Name|Description|Provider|Folder|\n"
        result += "|---|---|---|---|---|---|\n"

        for framework in frameworks:
            framework_id = framework.get("id", "N/A")
            urn = framework.get("urn", "N/A")
            name = framework.get("name", "N/A")
            description = framework.get("description") or ""
            provider = framework.get("provider", "N/A")
            folder = (framework.get("folder") or {}).get("str", "N/A")

            result += (
                f"|{framework_id}|{urn}|{name}|{description}|{provider}|{folder}|\n"
            )

        return result
    except Exception as e:
        return f"Error in get_frameworks: {str(e)}"


async def get_business_impact_analyses():
    """Get all Business Impact Analyses (BIAs) in CISO Assistant
    Returns a list of BIAs with their status and basic information
    """
    try:
        res = make_get_request("/resilience/business-impact-analysis/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        bias = get_paginated_results(data)

        if not bias:
            return "No Business Impact Analyses found"

        result = "# Business Impact Analyses\n\n"
        result += f"Total: {len(bias)}\n\n"
        result += "|ID|Name|Status|Version|Risk Matrix|Perimeter|Folder|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for bia in bias:
            bia_id = bia.get("id", "N/A")
            name = bia.get("name", "N/A")
            status = bia.get("status", "N/A")
            version = bia.get("version", "N/A")
            risk_matrix = (bia.get("risk_matrix") or {}).get("str", "N/A")
            perimeter = (bia.get("perimeter") or {}).get("str", "N/A")
            folder = (bia.get("folder") or {}).get("str", "N/A")

            result += f"|{bia_id}|{name}|{status}|{version}|{risk_matrix}|{perimeter}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_business_impact_analyses: {str(e)}"


async def get_requirement_assessments(
    compliance_assessment_id_or_name: str = None,
    ref_id: str = None,
):
    """Get requirement assessments (individual requirements within audits)

    Args:
        compliance_assessment_id_or_name: Optional ID or name of compliance assessment to filter by
        ref_id: Optional reference ID to filter by (e.g., "ISO 27001:2022 A.5.1")

    Returns a list of requirement assessments with their IDs, statuses, and results.
    Use the IDs to update specific requirements with update_requirement_assessment().
    """
    try:
        from ..resolvers import resolve_framework_id

        params = {}

        # If compliance assessment specified, resolve it
        if compliance_assessment_id_or_name:
            # Try to resolve as compliance assessment name/ID
            if (
                "-" in compliance_assessment_id_or_name
                and len(compliance_assessment_id_or_name) == 36
            ):
                params["compliance_assessment"] = compliance_assessment_id_or_name
            else:
                # Look up compliance assessment by name
                ca_res = make_get_request(
                    "/compliance-assessments/",
                    params={"name": compliance_assessment_id_or_name},
                )
                if ca_res.status_code == 200:
                    ca_data = ca_res.json()
                    ca_results = get_paginated_results(ca_data)
                    if ca_results:
                        params["compliance_assessment"] = ca_results[0]["id"]
                    else:
                        return f"Compliance assessment '{compliance_assessment_id_or_name}' not found"

        # Add ref_id filter if provided
        if ref_id:
            params["ref_id"] = ref_id

        res = make_get_request("/requirement-assessments/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        req_assessments = get_paginated_results(data)

        if not req_assessments:
            return "No requirement assessments found"

        result = "# Requirement Assessments\n\n"
        result += f"Total: {len(req_assessments)}\n\n"
        result += "|ID|Ref ID|Requirement|Compliance Assessment|Status|Result|Score|Observation|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for req in req_assessments:
            req_id = req.get("id", "N/A")
            req_ref_id = req.get("ref_id", "N/A")
            requirement = req.get("name", "N/A")
            comp_assessment = (req.get("compliance_assessment") or {}).get(
                "name", "N/A"
            )
            status = req.get("status", "N/A")
            result_val = req.get("result", "N/A")
            score = req.get("score", "N/A") if req.get("is_scored") else "N/A"
            observation = (req.get("observation") or "")[:50]  # Truncate

            result += f"|{req_id}|{req_ref_id}|{requirement}|{comp_assessment}|{status}|{result_val}|{score}|{observation}|\n"

        result += "\n**Use these IDs with update_requirement_assessment() to update individual requirements.**\n"

        return result
    except Exception as e:
        return f"Error in get_requirement_assessments: {str(e)}"
