"""EBIOS RM (Risk Management) MCP tools for CISO Assistant"""

from ..client import (
    make_get_request,
    make_post_request,
    make_patch_request,
    get_paginated_results,
)
from ..resolvers import (
    resolve_folder_id,
    resolve_ebios_rm_study_id,
    resolve_feared_event_id,
    resolve_ro_to_id,
    resolve_stakeholder_id,
    resolve_strategic_scenario_id,
    resolve_attack_path_id,
    resolve_operational_scenario_id,
    resolve_elementary_action_id,
    resolve_operating_mode_id,
    resolve_risk_matrix_id,
    resolve_asset_id,
    resolve_entity_id,
)
from ..utils.response_formatter import (
    success_response,
    error_response,
    empty_response,
    http_error_response,
)


# ============================================================================
# READ TOOLS
# ============================================================================


async def get_ebios_rm_studies(
    folder: str = None,
    status: str = None,
):
    """List EBIOS RM studies

    Args:
        folder: Folder ID/name filter
        status: Status filter (planned, in_progress, in_review, done, deprecated)
    """
    try:
        params = {}
        filters = {}

        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        if status:
            params["status"] = status
            filters["status"] = status

        res = make_get_request("/ebios-rm/studies/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        studies = get_paginated_results(data)

        if not studies:
            return empty_response("EBIOS RM studies", filters)

        result = f"Found {len(studies)} EBIOS RM studies"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Status|Version|Risk Matrix|Reference Entity|Folder|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for study in studies:
            study_id = study.get("id", "N/A")
            ref_id = study.get("ref_id") or "N/A"
            name = study.get("name", "N/A")
            status_val = study.get("status", "N/A")
            version = study.get("version") or "N/A"
            risk_matrix = (study.get("risk_matrix") or {}).get("str", "N/A")
            reference_entity = (study.get("reference_entity") or {}).get("str", "N/A")
            folder_name = (study.get("folder") or {}).get("str", "N/A")

            result += f"|{study_id}|{ref_id}|{name}|{status_val}|{version}|{risk_matrix}|{reference_entity}|{folder_name}|\n"

        return success_response(
            result,
            "get_ebios_rm_studies",
            "Use this table to identify EBIOS RM study IDs for further operations",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_feared_events(
    ebios_rm_study: str = None,
    is_selected: bool = None,
):
    """List feared events in EBIOS RM studies

    Args:
        ebios_rm_study: EBIOS RM study ID/name filter
        is_selected: Filter by selection status
    """
    try:
        params = {}
        filters = {}

        if ebios_rm_study:
            params["ebios_rm_study"] = resolve_ebios_rm_study_id(ebios_rm_study)
            filters["ebios_rm_study"] = ebios_rm_study

        if is_selected is not None:
            params["is_selected"] = str(is_selected).lower()
            filters["is_selected"] = is_selected

        res = make_get_request("/ebios-rm/feared-events/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        feared_events = get_paginated_results(data)

        if not feared_events:
            return empty_response("feared events", filters)

        result = f"Found {len(feared_events)} feared events"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Gravity|Selected|Study|Assets|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for fe in feared_events:
            fe_id = fe.get("id", "N/A")
            ref_id = fe.get("ref_id") or "N/A"
            name = fe.get("name", "N/A")
            gravity = fe.get("gravity", {})
            gravity_name = (
                gravity.get("name", "--") if isinstance(gravity, dict) else str(gravity)
            )
            selected = "Yes" if fe.get("is_selected") else "No"
            study_name = (fe.get("ebios_rm_study") or {}).get("str", "N/A")
            assets = fe.get("assets", [])
            assets_str = (
                ", ".join([a.get("str", "N/A") for a in assets[:3]])
                if assets
                else "None"
            )
            if len(assets) > 3:
                assets_str += f" (+{len(assets) - 3} more)"

            result += f"|{fe_id}|{ref_id}|{name}|{gravity_name}|{selected}|{study_name}|{assets_str}|\n"

        return success_response(
            result,
            "get_feared_events",
            "Use this table to identify feared events for RoTo couples and scenarios",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_ro_to_couples(
    ebios_rm_study: str = None,
    is_selected: bool = None,
):
    """List Risk Origin / Target Objective (RoTo) couples

    Args:
        ebios_rm_study: EBIOS RM study ID/name filter
        is_selected: Filter by selection status
    """
    try:
        params = {}
        filters = {}

        if ebios_rm_study:
            params["ebios_rm_study"] = resolve_ebios_rm_study_id(ebios_rm_study)
            filters["ebios_rm_study"] = ebios_rm_study

        if is_selected is not None:
            params["is_selected"] = str(is_selected).lower()
            filters["is_selected"] = is_selected

        res = make_get_request("/ebios-rm/ro-to/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        ro_to_couples = get_paginated_results(data)

        if not ro_to_couples:
            return empty_response("RoTo couples", filters)

        result = f"Found {len(ro_to_couples)} RoTo couples"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Risk Origin|Target Objective|Motivation|Resources|Pertinence|Selected|Study|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for roto in ro_to_couples:
            roto_id = roto.get("id", "N/A")
            risk_origin = roto.get("risk_origin", "N/A")
            target_objective = roto.get("target_objective", "N/A")[:50]
            if len(roto.get("target_objective", "")) > 50:
                target_objective += "..."
            motivation = roto.get("motivation", "N/A")
            resources = roto.get("resources", "N/A")
            pertinence = roto.get("pertinence", "N/A")
            selected = "Yes" if roto.get("is_selected") else "No"
            study_name = (roto.get("ebios_rm_study") or {}).get("str", "N/A")

            result += f"|{roto_id}|{risk_origin}|{target_objective}|{motivation}|{resources}|{pertinence}|{selected}|{study_name}|\n"

        return success_response(
            result,
            "get_ro_to_couples",
            "Use RoTo couple IDs to create strategic scenarios",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_stakeholders(
    ebios_rm_study: str = None,
    is_selected: bool = None,
    entity: str = None,
):
    """List stakeholders in EBIOS RM studies

    Args:
        ebios_rm_study: EBIOS RM study ID/name filter
        is_selected: Filter by selection status
        entity: Entity ID/name filter
    """
    try:
        params = {}
        filters = {}

        if ebios_rm_study:
            params["ebios_rm_study"] = resolve_ebios_rm_study_id(ebios_rm_study)
            filters["ebios_rm_study"] = ebios_rm_study

        if is_selected is not None:
            params["is_selected"] = str(is_selected).lower()
            filters["is_selected"] = is_selected

        if entity:
            params["entity"] = resolve_entity_id(entity)
            filters["entity"] = entity

        res = make_get_request("/ebios-rm/stakeholders/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        stakeholders = get_paginated_results(data)

        if not stakeholders:
            return empty_response("stakeholders", filters)

        result = f"Found {len(stakeholders)} stakeholders"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Entity|Category|Current Criticality|Residual Criticality|Selected|Study|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for sh in stakeholders:
            sh_id = sh.get("id", "N/A")
            entity_name = (sh.get("entity") or {}).get("str", "N/A")
            category = sh.get("category", "N/A")
            current_crit = sh.get("current_criticality", "N/A")
            residual_crit = sh.get("residual_criticality", "N/A")
            selected = "Yes" if sh.get("is_selected") else "No"
            study_name = (sh.get("ebios_rm_study") or {}).get("str", "N/A")

            result += f"|{sh_id}|{entity_name}|{category}|{current_crit}|{residual_crit}|{selected}|{study_name}|\n"

        return success_response(
            result,
            "get_stakeholders",
            "Use stakeholder IDs to link them to attack paths",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_strategic_scenarios(
    ebios_rm_study: str = None,
):
    """List strategic scenarios in EBIOS RM studies

    Args:
        ebios_rm_study: EBIOS RM study ID/name filter
    """
    try:
        params = {}
        filters = {}

        if ebios_rm_study:
            params["ebios_rm_study"] = resolve_ebios_rm_study_id(ebios_rm_study)
            filters["ebios_rm_study"] = ebios_rm_study

        res = make_get_request("/ebios-rm/strategic-scenarios/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        scenarios = get_paginated_results(data)

        if not scenarios:
            return empty_response("strategic scenarios", filters)

        result = f"Found {len(scenarios)} strategic scenarios"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|RoTo Couple|Gravity|Study|\n"
        result += "|---|---|---|---|---|---|\n"

        for scenario in scenarios:
            scenario_id = scenario.get("id", "N/A")
            ref_id = scenario.get("ref_id") or "N/A"
            name = scenario.get("name", "N/A")
            ro_to = (scenario.get("ro_to_couple") or {}).get("str", "N/A")
            gravity = scenario.get("gravity", {})
            gravity_name = (
                gravity.get("name", "--") if isinstance(gravity, dict) else str(gravity)
            )
            study_name = (scenario.get("ebios_rm_study") or {}).get("str", "N/A")

            result += (
                f"|{scenario_id}|{ref_id}|{name}|{ro_to}|{gravity_name}|{study_name}|\n"
            )

        return success_response(
            result,
            "get_strategic_scenarios",
            "Use strategic scenario IDs to create attack paths",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_attack_paths(
    ebios_rm_study: str = None,
    strategic_scenario: str = None,
    is_selected: bool = None,
):
    """List attack paths in EBIOS RM studies

    Args:
        ebios_rm_study: EBIOS RM study ID/name filter
        strategic_scenario: Strategic scenario ID/name filter
        is_selected: Filter by selection status
    """
    try:
        params = {}
        filters = {}

        if ebios_rm_study:
            params["ebios_rm_study"] = resolve_ebios_rm_study_id(ebios_rm_study)
            filters["ebios_rm_study"] = ebios_rm_study

        if strategic_scenario:
            params["strategic_scenario"] = resolve_strategic_scenario_id(
                strategic_scenario
            )
            filters["strategic_scenario"] = strategic_scenario

        if is_selected is not None:
            params["is_selected"] = str(is_selected).lower()
            filters["is_selected"] = is_selected

        res = make_get_request("/ebios-rm/attack-paths/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        attack_paths = get_paginated_results(data)

        if not attack_paths:
            return empty_response("attack paths", filters)

        result = f"Found {len(attack_paths)} attack paths"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Strategic Scenario|Selected|Stakeholders|Study|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for ap in attack_paths:
            ap_id = ap.get("id", "N/A")
            ref_id = ap.get("ref_id") or "N/A"
            name = ap.get("name", "N/A")
            strategic = (ap.get("strategic_scenario") or {}).get("str", "N/A")
            selected = "Yes" if ap.get("is_selected") else "No"
            stakeholders = ap.get("stakeholders", [])
            stakeholders_str = str(len(stakeholders)) if stakeholders else "0"
            study_name = (ap.get("ebios_rm_study") or {}).get("str", "N/A")

            result += f"|{ap_id}|{ref_id}|{name}|{strategic}|{selected}|{stakeholders_str}|{study_name}|\n"

        return success_response(
            result,
            "get_attack_paths",
            "Use attack path IDs to create operational scenarios",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_operational_scenarios(
    ebios_rm_study: str = None,
):
    """List operational scenarios in EBIOS RM studies

    Args:
        ebios_rm_study: EBIOS RM study ID/name filter
    """
    try:
        params = {}
        filters = {}

        if ebios_rm_study:
            params["ebios_rm_study"] = resolve_ebios_rm_study_id(ebios_rm_study)
            filters["ebios_rm_study"] = ebios_rm_study

        res = make_get_request("/ebios-rm/operational-scenarios/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        scenarios = get_paginated_results(data)

        if not scenarios:
            return empty_response("operational scenarios", filters)

        result = f"Found {len(scenarios)} operational scenarios"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Likelihood|Gravity|Risk Level|Selected|Study|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for scenario in scenarios:
            scenario_id = scenario.get("id", "N/A")
            ref_id = scenario.get("ref_id") or "N/A"
            name = (scenario.get("str") or scenario.get("name", "N/A"))[:40]
            if len(scenario.get("str", scenario.get("name", ""))) > 40:
                name += "..."

            likelihood = scenario.get("likelihood", {})
            likelihood_name = (
                likelihood.get("name", "--")
                if isinstance(likelihood, dict)
                else str(likelihood)
            )

            gravity = scenario.get("gravity", {})
            gravity_name = (
                gravity.get("name", "--") if isinstance(gravity, dict) else str(gravity)
            )

            risk_level = scenario.get("risk_level", {})
            risk_level_name = (
                risk_level.get("name", "--")
                if isinstance(risk_level, dict)
                else str(risk_level)
            )

            selected = "Yes" if scenario.get("is_selected") else "No"
            study_name = (scenario.get("ebios_rm_study") or {}).get("str", "N/A")

            result += f"|{scenario_id}|{ref_id}|{name}|{likelihood_name}|{gravity_name}|{risk_level_name}|{selected}|{study_name}|\n"

        return success_response(
            result,
            "get_operational_scenarios",
            "Use operational scenario IDs to manage operating modes",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_elementary_actions(
    operating_mode: str = None,
):
    """List elementary actions available for operating modes

    Args:
        operating_mode: Operating mode ID/name filter to show actions linked to that mode
    """
    try:
        params = {}
        filters = {}

        if operating_mode:
            params["operating_modes"] = resolve_operating_mode_id(operating_mode)
            filters["operating_mode"] = operating_mode

        res = make_get_request("/ebios-rm/elementary-actions/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        actions = get_paginated_results(data)

        if not actions:
            return empty_response("elementary actions", filters)

        result = f"Found {len(actions)} elementary actions"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Attack Stage|Icon|Threat|\n"
        result += "|---|---|---|---|---|---|\n"

        for action in actions:
            action_id = action.get("id", "N/A")
            ref_id = action.get("ref_id") or "N/A"
            name = action.get("name", "N/A")
            attack_stage = action.get("attack_stage", "N/A")
            icon = action.get("icon") or "N/A"
            threat = (action.get("threat") or {}).get("str", "N/A")

            result += f"|{action_id}|{ref_id}|{name}|{attack_stage}|{icon}|{threat}|\n"

        return success_response(
            result,
            "get_elementary_actions",
            "Use elementary action IDs to build kill chains in operating modes",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_operating_modes(
    operational_scenario: str = None,
):
    """List operating modes in operational scenarios

    Args:
        operational_scenario: Operational scenario ID filter
    """
    try:
        params = {}
        filters = {}

        if operational_scenario:
            params["operational_scenario"] = resolve_operational_scenario_id(
                operational_scenario
            )
            filters["operational_scenario"] = operational_scenario

        res = make_get_request("/ebios-rm/operating-modes/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        modes = get_paginated_results(data)

        if not modes:
            return empty_response("operating modes", filters)

        result = f"Found {len(modes)} operating modes"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Likelihood|Operational Scenario|Elementary Actions|\n"
        result += "|---|---|---|---|---|---|\n"

        for mode in modes:
            mode_id = mode.get("id", "N/A")
            ref_id = mode.get("ref_id") or "N/A"
            name = mode.get("name", "N/A")

            likelihood = mode.get("likelihood", {})
            likelihood_name = (
                likelihood.get("name", "--")
                if isinstance(likelihood, dict)
                else str(likelihood)
            )

            op_scenario = (mode.get("operational_scenario") or {}).get("str", "N/A")
            elem_actions = mode.get("elementary_actions", [])
            actions_count = str(len(elem_actions)) if elem_actions else "0"

            result += f"|{mode_id}|{ref_id}|{name}|{likelihood_name}|{op_scenario}|{actions_count}|\n"

        return success_response(
            result,
            "get_operating_modes",
            "Use operating mode IDs to manage kill chains and elementary actions",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


# ============================================================================
# WRITE TOOLS
# ============================================================================


async def create_ebios_rm_study(
    name: str,
    folder_id: str,
    risk_matrix_id: str,
    description: str = "",
    ref_id: str = "",
    version: str = "1.0",
    status: str = "planned",
    reference_entity_id: str = None,
    assets: list = None,
) -> str:
    """Create an EBIOS RM study

    Args:
        name: Study name (required)
        folder_id: Folder ID/name (required)
        risk_matrix_id: Risk matrix ID/name (required)
        description: Description
        ref_id: Reference ID
        version: Version string (default: "1.0")
        status: planned | in_progress | in_review | done | deprecated
        reference_entity_id: Reference entity ID/name (the organization being studied)
        assets: List of asset IDs/names to include in the study
    """
    try:
        folder_id = resolve_folder_id(folder_id)
        risk_matrix_id = resolve_risk_matrix_id(risk_matrix_id)

        payload = {
            "name": name,
            "folder": folder_id,
            "risk_matrix": risk_matrix_id,
            "description": description,
            "version": version,
            "status": status,
        }

        if ref_id:
            payload["ref_id"] = ref_id

        if reference_entity_id:
            payload["reference_entity"] = resolve_entity_id(reference_entity_id)

        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_assets.append(resolve_asset_id(asset))
            payload["assets"] = resolved_assets

        res = make_post_request("/ebios-rm/studies/", payload)

        if res.status_code == 201:
            study = res.json()
            return success_response(
                f"Created EBIOS RM study: {study.get('name')} (ID: {study.get('id')})",
                "create_ebios_rm_study",
                "Study created successfully. Next steps: add feared events, then create RoTo couples",
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


async def create_feared_event(
    name: str,
    ebios_rm_study_id: str,
    description: str = "",
    ref_id: str = "",
    gravity: int = -1,
    is_selected: bool = False,
    justification: str = "",
    assets: list = None,
) -> str:
    """Create a feared event in an EBIOS RM study

    Args:
        name: Feared event name (required)
        ebios_rm_study_id: EBIOS RM study ID/name (required)
        description: Description
        ref_id: Reference ID
        gravity: Gravity level (-1 for not rated, 0+ based on risk matrix)
        is_selected: Whether the feared event is selected for analysis
        justification: Justification for selection/deselection
        assets: List of asset IDs/names affected by this feared event
    """
    try:
        ebios_rm_study_id = resolve_ebios_rm_study_id(ebios_rm_study_id)

        payload = {
            "name": name,
            "ebios_rm_study": ebios_rm_study_id,
            "description": description,
            "gravity": gravity,
            "is_selected": is_selected,
            "justification": justification,
        }

        if ref_id:
            payload["ref_id"] = ref_id

        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_assets.append(resolve_asset_id(asset))
            payload["assets"] = resolved_assets

        res = make_post_request("/ebios-rm/feared-events/", payload)

        if res.status_code == 201:
            fe = res.json()
            return success_response(
                f"Created feared event: {fe.get('name')} (ID: {fe.get('id')})",
                "create_feared_event",
                "Feared event created successfully. Link it to assets and RoTo couples",
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


async def create_ro_to_couple(
    ebios_rm_study_id: str,
    risk_origin: str,
    target_objective: str,
    motivation: int = 0,
    resources: int = 0,
    activity: int = 0,
    is_selected: bool = False,
    justification: str = "",
    feared_events: list = None,
) -> str:
    """Create a Risk Origin / Target Objective (RoTo) couple

    Args:
        ebios_rm_study_id: EBIOS RM study ID/name (required)
        risk_origin: Risk origin terminology name (required, e.g., "State", "Organized crime")
        target_objective: Target objective description (required)
        motivation: Motivation level 0-4 (0=undefined, 1=very_low, 2=low, 3=significant, 4=strong)
        resources: Resources level 0-4 (0=undefined, 1=limited, 2=significant, 3=important, 4=unlimited)
        activity: Activity level 0-4 (0=undefined, 1=very_low, 2=low, 3=moderate, 4=important)
        is_selected: Whether the RoTo couple is selected for analysis
        justification: Justification for selection/deselection
        feared_events: List of feared event IDs/names to link
    """
    try:
        ebios_rm_study_id = resolve_ebios_rm_study_id(ebios_rm_study_id)

        # First, we need to resolve the risk_origin terminology
        # The API expects a terminology ID, so we search for it
        term_res = make_get_request("/terminologies/", params={"name": risk_origin})
        if term_res.status_code != 200:
            return http_error_response(term_res.status_code, term_res.text)

        term_data = term_res.json()
        terms = get_paginated_results(term_data)

        # Filter for ROTO_RISK_ORIGIN field path
        risk_origin_terms = [
            t for t in terms if t.get("field_path") == "roto_risk_origin"
        ]

        if not risk_origin_terms:
            return error_response(
                "Not Found",
                f"Risk origin terminology '{risk_origin}' not found. Use get_risk_origins to see available options.",
                "List available risk origins first",
                retry_allowed=True,
            )

        risk_origin_id = risk_origin_terms[0]["id"]

        payload = {
            "ebios_rm_study": ebios_rm_study_id,
            "risk_origin": risk_origin_id,
            "target_objective": target_objective,
            "motivation": motivation,
            "resources": resources,
            "activity": activity,
            "is_selected": is_selected,
            "justification": justification,
        }

        if feared_events:
            resolved_feared_events = []
            for fe in feared_events:
                resolved_feared_events.append(resolve_feared_event_id(fe))
            payload["feared_events"] = resolved_feared_events

        res = make_post_request("/ebios-rm/ro-to/", payload)

        if res.status_code == 201:
            roto = res.json()
            return success_response(
                f"Created RoTo couple: {risk_origin} - {target_objective[:50]} (ID: {roto.get('id')})",
                "create_ro_to_couple",
                "RoTo couple created successfully. Create strategic scenarios based on this couple",
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


async def create_stakeholder(
    ebios_rm_study_id: str,
    entity_id: str,
    category: str,
    current_dependency: int = 0,
    current_penetration: int = 0,
    current_maturity: int = 1,
    current_trust: int = 1,
    is_selected: bool = False,
    justification: str = "",
) -> str:
    """Create a stakeholder in an EBIOS RM study

    Args:
        ebios_rm_study_id: EBIOS RM study ID/name (required)
        entity_id: Entity ID/name (required)
        category: Category terminology name (required, e.g., "Partner", "Supplier", "Subcontractor")
        current_dependency: Dependency level 0-4
        current_penetration: Penetration level 0-4
        current_maturity: Maturity level 1-4
        current_trust: Trust level 1-4
        is_selected: Whether the stakeholder is selected for analysis
        justification: Justification for selection/deselection
    """
    try:
        ebios_rm_study_id = resolve_ebios_rm_study_id(ebios_rm_study_id)
        entity_id = resolve_entity_id(entity_id)

        # Resolve category terminology
        term_res = make_get_request("/terminologies/", params={"name": category})
        if term_res.status_code != 200:
            return http_error_response(term_res.status_code, term_res.text)

        term_data = term_res.json()
        terms = get_paginated_results(term_data)

        # Filter for ENTITY_RELATIONSHIP field path
        category_terms = [
            t for t in terms if t.get("field_path") == "entity_relationship"
        ]

        if not category_terms:
            return error_response(
                "Not Found",
                f"Category terminology '{category}' not found. Use get_stakeholder_categories to see available options.",
                "List available categories first",
                retry_allowed=True,
            )

        category_id = category_terms[0]["id"]

        payload = {
            "ebios_rm_study": ebios_rm_study_id,
            "entity": entity_id,
            "category": category_id,
            "current_dependency": current_dependency,
            "current_penetration": current_penetration,
            "current_maturity": current_maturity,
            "current_trust": current_trust,
            "is_selected": is_selected,
            "justification": justification,
        }

        res = make_post_request("/ebios-rm/stakeholders/", payload)

        if res.status_code == 201:
            sh = res.json()
            return success_response(
                f"Created stakeholder (ID: {sh.get('id')})",
                "create_stakeholder",
                "Stakeholder created successfully. Link stakeholders to attack paths",
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


async def create_strategic_scenario(
    name: str,
    ebios_rm_study_id: str,
    ro_to_couple_id: str,
    description: str = "",
    ref_id: str = "",
) -> str:
    """Create a strategic scenario in an EBIOS RM study

    Args:
        name: Scenario name (required)
        ebios_rm_study_id: EBIOS RM study ID/name (required)
        ro_to_couple_id: RoTo couple ID (required)
        description: Description
        ref_id: Reference ID
    """
    try:
        ebios_rm_study_id = resolve_ebios_rm_study_id(ebios_rm_study_id)
        ro_to_couple_id = resolve_ro_to_id(ro_to_couple_id)

        payload = {
            "name": name,
            "ebios_rm_study": ebios_rm_study_id,
            "ro_to_couple": ro_to_couple_id,
            "description": description,
        }

        if ref_id:
            payload["ref_id"] = ref_id

        res = make_post_request("/ebios-rm/strategic-scenarios/", payload)

        if res.status_code == 201:
            scenario = res.json()
            return success_response(
                f"Created strategic scenario: {scenario.get('name')} (ID: {scenario.get('id')})",
                "create_strategic_scenario",
                "Strategic scenario created successfully. Create attack paths for this scenario",
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


async def create_attack_path(
    name: str,
    strategic_scenario_id: str,
    description: str = "",
    ref_id: str = "",
    is_selected: bool = False,
    justification: str = "",
    stakeholders: list = None,
) -> str:
    """Create an attack path in a strategic scenario

    Args:
        name: Attack path name (required)
        strategic_scenario_id: Strategic scenario ID/name (required)
        description: Description
        ref_id: Reference ID (auto-generated if not provided)
        is_selected: Whether the attack path is selected for analysis
        justification: Justification for selection/deselection
        stakeholders: List of stakeholder IDs to link
    """
    try:
        strategic_scenario_id = resolve_strategic_scenario_id(strategic_scenario_id)

        payload = {
            "name": name,
            "strategic_scenario": strategic_scenario_id,
            "description": description,
            "is_selected": is_selected,
            "justification": justification,
        }

        if ref_id:
            payload["ref_id"] = ref_id

        if stakeholders:
            resolved_stakeholders = []
            for sh in stakeholders:
                resolved_stakeholders.append(resolve_stakeholder_id(sh))
            payload["stakeholders"] = resolved_stakeholders

        res = make_post_request("/ebios-rm/attack-paths/", payload)

        if res.status_code == 201:
            ap = res.json()
            return success_response(
                f"Created attack path: {ap.get('name')} (ID: {ap.get('id')})",
                "create_attack_path",
                "Attack path created successfully. Create an operational scenario for this attack path",
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


async def create_operational_scenario(
    ebios_rm_study_id: str,
    attack_path_id: str,
    operating_modes_description: str = "",
    likelihood: int = -1,
    is_selected: bool = False,
    justification: str = "",
    threats: list = None,
) -> str:
    """Create an operational scenario from an attack path

    Args:
        ebios_rm_study_id: EBIOS RM study ID/name (required)
        attack_path_id: Attack path ID/name (required)
        operating_modes_description: Description of operating modes
        likelihood: Likelihood level (-1 for not rated, 0+ based on risk matrix)
        is_selected: Whether the scenario is selected for treatment
        justification: Justification for selection/deselection
        threats: List of threat IDs/names to link
    """
    try:
        from ..resolvers import resolve_id_or_name

        ebios_rm_study_id = resolve_ebios_rm_study_id(ebios_rm_study_id)
        attack_path_id = resolve_attack_path_id(attack_path_id)

        payload = {
            "ebios_rm_study": ebios_rm_study_id,
            "attack_path": attack_path_id,
            "operating_modes_description": operating_modes_description,
            "likelihood": likelihood,
            "is_selected": is_selected,
            "justification": justification,
        }

        if threats:
            resolved_threats = []
            for threat in threats:
                resolved_threats.append(resolve_id_or_name(threat, "/threats/"))
            payload["threats"] = resolved_threats

        res = make_post_request("/ebios-rm/operational-scenarios/", payload)

        if res.status_code == 201:
            scenario = res.json()
            return success_response(
                f"Created operational scenario (ID: {scenario.get('id')})",
                "create_operational_scenario",
                "Operational scenario created successfully. Add operating modes to detail the attack",
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


async def create_elementary_action(
    name: str,
    folder_id: str,
    description: str = "",
    ref_id: str = "",
    attack_stage: int = 0,
    icon: str = None,
    threat_id: str = None,
) -> str:
    """Create an elementary action for use in operating modes

    Args:
        name: Action name (required)
        folder_id: Folder ID/name (required)
        description: Description
        ref_id: Reference ID
        attack_stage: Attack stage (0=Know/Reconnaissance, 1=Enter/Initial Access, 2=Discover/Discovery, 3=Exploit/Exploitation)
        icon: Icon name (server, computer, cloud, file, diamond, phone, cube, blocks, shapes, network, database, key, search, carrot, money, skull, globe, usb)
        threat_id: Threat ID/name to link
    """
    try:
        from ..resolvers import resolve_id_or_name

        folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "folder": folder_id,
            "description": description,
            "attack_stage": attack_stage,
        }

        if ref_id:
            payload["ref_id"] = ref_id

        if icon:
            payload["icon"] = icon

        if threat_id:
            payload["threat"] = resolve_id_or_name(threat_id, "/threats/")

        res = make_post_request("/ebios-rm/elementary-actions/", payload)

        if res.status_code == 201:
            action = res.json()
            return success_response(
                f"Created elementary action: {action.get('name')} (ID: {action.get('id')})",
                "create_elementary_action",
                "Elementary action created successfully. Add it to operating modes",
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


async def create_operating_mode(
    name: str,
    operational_scenario_id: str,
    description: str = "",
    ref_id: str = "",
    likelihood: int = -1,
    elementary_actions: list = None,
) -> str:
    """Create an operating mode in an operational scenario

    Args:
        name: Operating mode name (required)
        operational_scenario_id: Operational scenario ID (required)
        description: Description
        ref_id: Reference ID (auto-generated if not provided)
        likelihood: Likelihood level (-1 for not rated, 0+ based on risk matrix)
        elementary_actions: List of elementary action IDs/names to include
    """
    try:
        operational_scenario_id = resolve_operational_scenario_id(
            operational_scenario_id
        )

        payload = {
            "name": name,
            "operational_scenario": operational_scenario_id,
            "description": description,
            "likelihood": likelihood,
        }

        if ref_id:
            payload["ref_id"] = ref_id

        if elementary_actions:
            resolved_actions = []
            for action in elementary_actions:
                resolved_actions.append(resolve_elementary_action_id(action))
            payload["elementary_actions"] = resolved_actions

        res = make_post_request("/ebios-rm/operating-modes/", payload)

        if res.status_code == 201:
            mode = res.json()
            return success_response(
                f"Created operating mode: {mode.get('name')} (ID: {mode.get('id')})",
                "create_operating_mode",
                "Operating mode created successfully. Build the kill chain by adding elementary actions",
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


# ============================================================================
# UPDATE TOOLS
# ============================================================================


async def update_ebios_rm_study(
    study_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    version: str = None,
    status: str = None,
    observation: str = None,
    assets: list = None,
) -> str:
    """Update an EBIOS RM study

    Args:
        study_id: Study ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        version: New version string
        status: planned | in_progress | in_review | done | deprecated
        observation: Observation notes
        assets: List of asset IDs/names (replaces existing)
    """
    try:
        resolved_study_id = resolve_ebios_rm_study_id(study_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if version is not None:
            payload["version"] = version
        if status is not None:
            payload["status"] = status
        if observation is not None:
            payload["observation"] = observation

        if assets is not None:
            resolved_assets = []
            for asset in assets:
                resolved_assets.append(resolve_asset_id(asset))
            payload["assets"] = resolved_assets

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/studies/{resolved_study_id}/", payload)

        if res.status_code == 200:
            study = res.json()
            return success_response(
                f"Updated EBIOS RM study: {study.get('name')} (ID: {study.get('id')})",
                "update_ebios_rm_study",
                "Study updated successfully",
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


async def update_feared_event(
    feared_event_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    gravity: int = None,
    is_selected: bool = None,
    justification: str = None,
    assets: list = None,
) -> str:
    """Update a feared event

    Args:
        feared_event_id: Feared event ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        gravity: Gravity level (-1 for not rated, 0+ based on risk matrix)
        is_selected: Whether the feared event is selected
        justification: Justification text
        assets: List of asset IDs/names (replaces existing)
    """
    try:
        resolved_fe_id = resolve_feared_event_id(feared_event_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if gravity is not None:
            payload["gravity"] = gravity
        if is_selected is not None:
            payload["is_selected"] = is_selected
        if justification is not None:
            payload["justification"] = justification

        if assets is not None:
            resolved_assets = []
            for asset in assets:
                resolved_assets.append(resolve_asset_id(asset))
            payload["assets"] = resolved_assets

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/feared-events/{resolved_fe_id}/", payload)

        if res.status_code == 200:
            fe = res.json()
            return success_response(
                f"Updated feared event: {fe.get('name')} (ID: {fe.get('id')})",
                "update_feared_event",
                "Feared event updated successfully",
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


async def update_ro_to_couple(
    ro_to_id: str,
    target_objective: str = None,
    motivation: int = None,
    resources: int = None,
    activity: int = None,
    is_selected: bool = None,
    justification: str = None,
    feared_events: list = None,
) -> str:
    """Update a RoTo couple

    Args:
        ro_to_id: RoTo couple ID (required)
        target_objective: New target objective description
        motivation: Motivation level 0-4
        resources: Resources level 0-4
        activity: Activity level 0-4
        is_selected: Whether the RoTo couple is selected
        justification: Justification text
        feared_events: List of feared event IDs/names (replaces existing)
    """
    try:
        resolved_roto_id = resolve_ro_to_id(ro_to_id)

        payload = {}

        if target_objective is not None:
            payload["target_objective"] = target_objective
        if motivation is not None:
            payload["motivation"] = motivation
        if resources is not None:
            payload["resources"] = resources
        if activity is not None:
            payload["activity"] = activity
        if is_selected is not None:
            payload["is_selected"] = is_selected
        if justification is not None:
            payload["justification"] = justification

        if feared_events is not None:
            resolved_feared_events = []
            for fe in feared_events:
                resolved_feared_events.append(resolve_feared_event_id(fe))
            payload["feared_events"] = resolved_feared_events

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/ro-to/{resolved_roto_id}/", payload)

        if res.status_code == 200:
            roto = res.json()
            return success_response(
                f"Updated RoTo couple (ID: {roto.get('id')})",
                "update_ro_to_couple",
                "RoTo couple updated successfully",
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


async def update_stakeholder(
    stakeholder_id: str,
    current_dependency: int = None,
    current_penetration: int = None,
    current_maturity: int = None,
    current_trust: int = None,
    residual_dependency: int = None,
    residual_penetration: int = None,
    residual_maturity: int = None,
    residual_trust: int = None,
    is_selected: bool = None,
    justification: str = None,
    applied_controls: list = None,
) -> str:
    """Update a stakeholder

    Args:
        stakeholder_id: Stakeholder ID (required)
        current_dependency: Current dependency level 0-4
        current_penetration: Current penetration level 0-4
        current_maturity: Current maturity level 1-4
        current_trust: Current trust level 1-4
        residual_dependency: Residual dependency level 0-4
        residual_penetration: Residual penetration level 0-4
        residual_maturity: Residual maturity level 1-4
        residual_trust: Residual trust level 1-4
        is_selected: Whether the stakeholder is selected
        justification: Justification text
        applied_controls: List of applied control IDs/names (replaces existing)
    """
    try:
        from ..resolvers import resolve_applied_control_id

        resolved_sh_id = resolve_stakeholder_id(stakeholder_id)

        payload = {}

        if current_dependency is not None:
            payload["current_dependency"] = current_dependency
        if current_penetration is not None:
            payload["current_penetration"] = current_penetration
        if current_maturity is not None:
            payload["current_maturity"] = current_maturity
        if current_trust is not None:
            payload["current_trust"] = current_trust
        if residual_dependency is not None:
            payload["residual_dependency"] = residual_dependency
        if residual_penetration is not None:
            payload["residual_penetration"] = residual_penetration
        if residual_maturity is not None:
            payload["residual_maturity"] = residual_maturity
        if residual_trust is not None:
            payload["residual_trust"] = residual_trust
        if is_selected is not None:
            payload["is_selected"] = is_selected
        if justification is not None:
            payload["justification"] = justification

        if applied_controls is not None:
            resolved_controls = []
            for control in applied_controls:
                resolved_controls.append(resolve_applied_control_id(control))
            payload["applied_controls"] = resolved_controls

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/stakeholders/{resolved_sh_id}/", payload)

        if res.status_code == 200:
            sh = res.json()
            return success_response(
                f"Updated stakeholder (ID: {sh.get('id')})",
                "update_stakeholder",
                "Stakeholder updated successfully",
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


async def update_strategic_scenario(
    scenario_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    focused_feared_event_id: str = None,
) -> str:
    """Update a strategic scenario

    Args:
        scenario_id: Strategic scenario ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        focused_feared_event_id: Feared event ID to focus gravity calculation on
    """
    try:
        resolved_scenario_id = resolve_strategic_scenario_id(scenario_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if focused_feared_event_id is not None:
            payload["focused_feared_event"] = resolve_feared_event_id(
                focused_feared_event_id
            )

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/ebios-rm/strategic-scenarios/{resolved_scenario_id}/", payload
        )

        if res.status_code == 200:
            scenario = res.json()
            return success_response(
                f"Updated strategic scenario: {scenario.get('name')} (ID: {scenario.get('id')})",
                "update_strategic_scenario",
                "Strategic scenario updated successfully",
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


async def update_attack_path(
    attack_path_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    is_selected: bool = None,
    justification: str = None,
    stakeholders: list = None,
) -> str:
    """Update an attack path

    Args:
        attack_path_id: Attack path ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        is_selected: Whether the attack path is selected
        justification: Justification text
        stakeholders: List of stakeholder IDs (replaces existing)
    """
    try:
        resolved_ap_id = resolve_attack_path_id(attack_path_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if is_selected is not None:
            payload["is_selected"] = is_selected
        if justification is not None:
            payload["justification"] = justification

        if stakeholders is not None:
            resolved_stakeholders = []
            for sh in stakeholders:
                resolved_stakeholders.append(resolve_stakeholder_id(sh))
            payload["stakeholders"] = resolved_stakeholders

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/attack-paths/{resolved_ap_id}/", payload)

        if res.status_code == 200:
            ap = res.json()
            return success_response(
                f"Updated attack path: {ap.get('name')} (ID: {ap.get('id')})",
                "update_attack_path",
                "Attack path updated successfully",
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


async def update_operational_scenario(
    scenario_id: str,
    operating_modes_description: str = None,
    likelihood: int = None,
    is_selected: bool = None,
    justification: str = None,
    threats: list = None,
) -> str:
    """Update an operational scenario

    Args:
        scenario_id: Operational scenario ID (required)
        operating_modes_description: New operating modes description
        likelihood: Likelihood level (-1 for not rated, 0+ based on risk matrix)
        is_selected: Whether the scenario is selected
        justification: Justification text
        threats: List of threat IDs/names (replaces existing)
    """
    try:
        from ..resolvers import resolve_id_or_name

        resolved_scenario_id = resolve_operational_scenario_id(scenario_id)

        payload = {}

        if operating_modes_description is not None:
            payload["operating_modes_description"] = operating_modes_description
        if likelihood is not None:
            payload["likelihood"] = likelihood
        if is_selected is not None:
            payload["is_selected"] = is_selected
        if justification is not None:
            payload["justification"] = justification

        if threats is not None:
            resolved_threats = []
            for threat in threats:
                resolved_threats.append(resolve_id_or_name(threat, "/threats/"))
            payload["threats"] = resolved_threats

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/ebios-rm/operational-scenarios/{resolved_scenario_id}/", payload
        )

        if res.status_code == 200:
            scenario = res.json()
            return success_response(
                f"Updated operational scenario (ID: {scenario.get('id')})",
                "update_operational_scenario",
                "Operational scenario updated successfully",
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


async def update_operating_mode(
    mode_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    likelihood: int = None,
    elementary_actions: list = None,
) -> str:
    """Update an operating mode

    Args:
        mode_id: Operating mode ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        likelihood: Likelihood level (-1 for not rated, 0+ based on risk matrix)
        elementary_actions: List of elementary action IDs/names (replaces existing)
    """
    try:
        resolved_mode_id = resolve_operating_mode_id(mode_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if likelihood is not None:
            payload["likelihood"] = likelihood

        if elementary_actions is not None:
            resolved_actions = []
            for action in elementary_actions:
                resolved_actions.append(resolve_elementary_action_id(action))
            payload["elementary_actions"] = resolved_actions

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/ebios-rm/operating-modes/{resolved_mode_id}/", payload
        )

        if res.status_code == 200:
            mode = res.json()
            return success_response(
                f"Updated operating mode: {mode.get('name')} (ID: {mode.get('id')})",
                "update_operating_mode",
                "Operating mode updated successfully",
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
