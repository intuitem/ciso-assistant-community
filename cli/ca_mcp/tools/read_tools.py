"""Read-only MCP tools for querying CISO Assistant data"""

import json
import sys
from rich import print as rprint
from ..client import make_get_request, get_paginated_results


async def get_risk_scenarios(folder: str = None, risk_assessment: str = None):
    """Get risk scenarios

    Args:
        folder: Optional folder ID or name to filter by (filters by risk assessment's perimeter folder)
        risk_assessment: Optional risk assessment ID or name to filter by

    Query CISO Assistant Risk Registry
    """
    try:
        from ..resolvers import resolve_folder_id, resolve_risk_assessment_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        # Note: Risk scenarios filter by risk_assessment__perimeter__folder
        if folder:
            params["folder"] = resolve_folder_id(folder)

        # Add risk assessment filter if specified - resolve name to ID if needed
        if risk_assessment:
            params["risk_assessment"] = resolve_risk_assessment_id(risk_assessment)

        res = make_get_request("/risk-scenarios/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        scenarios = get_paginated_results(data)

        if not scenarios:
            return "No risk scenarios found"

        result = f"Found {len(scenarios)} risk scenarios"
        if folder:
            result += f" (folder: {folder})"
        if risk_assessment:
            result += f" (assessment: {risk_assessment})"
        result += "\n\n"
        result += "|Ref|Name|Current|Residual|Domain|\n"
        result += "|---|---|---|---|---|\n"

        for rs in scenarios:
            ref_id = rs.get("ref_id") or "N/A"
            name = rs.get("name", "N/A")
            current_level = rs.get("current_level", "N/A")
            residual_level = rs.get("residual_level", "N/A")
            domain = (rs.get("folder") or {}).get("str", "N/A")

            result += f"|{ref_id}|{name}|{current_level}|{residual_level}|{domain}|\n"

        return result
    except Exception as e:
        return f"Error in get_risk_scenarios: {str(e)}"


async def get_applied_controls(folder: str = None):
    """Get applied controls

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter applied controls)

    Query CISO Assistant combined action plan
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        res = make_get_request("/applied-controls/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        controls = get_paginated_results(data)

        if not controls:
            return "No applied controls found"

        result = f"Found {len(controls)} applied controls"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
        result += "|Ref|Name|Status|ETA|Domain|\n"
        result += "|---|---|---|---|---|\n"

        for item in controls:
            ref_id = item.get("ref_id") or "N/A"
            name = item.get("name", "N/A")
            status = item.get("status", "N/A")
            eta = item.get("eta") or "N/A"
            domain = (item.get("folder") or {}).get("str", "N/A")

            result += f"|{ref_id}|{name}|{status}|{eta}|{domain}|\n"

        return result
    except Exception as e:
        return f"Error in get_applied_controls: {str(e)}"


async def get_audits_progress(folder: str = None, perimeter: str = None):
    """Get the audits progress

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter audits)
        perimeter: Optional perimeter ID or name to filter by

    Query CISO Assistant compliance engine for audits progress
    """
    try:
        from ..resolvers import resolve_folder_id, resolve_perimeter_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        # Add perimeter filter if specified - resolve name to ID if needed
        if perimeter:
            params["perimeter"] = resolve_perimeter_id(perimeter)

        res = make_get_request("/compliance-assessments/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        audits = get_paginated_results(data)

        if not audits:
            return "No audits found"

        result = f"Found {len(audits)} audits"
        if folder:
            result += f" (folder: {folder})"
        if perimeter:
            result += f" (perimeter: {perimeter})"
        result += "\n\n"
        result += "|Name|Framework|Status|Progress|Domain|\n"
        result += "|---|---|---|---|---|\n"

        for item in audits:
            name = item.get("name", "N/A")
            framework = (item.get("framework") or {}).get("str", "N/A")
            status = item.get("status", "N/A")
            progress = item.get("progress", "N/A")
            domain = (item.get("folder") or {}).get("str", "N/A")

            result += f"|{name}|{framework}|{status}|{progress}|{domain}|\n"

        return result
    except Exception as e:
        return f"Error in get_audits_progress: {str(e)}"


async def get_folders(name: str = None):
    """Get folders (domains) in CISO Assistant

    Args:
        name: Optional name filter

    Folders (aka domains) are organizational units containing perimeters, assets, and risk assessments.
    """
    try:
        params = {}

        # Add name filter if specified
        if name:
            params["name"] = name

        res = make_get_request("/folders/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        folders = get_paginated_results(data)

        if not folders:
            if name:
                return f"No folders found matching '{name}'"
            return "No folders found"

        result = f"Found {len(folders)} folders"
        if name:
            result += f" (name: {name})"
        result += "\n\n"
        result += "|ID|Name|Parent|\n"
        result += "|---|---|---|\n"

        for folder in folders:
            folder_id = folder.get("id", "N/A")
            folder_name = folder.get("name", "N/A")
            parent = folder.get("parent_folder") or {}
            parent_name = parent.get("str", "Root") if parent else "Root"

            result += f"|{folder_id}|{folder_name}|{parent_name}|\n"

        return result
    except Exception as e:
        return f"Error in get_folders: {str(e)}"


async def get_perimeters(folder: str = None, name: str = None):
    """Get perimeters in CISO Assistant

    Args:
        folder: Optional folder ID or name filter
        name: Optional name filter

    Perimeters define the scope of risk assessments and audits within folders.
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        # Add name filter if specified
        if name:
            params["name"] = name

        res = make_get_request("/perimeters/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        perimeters = get_paginated_results(data)

        if not perimeters:
            return "No perimeters found"

        result = f"Found {len(perimeters)} perimeters"
        if folder:
            result += f" (folder: {folder})"
        if name:
            result += f" (name: {name})"
        result += "\n\n"
        result += "|ID|Name|Folder|\n"
        result += "|---|---|---|\n"

        for perimeter in perimeters:
            perimeter_id = perimeter.get("id", "N/A")
            perimeter_name = perimeter.get("name", "N/A")
            folder_name = (perimeter.get("folder") or {}).get("str", "N/A")

            result += f"|{perimeter_id}|{perimeter_name}|{folder_name}|\n"

        return result
    except Exception as e:
        return f"Error in get_perimeters: {str(e)}"


async def get_risk_matrices(folder: str = None):
    """Get all risk matrices in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter risk matrices)

    Returns a list of risk matrices with their IDs and names for reference when creating risk assessments
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        res = make_get_request("/risk-matrices/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        matrices = get_paginated_results(data)

        if not matrices:
            return "No risk matrices found"

        result = f"Found {len(matrices)} risk matrices"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
        result += "|ID|Name|\n"
        result += "|---|---|\n"

        for matrix in matrices:
            matrix_id = matrix.get("id", "N/A")
            name = matrix.get("name", "N/A")

            result += f"|{matrix_id}|{name}|\n"

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
        json_def_raw = matrix.get("json_definition", {})
        # Parse JSON string if needed (backend returns it as a string via get_json_translated)
        if isinstance(json_def_raw, str):
            json_def = json.loads(json_def_raw)
        else:
            json_def = json_def_raw

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


async def get_risk_assessments(folder: str = None, perimeter: str = None):
    """Get all risk assessments in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter risk assessments)
        perimeter: Optional perimeter ID or name to filter by

    Returns a list of risk assessments with their IDs, names, and status
    Use this to find the risk_assessment_id when creating risk scenarios
    """
    try:
        from ..resolvers import resolve_folder_id, resolve_perimeter_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        # Add perimeter filter if specified - resolve name to ID if needed
        if perimeter:
            params["perimeter"] = resolve_perimeter_id(perimeter)

        res = make_get_request("/risk-assessments/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        assessments = get_paginated_results(data)

        if not assessments:
            return "No risk assessments found"

        result = f"Found {len(assessments)} risk assessments"
        if folder:
            result += f" (folder: {folder})"
        if perimeter:
            result += f" (perimeter: {perimeter})"
        result += "\n\n"
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


async def get_threats(
    provider: str = None, folder: str = None, library: str = None, limit: int = 25
):
    """Get threats in CISO Assistant

    Args:
        provider: Optional provider name to filter by (e.g., "MITRE ATT&CK", "Custom")
        folder: Optional folder ID or name to filter by (domain/folder to filter threats)
        library: Optional library URN or ID to filter by (e.g., "urn:intuitem:risk:library:mitre-attack-enterprise-v15.1")
        limit: Maximum number of threats to return (default: 25, set to 0 for no limit)

    Returns a list of threats with their IDs, names, providers, and descriptions
    """
    try:
        from ..resolvers import resolve_folder_id, resolve_library_id

        params = {}

        # Add provider filter if specified
        if provider:
            params["provider"] = provider

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        # Add library filter if specified - resolve URN to ID if needed
        if library:
            params["library"] = resolve_library_id(library)

        res = make_get_request("/threats/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        threats = get_paginated_results(data)

        if not threats:
            return "No threats found"

        # Apply limit if specified (0 means no limit)
        total_count = len(threats)
        if limit > 0:
            threats = threats[:limit]

        result = f"Found {len(threats)} of {total_count} threats"
        if provider:
            result += f" (provider: {provider})"
        if folder:
            result += f" (folder: {folder})"
        if library:
            result += f" (library: {library})"
        result += "\n\n"
        result += "|ID|Name|Provider|\n"
        result += "|---|---|---|\n"

        for threat in threats:
            threat_id = threat.get("id", "N/A")
            name = threat.get("name", "N/A")
            provider_name = threat.get("provider", "N/A")

            result += f"|{threat_id}|{name}|{provider_name}|\n"

        return result
    except Exception as e:
        return f"Error in get_threats: {str(e)}"


async def get_assets(folder: str = None):
    """Get all assets in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter assets)

    Returns a list of assets with their IDs, names, types, and other details
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        res = make_get_request("/assets/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        assets = get_paginated_results(data)

        if not assets:
            return "No assets found"

        result = f"Found {len(assets)} assets"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
        result += "|ID|Name|Type|Folder|\n"
        result += "|---|---|---|---|\n"

        for asset in assets:
            asset_id = asset.get("id", "N/A")
            name = asset.get("name", "N/A")
            asset_type = asset.get("type", "N/A")
            folder_name = (asset.get("folder") or {}).get("str", "N/A")

            result += f"|{asset_id}|{name}|{asset_type}|{folder_name}|\n"

        return result
    except Exception as e:
        return f"Error in get_assets: {str(e)}"


async def get_incidents(folder: str = None):
    """Get all incidents in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter incidents)

    Returns a list of incidents with their IDs, names, severity, and status
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        res = make_get_request("/incidents/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        incidents = get_paginated_results(data)

        if not incidents:
            return "No incidents found"

        result = f"Found {len(incidents)} incidents"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
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


async def get_security_exceptions(folder: str = None):
    """Get all security exceptions in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter security exceptions)

    Returns a list of security exceptions with their IDs, names, approval status, and expiry dates
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        res = make_get_request("/security-exceptions/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        exceptions = get_paginated_results(data)

        if not exceptions:
            return "No security exceptions found"

        result = f"Found {len(exceptions)} security exceptions"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
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


async def get_frameworks(folder: str = None):
    """Get all frameworks available in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter frameworks)

    Returns a list of frameworks that have been imported/loaded and are available for creating compliance assessments.
    Use this to find framework IDs/URNs/names for creating audits.
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)

        res = make_get_request("/frameworks/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        frameworks = get_paginated_results(data)

        if not frameworks:
            return "No frameworks found"

        result = f"Found {len(frameworks)} frameworks"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
        result += "|ID|URN|Name|Provider|Folder|\n"
        result += "|---|---|---|---|---|\n"

        for framework in frameworks:
            framework_id = framework.get("id", "N/A")
            urn = framework.get("urn", "N/A")
            name = framework.get("name", "N/A")
            provider = framework.get("provider", "N/A")
            folder = (framework.get("folder") or {}).get("str", "N/A")

            result += f"|{framework_id}|{urn}|{name}|{provider}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_frameworks: {str(e)}"


async def get_business_impact_analyses(folder: str = None):
    """Get all Business Impact Analyses (BIAs) in CISO Assistant

    Args:
        folder: Optional folder ID or name to filter by (domain/folder to filter BIAs by their perimeter's folder)

    Returns a list of BIAs with their status and basic information
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}

        # Add folder filter if specified - resolve name to ID if needed
        # Note: BIA filters by perimeter__folder, not folder directly
        if folder:
            params["perimeter__folder"] = resolve_folder_id(folder)

        res = make_get_request("/resilience/business-impact-analysis/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        bias = get_paginated_results(data)

        if not bias:
            return "No Business Impact Analyses found"

        result = f"Found {len(bias)} Business Impact Analyses"
        if folder:
            result += f" (folder: {folder})"
        result += "\n\n"
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

        result = f"Found {len(req_assessments)} requirement assessments\n\n"
        result += "|ID|Ref|Requirement|Assessment|Status|Result|\n"
        result += "|---|---|---|---|---|---|\n"

        for req in req_assessments:
            req_id = req.get("id", "N/A")
            req_ref_id = req.get("ref_id", "N/A")
            requirement = req.get("name", "N/A")[:30]  # Truncate
            comp_assessment = (req.get("compliance_assessment") or {}).get(
                "name", "N/A"
            )[:20]
            status = req.get("status", "N/A")
            result_val = req.get("result", "N/A")

            result += f"|{req_id}|{req_ref_id}|{requirement}|{comp_assessment}|{status}|{result_val}|\n"

        return result
    except Exception as e:
        return f"Error in get_requirement_assessments: {str(e)}"


async def get_quantitative_risk_studies():
    """Get all quantitative risk studies in CISO Assistant
    Returns a list of quantitative risk studies with their IDs, names, status, and basic information
    """
    try:
        res = make_get_request("/crq/quantitative-risk-studies/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        studies = get_paginated_results(data)

        if not studies:
            return "No quantitative risk studies found"

        result = f"Found {len(studies)} quantitative risk studies\n\n"
        result += "|ID|Name|Status|Distribution Model|Loss Threshold|Folder|\n"
        result += "|---|---|---|---|---|---|\n"

        for study in studies:
            study_id = study.get("id", "N/A")
            name = study.get("name", "N/A")
            status = study.get("status", "N/A")
            distribution_model = study.get("distribution_model", "N/A")
            loss_threshold = study.get("loss_threshold_display", "N/A")
            folder = (study.get("folder") or {}).get("str", "N/A")

            result += f"|{study_id}|{name}|{status}|{distribution_model}|{loss_threshold}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_quantitative_risk_studies: {str(e)}"


async def get_quantitative_risk_scenarios(study_id_or_name: str = None):
    """Get quantitative risk scenarios in CISO Assistant

    Args:
        study_id_or_name: Optional ID or name of quantitative risk study to filter by

    Returns a list of quantitative risk scenarios with their IDs, names, status, and ALE information
    """
    try:
        params = {}

        # If study specified, resolve it
        if study_id_or_name:
            if "-" in study_id_or_name and len(study_id_or_name) == 36:
                params["quantitative_risk_study"] = study_id_or_name
            else:
                # Look up study by name
                study_res = make_get_request(
                    "/crq/quantitative-risk-studies/",
                    params={"name": study_id_or_name},
                )
                if study_res.status_code == 200:
                    study_data = study_res.json()
                    study_results = get_paginated_results(study_data)
                    if study_results:
                        params["quantitative_risk_study"] = study_results[0]["id"]
                    else:
                        return f"Quantitative risk study '{study_id_or_name}' not found"

        res = make_get_request("/crq/quantitative-risk-scenarios/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        scenarios = get_paginated_results(data)

        if not scenarios:
            return "No quantitative risk scenarios found"

        result = f"Found {len(scenarios)} quantitative risk scenarios\n\n"
        result += (
            "|ID|Ref|Name|Status|Priority|Current ALE|Residual ALE|Study|Folder|\n"
        )
        result += "|---|---|---|---|---|---|---|---|---|\n"

        for scenario in scenarios:
            scenario_id = scenario.get("id", "N/A")
            ref_id = scenario.get("ref_id", "N/A")
            name = scenario.get("name", "N/A")
            status = scenario.get("status", "N/A")
            priority = scenario.get("priority", "N/A")
            current_ale = scenario.get("current_ale_display", "N/A")
            residual_ale = scenario.get("residual_ale_display", "N/A")
            study = (scenario.get("quantitative_risk_study") or {}).get("name", "N/A")
            folder = (scenario.get("folder") or {}).get("str", "N/A")

            result += f"|{scenario_id}|{ref_id}|{name}|{status}|{priority}|{current_ale}|{residual_ale}|{study}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_quantitative_risk_scenarios: {str(e)}"


async def get_quantitative_risk_hypotheses(scenario_id_or_name: str = None):
    """Get quantitative risk hypotheses in CISO Assistant

    Args:
        scenario_id_or_name: Optional ID or name of quantitative risk scenario to filter by

    Returns a list of quantitative risk hypotheses with their IDs, names, risk stage, and metrics
    """
    try:
        params = {}

        # If scenario specified, resolve it
        if scenario_id_or_name:
            if "-" in scenario_id_or_name and len(scenario_id_or_name) == 36:
                params["quantitative_risk_scenario"] = scenario_id_or_name
            else:
                # Look up scenario by name
                scenario_res = make_get_request(
                    "/crq/quantitative-risk-scenarios/",
                    params={"name": scenario_id_or_name},
                )
                if scenario_res.status_code == 200:
                    scenario_data = scenario_res.json()
                    scenario_results = get_paginated_results(scenario_data)
                    if scenario_results:
                        params["quantitative_risk_scenario"] = scenario_results[0]["id"]
                    else:
                        return f"Quantitative risk scenario '{scenario_id_or_name}' not found"

        res = make_get_request("/crq/quantitative-risk-hypotheses/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        hypotheses = get_paginated_results(data)

        if not hypotheses:
            return "No quantitative risk hypotheses found"

        result = f"Found {len(hypotheses)} quantitative risk hypotheses\n\n"
        result += "|ID|Ref|Name|Risk Stage|Selected|ALE|ROC|Fresh|Scenario|Folder|\n"
        result += "|---|---|---|---|---|---|---|---|---|---|\n"

        for hyp in hypotheses:
            hyp_id = hyp.get("id", "N/A")
            ref_id = hyp.get("ref_id", "N/A")
            name = hyp.get("name", "N/A")
            risk_stage = hyp.get("risk_stage", "N/A")
            is_selected = "Yes" if hyp.get("is_selected") else "No"
            ale = hyp.get("ale_display", "N/A")
            roc = hyp.get("roc_display", "N/A")
            is_fresh = "Yes" if hyp.get("is_simulation_fresh") else "No"
            scenario = (hyp.get("quantitative_risk_scenario") or {}).get("name", "N/A")
            folder = (hyp.get("folder") or {}).get("str", "N/A")

            result += f"|{hyp_id}|{ref_id}|{name}|{risk_stage}|{is_selected}|{ale}|{roc}|{is_fresh}|{scenario}|{folder}|\n"

        return result
    except Exception as e:
        return f"Error in get_quantitative_risk_hypotheses: {str(e)}"
