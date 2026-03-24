"""
ORM query execution layer for chat tool calling.
Receives structured parameters from LLM tool calls and executes safe,
permission-filtered Django ORM queries.

No regex, no intent detection, no i18n concerns — the LLM handles
natural language understanding in any language.
"""

import structlog
from datetime import timedelta

from django.apps import apps
from django.db.models import Q, Count
from django.utils import timezone

logger = structlog.get_logger(__name__)

# Page size for paginated list results
LIST_PAGE_SIZE = 20
# Threshold to auto-switch list queries to summary + first page
SUMMARY_THRESHOLD = 30


def execute_tool_query(
    arguments: dict, accessible_folder_ids: list[str], parsed_context=None
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

    parsed_context: optional ParsedContext from page_context.py — when provided,
        queries are auto-scoped to the parent object (e.g., risk scenarios for
        a specific risk assessment).
    """
    from .tools import MODEL_MAP, PARENT_CHILD_MAP

    model_key = arguments.get("model")
    action = arguments.get("action", "list")

    if model_key not in MODEL_MAP:
        return None

    app_label, model_name, display_name, url_slug = MODEL_MAP[model_key]

    try:
        model_class = apps.get_model(app_label, model_name)
    except LookupError:
        return None

    # Base queryset filtered by accessible folders
    qs = model_class.objects.all()
    if model_name == "Folder":
        qs = qs.filter(id__in=accessible_folder_ids)
    elif hasattr(model_class, "folder_id"):
        qs = qs.filter(folder_id__in=accessible_folder_ids)
    elif hasattr(model_class, "compliance_assessment"):
        qs = qs.filter(compliance_assessment__folder_id__in=accessible_folder_ids)

    filters_applied = []

    # Auto-scope to parent object when page context is available
    if parsed_context and parsed_context.object_id:
        for child_key, fk_field in PARENT_CHILD_MAP.get(parsed_context.model_key, []):
            if child_key == model_key and fk_field:
                qs = qs.filter(**{fk_field: parsed_context.object_id})
                filters_applied.append(f"scoped to current {parsed_context.model_key}")
                break

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
                "url_slug": url_slug,
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

    # Compound relation filter — filter on properties of related objects
    related_filter = arguments.get("related_filter")
    if related_filter and isinstance(related_filter, dict):
        rf_q = _build_related_filter(related_filter, model_class)
        if rf_q:
            qs = qs.filter(rf_q["q"]).distinct()
            filters_applied.append(rf_q["label"])

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
            qs,
            model_class,
            model_name,
            display_name,
            url_slug,
            filters_applied,
            total_count,
        )
        result.update(pagination)
        return result

    if action == "count":
        result = {
            "model_name": model_name,
            "display_name": display_name,
            "url_slug": url_slug,
            "query_type": "count",
            "filters_applied": filters_applied,
            "total_count": total_count,
            "objects": [],
        }
        result.update(pagination)
        if total_count > 0:
            summary = _build_summary(
                qs,
                model_class,
                model_name,
                display_name,
                url_slug,
                filters_applied,
                total_count,
            )
            result["summary"] = summary.get("summary", {})
        return result

    # List query — always paginated, include summary on first page of large sets
    objects = _serialize_objects(
        qs[offset : offset + LIST_PAGE_SIZE], model_class, model_name
    )

    if total_count > SUMMARY_THRESHOLD and page == 1:
        result = _build_summary(
            qs,
            model_class,
            model_name,
            display_name,
            url_slug,
            filters_applied,
            total_count,
        )
        result["objects"] = objects
        result["query_type"] = "summary_with_list"
        result.update(pagination)
        return result

    result = {
        "model_name": model_name,
        "display_name": display_name,
        "url_slug": url_slug,
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
            parts.extend(
                _format_object_lines(result["objects"], result.get("url_slug", ""))
            )
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
        parts.extend(
            _format_object_lines(result["objects"], result.get("url_slug", ""))
        )
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


def _build_related_filter(related_filter: dict, model_class) -> dict | None:
    """
    Build a Q object for compound relation filters.

    related_filter keys:
        relation: field name of the relation (e.g., "evidences", "applied_controls")
        condition: one of "status_is", "status_not", "overdue", "no_attachment",
                   "result_is", "treatment_is"
        value: value for status_is/status_not/result_is/treatment_is
    """
    relation = related_filter.get("relation")
    condition = related_filter.get("condition")
    value = related_filter.get("value")

    if not relation or not condition:
        return None

    if not _is_valid_relation(model_class, relation):
        return None

    if condition == "status_is" and value:
        return {
            "q": Q(**{f"{relation}__status": value}),
            "label": f"{relation} with status={value}",
        }

    if condition == "status_not" and value:
        return {
            "q": ~Q(**{f"{relation}__status": value}),
            "label": f"{relation} with status!={value}",
        }

    if condition == "overdue":
        from django.utils import timezone

        today = timezone.now().date()
        # Try eta first, then expiry_date
        return {
            "q": Q(**{f"{relation}__eta__lt": today})
            | Q(**{f"{relation}__expiry_date__lt": today}),
            "label": f"{relation} overdue",
        }

    if condition == "no_attachment":
        # Specific to evidences → EvidenceRevision.attachment
        return {
            "q": Q(**{f"{relation}__isnull": False})
            & ~Q(**{f"{relation}__revisions__attachment__isnull": False}),
            "label": f"{relation} without attachments",
        }

    if condition == "result_is" and value:
        return {
            "q": Q(**{f"{relation}__result": value}),
            "label": f"{relation} with result={value}",
        }

    if condition == "treatment_is" and value:
        return {
            "q": Q(**{f"{relation}__treatment": value}),
            "label": f"{relation} with treatment={value}",
        }

    return None


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
        if hasattr(model_class, "eta_missed_q"):
            # Model defines its own "overdue" logic
            return {"q": model_class.eta_missed_q(), "label": "overdue (ETA missed)"}
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


def _format_object_lines(objects: list[dict], url_slug: str = "") -> list[str]:
    """Format a list of serialized objects into display lines with markdown links."""
    from django.conf import settings

    base_url = getattr(settings, "CISO_ASSISTANT_URL", "").rstrip("/")

    lines = []
    for obj in objects:
        name = obj.get("name", "Unnamed")
        ref_id = obj.get("ref_id", "")

        # Build a markdown link for the object name (full URL so sanitize-html allows it)
        if url_slug and obj.get("id") and base_url:
            display = f"[{ref_id}] {name}" if ref_id else name
            name_part = f"[{display}]({base_url}/{url_slug}/{obj['id']})"
        else:
            name_part = f"[{ref_id}] {name}" if ref_id else name

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
        if obj.get("current_risk_level") is not None:
            extras.append(f"current_risk={obj['current_risk_level']}")
        if obj.get("residual_risk_level") is not None:
            extras.append(f"residual_risk={obj['residual_risk_level']}")
        if obj.get("eta"):
            extras.append(f"eta={obj['eta']}")
        if obj.get("folder"):
            extras.append(f"domain={obj['folder']}")

        line = f"  - {name_part}"
        if extras:
            line += f" ({', '.join(extras)})"
        if obj.get("description"):
            line += f"\n    {obj['description']}"
        lines.append(line)
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
    qs, model_class, model_name, display_name, url_slug, filters_applied, total_count
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
        "url_slug": url_slug,
        "query_type": "summary",
        "filters_applied": filters_applied,
        "total_count": total_count,
        "objects": [],
        "summary": summary,
    }
