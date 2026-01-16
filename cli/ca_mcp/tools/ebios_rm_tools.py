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
    resolve_kill_chain_id,
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
# HELPER FUNCTIONS
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


def _resolve_or_create_risk_origin(risk_origin_input: str) -> tuple[str, bool]:
    """Resolve a risk origin terminology by smart matching, or create a new one.

    Args:
        risk_origin_input: User input for risk origin (e.g., "State", "states", "organized crime")

    Returns:
        Tuple of (terminology_id, was_created)
    """
    # Fetch all risk origin terminologies
    res = make_get_request(
        "/terminologies/",
        params={"field_path": "ro_to.risk_origin", "is_visible": "true"},
    )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to fetch risk origin terminologies: {res.status_code}"
        )

    data = res.json()
    terminologies = get_paginated_results(data)

    # Try to find a match
    match = _find_terminology_match(terminologies, risk_origin_input)
    if match:
        return match["id"], False

    # No match found - create a new terminology
    # Normalize the name to snake_case for storage
    normalized_name = (
        risk_origin_input.lower().strip().replace(" ", "_").replace("-", "_")
    )

    # Get the global folder for the new terminology
    from ..config import GLOBAL_FOLDER_ID

    create_payload = {
        "name": normalized_name,
        "field_path": "ro_to.risk_origin",
        "folder": GLOBAL_FOLDER_ID,
        "is_visible": True,
        "builtin": False,
        "translations": {
            "en": {"name": risk_origin_input.strip().title()},
        },
    }

    create_res = make_post_request("/terminologies/", create_payload)
    if create_res.status_code == 201:
        new_term = create_res.json()
        return new_term["id"], True
    else:
        raise ValueError(
            f"Failed to create risk origin terminology '{risk_origin_input}': {create_res.status_code} - {create_res.text}"
        )


def _resolve_or_create_stakeholder_category(category_input: str) -> tuple[str, bool]:
    """Resolve a stakeholder category terminology by smart matching, or create a new one.

    Args:
        category_input: User input for category (e.g., "Partner", "partners", "Subcontractor")

    Returns:
        Tuple of (terminology_id, was_created)
    """
    # Fetch all entity relationship terminologies
    res = make_get_request(
        "/terminologies/",
        params={"field_path": "entity.relationship", "is_visible": "true"},
    )

    if res.status_code != 200:
        raise ValueError(
            f"Failed to fetch stakeholder category terminologies: {res.status_code}"
        )

    data = res.json()
    terminologies = get_paginated_results(data)

    # Try to find a match
    match = _find_terminology_match(terminologies, category_input)
    if match:
        return match["id"], False

    # No match found - create a new terminology
    normalized_name = category_input.lower().strip().replace(" ", "_").replace("-", "_")

    from ..config import GLOBAL_FOLDER_ID

    create_payload = {
        "name": normalized_name,
        "field_path": "entity.relationship",
        "folder": GLOBAL_FOLDER_ID,
        "is_visible": True,
        "builtin": False,
        "translations": {
            "en": {"name": category_input.strip().title()},
        },
    }

    create_res = make_post_request("/terminologies/", create_payload)
    if create_res.status_code == 201:
        new_term = create_res.json()
        return new_term["id"], True
    else:
        raise ValueError(
            f"Failed to create stakeholder category '{category_input}': {create_res.status_code} - {create_res.text}"
        )


# ============================================================================
# READ TOOLS
# ============================================================================


