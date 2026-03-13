"""
ORM query layer for structured object queries from chat.
Detects user intent (list/count/filter) and queries Django models directly,
respecting folder-level permissions.
"""

import logging
import re
from datetime import timedelta

from django.apps import apps
from django.db.models import Q, Count
from django.utils import timezone

logger = logging.getLogger(__name__)

# Model registry: maps natural language aliases to (app_label, model_name, display_name)
MODEL_REGISTRY = {
    # Core
    "asset": ("core", "Asset", "Assets"),
    "assets": ("core", "Asset", "Assets"),
    "control": ("core", "AppliedControl", "Applied Controls"),
    "controls": ("core", "AppliedControl", "Applied Controls"),
    "applied control": ("core", "AppliedControl", "Applied Controls"),
    "applied controls": ("core", "AppliedControl", "Applied Controls"),
    "measure": ("core", "AppliedControl", "Applied Controls"),
    "measures": ("core", "AppliedControl", "Applied Controls"),
    "risk scenario": ("core", "RiskScenario", "Risk Scenarios"),
    "risk scenarios": ("core", "RiskScenario", "Risk Scenarios"),
    "risk": ("core", "RiskScenario", "Risk Scenarios"),
    "risks": ("core", "RiskScenario", "Risk Scenarios"),
    "risk assessment": ("core", "RiskAssessment", "Risk Assessments"),
    "risk assessments": ("core", "RiskAssessment", "Risk Assessments"),
    "compliance assessment": ("core", "ComplianceAssessment", "Compliance Assessments"),
    "compliance assessments": (
        "core",
        "ComplianceAssessment",
        "Compliance Assessments",
    ),
    "audit": ("core", "ComplianceAssessment", "Compliance Assessments"),
    "audits": ("core", "ComplianceAssessment", "Compliance Assessments"),
    "threat": ("core", "Threat", "Threats"),
    "threats": ("core", "Threat", "Threats"),
    "evidence": ("core", "Evidence", "Evidences"),
    "evidences": ("core", "Evidence", "Evidences"),
    "vulnerability": ("core", "Vulnerability", "Vulnerabilities"),
    "vulnerabilities": ("core", "Vulnerability", "Vulnerabilities"),
    "security exception": ("core", "SecurityException", "Security Exceptions"),
    "security exceptions": ("core", "SecurityException", "Security Exceptions"),
    "exception": ("core", "SecurityException", "Security Exceptions"),
    "exceptions": ("core", "SecurityException", "Security Exceptions"),
    "incident": ("core", "Incident", "Incidents"),
    "incidents": ("core", "Incident", "Incidents"),
    "risk acceptance": ("core", "RiskAcceptance", "Risk Acceptances"),
    "risk acceptances": ("core", "RiskAcceptance", "Risk Acceptances"),
    "requirement assessment": (
        "core",
        "RequirementAssessment",
        "Requirement Assessments",
    ),
    "requirement assessments": (
        "core",
        "RequirementAssessment",
        "Requirement Assessments",
    ),
    "framework": ("core", "Framework", "Frameworks"),
    "frameworks": ("core", "Framework", "Frameworks"),
    # TPRM
    "entity": ("tprm", "Entity", "Entities"),
    "entities": ("tprm", "Entity", "Entities"),
    "solution": ("tprm", "Solution", "Solutions"),
    "solutions": ("tprm", "Solution", "Solutions"),
    "contract": ("tprm", "Contract", "Contracts"),
    "contracts": ("tprm", "Contract", "Contracts"),
    "entity assessment": ("tprm", "EntityAssessment", "Entity Assessments"),
    "entity assessments": ("tprm", "EntityAssessment", "Entity Assessments"),
    # EBIOS RM
    "ebios study": ("ebios_rm", "EbiosRMStudy", "EBIOS RM Studies"),
    "ebios studies": ("ebios_rm", "EbiosRMStudy", "EBIOS RM Studies"),
    "feared event": ("ebios_rm", "FearedEvent", "Feared Events"),
    "feared events": ("ebios_rm", "FearedEvent", "Feared Events"),
    "stakeholder": ("ebios_rm", "Stakeholder", "Stakeholders"),
    "stakeholders": ("ebios_rm", "Stakeholder", "Stakeholders"),
}

