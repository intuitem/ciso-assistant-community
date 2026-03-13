"""
ORM query execution layer for chat tool calling.
Receives structured parameters from LLM tool calls and executes safe,
permission-filtered Django ORM queries.

No regex, no intent detection, no i18n concerns — the LLM handles
natural language understanding in any language.
"""

import logging
from datetime import timedelta

from django.apps import apps
from django.db.models import Q, Count
from django.utils import timezone

logger = logging.getLogger(__name__)

# Page size for paginated list results
LIST_PAGE_SIZE = 20
# Threshold to auto-switch list queries to summary + first page
SUMMARY_THRESHOLD = 30


def execute_tool_query(
    arguments: dict, accessible_folder_ids: list[str]
) -> dict | None:
    """
    Execute a structured query from tool call arguments.

    arguments keys:
        model (required): e.g. "applied_control", "asset", "risk_scenario"
        action (required): "list", "count", "summary"
        domain: folder/domain name filter
        status, treatment, result: status-like filters
        priority, category, effort, severity: categorization filters
        date_filter: "overdue", "due_this_month", "expiring_this_month", "created_recently"
        search: text search in name/description/ref_id
        page: page number (default 1)
    """
    from .tools import MODEL_MAP

    model_key = arguments.get("model")
    action = arguments.get("action", "list")

    if model_key not in MODEL_MAP:
        return None

    app_label, model_name, display_name = MODEL_MAP[model_key]

    try:
        model_class = apps.get_model(app_label, model_name)
    except LookupError:
        return None

    # Base queryset filtered by accessible folders
    qs = model_class.objects.all()
    if hasattr(model_class, "folder_id"):
        qs = qs.filter(folder_id__in=accessible_folder_ids)
    elif hasattr(model_class, "compliance_assessment"):
        qs = qs.filter(compliance_assessment__folder_id__in=accessible_folder_ids)

    filters_applied = []

    # Domain/folder filter
    domain = arguments.get("domain")
    if domain:
        folder_ids = _resolve_domain(domain, accessible_folder_ids)
        if folder_ids:
            if hasattr(model_class, "folder_id"):
                qs = qs.filter(folder_id__in=folder_ids)
            elif hasattr(model_class, "compliance_assessment"):
                qs = qs.filter(compliance_assessment__folder_id__in=folder_ids)
            filters_applied.append(f"domain = {domain}")
        else:
            # Domain not found — return empty result rather than unfiltered
            return {
                "model_name": model_name,
                "display_name": display_name,
                "query_type": action,
                "filters_applied": [f"domain = {domain} (not found)"],
                "total_count": 0,
                "objects": [],
            }

    # Status filter — validate against model's actual choices
    status = arguments.get("status")
    if status and hasattr(model_class, "status"):
        field = model_class._meta.get_field("status")
        valid_statuses = {c[0] for c in field.choices} if field.choices else None
        if valid_statuses is None or status in valid_statuses:
            qs = qs.filter(status=status)
            filters_applied.append(f"status = {status}")

    # Treatment filter (RiskScenario)
    treatment = arguments.get("treatment")
    if treatment and hasattr(model_class, "treatment"):
        qs = qs.filter(treatment=treatment)
        filters_applied.append(f"treatment = {treatment}")

    # Result filter (RequirementAssessment)
    result_filter = arguments.get("result")
    if result_filter and hasattr(model_class, "result"):
        qs = qs.filter(result=result_filter)
        filters_applied.append(f"result = {result_filter}")

    # Priority filter
    priority = arguments.get("priority")
    if priority is not None and hasattr(model_class, "priority"):
        try:
            priority = int(priority)
        except (TypeError, ValueError):
            priority = None
        if priority is not None:
            qs = qs.filter(priority=priority)
            filters_applied.append(f"priority = P{priority}")

    # Category filter
    category = arguments.get("category")
    if category and hasattr(model_class, "category"):
        qs = qs.filter(category=category)
        filters_applied.append(f"category = {category}")

    # Effort filter
    effort = arguments.get("effort")
    if effort and hasattr(model_class, "effort"):
        qs = qs.filter(effort=effort)
        filters_applied.append(f"effort = {effort}")

    # Severity filter
    severity = arguments.get("severity")
    if severity is not None and hasattr(model_class, "severity"):
        try:
            severity = int(severity)
        except (TypeError, ValueError):
            severity = None
        if severity is not None:
            qs = qs.filter(severity=severity)
            filters_applied.append(f"severity = {severity}")

    # Date filter
    date_filter = arguments.get("date_filter")
    if date_filter:
        date_q = _build_date_filter(date_filter, model_class)
        if date_q:
            qs = qs.filter(date_q["q"])
            filters_applied.append(date_q["label"])

    # Generic relationship filters — derived from model metadata
    for rel_name in arguments.get("has_related", []):
        if _is_valid_relation(model_class, rel_name):
            qs = qs.filter(**{f"{rel_name}__isnull": False}).distinct()
            filters_applied.append(f"has {rel_name}")

    for rel_name in arguments.get("has_no_related", []):
        if _is_valid_relation(model_class, rel_name):
            qs = qs.filter(**{f"{rel_name}__isnull": True})
            filters_applied.append(f"no {rel_name}")

    # Text search
    search = arguments.get("search")
    if search:
        search_q = Q()
        if hasattr(model_class, "name"):
            search_q |= Q(name__icontains=search)
        if hasattr(model_class, "description"):
            search_q |= Q(description__icontains=search)
        if hasattr(model_class, "ref_id"):
            search_q |= Q(ref_id__icontains=search)
        if search_q:
            qs = qs.filter(search_q)
            filters_applied.append(f"search = '{search}'")

    total_count = qs.count()
    try:
        page = int(arguments.get("page", 1) or 1)
    except (TypeError, ValueError):
        page = 1

    # Pagination — always applied
    total_pages = max(1, (total_count + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * LIST_PAGE_SIZE

    pagination = {
        "page": page,
        "page_size": LIST_PAGE_SIZE,
        "total_pages": total_pages,
        "has_more": offset + LIST_PAGE_SIZE < total_count,
    }

    # Execute based on action
    if action == "summary":
        result = _build_summary(
            qs, model_class, model_name, display_name, filters_applied, total_count
        )
        result.update(pagination)
        return result

    if action == "count":
        result = {
            "model_name": model_name,
            "display_name": display_name,
            "query_type": "count",
            "filters_applied": filters_applied,
            "total_count": total_count,
            "objects": [],
        }
        result.update(pagination)
        if total_count > 0:
            summary = _build_summary(
                qs, model_class, model_name, display_name, filters_applied, total_count
            )
            result["summary"] = summary.get("summary", {})
        return result

    # List query — always paginated, include summary on first page of large sets
    objects = _serialize_objects(
        qs[offset : offset + LIST_PAGE_SIZE], model_class, model_name
    )

    if total_count > SUMMARY_THRESHOLD and page == 1:
        result = _build_summary(
            qs, model_class, model_name, display_name, filters_applied, total_count
        )
        result["objects"] = objects
        result["query_type"] = "summary_with_list"
        result.update(pagination)
        return result

    result = {
        "model_name": model_name,
        "display_name": display_name,
        "query_type": "list",
        "filters_applied": filters_applied,
        "total_count": total_count,
        "objects": objects,
    }
    result.update(pagination)
    return result


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
        parts.append(f"[Query Result] Count of {display}{filter_desc}: {total}")
        if result.get("summary"):
            for key, value in result["summary"].items():
                parts.append(f"  {key}: {value}")

    elif result["query_type"] == "summary":
        parts.append(f"[Query Result] Summary of {display}{filter_desc}")
        parts.append(f"Total: {total}")
        if result.get("summary"):
            for key, value in result["summary"].items():
                parts.append(f"  {key}: {value}")

    elif result["query_type"] == "summary_with_list":
        parts.append(f"[Query Result] {display}{filter_desc}: {total} total")
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
                '\n(User can ask for "next page" or "page N" to see more, or narrow down with filters)'
            )

    elif result["query_type"] == "list":
        page = result.get("page", 1)
        total_pages = result.get("total_pages", 1)
        has_more = result.get("has_more", False)
        if total_pages > 1:
            parts.append(
                f"[Query Result] {display}{filter_desc}: {total} total "
                f"(page {page}/{total_pages})"
            )
        else:
            parts.append(f"[Query Result] {display}{filter_desc}: {total} total")
        parts.extend(_format_object_lines(result["objects"]))
        if has_more:
            parts.append('\n(User can ask for "next page" or "page N" to see more)')

    return "\n".join(parts)


# --- Internal helpers ---


def _is_valid_relation(model_class, field_name: str) -> bool:
    """Check if field_name is a valid M2M or FK relation on the model."""
    try:
        field = model_class._meta.get_field(field_name)
        return field.is_relation
    except Exception:
        logger.info(
            "Ignoring invalid relation '%s' on %s", field_name, model_class.__name__
        )
        return False


def _resolve_domain(domain_name: str, accessible_folder_ids: list[str]) -> list[str]:
    """Resolve a domain/folder name to folder IDs, restricted to accessible folders."""
    from iam.models import Folder

    matching = Folder.objects.filter(
        id__in=accessible_folder_ids,
        name__icontains=domain_name,
    )
    return [str(f.id) for f in matching]


def _build_date_filter(date_filter: str, model_class) -> dict | None:
    """Build a Q object for date-based filtering."""
    now = timezone.now()

    if date_filter == "overdue":
        if hasattr(model_class, "eta"):
            return {"q": Q(eta__lt=now.date()), "label": "overdue (ETA passed)"}
        if hasattr(model_class, "expiry_date"):
            return {"q": Q(expiry_date__lt=now.date()), "label": "expired"}
        if hasattr(model_class, "end_date"):
            return {"q": Q(end_date__lt=now.date()), "label": "past end date"}

    elif date_filter in ("due_this_month", "expiring_this_month"):
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

    elif date_filter == "created_recently":
        week_ago = now - timedelta(days=7)
        return {"q": Q(created_at__gte=week_ago), "label": "created in the last 7 days"}

    return None


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

    if hasattr(model_class, "status"):
        status_counts = (
            qs.values("status").annotate(count=Count("id")).order_by("-count")
        )
        if status_counts:
            summary["Status breakdown"] = {
                (item["status"] or "--"): item["count"] for item in status_counts
            }

    if hasattr(model_class, "treatment"):
        treatment_counts = (
            qs.values("treatment").annotate(count=Count("id")).order_by("-count")
        )
        if treatment_counts:
            summary["Treatment breakdown"] = {
                (item["treatment"] or "--"): item["count"] for item in treatment_counts
            }

    if hasattr(model_class, "result"):
        result_counts = (
            qs.values("result").annotate(count=Count("id")).order_by("-count")
        )
        if result_counts:
            summary["Result breakdown"] = {
                (item["result"] or "--"): item["count"] for item in result_counts
            }

    if hasattr(model_class, "priority"):
        priority_counts = (
            qs.values("priority").annotate(count=Count("id")).order_by("priority")
        )
        if priority_counts:
            summary["Priority breakdown"] = {
                (f"P{item['priority']}" if item["priority"] else "--"): item["count"]
                for item in priority_counts
            }

    if hasattr(model_class, "category"):
        cat_counts = (
            qs.values("category").annotate(count=Count("id")).order_by("-count")
        )
        if cat_counts:
            summary["Category breakdown"] = {
                (item["category"] or "--"): item["count"] for item in cat_counts
            }

    if hasattr(model_class, "type") and model_name == "Asset":
        type_counts = qs.values("type").annotate(count=Count("id")).order_by("-count")
        if type_counts:
            summary["Type breakdown"] = {
                (item["type"] or "--"): item["count"] for item in type_counts
            }

    if hasattr(model_class, "folder"):
        folder_counts = (
            qs.values("folder__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        if folder_counts:
            summary["By domain (top 10)"] = {
                (item["folder__name"] or "--"): item["count"] for item in folder_counts
            }

    return {
        "model_name": model_name,
        "display_name": display_name,
        "query_type": "summary",
        "filters_applied": filters_applied,
        "total_count": total_count,
        "objects": [],
        "summary": summary,
    }