async def get_ebios_rm_studies(
    folder: str = None,
    status: str = None,
):
    """List EBIOS RM studies (Workshop 1)

    Shows all EBIOS RM studies including their security baseline (compliance assessments count).

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
        result += "|ID|Ref|Name|Status|Version|Security Baseline|Risk Matrix|Folder|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for study in studies:
            study_id = study.get("id", "N/A")
            ref_id = study.get("ref_id") or "N/A"
            name = study.get("name", "N/A")
            status_val = study.get("status", "N/A")
            version = study.get("version") or "N/A"
            risk_matrix = (study.get("risk_matrix") or {}).get("str", "N/A")
            folder_name = (study.get("folder") or {}).get("str", "N/A")

            # Show security baseline (compliance assessments count)
            compliance_assessments = study.get("compliance_assessments", [])
            if compliance_assessments:
                baseline = f"{len(compliance_assessments)} audit(s)"
            else:
                baseline = "Not set"

            result += f"|{study_id}|{ref_id}|{name}|{status_val}|{version}|{baseline}|{risk_matrix}|{folder_name}|\n"

        return success_response(
            result,
            "get_ebios_rm_studies",
            "Workshop 1: Use update_ebios_rm_study to set security baseline (compliance_assessments). Use get_audits_progress to see available audits.",
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
            "Workshop 3: Use strategic scenario IDs to create attack paths",
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
            "Workshop 3: Use attack path IDs. Workshop 4: create operational scenarios from these",
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
            "Workshop 4: Use operational scenario IDs to manage operating modes",
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
            "Workshop 4: Use elementary action IDs to build kill chains in operating modes",
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
            "Workshop 4: Use operating mode IDs to manage kill chains and elementary actions",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_kill_chains(
    operating_mode: str,
):
    """List kill chain steps for an operating mode (Workshop 4)

    Kill chains define the sequence of elementary actions in an attack scenario.
    Each step has an attack stage (0=Know, 1=Enter, 2=Discover, 3=Exploit)
    and can have antecedents (actions that must precede it).

    **Workflow:**
    1. Associate elementary actions with the operating mode (update_operating_mode)
    2. Create kill chain steps to define the attack sequence (create_kill_chain_step)

    Args:
        operating_mode: Operating mode ID (required)
    """
    try:
        operating_mode_id = resolve_operating_mode_id(operating_mode)

        res = make_get_request(
            "/ebios-rm/kill-chains/",
            params={"operating_mode": operating_mode_id},
        )

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        kill_chains = get_paginated_results(data)

        if not kill_chains:
            return empty_response(
                "kill chain steps", {"operating_mode": operating_mode}
            )

        # Sort by attack stage for better visualization
        kill_chains.sort(
            key=lambda x: (
                x.get("elementary_action", {}).get("attack_stage", 0)
                if isinstance(x.get("elementary_action"), dict)
                else 0
            )
        )

        result = f"Found {len(kill_chains)} kill chain steps for operating mode\n\n"
        result += "**Attack Stages:** 0=Know/Reconnaissance, 1=Enter/Initial Access, 2=Discover/Discovery, 3=Exploit/Exploitation\n\n"
        result += "|ID|Elementary Action|Stage|Highlighted|Logic Op|Antecedents|\n"
        result += "|---|---|---|---|---|---|\n"

        for kc in kill_chains:
            kc_id = kc.get("id", "N/A")
            elem_action = kc.get("elementary_action", {})
            action_name = (
                elem_action.get("str", "N/A")
                if isinstance(elem_action, dict)
                else "N/A"
            )
            attack_stage = kc.get("attack_stage", "N/A")
            highlighted = "Yes" if kc.get("is_highlighted") else "No"
            logic_op = kc.get("logic_operator") or "-"

            antecedents = kc.get("antecedents", [])
            if antecedents:
                antecedent_names = [a.get("str", "?") for a in antecedents[:2]]
                antecedents_str = ", ".join(antecedent_names)
                if len(antecedents) > 2:
                    antecedents_str += f" (+{len(antecedents) - 2})"
            else:
                antecedents_str = "-"

            result += f"|{kc_id}|{action_name}|{attack_stage}|{highlighted}|{logic_op}|{antecedents_str}|\n"

        return success_response(
            result,
            "get_kill_chains",
            "Workshop 4: Add more steps with create_kill_chain_step. Stage 0 actions cannot have antecedents.",
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
    compliance_assessments: list = None,
) -> str:
    """Create an EBIOS RM study (Workshop 1)

    **Workshop 1 - Security Baseline:**
    The compliance_assessments parameter allows you to associate existing audits (compliance
    assessments) with this study. These audits form the security baseline/foundation that
    will be used throughout the EBIOS RM analysis.

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
        compliance_assessments: List of compliance assessment (audit) IDs/names for security baseline
    """
    try:
        from ..resolvers import resolve_compliance_assessment_id

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

        if compliance_assessments:
            resolved_assessments = []
            for assessment in compliance_assessments:
                resolved_assessments.append(
                    resolve_compliance_assessment_id(assessment)
                )
            payload["compliance_assessments"] = resolved_assessments

        res = make_post_request("/ebios-rm/studies/", payload)

        if res.status_code == 201:
            study = res.json()
            baseline_msg = (
                f" with {len(compliance_assessments)} audit(s) for security baseline"
                if compliance_assessments
                else ""
            )
            return success_response(
                f"Created EBIOS RM study: {study.get('name')} (ID: {study.get('id')}){baseline_msg}",
                "create_ebios_rm_study",
                "Workshop 1: Study created. Add compliance assessments for security baseline, feared events, then RoTo couples",
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
        risk_origin: Risk origin name (required, e.g., "State", "states", "Organized crime", "organized_crime")
                     Supports case-insensitive and plural-insensitive matching against existing terminologies.
                     If no match is found, a new risk origin terminology will be created.
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

        # Smart resolve risk origin: matches against name, translations, case/plural insensitive
        # Creates new terminology if no match found
        risk_origin_id, was_created = _resolve_or_create_risk_origin(risk_origin)

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
            created_msg = (
                " (new risk origin terminology created)" if was_created else ""
            )
            return success_response(
                f"Created RoTo couple: {risk_origin} - {target_objective[:50]} (ID: {roto.get('id')}){created_msg}",
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
        category: Category name (required, e.g., "Partner", "partners", "Supplier", "Subcontractor")
                  Supports case-insensitive and plural-insensitive matching against existing terminologies.
                  If no match is found, a new category terminology will be created.
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

        # Smart resolve category: matches against name, translations, case/plural insensitive
        # Creates new terminology if no match found
        category_id, was_created = _resolve_or_create_stakeholder_category(category)

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
            created_msg = " (new category terminology created)" if was_created else ""
            return success_response(
                f"Created stakeholder (ID: {sh.get('id')}){created_msg}",
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
    """Create a strategic scenario in an EBIOS RM study (Workshop 3)

    Strategic scenarios are part of EBIOS RM Workshop 3 - Strategic Scenarios.
    They describe high-level attack scenarios based on RoTo couples.

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
                "Strategic scenario created (Workshop 3). Next: create attack paths for this scenario",
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
    """Create an attack path in a strategic scenario (Workshop 3)

    Attack paths are part of EBIOS RM Workshop 3 - Strategic Scenarios.
    They detail the paths an attacker might take through stakeholders.

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

        # Fetch the strategic scenario to get its ebios_rm_study (required by serializer)
        scenario_res = make_get_request(
            f"/ebios-rm/strategic-scenarios/{strategic_scenario_id}/"
        )
        if scenario_res.status_code != 200:
            return http_error_response(scenario_res.status_code, scenario_res.text)

        scenario_data = scenario_res.json()
        ebios_rm_study_id = scenario_data.get("ebios_rm_study", {}).get("id")

        if not ebios_rm_study_id:
            return error_response(
                "Invalid Data",
                "Could not determine EBIOS RM study from strategic scenario",
                "Verify the strategic scenario exists and has a valid study",
                retry_allowed=False,
            )

        payload = {
            "name": name,
            "strategic_scenario": strategic_scenario_id,
            "ebios_rm_study": ebios_rm_study_id,
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
                "Attack path created (Workshop 3). Next in Workshop 4: create operational scenarios",
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
    """Create an operational scenario from an attack path (Workshop 4)

    Operational scenarios are part of EBIOS RM Workshop 4 - Operational Scenarios.
    They describe concrete attack implementations derived from attack paths.

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
                "Operational scenario created (Workshop 4). Next: add operating modes to detail the attack",
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
    """Create an elementary action for use in operating modes (Workshop 4)

    Elementary actions are part of EBIOS RM Workshop 4 - Operational Scenarios.
    They represent atomic attack steps that compose operating modes.

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
                "Elementary action created (Workshop 4). Add it to operating modes to build kill chains",
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
    """Create an operating mode in an operational scenario (Workshop 4)

    Operating modes are part of EBIOS RM Workshop 4 - Operational Scenarios.
    They describe specific attack implementations using elementary actions.

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
                "Operating mode created (Workshop 4). Add elementary actions to build the kill chain",
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


