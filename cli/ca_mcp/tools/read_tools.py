"""Read-only MCP tools for querying CISO Assistant data"""

import json
import sys
from rich import print as rprint
from ..client import make_get_request, get_paginated_results, fetch_all_results
from ..utils.response_formatter import (
    success_response,
    error_response,
    empty_response,
    http_error_response,
)


async def get_risk_scenarios(folder: str = None, risk_assessment: str = None):
    """List risk scenarios from Risk Registry; filter by folder or assessment

    Args:
        folder: Folder ID/name
        risk_assessment: Risk assessment ID/name
    """
    try:
        from ..resolvers import resolve_folder_id, resolve_risk_assessment_id

        params = {}
        filters = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        # Add risk assessment filter if specified - resolve name to ID if needed
        if risk_assessment:
            params["risk_assessment"] = resolve_risk_assessment_id(risk_assessment)
            filters["risk_assessment"] = risk_assessment

        res = make_get_request("/risk-scenarios/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        scenarios = get_paginated_results(data)

        if not scenarios:
            return empty_response("risk scenarios", filters)

        result = f"Found {len(scenarios)} risk scenarios"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|UUID|Ref|Name|Inherent Level|Current Level|Residual Level|Treatment|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for rs in scenarios:
            uuid = rs.get("id", "N/A")
            ref_id = rs.get("ref_id") or "N/A"
            name = rs.get("name", "N/A")
            inherent_level = (rs.get("inherent_level") or {}).get("name", "--")
            current_level = (rs.get("current_level") or {}).get("name", "--")
            residual_level = (rs.get("residual_level") or {}).get("name", "--")
            treatment = rs.get("treatment") or "--"

            result += f"|{uuid}|{ref_id}|{name}|{inherent_level}|{current_level}|{residual_level}|{treatment}|\n"

        return success_response(
            result,
            "get_risk_scenarios",
            "Use get_risk_scenario with a UUID to retrieve full details of a specific scenario",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_risk_scenario(scenario_id: str):
    """Retrieve full details of a single risk scenario by its UUID

    Args:
        scenario_id: Risk scenario UUID
    """
    try:
        from ..resolvers import resolve_risk_scenario_id

        resolved_id = resolve_risk_scenario_id(scenario_id)
        res = make_get_request(f"/risk-scenarios/{resolved_id}/")

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        rs = res.json()

        result = f"## Risk Scenario: {rs.get('name', 'N/A')}\n\n"
        result += f"**ID:** {rs.get('id', 'N/A')}\n"
        result += f"**Ref ID:** {rs.get('ref_id') or '-'}\n"
        result += f"**Description:** {rs.get('description') or '-'}\n"
        result += f"**Justification:** {rs.get('justification') or '-'}\n"
        result += f"**Treatment:** {rs.get('treatment') or '-'}\n"
        result += f"**Existing Controls:** {rs.get('existing_controls') or '-'}\n\n"

        result += "### Inherent Risk\n"
        result += f"**Proba:** {(rs.get('inherent_proba') or {}).get('name', '--')}\n"
        result += f"**Impact:** {(rs.get('inherent_impact') or {}).get('name', '--')}\n"
        result += f"**Level:** {(rs.get('inherent_level') or {}).get('name', '--')}\n\n"

        result += "### Current Risk\n"
        result += f"**Proba:** {(rs.get('current_proba') or {}).get('name', '--')}\n"
        result += f"**Impact:** {(rs.get('current_impact') or {}).get('name', '--')}\n"
        result += f"**Level:** {(rs.get('current_level') or {}).get('name', '--')}\n\n"

        result += "### Residual Risk\n"
        result += f"**Proba:** {(rs.get('residual_proba') or {}).get('name', '--')}\n"
        result += f"**Impact:** {(rs.get('residual_impact') or {}).get('name', '--')}\n"
        result += f"**Level:** {(rs.get('residual_level') or {}).get('name', '--')}\n\n"

        threats = rs.get("threats", [])
        if threats:
            result += f"**Threats:** {', '.join(t.get('str', str(t)) if isinstance(t, dict) else str(t) for t in threats)}\n"

        assets = rs.get("assets", [])
        if assets:
            result += f"**Assets:** {', '.join(a.get('str', str(a)) if isinstance(a, dict) else str(a) for a in assets)}\n"

        applied_controls = rs.get("applied_controls", [])
        if applied_controls:
            result += f"**Applied Controls:** {', '.join(c.get('str', str(c)) if isinstance(c, dict) else str(c) for c in applied_controls)}\n"

        return success_response(
            result,
            "get_risk_scenario",
            "Use update_risk_scenario to modify this scenario",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_applied_controls(folder: str = None):
    """List applied controls from action plan; filter by folder

    Args:
        folder: Folder ID/name
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}
        filters = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        res = make_get_request("/applied-controls/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        controls = get_paginated_results(data)

        if not controls:
            return empty_response("applied controls", filters)

        result = f"Found {len(controls)} applied controls"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|UUID|Ref|Name|Status|ETA|Owner|Owner UUIDs|Domain|Category|CSF Function|Effort|Impact|Priority|Cost|\n"
        result += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"

        for item in controls:
            uuid = item.get("id")
            ref_id = item.get("ref_id") or "N/A"
            name = item.get("name", "N/A")
            status = item.get("status", "N/A")
            eta = item.get("eta") or "N/A"
            owners = item.get("owner") or []
            owner_str = (
                ", ".join(
                    o.get("str", str(o)) if isinstance(o, dict) else str(o)
                    for o in owners
                )
                if owners
                else "N/A"
            )
            owner_uuids = (
                ", ".join(
                    o.get("id", "") if isinstance(o, dict) else str(o)
                    for o in owners
                )
                if owners
                else "N/A"
            )
            domain = (item.get("folder") or {}).get("str", "N/A")
            category = item.get("category", "N/A")
            csf_function = item.get("csf_function", "N/A")
            effort = item.get("effort", "N/A")
            impact = item.get("control_impact", "N/A")
            priority = item.get("priority", "N/A")
            cost = item.get("cost", 0)

            result += f"|{uuid}|{ref_id}|{name}|{status}|{eta}|{owner_str}|{owner_uuids}|{domain}|{category}|{csf_function}|{effort}|{impact}|{priority}|{cost}|\n"

        return success_response(
            result,
            "get_applied_controls",
            "Use this table to answer the user's question about applied controls",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


def _markdown_cell(value):
    return (
        str(value if value not in (None, "") else "--")
        .replace("\n", " ")
        .replace("|", "\\|")
    )


def _markdown_list(value):
    if not value:
        return "--"
    if not isinstance(value, list):
        return _markdown_cell(value)
    return ", ".join(
        _markdown_cell(item.get("str", item) if isinstance(item, dict) else item)
        for item in value
    )


async def get_policy_control_catalogue(
    policy: str,
    search: str = None,
    ordering: str = None,
    limit: int = 100,
):
    """List the derived Control Catalogue for a policy.

    Args:
        policy: Policy UUID, ref_id, or name
        search: Optional search term for catalogue rows
        ordering: Optional ordering field, e.g. ref_id or -ref_id
        limit: Maximum rows to display in the MCP response
    """
    try:
        from ..resolvers import resolve_policy_id

        policy_id = resolve_policy_id(policy)
        display_limit = max(1, min(int(limit or 100), 500))
        params = {"limit": display_limit}
        filters = {"policy": policy}

        if search:
            params["search"] = search
            filters["search"] = search

        if ordering:
            params["ordering"] = ordering
            filters["ordering"] = ordering

        res = make_get_request(
            f"/policies/{policy_id}/control-catalogue/", params=params
        )

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        controls = get_paginated_results(data)

        if not controls:
            return empty_response("policy control catalogue rows", filters)

        total_count = (
            data.get("count", len(controls)) if isinstance(data, dict) else len(controls)
        )

        result = f"Found {total_count} policy control catalogue rows"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        if total_count > len(controls):
            result += f"; showing first {len(controls)}"
        result += "\n\n"
        result += "|UUID|Ref|Name|Status|Category|CSF Function|Owner|Domain|ETA|\n"
        result += "|---|---|---|---|---|---|---|---|---|\n"

        for control in controls:
            result += (
                f"|{_markdown_cell(control.get('id'))}"
                f"|{_markdown_cell(control.get('ref_id'))}"
                f"|{_markdown_cell(control.get('name'))}"
                f"|{_markdown_cell(control.get('status'))}"
                f"|{_markdown_cell(control.get('category'))}"
                f"|{_markdown_cell(control.get('csf_function'))}"
                f"|{_markdown_list(control.get('owner'))}"
                f"|{_markdown_cell((control.get('folder') or {}).get('str'))}"
                f"|{_markdown_cell(control.get('eta'))}|\n"
            )

        return success_response(
            result,
            "get_policy_control_catalogue",
            "Use this table to answer questions about the policy-level Control Catalogue. Use update_applied_control only if the user explicitly asks to edit a listed control.",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_audits_progress(
    folder: str = None,
    perimeter: str = None,
    status: str = None,
    framework: str = None,
):
    """List compliance assessments (audits) with progress metrics

    Args:
        folder: Folder ID/name
        perimeter: Perimeter ID/name
        status: Filter by status: created | in_progress | in_review | done | deprecated
        framework: Framework ID/name to filter by
    """
    try:
        from ..resolvers import (
            resolve_folder_id,
            resolve_perimeter_id,
            resolve_framework_id,
        )

        params = {}
        filters = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        # Add perimeter filter if specified - resolve name to ID if needed
        if perimeter:
            params["perimeter"] = resolve_perimeter_id(perimeter)
            filters["perimeter"] = perimeter

        if status:
            params["status"] = status
            filters["status"] = status

        if framework:
            params["framework"] = resolve_framework_id(framework)
            filters["framework"] = framework

        res = make_get_request("/compliance-assessments/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        audits = get_paginated_results(data)

        if not audits:
            return empty_response("audits", filters)

        total_count = (
            data.get("count", len(audits)) if isinstance(data, dict) else len(audits)
        )
        result = f"Found {total_count} audits"
        if total_count > len(audits):
            result += f" (showing first {len(audits)}, use filters to narrow down)"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|Name|Framework|Status|Progress|Domain|\n"
        result += "|---|---|---|---|---|\n"

        for item in audits:
            name = item.get("name", "N/A")
            fw = (item.get("framework") or {}).get("str", "N/A")
            st = item.get("status", "N/A")
            progress = item.get("progress", "N/A")
            domain = (item.get("folder") or {}).get("str", "N/A")

            result += f"|{name}|{fw}|{st}|{progress}|{domain}|\n"

        return success_response(
            result,
            "get_audits_progress",
            "Use this table to answer the user's question about audit progress",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_folders(name: str = None):
    """List folders (domains) - organizational units containing perimeters, assets, and assessments

    Args:
        name: Name filter
    """
    try:
        params = {}
        filters = {}

        # Add name filter if specified
        if name:
            params["name"] = name
            filters["name"] = name

        res = make_get_request("/folders/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        folders = get_paginated_results(data)

        if not folders:
            return empty_response("folders", filters)

        result = f"Found {len(folders)} folders"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Name|Parent|\n"
        result += "|---|---|---|\n"

        for folder in folders:
            folder_id = folder.get("id", "N/A")
            folder_name = folder.get("name", "N/A")
            parent = folder.get("parent_folder") or {}
            parent_name = parent.get("str", "Root") if parent else "Root"

            result += f"|{folder_id}|{folder_name}|{parent_name}|\n"

        return success_response(
            result,
            "get_folders",
            "Use this table to identify folder IDs/names for filtering other resources",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_perimeters(folder: str = None, name: str = None):
    """List perimeters - scope definitions for risk assessments and audits

    Args:
        folder: Folder ID/name
        name: Name filter
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}
        filters = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        # Add name filter if specified
        if name:
            params["name"] = name
            filters["name"] = name

        res = make_get_request("/perimeters/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        perimeters = get_paginated_results(data)

        if not perimeters:
            return empty_response("perimeters", filters)

        result = f"Found {len(perimeters)} perimeters"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Name|Folder|\n"
        result += "|---|---|---|\n"

        for perimeter in perimeters:
            perimeter_id = perimeter.get("id", "N/A")
            perimeter_name = perimeter.get("name", "N/A")
            folder_name = (perimeter.get("folder") or {}).get("str", "N/A")

            result += f"|{perimeter_id}|{perimeter_name}|{folder_name}|\n"

        return success_response(
            result,
            "get_perimeters",
            "Use this table to identify perimeter IDs for creating risk assessments or audits",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_risk_matrices():
    """List risk matrices with IDs and names for creating risk assessments"""
    try:
        res = make_get_request("/risk-matrices/")

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        matrices = get_paginated_results(data)

        if not matrices:
            return empty_response("risk matrices", None)

        result = f"Found {len(matrices)} risk matrices\n\n"
        result += "|ID|Name|\n"
        result += "|---|---|\n"

        for matrix in matrices:
            matrix_id = matrix.get("id", "N/A")
            name = matrix.get("name", "N/A")

            result += f"|{matrix_id}|{name}|\n"

        return success_response(
            result,
            "get_risk_matrices",
            "Use these matrix IDs when creating risk assessments",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_risk_matrix_details(matrix_id_or_name: str):
    """Get risk matrix details: probability/impact scales and risk grid. Use to find valid indices for updating scenarios

    Args:
        matrix_id_or_name: Matrix ID/name
    """
    try:
        from ..resolvers import resolve_risk_matrix_id

        # Resolve matrix name to ID if needed
        matrix_id = resolve_risk_matrix_id(matrix_id_or_name)

        res = make_get_request(f"/risk-matrices/{matrix_id}/")

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

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

        return success_response(
            result,
            "get_risk_matrix_details",
            "Use these probability/impact indices when creating or updating risk scenarios",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_risk_assessments(folder: str = None, perimeter: str = None):
    """List risk assessments with IDs and status. Use to find risk_assessment_id for creating scenarios

    Args:
        folder: Folder ID/name
        perimeter: Perimeter ID/name
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
    """List threats with IDs, names, and providers

    Args:
        provider: Provider name (e.g. "MITRE ATT&CK")
        folder: Folder ID/name
        library: Library URN/ID
        limit: Max results (default 25, 0=unlimited)
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
    """List assets with IDs, names, and types

    Args:
        folder: Folder ID/name
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}
        filters = {}

        # Add folder filter if specified - resolve name to ID if needed
        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        res = make_get_request("/assets/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        assets = get_paginated_results(data)

        if not assets:
            return empty_response("assets", filters)

        result = f"Found {len(assets)} assets"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Name|Type|Folder|\n"
        result += "|---|---|---|---|\n"

        for asset in assets:
            asset_id = asset.get("id", "N/A")
            name = asset.get("name", "N/A")
            asset_type = asset.get("type", "N/A")
            folder_name = (asset.get("folder") or {}).get("str", "N/A")

            result += f"|{asset_id}|{name}|{asset_type}|{folder_name}|\n"

        return success_response(
            result,
            "get_assets",
            "Use this table to identify asset IDs for linking to risk scenarios",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_incidents(folder: str = None):
    """List incidents with IDs, severity, and status

    Args:
        folder: Folder ID/name
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
    """List security exceptions with IDs, approval status, and expiry dates

    Args:
        folder: Folder ID/name
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
        result += "|ID|Ref ID|Name|Severity|Status|Approver|Owners|Expiration Date|Associated Objects|Folder|\n"
        result += "|---|---|---|---|---|---|---|---|---|---|\n"

        for exception in exceptions:
            exception_id = exception.get("id", "N/A")
            ref_id = exception.get("ref_id") or "N/A"
            name = exception.get("name", "N/A")
            severity = exception.get("severity") or "N/A"
            status = exception.get("status", "N/A")
            approver = exception.get("approver")
            approver_str = (
                approver.get("str", "N/A")
                if isinstance(approver, dict)
                else (approver or "N/A")
            )
            owners = exception.get("owners") or []
            owners_str = (
                ", ".join(
                    o.get("str", str(o)) if isinstance(o, dict) else str(o)
                    for o in owners
                )
                if owners
                else "N/A"
            )
            expiration_date = exception.get("expiration_date") or "N/A"
            associated_objects_count = exception.get("associated_objects_count")
            if associated_objects_count is None:
                associated_objects_count = "N/A"
            folder = (exception.get("folder") or {}).get("str", "N/A")

            result += (
                f"|{exception_id}|{ref_id}|{name}|{severity}|{status}|{approver_str}|"
                f"{owners_str}|{expiration_date}|{associated_objects_count}|{folder}|\n"
            )

        return result
    except Exception as e:
        return f"Error in get_security_exceptions: {str(e)}"


async def get_frameworks(folder: str = None):
    """List imported frameworks available for compliance assessments. Use to find framework IDs/URNs for audits

    Args:
        folder: Folder ID/name
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
    """List Business Impact Analyses (BIAs) with status and details

    Args:
        folder: Folder ID/name
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
    """List requirement assessments (audit requirements) with IDs and results. Use IDs with update_requirement_assessment()

    Args:
        compliance_assessment_id_or_name: Compliance assessment ID/name
        ref_id: Reference ID (e.g. "ISO 27001:2022 A.5.1")
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
        result += "|ID|Ref|Description|Requirement|Assessment|Status|Result|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for req in req_assessments:
            req_id = req.get("id", "N/A")
            req_ref_id = req.get("ref_id", "N/A")
            requirement = req.get("name", "N/A")[:30]  # Truncate
            description = req.get("description", "N/A")
            comp_assessment = (req.get("compliance_assessment") or {}).get(
                "name", "N/A"
            )[:20]
            status = req.get("status", "N/A")
            result_val = req.get("result", "N/A")

            result += f"|{req_id}|{req_ref_id}|{description}|{requirement}|{comp_assessment}|{status}|{result_val}|\n"

        return result
    except Exception as e:
        return f"Error in get_requirement_assessments: {str(e)}"


async def get_quantitative_risk_studies():
    """List quantitative risk studies with IDs, names, and status"""
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
    """List quantitative risk scenarios with IDs, status, and ALE

    Args:
        study_id_or_name: Study ID/name
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
    """List quantitative risk hypotheses with IDs, risk stage, and metrics

    Args:
        scenario_id_or_name: Scenario ID/name
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


async def get_task_templates(
    limit: int = None, offset: int = None, ordering: str = None, search: str = None
):
    """List task templates with IDs, names, and details

    Args:
        limit: Number of results to return per page
        offset: The initial index from which to return the results
        ordering: Which field to use when ordering the results
        search: A search term
    """
    try:
        params = {}

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if ordering:
            params["ordering"] = ordering
        if search:
            params["search"] = search

        res = make_get_request("/task-templates/", params=params)

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        data = res.json()
        tasks = get_paginated_results(data)

        if not tasks:
            return "No task found"

        result = f"Found {len(tasks)} task templates\n\n"
        result += "|ID|Name|Description|Ref ID|Status|Recurrent|Enabled|Task Date|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for task in tasks:
            task_id = task.get("id", "N/A")
            name = task.get("name", "N/A")
            description = (task.get("description", "N/A") or "N/A")[:40]  # Truncate
            ref_id = task.get("ref_id", "N/A")
            status = task.get("status", "N/A")
            is_recurrent = "Yes" if task.get("is_recurrent") else "No"
            enabled = "Yes" if task.get("enabled") else "No"
            task_date = task.get("task_date", "N/A")

            result += f"|{task_id}|{name}|{description}|{ref_id}|{status}|{is_recurrent}|{enabled}|{task_date}|\n"

        return result
    except Exception as e:
        return f"Error in get_task_templates: {str(e)}"


async def get_task_template_details(task_id: str):
    """Get detailed information for a specific task template

    Args:
        task_id: Task template ID
    """
    try:
        res = make_get_request(f"/task-templates/{task_id}/")

        if res.status_code != 200:
            return f"Error: HTTP {res.status_code} - {res.text}"

        task = res.json()

        # Create result
        result = f"|ID|Name|Description|Ref ID|Status|Task Date|Recurrent|Enabled|Published|Link|Folder|Path|Observation|Evidences|Created|Updated|Assets|Applied Controls|Compliance Assessment|Risk Assessment|Assign To|\n"
        result += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        result += f"|{task.get('id', 'N/A')}|{task.get('name', 'N/A')}"
        result += f"|{task.get('description', 'N/A')}"
        result += f"|{task.get('ref_id', 'N/A')}"
        result += f"|{task.get('status', 'N/A')}"
        result += f"|{task.get('task_date', 'N/A')}"
        result += f"|{'Yes' if task.get('is_recurrent') else 'No'}"
        result += f"|{'Yes' if task.get('enabled') else 'No'}"
        result += f"|{'Yes' if task.get('is_published') else 'No'}"
        result += f"|{task.get('link', 'N/A')}"
        result += f"|{task.get('folder', 'N/A')}"
        result += f"|{task.get('path', 'N/A')}"
        result += f"|{task.get('observation', 'N/A')}"
        result += f"|{task.get('evidences', 'N/A')}"
        result += f"|{task.get('created_at', 'N/A')}"
        result += f"|{task.get('updated_at', 'N/A')}"
        result += f"|{task.get('assets', [])}"
        result += f"|{task.get('applied_controls', [])}"
        result += f"|{task.get('compliance_assessments', [])}"
        result += f"|{task.get('risk_assessments', [])}"
        result += f"|{task.get('assigned_to', [])}"
        result += "|\n"

        return result
    except Exception as e:
        return f"Error in get_task_template_details: {str(e)}"


SEVERITY_LABELS = {
    -1: "undefined",
    0: "info",
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
}

STATUS_LABELS = {
    "--": "Undefined",
    "potential": "Potential",
    "exploitable": "Exploitable",
    "mitigated": "Mitigated",
    "fixed": "Fixed",
    "not_exploitable": "Not exploitable",
    "unaffected": "Unaffected",
}


async def get_vulnerabilities(
    folder: str = None,
    status: str = None,
    severity: int = None,
    search: str = None,
):
    """List vulnerabilities with optional filters

    Args:
        folder: Folder ID/name to filter by
        status: Filter by status: -- | potential | exploitable | mitigated | fixed | not_exploitable | unaffected
        severity: Filter by severity: -1 (undefined) | 0 (info) | 1 (low) | 2 (medium) | 3 (high) | 4 (critical)
        search: Search term to filter results
    """
    try:
        from ..resolvers import resolve_folder_id

        params = {}
        filters = {}

        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder
        if status:
            params["status"] = status
            filters["status"] = status
        if severity is not None:
            params["severity"] = severity
            filters["severity"] = SEVERITY_LABELS.get(severity, str(severity))
        if search:
            params["search"] = search
            filters["search"] = search

        res = make_get_request("/vulnerabilities/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        vulnerabilities = get_paginated_results(data)

        if not vulnerabilities:
            return empty_response("vulnerabilities", filters)

        result = f"Found {len(vulnerabilities)} vulnerabilities"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Name|Ref ID|Status|Severity|Folder|\n"
        result += "|---|---|---|---|---|---|\n"

        for vuln in vulnerabilities:
            vuln_id = vuln.get("id", "N/A")
            name = vuln.get("name", "N/A")
            ref_id = vuln.get("ref_id") or "-"
            vuln_status = STATUS_LABELS.get(
                vuln.get("status", "--"), vuln.get("status", "--")
            )
            sev_val = vuln.get("severity", -1)
            vuln_severity = SEVERITY_LABELS.get(sev_val, str(sev_val))
            vuln_folder = vuln.get("folder") or {}
            if isinstance(vuln_folder, dict):
                vuln_folder = vuln_folder.get("str", vuln_folder.get("name", "-"))
            else:
                vuln_folder = str(vuln_folder) if vuln_folder else "-"

            result += f"|{vuln_id}|{name}|{ref_id}|{vuln_status}|{vuln_severity}|{vuln_folder}|\n"

        return success_response(
            result,
            "get_vulnerabilities",
            "Use get_vulnerability with a specific ID to retrieve full details, or create_vulnerability to add a new one",
        )
    except Exception as e:
        return error_response(
            "Error", str(e), "Check parameters and retry", retry_allowed=True
        )


async def get_vulnerability(vulnerability_id: str):
    """Retrieve a single vulnerability by ID

    Args:
        vulnerability_id: Vulnerability UUID or name
    """
    try:
        from ..resolvers import resolve_vulnerability_id

        resolved_id = resolve_vulnerability_id(vulnerability_id)
        res = make_get_request(f"/vulnerabilities/{resolved_id}/")

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        vuln = res.json()

        sev_val = vuln.get("severity", -1)
        vuln_severity = SEVERITY_LABELS.get(sev_val, str(sev_val))
        vuln_status = STATUS_LABELS.get(
            vuln.get("status", "--"), vuln.get("status", "--")
        )

        result = f"## Vulnerability: {vuln.get('name', 'N/A')}\n\n"
        result += f"**ID:** {vuln.get('id', 'N/A')}\n"
        result += f"**Ref ID:** {vuln.get('ref_id') or '-'}\n"
        result += f"**Status:** {vuln_status}\n"
        result += f"**Severity:** {vuln_severity}\n"
        result += f"**Description:** {vuln.get('description') or '-'}\n"

        folder = vuln.get("folder")
        if isinstance(folder, dict):
            result += f"**Folder:** {folder.get('str', folder.get('name', folder.get('id', '-')))}\n"
        elif folder:
            result += f"**Folder:** {folder}\n"

        filtering_labels = vuln.get("filtering_labels", [])
        if filtering_labels:
            result += f"**Labels:** {', '.join(str(l) for l in filtering_labels)}\n"

        applied_controls = vuln.get("applied_controls", [])
        if applied_controls:
            result += (
                f"**Applied Controls:** {', '.join(str(c) for c in applied_controls)}\n"
            )

        assets = vuln.get("assets", [])
        if assets:
            result += f"**Assets:** {', '.join(str(a) for a in assets)}\n"

        security_exceptions = vuln.get("security_exceptions", [])
        if security_exceptions:
            result += f"**Security Exceptions:** {', '.join(str(e) for e in security_exceptions)}\n"

        return success_response(
            result,
            "get_vulnerability",
            "Use create_vulnerability to add a new vulnerability or get_vulnerabilities to list all",
        )
    except Exception as e:
        return error_response(
            "Error", str(e), "Check the vulnerability ID and retry", retry_allowed=True
        )


async def get_asset_classes(
    parent: str = None,
    search: str = None,
):
    """List all asset classes with IDs and names

    Args:
        parent: Parent asset class UUID to filter by
        search: Search term to filter results
    """
    try:
        params = {}
        filters = {}

        if parent:
            params["parent"] = parent
            filters["parent"] = parent
        if search:
            params["search"] = search
            filters["search"] = search

        res = make_get_request("/asset-class/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        asset_classes = get_paginated_results(data)

        if not asset_classes:
            return empty_response("asset classes", filters)

        result = f"Found {len(asset_classes)} asset classes"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Name|Parent|\n"
        result += "|---|---|---|\n"

        for ac in asset_classes:
            ac_id = ac.get("id", "N/A")
            name = ac.get("name", "N/A")
            parent_obj = ac.get("parent")
            parent_name = parent_obj.get("str", "N/A") if isinstance(parent_obj, dict) else (parent_obj or "N/A")
            result += f"|{ac_id}|{name}|{parent_name}|\n"

        return success_response(
            result,
            "get_asset_classes",
            "Use the asset class ID or name with update_asset to set the asset_class field",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_users(
    search: str = None,
    email: str = None,
    first_name: str = None,
    last_name: str = None,
    is_active: bool = None,
    is_applied_control_owner: bool = None,
    exclude_current: bool = None,
):
    """List users with their UUIDs, names and emails

    Args:
        search: Search term (name or email)
        email: Filter by email address
        first_name: Filter by first name
        last_name: Filter by last name
        is_active: Filter by active status
        is_applied_control_owner: Filter to users who are applied control owners
        exclude_current: Exclude the currently authenticated user
    """
    try:
        params = {}
        filters = {}

        if search:
            params["search"] = search
            filters["search"] = search
        if email:
            params["email"] = email
            filters["email"] = email
        if first_name:
            params["first_name"] = first_name
            filters["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name
            filters["last_name"] = last_name
        if is_active is not None:
            params["is_active"] = is_active
            filters["is_active"] = is_active
        if is_applied_control_owner is not None:
            params["is_applied_control_owner"] = is_applied_control_owner
            filters["is_applied_control_owner"] = is_applied_control_owner
        if exclude_current is not None:
            params["exclude_current"] = exclude_current

        res = make_get_request("/users/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        users = get_paginated_results(data)

        if not users:
            return empty_response("users", filters)

        result = f"Found {len(users)} users"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|UUID|Email|First Name|Last Name|Active|\n"
        result += "|---|---|---|---|---|\n"

        for user in users:
            user_id = user.get("id", "N/A")
            user_email = user.get("email", "N/A")
            first = user.get("first_name", "") or ""
            last = user.get("last_name", "") or ""
            active = user.get("is_active", "N/A")
            result += f"|{user_id}|{user_email}|{first}|{last}|{active}|\n"

        return success_response(
            result,
            "get_users",
            "Use the UUID column to set the owner field when calling update_applied_control or update_asset",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )
