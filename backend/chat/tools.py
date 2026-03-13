"""
Tool definitions for LLM function calling.
The LLM picks which tool to call and with what parameters.
Our code executes the safe, pre-built ORM queries.

Enum values for filters are derived from the Django models at import time,
so they stay in sync with model field choices without duplication.
"""

import logging

from django.apps import apps

logger = logging.getLogger(__name__)


# Maps tool model param values to (app_label, model_name, display_name, url_slug)
MODEL_MAP = {
    "applied_control": (
        "core",
        "AppliedControl",
        "Applied Controls",
        "applied-controls",
    ),
    "asset": ("core", "Asset", "Assets", "assets"),
    "risk_scenario": ("core", "RiskScenario", "Risk Scenarios", "risk-scenarios"),
    "risk_assessment": (
        "core",
        "RiskAssessment",
        "Risk Assessments",
        "risk-assessments",
    ),
    "compliance_assessment": (
        "core",
        "ComplianceAssessment",
        "Compliance Assessments",
        "compliance-assessments",
    ),
    "threat": ("core", "Threat", "Threats", "threats"),
    "evidence": ("core", "Evidence", "Evidences", "evidences"),
    "vulnerability": ("core", "Vulnerability", "Vulnerabilities", "vulnerabilities"),
    "security_exception": (
        "core",
        "SecurityException",
        "Security Exceptions",
        "security-exceptions",
    ),
    "incident": ("core", "Incident", "Incidents", "incidents"),
    "risk_acceptance": (
        "core",
        "RiskAcceptance",
        "Risk Acceptances",
        "risk-acceptances",
    ),
    "requirement_assessment": (
        "core",
        "RequirementAssessment",
        "Requirement Assessments",
        "requirement-assessments",
    ),
    "framework": ("core", "Framework", "Frameworks", "frameworks"),
    "entity": ("tprm", "Entity", "Entities", "entities"),
    "solution": ("tprm", "Solution", "Solutions", "solutions"),
    "contract": ("tprm", "Contract", "Contracts", "contracts"),
    "entity_assessment": (
        "tprm",
        "EntityAssessment",
        "Entity Assessments",
        "entity-assessments",
    ),
    "ebios_rm_study": (
        "ebios_rm",
        "EbiosRMStudy",
        "EBIOS RM Studies",
        "ebios-rm-studies",
    ),
    "feared_event": ("ebios_rm", "FearedEvent", "Feared Events", "feared-events"),
    "stakeholder": ("ebios_rm", "Stakeholder", "Stakeholders", "stakeholders"),
}


def _get_field_choices(
    app_label: str, model_name: str, field_name: str
) -> list[str] | None:
    """Extract choice values from a Django model field, returns None if field has no choices."""
    try:
        model = apps.get_model(app_label, model_name)
        field = model._meta.get_field(field_name)
        if field.choices:
            return [choice[0] for choice in field.choices if choice[0]]
    except (LookupError, Exception):
        pass
    return None


def _build_filter_properties() -> tuple[dict, dict]:
    """
    Build filter properties for the tool schema and a valid-values lookup,
    both derived from actual Django model field choices.
    Returns (properties_dict, valid_values_dict).
    """
    valid_values = {
        "model": set(MODEL_MAP.keys()),
        "action": {"list", "count", "summary"},
        "date_filter": {
            "overdue",
            "due_this_month",
            "expiring_this_month",
            "created_recently",
        },
    }

    # Derive enum values from model fields
    # Use AppliedControl as the reference for category/effort/status/priority
    category_choices = _get_field_choices("core", "AppliedControl", "category")
    effort_choices = _get_field_choices("core", "AppliedControl", "effort")
    treatment_choices = _get_field_choices("core", "RiskScenario", "treatment")
    result_choices = _get_field_choices("core", "RequirementAssessment", "result")

    properties = {}

    if treatment_choices:
        properties["treatment"] = {
            "type": "string",
            "enum": treatment_choices,
            "description": "Filter risk scenarios by treatment",
        }
        valid_values["treatment"] = set(treatment_choices)

    if result_choices:
        properties["result"] = {
            "type": "string",
            "enum": result_choices,
            "description": "Filter requirement assessments by compliance result",
        }
        valid_values["result"] = set(result_choices)

    if category_choices:
        properties["category"] = {
            "type": "string",
            "enum": category_choices,
            "description": (
                "Filter applied controls by their category sub-type. "
                "Only use this when the user explicitly asks to filter by category "
                "(e.g. 'show me technical controls'). Do NOT set this just because "
                "the user says 'controls' — that refers to the model, not the category."
            ),
        }
        valid_values["category"] = set(category_choices)

    if effort_choices:
        properties["effort"] = {
            "type": "string",
            "enum": effort_choices,
            "description": "Filter applied controls by effort level",
        }
        valid_values["effort"] = set(effort_choices)

    return properties, valid_values