# Status value aliases for natural language matching
STATUS_ALIASES = {
    # AppliedControl
    "to do": "to_do",
    "todo": "to_do",
    "in progress": "in_progress",
    "on hold": "on_hold",
    "active": "active",
    "deprecated": "deprecated",
    # RequirementAssessment
    "in review": "in_review",
    "done": "done",
    # RequirementAssessment results
    "compliant": "compliant",
    "non compliant": "non_compliant",
    "non-compliant": "non_compliant",
    "partially compliant": "partially_compliant",
    "partially-compliant": "partially_compliant",
    "not assessed": "not_assessed",
    "not applicable": "not_applicable",
    # Evidence
    "draft": "draft",
    "missing": "missing",
    "approved": "approved",
    "rejected": "rejected",
    "expired": "expired",
    # Incident
    "new": "new",
    "ongoing": "ongoing",
    "resolved": "resolved",
    "closed": "closed",
    "dismissed": "dismissed",
    # RiskScenario treatment
    "open": "open",
    "mitigate": "mitigate",
    "accept": "accept",
    "avoid": "avoid",
    "transfer": "transfer",
    # General
    "planned": "planned",
    "terminated": "terminated",
}

# Priority aliases
PRIORITY_ALIASES = {
    "p1": 1,
    "critical": 1,
    "highest": 1,
    "p2": 2,
    "high": 2,
    "p3": 3,
    "medium": 3,
    "p4": 4,
    "low": 4,
}

# Severity aliases (Incident)
SEVERITY_ALIASES = {
    "critical": 1,
    "major": 2,
    "significant": 3,
    "minor": 4,
    "negligible": 5,
    "unknown": 6,
}

# Category aliases (AppliedControl)
CATEGORY_ALIASES = {
    "policy": "policy",
    "process": "process",
    "technical": "technical",
    "physical": "physical",
}

# Effort aliases (AppliedControl)
EFFORT_ALIASES = {
    "xs": "XS",
    "extra small": "XS",
    "s": "S",
    "small": "S",
    "m": "M",
    "medium": "M",
    "l": "L",
    "large": "L",
    "xl": "XL",
    "extra large": "XL",
}

# Maximum objects to return in a list query before auto-switching to summary
MAX_LIST_RESULTS = 30
# Page size for paginated list results
LIST_PAGE_SIZE = 20


def detect_intent(query: str) -> str:
    """
    Classify the user query as 'query' (structured ORM), 'search' (semantic RAG), or 'general'.
    Returns 'query' if the user is asking to list/count/filter objects.
    """
    q = query.lower().strip()

    # Patterns that indicate structured queries
    query_patterns = [
        r"\b(list|show|display|give me|what are|get|find)\b.*\b("
        + "|".join(_get_model_keywords())
        + r")\b",
        r"\b(how many|count|number of|total)\b.*\b("
        + "|".join(_get_model_keywords())
        + r")\b",
        r"\b("
        + "|".join(_get_model_keywords())
        + r")\b.*(with|that are|that have|where|status|in progress|overdue|expiring|expired)",
        r"\b(overdue|expiring|expired|upcoming)\b.*\b("
        + "|".join(_get_model_keywords())
        + r")\b",
        r"\b(summary|overview|dashboard|stats|statistics)\b",
        r"\b("
        + "|".join(_get_model_keywords())
        + r")\b.*\b(on|in|from)\s+(domain|folder|project)\b",
        r"\b(domain|folder|project)\s+\w+.*\b("
        + "|".join(_get_model_keywords())
        + r")\b",
    ]

    for pattern in query_patterns:
        if re.search(pattern, q):
            return "query"

    return "search"