async def create_kill_chain_step(
    operating_mode_id: str,
    elementary_action_id: str,
    is_highlighted: bool = False,
    logic_operator: str = None,
    antecedents: list = None,
) -> str:
    """Create a kill chain step linking an elementary action to an operating mode (Workshop 4)

    **Workflow:**
    1. First, associate elementary actions with the operating mode using update_operating_mode
       with the elementary_actions parameter
    2. Then, create kill chain steps to define the sequence and relationships between actions

    Kill chain steps define how elementary actions connect in a sequence via antecedent relationships.

    **Attack Stage Rules:**
    - Stage 0 (Know/Reconnaissance): Cannot have antecedents - these are starting points
    - Stage 1 (Enter/Initial Access): Can have antecedents from Stage 0 or 1
    - Stage 2 (Discover/Discovery): Can have antecedents from Stage 0, 1, or 2
    - Stage 3 (Exploit/Exploitation): Can have antecedents from any stage

    **Important:** Antecedents must already exist as kill chain steps in this operating mode.

    Args:
        operating_mode_id: Operating mode ID (required)
        elementary_action_id: Elementary action ID/name to add as a step (required)
        is_highlighted: Whether to highlight this step in visualizations
        logic_operator: "AND" or "OR" - how to combine multiple antecedents
        antecedents: List of elementary action IDs that must precede this action
                     (Must already be kill chain steps, stage must be <= this action's stage)
    """
    try:
        operating_mode_id = resolve_operating_mode_id(operating_mode_id)
        elementary_action_id = resolve_elementary_action_id(elementary_action_id)

        # Fetch the elementary action to get its attack stage for validation hints
        action_res = make_get_request(
            f"/ebios-rm/elementary-actions/{elementary_action_id}/"
        )
        if action_res.status_code != 200:
            return http_error_response(action_res.status_code, action_res.text)

        action_data = action_res.json()
        attack_stage = action_data.get("attack_stage", 0)
        stage_name = {0: "Know", 1: "Enter", 2: "Discover", 3: "Exploit"}.get(
            attack_stage, "Unknown"
        )

        # Stage 0 actions cannot have antecedents
        if attack_stage == 0 and antecedents:
            return error_response(
                "Validation Error",
                f"Elementary action is at Stage 0 ({stage_name}) and cannot have antecedents. Stage 0 actions are starting points.",
                "Remove antecedents for Stage 0 actions",
                retry_allowed=True,
            )

        payload = {
            "operating_mode": operating_mode_id,
            "elementary_action": elementary_action_id,
            "is_highlighted": is_highlighted,
        }

        if logic_operator:
            payload["logic_operator"] = logic_operator

        if antecedents:
            resolved_antecedents = []
            for ant in antecedents:
                resolved_antecedents.append(resolve_elementary_action_id(ant))
            payload["antecedents"] = resolved_antecedents

        res = make_post_request("/ebios-rm/kill-chains/", payload)

        if res.status_code == 201:
            kc = res.json()
            antecedent_info = (
                f" with {len(antecedents)} antecedent(s)" if antecedents else ""
            )
            return success_response(
                f"Added kill chain step (ID: {kc.get('id')}) - Stage {attack_stage} ({stage_name}){antecedent_info}",
                "create_kill_chain_step",
                "Workshop 4: Kill chain step added. Use get_kill_chains to see the full chain.",
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
    compliance_assessments: list = None,
) -> str:
    """Update an EBIOS RM study (Workshop 1)

    **Workshop 1 - Security Baseline:**
    Use compliance_assessments to manage the audits (compliance assessments) that form
    the security baseline for this study. You can add existing audits or suggest creating
    new ones with create_compliance_assessment.

    Args:
        study_id: Study ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        version: New version string
        status: planned | in_progress | in_review | done | deprecated
        observation: Observation notes
        assets: List of asset IDs/names (replaces existing)
        compliance_assessments: List of compliance assessment (audit) IDs/names for security baseline (replaces existing)
    """
    try:
        from ..resolvers import resolve_compliance_assessment_id

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

        if compliance_assessments is not None:
            resolved_assessments = []
            for assessment in compliance_assessments:
                resolved_assessments.append(
                    resolve_compliance_assessment_id(assessment)
                )
            payload["compliance_assessments"] = resolved_assessments

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/studies/{resolved_study_id}/", payload)

        if res.status_code == 200:
            study = res.json()
            baseline_msg = (
                f" (security baseline: {len(compliance_assessments)} audit(s))"
                if compliance_assessments
                else ""
            )
            return success_response(
                f"Updated EBIOS RM study: {study.get('name')} (ID: {study.get('id')}){baseline_msg}",
                "update_ebios_rm_study",
                "Workshop 1: Study updated. Use get_audits_progress to see available audits for security baseline.",
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
    """Update an operating mode (Workshop 4)

    **Kill Chain Workflow:**
    1. Use this function to associate elementary actions with the operating mode
    2. Then use create_kill_chain_step to define the sequence and relationships

    Args:
        mode_id: Operating mode ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        likelihood: Likelihood level (-1 for not rated, 0+ based on risk matrix)
        elementary_actions: List of elementary action IDs/names to associate (replaces existing).
                            This is the first step before creating kill chain steps.
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


async def update_kill_chain_step(
    kill_chain_id: str,
    is_highlighted: bool = None,
    logic_operator: str = None,
    antecedents: list = None,
) -> str:
    """Update a kill chain step (Workshop 4)

    Updates an existing kill chain step's properties (antecedents, highlighting, logic operator).

    **Attack Stage Rules for antecedents:**
    - Stage 0 (Know/Reconnaissance): Cannot have antecedents - these are starting points
    - Stage 1 (Enter/Initial Access): Can have antecedents from Stage 0 or 1
    - Stage 2 (Discover/Discovery): Can have antecedents from Stage 0, 1, or 2
    - Stage 3 (Exploit/Exploitation): Can have antecedents from any stage

    **Important:** Antecedents must already exist as kill chain steps in the same operating mode.

    Args:
        kill_chain_id: Kill chain step UUID (required)
        is_highlighted: Whether to highlight this step in visualizations
        logic_operator: "AND" or "OR" - how to combine multiple antecedents
        antecedents: List of elementary action IDs that must precede this action
                     (Must already be kill chain steps, stage must be <= this action's stage)
    """
    try:
        resolved_kc_id = resolve_kill_chain_id(kill_chain_id)

        # Fetch the kill chain step to get its elementary action's attack stage
        kc_res = make_get_request(f"/ebios-rm/kill-chains/{resolved_kc_id}/")
        if kc_res.status_code != 200:
            return http_error_response(kc_res.status_code, kc_res.text)

        kc_data = kc_res.json()
        elementary_action = kc_data.get("elementary_action", {})
        attack_stage = elementary_action.get("attack_stage", 0)
        stage_name = {0: "Know", 1: "Enter", 2: "Discover", 3: "Exploit"}.get(
            attack_stage, "Unknown"
        )

        # Stage 0 actions cannot have antecedents
        if attack_stage == 0 and antecedents:
            return error_response(
                "Validation Error",
                f"Elementary action is at Stage 0 ({stage_name}) and cannot have antecedents. Stage 0 actions are starting points.",
                "Remove antecedents for Stage 0 actions",
                retry_allowed=True,
            )

        payload = {}

        if is_highlighted is not None:
            payload["is_highlighted"] = is_highlighted
        if logic_operator is not None:
            payload["logic_operator"] = logic_operator

        if antecedents is not None:
            resolved_antecedents = []
            for ant in antecedents:
                resolved_antecedents.append(resolve_elementary_action_id(ant))
            payload["antecedents"] = resolved_antecedents

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/ebios-rm/kill-chains/{resolved_kc_id}/", payload)

        if res.status_code == 200:
            kc = res.json()
            antecedent_info = (
                f" with {len(antecedents)} antecedent(s)" if antecedents else ""
            )
            return success_response(
                f"Updated kill chain step (ID: {kc.get('id')}) - Stage {attack_stage} ({stage_name}){antecedent_info}",
                "update_kill_chain_step",
                "Workshop 4: Kill chain step updated. Use get_kill_chains to see the full chain.",
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
