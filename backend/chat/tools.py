"""
Tool definitions for LLM function calling.
The LLM picks which tool to call and with what parameters.
Our code executes the safe, pre-built ORM queries.

Enum values for filters are derived from the Django models at import time,
so they stay in sync with model field choices without duplication.

Architecture:
    - Generic tools (query_objects, propose_create) are always available.
    - Contextual tools (attach_existing) use page context to scope operations.
    - PARENT_CHILD_MAP and ATTACHABLE_RELATIONS are declarative registries —
      adding a new relationship is a one-line addition.
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
    "folder": ("iam", "Folder", "Domains", "folders"),
}

# Models the LLM is allowed to propose creating.
# Excludes complex models (framework, compliance_assessment, requirement_assessment, folder)
# and models that require special setup flows.
CREATABLE_MODELS = {
    "applied_control",
    "asset",
    "risk_scenario",
    "threat",
    "evidence",
    "vulnerability",
    "security_exception",
    "incident",
    "entity",
    "solution",
}

# --- Declarative relationship registries ---
# Adding a new contextual relationship = one line here. No logic changes needed.

# Parent → children via FK.  parent_model_key → [(child_model_key, fk_field_on_child)]
PARENT_CHILD_MAP: dict[str, list[tuple[str, str]]] = {
    "risk_assessment": [
        ("risk_scenario", "risk_assessment"),
    ],
    "compliance_assessment": [
        # requirement_assessments are auto-created by the framework, not user-created
    ],
}

# Parent → attachable objects via M2M.  parent_model_key → [(related_model_key, m2m_field_on_parent)]
ATTACHABLE_RELATIONS: dict[str, list[tuple[str, str]]] = {
    "requirement_assessment": [
        ("applied_control", "applied_controls"),
        ("evidence", "evidences"),
    ],
    "risk_scenario": [
        ("applied_control", "applied_controls"),
        ("threat", "threats"),
        ("asset", "assets"),
        ("vulnerability", "vulnerabilities"),
    ],
    "compliance_assessment": [
        ("asset", "assets"),
        ("evidence", "evidences"),
    ],
    "applied_control": [
        ("evidence", "evidences"),
    ],
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
                "'stakeholders'/'parties prenantes' → stakeholder, "
                "'domains'/'domaines'/'folders'/'dossiers'/'projects'/'projets' → folder. "
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
        "related_filter": {
            "type": "object",
            "description": (
                "Filter objects based on properties of their related objects. "
                "Use this for compound queries like 'controls with expired evidences', "
                "'controls with evidences lacking files', 'requirements with overdue controls', "
                "'risk scenarios with deprecated controls'. "
                "Combine with has_related/has_no_related for multi-relation queries."
            ),
            "properties": {
                "relation": {
                    "type": "string",
                    "description": (
                        "The relation field name to filter on (e.g., 'evidences', "
                        "'applied_controls', 'threats', 'assets')"
                    ),
                },
                "condition": {
                    "type": "string",
                    "enum": [
                        "status_is",
                        "status_not",
                        "overdue",
                        "no_attachment",
                        "result_is",
                        "treatment_is",
                    ],
                    "description": (
                        "The condition to check on related objects: "
                        "status_is/status_not (filter by related status), "
                        "overdue (related objects past their ETA/expiry), "
                        "no_attachment (evidences without uploaded files), "
                        "result_is (requirement assessment result), "
                        "treatment_is (risk scenario treatment)"
                    ),
                },
                "value": {
                    "type": "string",
                    "description": "Value for status_is/status_not/result_is/treatment_is conditions",
                },
            },
            "required": ["relation", "condition"],
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

    # --- propose_create tool ---
    propose_create_tool = {
        "type": "function",
        "function": {
            "name": "propose_create",
            "description": (
                "Propose creating one or more GRC objects. Use this when the user asks to "
                "create, add, or import objects like controls, assets, threats, risk scenarios, etc. "
                "The objects will NOT be created immediately — the user will review and confirm. "
                "You can propose multiple objects at once by providing an array of items."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "enum": sorted(CREATABLE_MODELS),
                        "description": (
                            "The type of object to create. Same mapping as query_objects: "
                            "'controls' → applied_control, 'assets' → asset, "
                            "'risk scenarios' → risk_scenario, 'threats' → threat, "
                            "'evidences' → evidence, 'vulnerabilities' → vulnerability, "
                            "'exceptions' → security_exception, 'incidents' → incident, "
                            "'entities'/'third parties' → entity, 'solutions' → solution."
                        ),
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the object to create (required)",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional description",
                                },
                            },
                            "required": ["name"],
                        },
                        "description": (
                            "List of objects to create. Each must have at least a 'name'. "
                            "Parse user input intelligently: comma-separated lists, "
                            "line-by-line lists, or natural language descriptions."
                        ),
                    },
                    "domain": {
                        "type": "string",
                        "description": "Target domain/folder name for the new objects (e.g. 'DEMO', 'Production')",
                    },
                },
                "required": ["model", "items"],
            },
        },
    }

    # --- attach_existing tool ---
    attachable_model_keys = set()
    for relations in ATTACHABLE_RELATIONS.values():
        for related_key, _ in relations:
            attachable_model_keys.add(related_key)

    attach_existing_tool = {
        "type": "function",
        "function": {
            "name": "attach_existing",
            "description": (
                "Search for existing objects and propose attaching/linking them to the "
                "object on the user's current page. Use this tool when:\n"
                "- The user says 'attach', 'link', 'add existing', 'associate' controls, evidences, etc.\n"
                "- The user asks what controls to implement, what to add, or how to comply with a requirement.\n"
                "- The user asks for suggestions or recommendations for the current item.\n"
                "This only works when the user is on a detail/edit page. "
                "If no search term is provided, the system will automatically suggest relevant objects "
                "based on the current item's context. The user will confirm before anything is linked."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "related_model": {
                        "type": "string",
                        "enum": sorted(attachable_model_keys),
                        "description": (
                            "Type of object to search for and attach. "
                            "Same mapping as query_objects model names. "
                            "When the user asks about 'controls to implement' or 'measures', "
                            "use 'applied_control'."
                        ),
                    },
                    "search": {
                        "type": "string",
                        "description": (
                            "Optional search term to find objects to attach. "
                            "Searches in name, description, and ref_id. "
                            "If omitted, the system suggests objects based on the current item's context."
                        ),
                    },
                },
                "required": ["related_model"],
            },
        },
    }

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
        propose_create_tool,
        attach_existing_tool,
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
        if k in ("has_related", "has_no_related", "items"):
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


def _build_create_proposal(
    arguments: dict, accessible_folder_ids: list[str], parsed_context=None
) -> dict | None:
    """
    Build a structured creation proposal from LLM tool call arguments.
    Does NOT create anything — returns a proposal for the frontend to confirm.

    If parsed_context is provided and the target model is a child of the context
    parent (via PARENT_CHILD_MAP), auto-injects the parent FK into each item.
    """
    model_key = arguments.get("model")
    if model_key not in CREATABLE_MODELS or model_key not in MODEL_MAP:
        return None

    app_label, model_name, display_name, url_slug = MODEL_MAP[model_key]

    items = arguments.get("items", [])
    if not items:
        return None

    # Resolve folder: from parent context, domain argument, or first accessible
    folder_id = None
    parent_fk_field = None
    parent_id = None

    # Check if creating a child of the current page's object
    if parsed_context and parsed_context.object_id:
        for child_key, fk_field in PARENT_CHILD_MAP.get(parsed_context.model_key, []):
            if child_key == model_key:
                parent_fk_field = fk_field
                parent_id = parsed_context.object_id
                # Inherit folder from parent object
                parent_info = MODEL_MAP.get(parsed_context.model_key)
                if parent_info:
                    try:
                        parent_model = apps.get_model(parent_info[0], parent_info[1])
                        parent_obj = parent_model.objects.filter(id=parent_id).first()
                        if parent_obj and hasattr(parent_obj, "folder_id"):
                            folder_id = str(parent_obj.folder_id)
                    except Exception:
                        pass
                break

    if not folder_id:
        domain = arguments.get("domain")
        if domain:
            from .orm_query import _resolve_domain

            folder_ids = _resolve_domain(domain, accessible_folder_ids)
            if folder_ids:
                folder_id = folder_ids[0]

    if not folder_id and accessible_folder_ids:
        folder_id = accessible_folder_ids[0]

    # Build proposal items — each gets name, description, folder, and parent FK
    proposal_items = []
    for item in items:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict) or not item.get("name"):
            continue
        entry = {"name": item["name"].strip()}
        if item.get("description"):
            entry["description"] = item["description"].strip()
        if folder_id:
            entry["folder"] = folder_id
        if parent_fk_field and parent_id:
            entry[parent_fk_field] = parent_id
        proposal_items.append(entry)

    if not proposal_items:
        return None

    return {
        "type": "propose_create",
        "model_key": model_key,
        "model_name": model_name,
        "display_name": display_name,
        "url_slug": url_slug,
        "folder_id": folder_id,
        "items": proposal_items,
    }


def _build_attach_proposal(
    arguments: dict, accessible_folder_ids: list[str], parsed_context=None
) -> dict | None:
    """
    Search for existing objects and propose attaching them to the current page's object.
    Returns a proposal dict with type="propose_attach".
    """
    if not parsed_context or not parsed_context.object_id:
        return None

    related_model_key = arguments.get("related_model")
    if not related_model_key or related_model_key not in MODEL_MAP:
        return None

    # Validate this attachment is allowed
    relations = ATTACHABLE_RELATIONS.get(parsed_context.model_key, [])
    m2m_field = None
    for rel_key, rel_field in relations:
        if rel_key == related_model_key:
            m2m_field = rel_field
            break

    if not m2m_field:
        return None

    # Get parent info
    parent_info = MODEL_MAP.get(parsed_context.model_key)
    if not parent_info:
        return None

    parent_url_slug = parent_info[3]
    parent_display = parent_info[2]
    related_info = MODEL_MAP[related_model_key]
    related_display = related_info[2]

    # Search for matching objects
    search = arguments.get("search", "")
    from .orm_query import execute_tool_query

    # Smart suggest mode: when on a requirement assessment page looking for controls,
    # and no explicit search term, use the requirement's name/description to search
    if (
        not search
        and parsed_context.model_key == "requirement_assessment"
        and related_model_key == "applied_control"
    ):
        try:
            parent_model = apps.get_model(parent_info[0], parent_info[1])
            ra_obj = (
                parent_model.objects.select_related("requirement")
                .filter(id=parsed_context.object_id)
                .first()
            )
            if ra_obj and hasattr(ra_obj, "requirement") and ra_obj.requirement:
                req = ra_obj.requirement
                # Use the requirement's description or name as search context
                search = req.description[:200] if req.description else (req.name or "")
        except Exception:
            pass

    query_args = {
        "model": related_model_key,
        "action": "list",
    }
    if search:
        query_args["search"] = search

    query_result = execute_tool_query(query_args, accessible_folder_ids)
    if not query_result or not query_result.get("objects"):
        return None

    # Get already-attached IDs to exclude them
    try:
        parent_model = apps.get_model(parent_info[0], parent_info[1])
        parent_obj = parent_model.objects.filter(id=parsed_context.object_id).first()
        if parent_obj:
            existing_ids = set(
                str(pk)
                for pk in getattr(parent_obj, m2m_field).values_list("id", flat=True)
            )
        else:
            existing_ids = set()
    except Exception:
        existing_ids = set()

    # Filter out already-attached objects
    available = [
        obj for obj in query_result["objects"] if obj["id"] not in existing_ids
    ]
    if not available:
        return None

    return {
        "type": "propose_attach",
        "parent_model_key": parsed_context.model_key,
        "parent_id": parsed_context.object_id,
        "parent_url_slug": parent_url_slug,
        "parent_display": parent_display,
        "m2m_field": m2m_field,
        "related_model_key": related_model_key,
        "related_display": related_display,
        "items": [
            {"id": obj["id"], "name": obj["name"]}
            for obj in available[:20]  # Cap at 20 suggestions
        ],
        "total_available": len(available),
    }


def dispatch_tool_call(
    tool_name: str,
    arguments: dict,
    accessible_folder_ids: list[str],
    parsed_context=None,
) -> dict | None:
    """
    Execute a tool call from the LLM.
    Returns a result dict compatible with format_query_result(),
    or a proposal dict for propose_create / propose_attach.
    """
    cleaned = _sanitize_arguments(arguments)

    if tool_name == "query_objects":
        from .orm_query import execute_tool_query

        return execute_tool_query(cleaned, accessible_folder_ids, parsed_context)

    if tool_name == "propose_create":
        return _build_create_proposal(cleaned, accessible_folder_ids, parsed_context)

    if tool_name == "attach_existing":
        return _build_attach_proposal(cleaned, accessible_folder_ids, parsed_context)

    logger.warning("Unknown tool: %s", tool_name)
    return None