def detect_followup(query: str) -> dict | None:
    """
    Detect if the user query is a follow-up to a previous ORM query.
    Returns a dict describing the follow-up action, or None.

    Handles: "list them", "show them", "can you list them", "next page",
    "show more", "page 3", "give me the details", etc.
    """
    q = query.lower().strip()

    # Pagination follow-ups
    page_match = re.search(r"\bpage\s+(\d+)\b", q)
    if page_match:
        return {"action": "paginate", "page": int(page_match.group(1))}

    if re.search(
        r"\b(next page|next batch|show more|more results|continue listing)\b", q
    ):
        return {"action": "next_page"}

    # List follow-ups: "list them", "show them all", "can you list them", "display them"
    if re.search(
        r"\b(list|show|display|give|enumerate|see)\b.*\b(them|those|these|all|the rest|details)\b",
        q,
    ):
        return {"action": "list"}

    # "yes" / "sure" / "go ahead" after a "want me to list them?" type prompt
    if re.search(r"^(yes|sure|go ahead|please|ok|yeah|yep|do it)\b", q):
        return {"action": "list"}

    return None


def execute_followup(
    followup: dict,
    previous_query_meta: dict,
    accessible_folder_ids: list[str],
) -> dict | None:
    """
    Re-execute a previous ORM query with modified parameters (e.g., list instead of count,
    or next page).

    previous_query_meta should contain: model_name, app_label, filters, page, query_type
    """
    app_label = previous_query_meta.get("app_label")
    model_name = previous_query_meta.get("model_name")
    if not app_label or not model_name:
        return None

    try:
        model_class = apps.get_model(app_label, model_name)
    except LookupError:
        return None

    display_name = previous_query_meta.get("display_name", model_name)

    # Rebuild queryset with same filters
    qs = model_class.objects.all()

    # Apply folder permission filter
    if hasattr(model_class, "folder_id"):
        qs = qs.filter(folder_id__in=accessible_folder_ids)
    elif hasattr(model_class, "compliance_assessment"):
        qs = qs.filter(compliance_assessment__folder_id__in=accessible_folder_ids)

    # Re-apply saved filters
    saved_filters = previous_query_meta.get("filters", {})
    if saved_filters:
        qs = qs.filter(**saved_filters)

    filters_applied = previous_query_meta.get("filters_applied", [])
    total_count = qs.count()

    # Determine page
    action = followup.get("action", "list")
    prev_page = previous_query_meta.get("page", 1)

    if action == "next_page":
        page = prev_page + 1
    elif action == "paginate":
        page = followup.get("page", 1)
    else:
        page = 1

    # Clamp page
    total_pages = max(1, (total_count + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
    page = max(1, min(page, total_pages))

    offset = (page - 1) * LIST_PAGE_SIZE
    objects = _serialize_objects(
        qs[offset : offset + LIST_PAGE_SIZE], model_class, model_name
    )

    return {
        "model_name": model_name,
        "display_name": display_name,
        "query_type": "list",
        "filters_applied": filters_applied,
        "total_count": total_count,
        "objects": objects,
        "page": page,
        "page_size": LIST_PAGE_SIZE,
        "total_pages": total_pages,
        "has_more": offset + LIST_PAGE_SIZE < total_count,
    }


def execute_query(query: str, accessible_folder_ids: list[str]) -> dict | None:
    """
    Parse a natural language query and execute it against the ORM.
    Returns a dict with results or None if the query can't be parsed.

    Result format:
    {
        "model_name": str,
        "display_name": str,
        "query_type": "list" | "count" | "summary",
        "filters_applied": list[str],
        "total_count": int,
        "objects": list[dict],  # for list queries
        "summary": dict,  # for summary queries
    }
    """
    q = query.lower().strip()

    # Detect the target model
    model_info = _detect_model(q)
    if not model_info:
        return None

    app_label, model_name, display_name = model_info

    try:
        model_class = apps.get_model(app_label, model_name)
    except LookupError:
        return None

    # Base queryset filtered by accessible folders
    folder_ids_uuid = [fid for fid in accessible_folder_ids]
    qs = model_class.objects.all()

    # Apply folder permission filter
    if hasattr(model_class, "folder_id"):
        qs = qs.filter(folder_id__in=folder_ids_uuid)
    elif hasattr(model_class, "compliance_assessment"):
        # RequirementAssessment doesn't have folder directly
        qs = qs.filter(compliance_assessment__folder_id__in=folder_ids_uuid)

    filters_applied = []

    # Apply folder/domain name filter
    folder_filter = _extract_folder_filter(q, accessible_folder_ids)
    if folder_filter:
        if hasattr(model_class, "folder_id"):
            qs = qs.filter(folder_id__in=folder_filter["folder_ids"])
        elif hasattr(model_class, "compliance_assessment"):
            qs = qs.filter(
                compliance_assessment__folder_id__in=folder_filter["folder_ids"]
            )
        filters_applied.append(folder_filter["label"])

    # Apply status filter
    status_filter = _extract_status(q, model_name)
    if status_filter:
        field_name, value, label = status_filter
        qs = qs.filter(**{field_name: value})
        filters_applied.append(label)

    # Apply priority filter
    priority = _extract_priority(q)
    if priority and hasattr(model_class, "priority"):
        qs = qs.filter(priority=priority)
        filters_applied.append(f"priority = P{priority}")

    # Apply category filter
    category = _extract_category(q)
    if category and hasattr(model_class, "category"):
        qs = qs.filter(category=category)
        filters_applied.append(f"category = {category}")

    # Apply effort filter
    effort = _extract_effort(q)
    if effort and hasattr(model_class, "effort"):
        qs = qs.filter(effort=effort)
        filters_applied.append(f"effort = {effort}")

    # Apply severity filter
    severity = _extract_severity(q)
    if severity and hasattr(model_class, "severity"):
        qs = qs.filter(severity=severity)
        filters_applied.append(f"severity = {severity}")

    # Apply date-based filters
    date_filter = _extract_date_filter(q, model_class)
    if date_filter:
        qs = qs.filter(date_filter["q"])
        filters_applied.append(date_filter["label"])

    # Apply name/text search
    name_search = _extract_name_search(q)
    if name_search:
        name_q = Q()
        if hasattr(model_class, "name"):
            name_q |= Q(name__icontains=name_search)
        if hasattr(model_class, "description"):
            name_q |= Q(description__icontains=name_search)
        if hasattr(model_class, "ref_id"):
            name_q |= Q(ref_id__icontains=name_search)
        if name_q:
            qs = qs.filter(name_q)
            filters_applied.append(f"matching '{name_search}'")

    # Determine query type
    is_count = bool(re.search(r"\b(how many|count|number of|total)\b", q))
    is_summary = bool(
        re.search(r"\b(summary|overview|breakdown|stats|statistics|dashboard)\b", q)
    )

    # Pagination: detect "next", "more", "page N", "show more"
    page = _extract_page(q)

    total_count = qs.count()

    if is_summary:
        return _build_summary(
            qs, model_class, model_name, display_name, filters_applied, total_count
        )

    if is_count:
        # For count queries, also include a summary breakdown so the LLM can
        # give a richer answer than just a number
        result = {
            "model_name": model_name,
            "display_name": display_name,
            "query_type": "count",
            "filters_applied": filters_applied,
            "total_count": total_count,
            "objects": [],
        }
        if total_count > 0:
            summary = _build_summary(
                qs, model_class, model_name, display_name, filters_applied, total_count
            )
            result["summary"] = summary.get("summary", {})
        return result

    # For large result sets, auto-switch to summary + top items
    if total_count > MAX_LIST_RESULTS and page == 1:
        summary = _build_summary(
            qs, model_class, model_name, display_name, filters_applied, total_count
        )
        # Also include the first page of items so the LLM can show some examples
        objects = _serialize_objects(qs[:LIST_PAGE_SIZE], model_class, model_name)
        summary["objects"] = objects
        summary["query_type"] = "summary_with_list"
        summary["has_more"] = total_count > LIST_PAGE_SIZE
        summary["page"] = 1
        summary["page_size"] = LIST_PAGE_SIZE
        summary["total_pages"] = (total_count + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
        return summary

    # Paginated list query
    offset = (page - 1) * LIST_PAGE_SIZE
    objects = _serialize_objects(
        qs[offset : offset + LIST_PAGE_SIZE], model_class, model_name
    )

    return {
        "model_name": model_name,
        "display_name": display_name,
        "query_type": "list",
        "filters_applied": filters_applied,
        "total_count": total_count,
        "objects": objects,
        "page": page,
        "page_size": LIST_PAGE_SIZE,
        "total_pages": (total_count + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE,
        "has_more": offset + LIST_PAGE_SIZE < total_count,
    }


def format_query_result(result: dict) -> str:
    """Format a query result dict into a context string for the LLM."""
    if not result:
        return ""

    parts = []
    display = result["display_name"]
    total = result["total_count"]
    filters = result.get("filters_applied", [])

    filter_desc = f" (filters: {', '.join(filters)})" if filters else ""

    if result["query_type"] == "count":
        parts.append(f"[ORM Query Result] Count of {display}{filter_desc}: {total}")
        # Include summary breakdown if available
        if result.get("summary"):
            for key, value in result["summary"].items():
                parts.append(f"  {key}: {value}")

    elif result["query_type"] == "summary":
        parts.append(f"[ORM Query Result] Summary of {display}{filter_desc}")
        parts.append(f"Total: {total}")
        if result.get("summary"):
            for key, value in result["summary"].items():
                parts.append(f"  {key}: {value}")

    elif result["query_type"] == "summary_with_list":
        # Large result set: summary + first page of items
        parts.append(f"[ORM Query Result] {display}{filter_desc}: {total} total")
        if result.get("summary"):
            parts.append("Breakdown:")
            for key, value in result["summary"].items():
                parts.append(f"  {key}: {value}")
        if result.get("objects"):
            page = result.get("page", 1)
            total_pages = result.get("total_pages", 1)
            parts.append(
                f"\nShowing page {page} of {total_pages} ({len(result['objects'])} items):"
            )
            parts.extend(_format_object_lines(result["objects"]))
        if result.get("has_more"):
            parts.append(
                f'\n(Ask for "next page" or "page N" to see more, or narrow down with filters)'
            )

    elif result["query_type"] == "list":
        page = result.get("page", 1)
        total_pages = result.get("total_pages", 1)
        has_more = result.get("has_more", False)
        if total_pages > 1:
            parts.append(
                f"[ORM Query Result] {display}{filter_desc}: {total} total "
                f"(page {page}/{total_pages})"
            )
        else:
            parts.append(f"[ORM Query Result] {display}{filter_desc}: {total} total")
        parts.extend(_format_object_lines(result["objects"]))
        if has_more:
            parts.append(f'\n(Ask for "next page" or "page N" to see more)')

    return "\n".join(parts)


def _format_object_lines(objects: list[dict]) -> list[str]:
    """Format a list of serialized objects into display lines."""
    lines = []
    for obj in objects:
        line_parts = []
        if obj.get("ref_id"):
            line_parts.append(f"[{obj['ref_id']}]")
        line_parts.append(obj.get("name", "Unnamed"))
        extras = []
        for key in (
            "status",
            "treatment",
            "category",
            "priority",
            "severity",
            "result",
            "type",
        ):
            if obj.get(key):
                extras.append(f"{key}={obj[key]}")
        if obj.get("folder"):
            extras.append(f"domain={obj['folder']}")
        if extras:
            line_parts.append(f"({', '.join(extras)})")
        lines.append(f"  - {' '.join(line_parts)}")
    return lines


# --- Internal helpers ---


def _get_model_keywords() -> list[str]:
    """Get all model alias keywords for regex matching."""
    # Return multi-word aliases first (longest match), then single-word
    aliases = sorted(MODEL_REGISTRY.keys(), key=len, reverse=True)
    return [re.escape(a) for a in aliases]


def _detect_model(query: str) -> tuple[str, str, str] | None:
    """Detect which model the user is asking about."""
    # Check longest aliases first to match "risk scenario" before "risk"
    for alias in sorted(MODEL_REGISTRY.keys(), key=len, reverse=True):
        if alias in query:
            return MODEL_REGISTRY[alias]
    return None


def _extract_page(query: str) -> int:
    """Extract page number from natural language pagination requests."""
    # "page 3", "page 2"
    match = re.search(r"\bpage\s+(\d+)\b", query)
    if match:
        return max(1, int(match.group(1)))

    # "next page", "show more", "more results", "next 20", "next batch"
    if re.search(r"\b(next|more|continue|show more|next page|next batch)\b", query):
        return 2  # Will be adjusted by the view using session context

    return 1


def _extract_folder_filter(query: str, accessible_folder_ids: list[str]) -> dict | None:
    """
    Extract folder/domain name filter from natural language.
    Matches patterns like "on domain X", "in folder X", "in X domain", "domain X".
    """
    from iam.models import Folder

    patterns = [
        r"\b(?:on|in|from|for|of)\s+(?:domain|folder|project)\s+[\"']?([^\"',.?!]+?)[\"']?\s*(?:\?|$|,|\.|\band\b|\bwith\b|\bthat\b)",
        r"\b(?:domain|folder|project)\s+[\"']?([^\"',.?!]+?)[\"']?\s*(?:\?|$|,|\.|\band\b|\bwith\b|\bthat\b)",
        r"\b(?:on|in|from|for)\s+[\"']([^\"']+)[\"']",
    ]

    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            folder_name = match.group(1).strip()
            if not folder_name:
                continue
            # Don't match if the "folder name" is just a model keyword
            if folder_name.lower() in MODEL_REGISTRY:
                continue

            # Find matching folders by name (case-insensitive), restricted to accessible ones
            matching_folders = Folder.objects.filter(
                id__in=accessible_folder_ids,
                name__icontains=folder_name,
            )
            if matching_folders.exists():
                folder_ids = [str(f.id) for f in matching_folders]
                matched_names = ", ".join(f.name for f in matching_folders)
                return {
                    "folder_ids": folder_ids,
                    "label": f"domain = {matched_names}",
                }

    return None


def _extract_status(query: str, model_name: str) -> tuple[str, str, str] | None:
    """Extract status/treatment/result filter from query."""
    # For RiskScenario, check treatment
    if model_name == "RiskScenario":
        for alias, value in STATUS_ALIASES.items():
            if alias in query and value in (
                "open",
                "mitigate",
                "accept",
                "avoid",
                "transfer",
            ):
                return ("treatment", value, f"treatment = {value}")

    # For RequirementAssessment, check result
    if model_name == "RequirementAssessment":
        for alias, value in STATUS_ALIASES.items():
            if alias in query and value in (
                "compliant",
                "non_compliant",
                "partially_compliant",
                "not_assessed",
                "not_applicable",
            ):
                return ("result", value, f"result = {value}")

    # Generic status
    for alias, value in STATUS_ALIASES.items():
        if alias in query:
            return ("status", value, f"status = {value}")

    return None


def _extract_priority(query: str) -> int | None:
    for alias, value in PRIORITY_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", query):
            return value
    return None


def _extract_category(query: str) -> str | None:
    for alias, value in CATEGORY_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", query):
            return value
    return None


def _extract_effort(query: str) -> str | None:
    for alias, value in EFFORT_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", query):
            return value
    return None


def _extract_severity(query: str) -> int | None:
    for alias, value in SEVERITY_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", query):
            return value
    return None


def _extract_date_filter(query: str, model_class) -> dict | None:
    """Extract date-based filters like 'overdue', 'expiring this month', etc."""
    now = timezone.now()

    if re.search(r"\b(overdue|past due|late)\b", query):
        if hasattr(model_class, "eta"):
            return {"q": Q(eta__lt=now.date()), "label": "overdue (ETA passed)"}
        if hasattr(model_class, "expiry_date"):
            return {"q": Q(expiry_date__lt=now.date()), "label": "expired"}
        if hasattr(model_class, "end_date"):
            return {"q": Q(end_date__lt=now.date()), "label": "past end date"}

    if re.search(r"\b(expiring|due)\b.*\b(this month|soon)\b", query) or re.search(
        r"\b(upcoming|soon)\b", query
    ):
        end_of_month = (now.replace(day=28) + timedelta(days=4)).replace(
            day=1
        ) - timedelta(days=1)
        if hasattr(model_class, "eta"):
            return {
                "q": Q(eta__gte=now.date(), eta__lte=end_of_month.date()),
                "label": "due this month",
            }
        if hasattr(model_class, "expiry_date"):
            return {
                "q": Q(
                    expiry_date__gte=now.date(), expiry_date__lte=end_of_month.date()
                ),
                "label": "expiring this month",
            }

    if re.search(r"\b(created|new)\b.*\b(this week|recently|today)\b", query):
        week_ago = now - timedelta(days=7)
        return {"q": Q(created_at__gte=week_ago), "label": "created in the last 7 days"}

    return None


def _extract_name_search(query: str) -> str | None:
    """Extract a quoted name search or 'named/called/about X' pattern."""
    # Quoted strings
    match = re.search(r'"([^"]+)"', query)
    if match:
        return match.group(1)
    match = re.search(r"'([^']+)'", query)
    if match:
        return match.group(1)

    # "named X", "called X", "about X", "related to X", "containing X"
    match = re.search(
        r"\b(?:named|called|about|related to|containing|mentioning)\s+(.+?)(?:\s+(?:with|that|and|in)\b|$)",
        query,
    )
    if match:
        term = match.group(1).strip()
        # Don't return if it's just a model name
        if term.lower() not in MODEL_REGISTRY:
            return term

    return None


def _serialize_objects(queryset, model_class, model_name: str) -> list[dict]:
    """Serialize queryset objects into dicts for the LLM context."""
    objects = []
    for obj in queryset:
        data = {
            "id": str(obj.id),
            "name": str(obj),
        }

        if hasattr(obj, "ref_id") and obj.ref_id:
            data["ref_id"] = obj.ref_id

        if hasattr(obj, "description") and obj.description:
            # Truncate long descriptions
            desc = obj.description
            data["description"] = desc[:200] + "..." if len(desc) > 200 else desc

        # Status/treatment/result
        if hasattr(obj, "status") and obj.status:
            data["status"] = (
                obj.get_status_display()
                if hasattr(obj, "get_status_display")
                else obj.status
            )
        if hasattr(obj, "treatment") and obj.treatment:
            data["treatment"] = (
                obj.get_treatment_display()
                if hasattr(obj, "get_treatment_display")
                else obj.treatment
            )
        if hasattr(obj, "result") and obj.result:
            data["result"] = (
                obj.get_result_display()
                if hasattr(obj, "get_result_display")
                else obj.result
            )

        # Categorization
        if hasattr(obj, "category") and obj.category:
            data["category"] = (
                obj.get_category_display()
                if hasattr(obj, "get_category_display")
                else obj.category
            )
        if hasattr(obj, "priority") and obj.priority:
            data["priority"] = f"P{obj.priority}"
        if hasattr(obj, "severity") and obj.severity:
            data["severity"] = (
                obj.get_severity_display()
                if hasattr(obj, "get_severity_display")
                else str(obj.severity)
            )
        if hasattr(obj, "type") and obj.type:
            data["type"] = (
                obj.get_type_display() if hasattr(obj, "get_type_display") else obj.type
            )

        # Dates
        if hasattr(obj, "eta") and obj.eta:
            data["eta"] = str(obj.eta)
        if hasattr(obj, "expiry_date") and obj.expiry_date:
            data["expiry_date"] = str(obj.expiry_date)

        # Risk levels
        if (
            hasattr(obj, "current_level")
            and obj.current_level is not None
            and obj.current_level >= 0
        ):
            data["current_risk_level"] = obj.current_level
        if (
            hasattr(obj, "residual_level")
            and obj.residual_level is not None
            and obj.residual_level >= 0
        ):
            data["residual_risk_level"] = obj.residual_level

        # Folder
        if hasattr(obj, "folder") and obj.folder:
            data["folder"] = str(obj.folder)

        objects.append(data)

    return objects


def _build_summary(
    qs, model_class, model_name, display_name, filters_applied, total_count
) -> dict:
    """Build a summary/breakdown of the queryset."""
    summary = {}

    # Status breakdown
    if hasattr(model_class, "status"):
        status_counts = (
            qs.values("status").annotate(count=Count("id")).order_by("-count")
        )
        if status_counts:
            breakdown = {}
            for item in status_counts:
                status_val = item["status"] or "--"
                breakdown[status_val] = item["count"]
            summary["Status breakdown"] = breakdown

    # Treatment breakdown (RiskScenario)
    if hasattr(model_class, "treatment"):
        treatment_counts = (
            qs.values("treatment").annotate(count=Count("id")).order_by("-count")
        )
        if treatment_counts:
            breakdown = {}
            for item in treatment_counts:
                treatment_val = item["treatment"] or "--"
                breakdown[treatment_val] = item["count"]
            summary["Treatment breakdown"] = breakdown

    # Result breakdown (RequirementAssessment)
    if hasattr(model_class, "result"):
        result_counts = (
            qs.values("result").annotate(count=Count("id")).order_by("-count")
        )
        if result_counts:
            breakdown = {}
            for item in result_counts:
                result_val = item["result"] or "--"
                breakdown[result_val] = item["count"]
            summary["Result breakdown"] = breakdown

    # Priority breakdown
    if hasattr(model_class, "priority"):
        priority_counts = (
            qs.values("priority").annotate(count=Count("id")).order_by("priority")
        )
        if priority_counts:
            breakdown = {}
            for item in priority_counts:
                p = item["priority"]
                breakdown[f"P{p}" if p else "--"] = item["count"]
            summary["Priority breakdown"] = breakdown

    # Category breakdown
    if hasattr(model_class, "category"):
        cat_counts = (
            qs.values("category").annotate(count=Count("id")).order_by("-count")
        )
        if cat_counts:
            breakdown = {}
            for item in cat_counts:
                breakdown[item["category"] or "--"] = item["count"]
            summary["Category breakdown"] = breakdown

    # Type breakdown (Asset)
    if hasattr(model_class, "type") and model_name == "Asset":
        type_counts = qs.values("type").annotate(count=Count("id")).order_by("-count")
        if type_counts:
            breakdown = {}
            for item in type_counts:
                breakdown[item["type"] or "--"] = item["count"]
            summary["Type breakdown"] = breakdown

    # Folder breakdown
    if hasattr(model_class, "folder"):
        folder_counts = (
            qs.values("folder__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        if folder_counts:
            breakdown = {}
            for item in folder_counts:
                breakdown[item["folder__name"] or "--"] = item["count"]
            summary["By domain (top 10)"] = breakdown

    return {
        "model_name": model_name,
        "display_name": display_name,
        "query_type": "summary",
        "filters_applied": filters_applied,
        "total_count": total_count,
        "objects": [],
        "summary": summary,
    }
