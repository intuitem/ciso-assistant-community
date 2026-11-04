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
from django.db.models import Count, Q, QuerySet
from django.http import QueryDict
from rest_framework.exceptions import ValidationError

from core.models import AppliedControl, RiskAssessment, RiskScenario
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

# Filters the selection bar offers, in display order.
FACETS = (
    "within_tolerance",
    "treatment",
    "current_level",
    "residual_level",
    "owner",
    "threats",
    "assets",
    "qualifications",
    "filtering_labels",
)
_LEVEL_FACETS = ("current_level", "residual_level")
_RELATED_FACETS = ("owner", "threats", "assets", "qualifications", "filtering_labels")


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


def _viewable_ids(user, model):
    """IDs of `model` the user may view, or None when nothing is hidden from them.

    Mirrors the related-field masking of the list endpoints, so an option label
    never names an object the scenario table would hide.
    """
    try:
        return {str(pk) for pk in RoleAssignment.get_viewable_object_ids(user, model)}
    except NotImplementedError, Permission.DoesNotExist:
        return None


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


def _related_options(risk_assessment, field_name, user):
    model = RiskScenario._meta.get_field(field_name).related_model
    objects = model.objects.filter(
        pk__in=risk_assessment.risk_scenarios.values(field_name)
    ).distinct()
    viewable = _viewable_ids(user, model)
    options = [
        {"value": str(obj.pk), "label": str(obj)}
        for obj in objects
        if viewable is None or str(obj.pk) in viewable
    ]
    return sorted(options, key=lambda o: o["label"].lower())


def selection_facets(selection: ScenarioSelection, request) -> dict:
    """For each filter the bar offers, the scenarios each value would keep given
    the other active filters."""
    risk_assessment = selection.risk_assessment
    user = request.user
    facets = {}
    for name in FACETS:
        base = _scenarios_without(selection, name, request)
        if name == "within_tolerance":
            facets[name] = (
                _tolerance_counts(base) if risk_assessment.risk_tolerance >= 0 else []
            )
            continue
        if name == "treatment":
            counts = _grouped_counts(base, "treatment")
            facets[name] = [
                {"value": value, "count": counts.get(value, 0)}
                for value, _label in RiskScenario.TREATMENT_OPTIONS
            ]
            continue
        if name in _LEVEL_FACETS:
            counts = _grouped_counts(base, name)
            levels = len(risk_assessment.risk_matrix.parse_json().get("risk", []))
            values = list(range(levels - 1, -1, -1))
            if counts.get(-1):
                values.append(-1)
            facets[name] = [
                {"value": str(v), "count": counts.get(v, 0)} for v in values
            ]
            continue
        counts = _grouped_counts(base, name)
        facets[name] = [
            {**option, "count": counts.get(UUID(option["value"]), 0)}
            for option in _related_options(risk_assessment, name, user)
        ]
    return facets


# ----------------------------------------------------------------- reports


def selection_report_context(selection: ScenarioSelection, total: int) -> dict | None:
    """What a filtered report states about its selection, or None when unfiltered.

    Choice values (tolerance, treatment) stay raw keys for the locale template to
    label; levels and related objects are resolved here.
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
            labels = sorted(str(obj) for obj in queryset.filter(pk__in=values))
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