def _build_tools() -> tuple[list[dict], dict]:
    """Build the TOOLS list and VALID_VALUES dict. Called once at first use."""
    filter_properties, valid_values = _build_filter_properties()

    properties = {
        "model": {
            "type": "string",
            "enum": sorted(MODEL_MAP.keys()),
            "description": (
                "The type of object to query. Mapping: "
                "'controls'/'measures'/'mesures'/'contrôles' → applied_control, "
                "'assets'/'actifs' → asset, "
                "'risk scenarios'/'scénarios de risque' → risk_scenario, "
                "'risk assessments'/'analyses de risque' → risk_assessment, "
                "'audits'/'compliance assessments' → compliance_assessment, "
                "'threats'/'menaces' → threat, "
                "'evidences'/'preuves' → evidence, "
                "'vulnerabilities'/'vulnérabilités' → vulnerability, "
                "'exceptions' → security_exception, "
                "'incidents' → incident, "
                "'risk acceptances'/'acceptations de risque' → risk_acceptance, "
                "'requirement assessments'/'exigences' → requirement_assessment, "
                "'frameworks'/'référentiels' → framework, "
                "'entities'/'entités'/'third parties'/'tiers' → entity, "
                "'solutions' → solution, "
                "'contracts'/'contrats' → contract, "
                "'entity assessments' → entity_assessment, "
                "'EBIOS RM studies'/'études EBIOS' → ebios_rm_study, "
                "'feared events'/'événements redoutés' → feared_event, "
                "'stakeholders'/'parties prenantes' → stakeholder. "
                "IMPORTANT: when the user says 'controls' without further qualification, "
                "use applied_control as the model with NO category filter."
            ),
        },
        "action": {
            "type": "string",
            "enum": ["list", "count", "summary"],
            "description": "list: return objects, count: return count, summary: return breakdown by status/category/etc",
        },
        "domain": {
            "type": "string",
            "description": "Filter by domain/folder name (e.g. 'DEMO', 'Production')",
        },
        "status": {
            "type": "string",
            "description": "Filter by status (e.g. 'active', 'in_progress', 'to_do', 'done', 'draft', 'open', 'closed')",
        },
        "priority": {
            "type": "integer",
            "minimum": 1,
            "maximum": 4,
            "description": "Filter by priority (1=critical/P1, 2=high/P2, 3=medium/P3, 4=low/P4)",
        },
        "severity": {
            "type": "integer",
            "minimum": 1,
            "maximum": 6,
            "description": "Filter by severity (1=critical, 2=major, 3=significant, 4=minor, 5=negligible, 6=unknown)",
        },
        "date_filter": {
            "type": "string",
            "enum": [
                "overdue",
                "due_this_month",
                "expiring_this_month",
                "created_recently",
            ],
            "description": "Filter by date condition",
        },
        "has_related": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Only return objects that HAVE at least one related object for each listed relationship. "
                "Use the relationship field name as it exists on the model. Examples: "
                "'evidences' (controls with evidence), 'applied_controls' (risk scenarios with controls), "
                "'assets' (controls linked to assets), 'owner' (objects with an owner), "
                "'threats' (risk scenarios with threats), 'vulnerabilities' (risk scenarios with vulnerabilities). "
                "The field names are validated against the actual model — invalid names are ignored."
            ),
        },
        "has_no_related": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Only return objects that have NO related object for each listed relationship. "
                "Same field names as has_related. Examples: "
                "'evidences' (controls WITHOUT evidence), 'owner' (objects with no owner), "
                "'applied_controls' (risk scenarios with no controls)."
            ),
        },
        "search": {
            "type": "string",
            "description": "Search in name, description, or ref_id",
        },
        "page": {
            "type": "integer",
            "minimum": 1,
            "description": "Page number for paginated results (default: 1)",
        },
    }

    # Merge in model-derived filter properties
    properties.update(filter_properties)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_objects",
                "description": (
                    "Query, list, count, or get a summary of objects in the GRC system. "
                    "Use this for any question about assets, controls, risk scenarios, "
                    "compliance assessments, threats, incidents, evidences, vulnerabilities, "
                    "security exceptions, risk acceptances, frameworks, entities, solutions, "
                    "contracts, or any other GRC object."
                ),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": ["model", "action"],
                },
            },
        },
    ]

    return tools, valid_values


# Lazy-initialized at first use (needs Django apps to be ready)
_tools_cache: list[dict] | None = None
_valid_values_cache: dict | None = None


def get_tools() -> list[dict]:
    """Get tool definitions, building them on first call."""
    global _tools_cache, _valid_values_cache
    if _tools_cache is None:
        _tools_cache, _valid_values_cache = _build_tools()
    return _tools_cache


def _get_valid_values() -> dict:
    """Get valid values for sanitization, building them on first call."""
    global _tools_cache, _valid_values_cache
    if _valid_values_cache is None:
        _tools_cache, _valid_values_cache = _build_tools()
    return _valid_values_cache


def _sanitize_arguments(arguments: dict) -> dict:
    """
    Clean up LLM tool call arguments:
    - Remove null/None/empty values
    - Validate enum fields against model-derived allowed values
    """
    valid_values = _get_valid_values()
    cleaned = {}
    for k, v in arguments.items():
        # Skip junk values LLMs love to send
        if v is None or v == "":
            continue
        if isinstance(v, str) and v.lower() in (
            "null",
            "none",
            "nil",
            "n/a",
            "undefined",
        ):
            continue

        # Coerce array fields (LLM may send a single string instead of an array)
        if k in ("has_related", "has_no_related"):
            if isinstance(v, str):
                v = [v]
            if not isinstance(v, list) or not v:
                continue

        # Validate enum fields against model-derived allowed values
        if k in valid_values and v not in valid_values[k]:
            logger.info("Dropping invalid value for %s: %r", k, v)
            continue

        cleaned[k] = v

    return cleaned


def dispatch_tool_call(
    tool_name: str,
    arguments: dict,
    accessible_folder_ids: list[str],
) -> dict | None:
    """
    Execute a tool call from the LLM.
    Returns a result dict compatible with format_query_result().
    """
    if tool_name != "query_objects":
        logger.warning("Unknown tool: %s", tool_name)
        return None

    cleaned = _sanitize_arguments(arguments)

    from .orm_query import execute_tool_query

    return execute_tool_query(cleaned, accessible_folder_ids)
