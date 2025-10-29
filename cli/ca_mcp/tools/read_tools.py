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
