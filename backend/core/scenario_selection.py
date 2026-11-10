"""Scenario selection: one set of risk scenario filters shared by every view of a
risk assessment (scenario table, matrices, action plan, exports).

The selection is the `RiskScenarioFilter` parameters behind a `scenario__`
prefix, so it can share a query string with the action plan's own control
filters (`owner`, `folder`, `created_at` exist on both). See
documentation/architecture/decisions/risk-assessment-scenario-scope.md.
"""

from dataclasses import dataclass, field
from functools import cache
from uuid import UUID

import django_filters as df
from django import forms
from django.db.models import (
    Case,
    CharField,
    Count,
    IntegerField,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, Lower
from django.http import QueryDict
from rest_framework.exceptions import ValidationError

from core.models import Actor, AppliedControl, RiskAssessment, RiskScenario
from core.pagination import CustomLimitOffsetPagination
from core.utils import sanitize_xlsx_value
from iam.models import Permission, RoleAssignment

PREFIX = "scenario"
PARAM_PREFIX = f"{PREFIX}__"

# Fixed by the assessment the selection applies to.
FIXED_FILTERS = ("risk_assessment", "folder", "perimeter")

LINK_TYPE_PARAM = "link_type"
LINK_ADDITIONAL = "additional"
LINK_EXISTING = "existing"
LINK_ALL = "all"
LINK_TYPES = (LINK_ADDITIONAL, LINK_EXISTING, LINK_ALL)

# Filters the selection bar offers, in display order. The first four have a
# handful of fixed values and travel with the selection. The related ones can
# hold thousands of objects: the selection only says whether they have anything
# to offer, and their options are served one page at a time.
FACETS = ("within_tolerance", "treatment", "current_level", "residual_level")
RELATED_FACETS = ("owner", "threats", "assets", "qualifications", "filtering_labels")
_LEVEL_FACETS = ("current_level", "residual_level")

# What `str(actor)` shows: a user's full name when they have one, else their
# email; a team's or an entity's name.
_OWNER_LABEL = Case(
    When(
        user__first_name__gt="",
        user__last_name__gt="",
        then=Concat("user__first_name", Value(" "), "user__last_name"),
    ),
    default=Coalesce("user__email", "team__name", "entity__name"),
    output_field=CharField(),
)

# Related filter -> (fields its search reads, expression its options sort on).
# Both follow the label the option shows.
_RELATED_LOOKUPS = {
    "owner": (
        (
            "user__first_name",
            "user__last_name",
            "user__email",
            "team__name",
            "entity__name",
        ),
        _OWNER_LABEL,
    ),
    "threats": (("name",), "name"),
    "assets": (("name",), "name"),
    "qualifications": (("name",), "name"),
    "filtering_labels": (("label",), "label"),
}


class _DunderPrefixForm(forms.Form):
    """Join the form prefix with `__` instead of Django's `-`, matching the
    double-underscore names the rest of the API filters on."""

    def add_prefix(self, field_name):
        return f"{self.prefix}__{field_name}" if self.prefix else field_name


@cache
def selection_filter_class():
    # Built lazily: RiskScenarioFilter lives in core.views, which imports us.
    from core.views import RiskScenarioFilter

    class ScenarioSelectionFilter(RiskScenarioFilter):
        class Meta(RiskScenarioFilter.Meta):
            form = _DunderPrefixForm

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for name in FIXED_FILTERS:
                self.filters.pop(name, None)

    return ScenarioSelectionFilter


@dataclass
class ScenarioSelection:
    risk_assessment: RiskAssessment
    scenarios: QuerySet
    # Filter name -> raw values, as applied (stale values already dropped).
    filters: dict[str, list[str]] = field(default_factory=dict)
    # Values dropped because the object they point to no longer exists.
    ignored: list[dict[str, str]] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return bool(self.filters)


def _filter_name(param: str) -> str:
    name = param[len(PARAM_PREFIX) :]
    # QueryArrayWidget also reads `name[]`.
    return name[:-2] if name.endswith("[]") else name


def _requested_filters(params: QueryDict, filters: dict) -> dict[str, list[str]]:
    requested: dict[str, list[str]] = {}
    unknown = []
    for param in params:
        if not param.startswith(PARAM_PREFIX):
            continue
        name = _filter_name(param)
        if name not in filters:
            unknown.append(param)
            continue
        values = [v for v in params.getlist(param) if v != ""]
        if values:
            requested.setdefault(name, []).extend(values)
    if unknown:
        # A mistyped selection must not silently export every scenario.
        raise ValidationError({p: "Unknown scenario filter." for p in unknown})
    return requested


def _model_filter_queryset(flt, request):
    if not isinstance(flt, (df.ModelMultipleChoiceFilter, df.ModelChoiceFilter)):
        return None
    queryset = flt.queryset
    return queryset(request) if callable(queryset) else queryset


def _drop_stale_values(requested, filters, request):
    """Split model-backed values into existing ones and ones that point nowhere.

    A shared link outlives the objects it names; failing the whole request on a
    deleted asset would make the link useless, so the value is reported instead.
    """
    ignored = []
    for name, values in list(requested.items()):
        queryset = _model_filter_queryset(filters[name], request)
        if queryset is None:
            continue
        parsed = {}
        for value in values:
            try:
                parsed[value] = UUID(value)
            except ValueError:
                pass
        existing = (
            set(queryset.filter(pk__in=parsed.values()).values_list("pk", flat=True))
            if parsed
            else set()
        )
        kept = []
        for value in values:
            if parsed.get(value) in existing:
                kept.append(value)
            else:
                ignored.append({"filter": name, "value": value})
        if kept:
            requested[name] = kept
        else:
            del requested[name]
    return ignored


def _run_filter(requested, scenarios, request):
    data = QueryDict(mutable=True)
    for name, values in requested.items():
        data.setlist(f"{PARAM_PREFIX}{name}", values)
    filterset = selection_filter_class()(
        data, queryset=scenarios, request=request, prefix=PREFIX
    )
    if not filterset.is_valid():
        raise ValidationError(
            {f"{PARAM_PREFIX}{k}": v for k, v in filterset.errors.items()}
        )
    # A single-valued filter reads the last value it is given and drops the
    # rest: the selection would then state values it did not apply.
    cleaned = filterset.form.cleaned_data
    surplus = [
        name
        for name, values in requested.items()
        if len(values) > 1
        and not isinstance(cleaned.get(name), (list, tuple, QuerySet))
    ]
    if surplus:
        raise ValidationError(
            {f"{PARAM_PREFIX}{name}": "Expected a single value." for name in surplus}
        )
    return filterset.qs


def resolve_selection(request, risk_assessment: RiskAssessment) -> ScenarioSelection:
    """The assessment's scenarios narrowed by the request's `scenario__*` params."""
    scenarios = risk_assessment.risk_scenarios.all()
    params = getattr(request, "query_params", request.GET)
    filters = selection_filter_class()(
        queryset=scenarios, request=request, prefix=PREFIX
    ).filters
    requested = _requested_filters(params, filters)
    if not requested:
        return ScenarioSelection(risk_assessment, scenarios)
    ignored = _drop_stale_values(requested, filters, request)
    if requested:
        scenarios = _run_filter(requested, scenarios, request)
    return ScenarioSelection(risk_assessment, scenarios, requested, ignored)


def resolve_link_type(request) -> str:
    params = getattr(request, "query_params", request.GET)
    link_type = params.get(LINK_TYPE_PARAM) or LINK_ALL
    if link_type not in LINK_TYPES:
        raise ValidationError(
            {LINK_TYPE_PARAM: f"Expected one of: {', '.join(LINK_TYPES)}."}
        )
    return link_type


def link_q(scenarios, link_type: str, prefix: str = "") -> Q:
    """Controls linked to `scenarios` through the relations `link_type` names."""
    q = Q()
    if link_type in (LINK_ADDITIONAL, LINK_ALL):
        q |= Q(**{f"{prefix}risk_scenarios__in": scenarios})
    if link_type in (LINK_EXISTING, LINK_ALL):
        q |= Q(**{f"{prefix}risk_scenarios_e__in": scenarios})
    return q


def action_plan_controls(user, scenarios, link_type: str) -> QuerySet:
    """The action plan: viewable controls linked to `scenarios` by `link_type`."""
    viewable = RoleAssignment.get_viewable_object_ids(user, AppliedControl)
    return (
        AppliedControl.objects.filter(link_q(scenarios, link_type))
        .distinct()
        .filter(id__in=viewable)
    )


def linked_scenarios_q(control, link_type: str) -> Q:
    """Scenarios a control is linked to through the relations `link_type` names."""
    q = Q()
    if link_type in (LINK_ADDITIONAL, LINK_ALL):
        q |= Q(applied_controls=control)
    if link_type in (LINK_EXISTING, LINK_ALL):
        q |= Q(existing_applied_controls=control)
    return q


# ------------------------------------------------------------------ facets


def _viewable_objects(user, model) -> QuerySet:
    """`model` objects the user may view.

    Mirrors the related-field masking of the list endpoints, so an option never
    names an object the scenario table would hide. The viewable ids stay a
    subquery: they are never loaded for the whole instance.
    """
    objects = model.objects.all()
    if model is Actor:
        # An actor's label is its user, team or entity.
        objects = objects.select_related("user", "team", "entity")
    try:
        viewable = RoleAssignment.get_viewable_object_ids(user, model)
    except NotImplementedError, Permission.DoesNotExist:
        return objects
    return objects.filter(pk__in=viewable)


def _related_objects(risk_assessment, name, user) -> QuerySet:
    """What a related filter can offer: the viewable objects linked to at least
    one scenario of the assessment. One row per link, until grouped."""
    field = RiskScenario._meta.get_field(name)
    return _viewable_objects(user, field.related_model).filter(
        **{f"{field.related_query_name()}__risk_assessment": risk_assessment}
    )


def _scenarios_without(selection, name, request):
    if name not in selection.filters:
        return selection.scenarios
    requested = {k: v for k, v in selection.filters.items() if k != name}
    base = selection.risk_assessment.risk_scenarios.all()
    return _run_filter(requested, base, request) if requested else base


def _tolerance_counts(scenarios):
    filterset = selection_filter_class()(queryset=scenarios, prefix=PREFIX)
    return [
        {
            "value": value,
            "count": filterset.filter_within_tolerance(
                scenarios, "within_tolerance", value
            ).count(),
        }
        for value in ("NO", "YES")
    ]


def _grouped_counts(scenarios, field_name):
    return {
        row[field_name]: row["n"]
        for row in scenarios.values(field_name).annotate(n=Count("id", distinct=True))
    }


def selection_facets(selection: ScenarioSelection, request) -> dict:
    """For each fixed-value filter the bar offers, the scenarios each value would
    keep given the other active filters."""
    risk_assessment = selection.risk_assessment
    facets = {}
    for name in FACETS:
        base = _scenarios_without(selection, name, request)
        if name == "within_tolerance":
            facets[name] = (
                _tolerance_counts(base) if risk_assessment.risk_tolerance >= 0 else []
            )
            continue
        counts = _grouped_counts(base, name)
        if name == "treatment":
            facets[name] = [
                {"value": value, "count": counts.get(value, 0)}
                for value, _label in RiskScenario.TREATMENT_OPTIONS
            ]
            continue
        levels = len(risk_assessment.risk_matrix.parse_json().get("risk", []))
        values = list(range(levels - 1, -1, -1))
        if counts.get(-1):
            values.append(-1)
        facets[name] = [{"value": str(v), "count": counts.get(v, 0)} for v in values]
    return facets


def selection_related_filters(selection: ScenarioSelection, request) -> dict:
    """For each related filter, whether the assessment has anything to pick and
    the labels of the values applied. The options themselves are paged, see
    `related_filter_options`."""
    user = request.user
    related = {}
    for name in RELATED_FACETS:
        model = RiskScenario._meta.get_field(name).related_model
        applied = selection.filters.get(name)
        selected = (
            _viewable_objects(user, model).filter(pk__in=applied) if applied else ()
        )
        related[name] = {
            "has_options": _related_objects(
                selection.risk_assessment, name, user
            ).exists(),
            "selected": [{"value": str(obj.pk), "label": str(obj)} for obj in selected],
        }
    return related


class RelatedOptionsPagination(CustomLimitOffsetPagination):
    default_limit = 25
    max_limit = 100


def related_filter_options(
    selection: ScenarioSelection, name: str, request, search: str = ""
) -> QuerySet:
    """The objects a related filter offers, each with `scenario_count`: the
    scenarios it would keep given the other active filters.

    Applied values come first, so they can be unticked without looking for
    them, then the values keeping the most scenarios. The label and the id
    settle ties: a page boundary must not depend on the database's mood.
    """
    if name not in RELATED_FACETS:
        raise ValidationError(
            {"filter": f"Expected one of: {', '.join(RELATED_FACETS)}."}
        )
    link = RiskScenario._meta.get_field(name).related_query_name()
    search_fields, sort_key = _RELATED_LOOKUPS[name]
    options = _related_objects(selection.risk_assessment, name, request.user)
    # Every word has to match, in any of the fields: "ada lovelace" finds a
    # first and a last name.
    for term in search.split():
        matches = Q()
        for search_field in search_fields:
            matches |= Q(**{f"{search_field}__icontains": term})
        options = options.filter(matches)
    # Counts the links `_related_objects` joined, so this assessment's only.
    # Without other filters every one of them counts.
    others = {k: v for k, v in selection.filters.items() if k != name}
    kept = (
        Q(**{f"{link}__in": _scenarios_without(selection, name, request).values("pk")})
        if others
        else None
    )
    options = options.annotate(scenario_count=Count(link, filter=kept, distinct=True))
    ordering = ["-scenario_count", Lower(sort_key), "pk"]
    if applied := selection.filters.get(name):
        options = options.annotate(
            unapplied=Case(
                When(pk__in=applied, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        ordering.insert(0, "unapplied")
    return options.order_by(*ordering)


# ----------------------------------------------------------------- reports


def selection_report_context(
    selection: ScenarioSelection, total: int, user
) -> dict | None:
    """What a filtered report states about its selection, or None when unfiltered.

    Choice values (tolerance, treatment) stay raw keys for the locale template to
    label; levels and related objects are resolved here. An object `user` cannot
    view keeps the id the request gave, as it does on the selection bar.
    """
    if not selection.active:
        return None
    risk_levels = selection.risk_assessment.risk_matrix.parse_json_translated().get(
        "risk", []
    )
    filters = selection_filter_class()(prefix=PREFIX).filters
    rows = []
    for name, values in selection.filters.items():
        if name in _LEVEL_FACETS:
            labels = [
                str(risk_levels[int(v)].get("name", v))
                if 0 <= int(v) < len(risk_levels)
                else "--"
                for v in values
            ]
        elif (queryset := _model_filter_queryset(filters[name], None)) is not None:
            names = {
                str(obj.pk): str(obj)
                for obj in _viewable_objects(user, queryset.model).filter(pk__in=values)
            }
            labels = sorted(names.values()) + [
                v for v in values if str(UUID(v)) not in names
            ]
        else:
            labels = list(values)
        rows.append({"key": name, "values": labels})
    return {"count": selection.scenarios.count(), "total": total, "filters": rows}


def append_selection_sheet(workbook, report_selection: dict) -> None:
    """A spreadsheet has no cover page: a filtered one says so on its own sheet."""
    sheet = workbook.create_sheet("Selection")
    sheet.append(
        ["Scenarios", f"{report_selection['count']} / {report_selection['total']}"]
    )
    for row in report_selection["filters"]:
        sheet.append([row["key"], sanitize_xlsx_value(", ".join(row["values"]))])
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 60
