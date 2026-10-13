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

from .risk_levels import (
    LEVEL_FIELDS,
    known_level_names,
    level_label,
    matrices_for_scenarios,
    resolve_levels_by_matrix,
)

logger = structlog.get_logger(__name__)

# Page size for paginated list results
LIST_PAGE_SIZE = 20
# Threshold to auto-switch list queries to summary + first page
SUMMARY_THRESHOLD = 30


def execute_tool_query(arguments: dict, scope, parsed_context=None) -> dict | None:
    """
    Execute a structured query from tool call arguments.

    arguments keys:
        model (required): e.g. "applied_control", "asset", "risk_scenario"
        action (required): "list", "count", "summary"
        domain: folder/domain name filter
        status, treatment, result: status-like filters
        priority, category, effort, severity: categorization filters
        risk_level, risk_level_scope: risk scenario rating filters
        date_filter: "overdue", "due_this_month", "expiring_this_month", "created_recently"
        search: text search in name/description/ref_id
        page: page number (default 1)

    scope: ReadScope — every row returned is one the user could read via the API.

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

    qs = scope.queryset(model_class)
    if model_name == "RiskScenario":
        qs = qs.select_related("risk_assessment__risk_matrix")
    if model_name == "RequirementAssessment":
        # Non-assessable nodes are headings. Progress, the donut and flash mode
        # all ignore them, so counting them here would disagree with the page.
        qs = qs.filter(requirement__assessable=True)

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
        folder_ids = _resolve_domain(domain, scope.folder_ids)
        if folder_ids:
            if model_name == "Folder":
                qs = qs.filter(id__in=folder_ids)
            elif hasattr(model_class, "folder_id"):
                qs = qs.filter(folder_id__in=folder_ids)
            elif hasattr(model_class, "compliance_assessment"):
                qs = qs.filter(compliance_assessment__folder_id__in=folder_ids)
            else:
                # No folder to filter on — say so rather than silently widening
                folder_ids = []
        if folder_ids:
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

    # Choice-field filters. All accept several values so a question like
    # "non-compliant or partially compliant" is one authoritative count rather
    # than two counts the model has to add up itself.
    # Severity is resolved per model: Incident's 1..6 is not core.Severity's -1..4.
    for field in (
        "status",
        "treatment",
        "result",
        "priority",
        "category",
        "effort",
        "severity",
    ):
        raw = arguments.get(field)
        if raw is None or raw == "" or not hasattr(model_class, field):
            continue
        values, labels = [], []
        for candidate in _as_list(raw):
            resolved = _resolve_choice_value(model_class, field, candidate)
            if resolved is None:
                continue
            if resolved not in values:
                values.append(resolved)
                labels.append(_choice_label(model_class, field, resolved))
        if not values:
            return _unresolved_filter_result(
                model_class,
                field,
                raw,
                model_name,
                display_name,
                url_slug,
                action,
                filters_applied,
            )
        qs = qs.filter(**{f"{field}__in": values})
        filters_applied.append(f"{field} = {' or '.join(labels)}")

    # Risk level — resolved against the risk matrix wording
    risk_level = arguments.get("risk_level")
    if risk_level and model_name == "RiskScenario":
        level_scope = arguments.get("risk_level_scope") or "current"
        level_field = LEVEL_FIELDS.get(level_scope, "current_level")
        terms = _as_list(risk_level)
        matrices = matrices_for_scenarios(qs)
        per_matrix: dict[str, set[int]] = {}
        for term in terms:
            for matrix_id, levels in resolve_levels_by_matrix(term, matrices).items():
                per_matrix.setdefault(matrix_id, set()).update(levels)
        wanted = " or ".join(str(t) for t in terms)
        if per_matrix:
            level_q = Q()
            for matrix_id, levels in per_matrix.items():
                level_q |= Q(
                    risk_assessment__risk_matrix_id=matrix_id,
                    **{f"{level_field}__in": sorted(levels)},
                )
            qs = qs.filter(level_q)
            filters_applied.append(f"{level_scope} risk level = {wanted}")
        else:
            known = known_level_names(matrices)
            return {
                "model_name": model_name,
                "display_name": display_name,
                "url_slug": url_slug,
                "query_type": action,
                "filters_applied": filters_applied
                + [f"{level_scope} risk level = {wanted} (unknown)"],
                "total_count": 0,
                "objects": [],
                "note": (
                    f"'{wanted}' is not a level of the risk matrix in use. "
                    f"Levels available: {', '.join(known)}."
                    if known
                    else f"'{wanted}' is not a level of the risk matrix in use."
                ),
            }

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

    # Text search — also searches through related object names (e.g., framework name)
    search = arguments.get("search")
    if search:
        search_q = Q()
        if hasattr(model_class, "name"):
            search_q |= Q(name__icontains=search)
        if hasattr(model_class, "description"):
            search_q |= Q(description__icontains=search)
        if hasattr(model_class, "ref_id"):
            search_q |= Q(ref_id__icontains=search)
        # Search through FK names for richer matching
        if hasattr(model_class, "framework"):
            search_q |= Q(framework__name__icontains=search)
        if search_q:
            qs = qs.filter(search_q)
            filters_applied.append(f"search = '{search}'")

    total_count = qs.count()
    try:
        page = int(arguments.get("page", 1) or 1)
    except TypeError, ValueError:
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

    if result.get("note"):
        parts.append(result["note"])

    return "\n".join(parts)


# --- Internal helpers ---


def _unresolved_filter_result(
    model_class,
    field_name: str,
    value,
    model_name: str,
    display_name: str,
    url_slug: str,
    action: str,
    filters_applied: list[str],
) -> dict:
    """Empty result for an unrecognised filter value — never the unfiltered set."""
    try:
        labels = [
            str(label)
            for _, label in (model_class._meta.get_field(field_name).choices or [])
        ]
    except Exception:
        labels = []
    note = f"'{value}' is not a valid {field_name} for {display_name}."
    if labels:
        note += f" Valid values: {', '.join(labels)}."
    return {
        "model_name": model_name,
        "display_name": display_name,
        "url_slug": url_slug,
        "query_type": action,
        "filters_applied": filters_applied + [f"{field_name} = {value} (unknown)"],
        "total_count": 0,
        "objects": [],
        "note": note,
    }


def _as_list(value) -> list:
    """Accept a scalar, a list, or a comma-separated string from the model."""
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v not in (None, "")]
    if isinstance(value, str) and "," in value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return [value]


def _choice_label(model_class, field_name: str, value) -> str:
    try:
        labels = dict(model_class._meta.get_field(field_name).choices or [])
    except Exception:
        labels = {}
    return str(labels.get(value, value))


def _resolve_choice_value(model_class, field_name: str, value):
    """Match a stored value (3, "3") or its label ("high"); None if neither."""
    try:
        field = model_class._meta.get_field(field_name)
    except Exception:
        return None

    choices = list(field.choices or [])
    if not choices:
        try:
            return int(value)
        except TypeError, ValueError:
            return None

    for stored, label in choices:
        if value == stored or str(value).strip() == str(stored):
            return stored
        if str(value).strip().casefold() == str(label).strip().casefold():
            return stored

    logger.info(
        "Dropping unresolvable %s value for %s: %r",
        field_name,
        model_class.__name__,
        value,
    )
    return None


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
        for scope in ("inherent", "current", "residual"):
            level = obj.get(f"{scope}_risk_level")
            if level is not None:
                extras.append(f"{scope}_risk={level}")
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

        # Risk levels, labelled with the matrix wording rather than the index
        if model_name == "RiskScenario":
            matrix = getattr(getattr(obj, "risk_assessment", None), "risk_matrix", None)
            for scope, level_field in LEVEL_FIELDS.items():
                level = getattr(obj, level_field, None)
                if level is not None and level >= 0:
                    data[f"{scope}_risk_level"] = level_label(matrix, level)

        # Folder
        if hasattr(obj, "folder") and obj.folder:
            data["folder"] = str(obj.folder)

        objects.append(data)

    return objects


def _choice_breakdown(qs, model_class, field: str, order_by: str) -> dict:
    """Count per value of a choice field, keyed by the human label."""
    try:
        labels = dict(model_class._meta.get_field(field).choices or [])
    except Exception:
        labels = {}
    counts = qs.values(field).annotate(count=Count("id")).order_by(order_by)
    breakdown = {}
    for item in counts:
        if not item["count"]:
            continue
        value = item[field]
        label = labels.get(value) or value or "--"
        breakdown[str(label)] = breakdown.get(str(label), 0) + item["count"]
    return breakdown


def _risk_level_breakdowns(qs) -> dict:
    """Count risk scenarios per level label, highest level first, per scope."""
    matrices = {str(m.id): m for m in matrices_for_scenarios(qs)}
    if not matrices:
        return {}

    breakdowns = {}
    for scope, level_field in LEVEL_FIELDS.items():
        counts = qs.values("risk_assessment__risk_matrix_id", level_field).annotate(
            count=Count("id")
        )
        buckets: dict[str, list] = {}
        for item in counts:
            level = item[level_field]
            matrix = matrices.get(str(item["risk_assessment__risk_matrix_id"]))
            label = level_label(matrix, level)
            bucket = buckets.setdefault(label, [level if level is not None else -1, 0])
            bucket[0] = max(bucket[0], level if level is not None else -1)
            bucket[1] += item["count"]

        if not buckets or set(buckets) == {"--"}:
            continue
        breakdowns[f"{scope.capitalize()} risk level breakdown"] = {
            label: count
            for label, (_, count) in sorted(
                buckets.items(), key=lambda kv: kv[1][0], reverse=True
            )
        }
    return breakdowns


def _build_summary(
    qs, model_class, model_name, display_name, url_slug, filters_applied, total_count
) -> dict:
    """Build a summary/breakdown of the queryset."""
    summary = {}

    for field, title, order_by in (
        ("status", "Status breakdown", "-count"),
        ("treatment", "Treatment breakdown", "-count"),
        ("result", "Result breakdown", "-count"),
        ("priority", "Priority breakdown", "priority"),
        ("severity", "Severity breakdown", "-severity"),
    ):
        if not hasattr(model_class, field):
            continue
        breakdown = _choice_breakdown(qs, model_class, field, order_by)
        if breakdown:
            summary[title] = breakdown

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

    if model_name == "RiskScenario":
        summary.update(_risk_level_breakdowns(qs))

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
