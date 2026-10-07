"""Reads against the database: scope, queryset construction, serialization,
paging limits and the save-time validator. The workflow engine's own tests
cover the same behaviour through a run; these pin it at the core boundary,
where a consumer with no run identity will also call it."""

import uuid
from datetime import date

import pytest
from django.db.models import Prefetch

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from core.reads import (
    READ_DEFAULT_LIMIT,
    READABLE_MODELS,
    ReadError,
    ReadScope,
    accessible_folder_ids,
    build_queryset,
    effective_computed,
    page_limit,
    read_max_limit,
    scoped_prefetches,
    serialize_row,
    subtree_folder_ids,
    validate_read_config,
)
from iam.models import Folder


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def scope_of(folder, **kwargs):
    return ReadScope(folder_ids=subtree_folder_ids(folder), **kwargs)


def rows(config, scope, resolve=None):
    _entry, fields, queryset = (
        build_queryset(config, scope, resolve)
        if resolve
        else build_queryset(config, scope)
    )
    return [serialize_row(obj, fields) for obj in queryset]


def names(config, scope, resolve=None):
    return [row["name"] for row in rows(config, scope, resolve)]


def make_audit(domain, requirements=1, assessable=True):
    suffix = uuid.uuid4().hex[:8]
    framework = Framework.objects.create(
        name="FW", urn=f"urn:test:fw-{suffix}", folder=Folder.get_root_folder()
    )
    perimeter = Perimeter.objects.create(name=f"P {suffix}", folder=domain)
    audit = ComplianceAssessment.objects.create(
        name=f"Audit {suffix}", framework=framework, perimeter=perimeter, folder=domain
    )
    assessments = []
    for index in range(requirements):
        requirement = RequirementNode.objects.create(
            name=f"Req {index}",
            urn=f"urn:test:fw-{suffix}:req{index}",
            framework=framework,
            assessable=assessable,
            folder=Folder.get_root_folder(),
        )
        assessments.append(
            RequirementAssessment.objects.create(
                compliance_assessment=audit, requirement=requirement, folder=domain
            )
        )
    return audit, assessments


@pytest.mark.django_db
class TestFolderSets:
    def test_subtree_is_the_folder_and_its_descendants_only(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        sub = make_domain("Sub", mine)
        deeper = make_domain("Deeper", sub)
        sibling = make_domain("Sibling", parent)
        assert subtree_folder_ids(mine) == {mine.id, sub.id, deeper.id}
        assert sibling.id not in subtree_folder_ids(mine)
        assert parent.id not in subtree_folder_ids(mine)

    def test_accessible_adds_the_ancestors(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        sub = make_domain("Sub", mine)
        sibling = make_domain("Sibling", parent)
        accessible = accessible_folder_ids(mine)
        assert {mine.id, sub.id, parent.id, Folder.get_root_folder().id} <= accessible
        assert sibling.id not in accessible


@pytest.mark.django_db
class TestReadScope:
    def test_folder_ids_are_frozen_whatever_was_passed(self):
        scope = ReadScope(folder_ids={uuid.uuid4()})
        assert isinstance(scope.folder_ids, frozenset)
        with pytest.raises(AttributeError):
            scope.folder_ids = set()

    def test_rows_outside_the_folders_are_invisible(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        sub = make_domain("Sub", mine)
        sibling = make_domain("Sibling", parent)
        for folder, name in [
            (parent, "parent"),
            (mine, "mine"),
            (sub, "sub"),
            (sibling, "sibling"),
        ]:
            AppliedControl.objects.create(name=name, folder=folder)
        assert set(names({"model": "applied_control"}, scope_of(mine))) == {
            "mine",
            "sub",
        }

    def test_no_identity_means_every_row_in_the_folders(self):
        domain = make_domain("Domain")
        for index in range(3):
            AppliedControl.objects.create(name=f"AC {index}", folder=domain)
        assert len(names({"model": "applied_control"}, scope_of(domain))) == 3

    def test_an_identity_narrows_to_what_it_may_view(self):
        domain = make_domain("Domain")
        for index in range(3):
            AppliedControl.objects.create(name=f"AC {index}", folder=domain)
        scope = scope_of(
            domain,
            viewable=lambda model: model.objects.filter(name="AC 1").values_list(
                "id", flat=True
            ),
        )
        assert names({"model": "applied_control"}, scope) == ["AC 1"]

    def test_an_identity_that_sees_nothing_reads_nothing(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="AC", folder=domain)
        scope = scope_of(domain, viewable=lambda model: model.objects.none())
        assert names({"model": "applied_control"}, scope) == []

    def test_related_folders_default_to_the_read_folders(self):
        domain = make_domain("Domain")
        scope = scope_of(domain)
        queryset = scope.narrow_related(AppliedControl, AppliedControl.objects.all())
        assert str(queryset.query) == str(
            AppliedControl.objects.filter(folder_id__in=scope.folder_ids).query
        )


@pytest.mark.django_db
class TestBuildQueryset:
    def test_unknown_model(self):
        with pytest.raises(ReadError, match="unknown model 'user'"):
            build_queryset({"model": "user"}, scope_of(make_domain("D")))
        with pytest.raises(ReadError, match="unknown model 'None'"):
            build_queryset({}, scope_of(make_domain("D")))

    def test_returns_the_entry_its_fields_and_a_lazy_queryset(self):
        domain = make_domain("Domain")
        entry, fields, queryset = build_queryset(
            {"model": "applied_control"}, scope_of(domain)
        )
        assert entry is READABLE_MODELS["applied_control"]
        assert fields == entry.readable_fields()
        assert queryset.model is AppliedControl
        assert queryset.count() == 0

    def test_default_order_is_newest_first_with_an_id_tie_break(self):
        domain = make_domain("Domain")
        _e, _f, queryset = build_queryset(
            {"model": "applied_control"}, scope_of(domain)
        )
        assert queryset.query.order_by == ("-created_at", "id")
        _e, _f, queryset = build_queryset(
            {"model": "applied_control", "order_by": "eta"}, scope_of(domain)
        )
        assert queryset.query.order_by == ("eta", "id")

    def test_ordering_is_applied(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="B", folder=domain, eta=date(2026, 9, 1))
        AppliedControl.objects.create(name="A", folder=domain, eta=date(2026, 8, 1))
        assert names(
            {"model": "applied_control", "order_by": "eta"}, scope_of(domain)
        ) == ["A", "B"]
        assert names(
            {"model": "applied_control", "order_by": "-eta"}, scope_of(domain)
        ) == ["B", "A"]

    def test_only_readable_fields_order(self):
        with pytest.raises(ReadError, match="'folder' is not an orderable field"):
            build_queryset(
                {"model": "applied_control", "order_by": "folder"},
                scope_of(make_domain("D")),
            )
        with pytest.raises(ReadError, match="'-scores' is not an orderable field"):
            build_queryset(
                {"model": "compliance_assessment", "order_by": "-scores"},
                scope_of(make_domain("D")),
            )

    def test_filters_narrow_the_rows(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="on", folder=domain, status="active")
        AppliedControl.objects.create(name="off", folder=domain, status="to_do")
        config = {
            "model": "applied_control",
            "filters": {
                "conditions": [{"field": "status", "op": "eq", "value": "active"}]
            },
        }
        assert names(config, scope_of(domain)) == ["on"]

    def test_filter_values_are_resolved_before_compiling(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="on", folder=domain, status="active")
        AppliedControl.objects.create(name="off", folder=domain, status="to_do")
        config = {
            "model": "applied_control",
            "filters": {
                "conditions": [{"field": "status", "op": "eq", "value": "{{s}}"}]
            },
        }
        assert names(
            config, scope_of(domain), lambda v: v.replace("{{s}}", "active")
        ) == ["on"]

    def test_a_bad_filter_is_a_read_error_not_a_query(self):
        for bad in (
            {"conditions": [{"field": "folder", "op": "eq", "value": "x"}]},
            {"conditions": [{"field": "eta", "op": "contains", "value": "x"}]},
            {"conditions": [{"field": "name", "op": "like", "value": "x"}]},
        ):
            with pytest.raises(ReadError):
                build_queryset(
                    {"model": "applied_control", "filters": bad},
                    scope_of(make_domain("D")),
                )

    def test_an_incompatible_value_is_djangos_to_refuse(self):
        """Compiling a typed lookup is where Django validates the value, so a
        caller wraps build_queryset as well as evaluation."""
        from django.core.exceptions import ValidationError

        config = {
            "model": "applied_control",
            "filters": {
                "conditions": [{"field": "eta", "op": "gt", "value": "not a date"}]
            },
        }
        with pytest.raises(ValidationError):
            build_queryset(config, scope_of(make_domain("Domain")))

    def test_the_base_filter_always_applies(self):
        domain = make_domain("Domain")
        make_audit(domain, requirements=2, assessable=True)
        make_audit(domain, requirements=2, assessable=False)
        _e, _f, queryset = build_queryset(
            {"model": "requirement_assessment"}, scope_of(domain)
        )
        assert queryset.count() == 2
        assert all(ra.requirement.assessable for ra in queryset)

    def test_an_unknown_include_is_refused_before_any_query(self):
        with pytest.raises(
            ReadError, match="'nope' is not includable for model 'applied_control'"
        ):
            build_queryset(
                {"model": "applied_control", "include": ["nope"]},
                scope_of(make_domain("D")),
            )

    def test_declared_relations_are_prefetched_and_joined(self):
        domain = make_domain("Domain")
        _e, _f, queryset = build_queryset(
            {"model": "compliance_assessment"}, scope_of(domain)
        )
        assert set(queryset._prefetch_related_lookups) >= {"reviewers", "authors"}
        _e, _f, queryset = build_queryset({"model": "finding"}, scope_of(domain))
        assert "findings_assessment" in queryset.query.select_related

    @pytest.mark.parametrize("key", sorted(READABLE_MODELS))
    def test_every_entry_compiles_and_evaluates_with_every_include(self, key):
        """The joins, prefetches and ordering of every entry run against both
        databases, with every optional value requested at once."""
        entry = READABLE_MODELS[key]
        scope = scope_of(make_domain("Domain"))
        config = {"model": key, "include": sorted(entry.optional_computed)}
        _entry, fields, queryset = build_queryset(config, scope)
        assert list(queryset) == []
        assert set(fields) <= {f.name for f in entry.model._meta.concrete_fields}


@pytest.mark.django_db
class TestScopedPrefetches:
    def link(self, assessment, folder, name):
        control = AppliedControl.objects.create(name=name, folder=folder)
        assessment.applied_controls.add(control)
        return control

    def test_nothing_is_built_unless_the_computed_value_was_asked_for(self):
        entry = READABLE_MODELS["requirement_assessment"]
        scope = ReadScope(folder_ids=set())
        assert scoped_prefetches(entry, scope, entry.computed) == []

    def test_roots_carry_their_nested_paths(self):
        entry = READABLE_MODELS["requirement_assessment"]
        scope = ReadScope(folder_ids=set())
        computed = {
            **entry.computed,
            "applied_controls": entry.optional_computed["applied_controls"],
        }
        built = scoped_prefetches(entry, scope, computed)
        assert [p.prefetch_to for p in built] == ["applied_controls"]
        assert isinstance(built[0], Prefetch)
        nested = built[0].queryset._prefetch_related_lookups
        assert len(nested) == 1 and nested[0].prefetch_to == "evidences"
        assert (
            nested[0].queryset._prefetch_related_lookups[0].prefetch_to == "revisions"
        )

    def test_related_rows_follow_the_related_folders(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        sibling = make_domain("Sibling", parent)
        _audit, (assessment,) = make_audit(mine)
        self.link(assessment, mine, "own")
        self.link(assessment, parent, "inherited")
        self.link(assessment, sibling, "foreign")
        config = {"model": "requirement_assessment", "include": ["applied_controls"]}

        def backing(scope):
            _e, _f, queryset = build_queryset(config, scope)
            row = queryset.get()
            return sorted(control.name for control in row.applied_controls.all())

        # Subtree only: the parent-domain control is out.
        assert backing(scope_of(mine)) == ["own"]
        # The workflow shape: related objects may live in ancestor domains.
        assert backing(
            scope_of(mine, related_folder_ids=accessible_folder_ids(mine))
        ) == [
            "inherited",
            "own",
        ]

    def test_related_rows_follow_the_identity(self):
        domain = make_domain("Domain")
        _audit, (assessment,) = make_audit(domain)
        self.link(assessment, domain, "seen")
        self.link(assessment, domain, "hidden")

        def viewable(model):
            rows = model.objects.all()
            if model is AppliedControl:
                rows = rows.exclude(name="hidden")
            return rows.values_list("id", flat=True)

        scope = scope_of(domain, viewable=viewable)
        _e, _f, queryset = build_queryset(
            {"model": "requirement_assessment", "include": ["applied_controls"]}, scope
        )
        row = queryset.get()
        assert [control.name for control in row.applied_controls.all()] == ["seen"]


@pytest.mark.django_db
class TestComputedAndSerialization:
    def test_effective_computed_merges_opt_ins(self):
        entry = READABLE_MODELS["requirement_assessment"]
        always = effective_computed(entry, {"model": "requirement_assessment"})
        assert set(always) == set(entry.computed)
        asked = effective_computed(
            entry, {"model": "requirement_assessment", "include": "quality_check"}
        )
        assert set(asked) == set(entry.computed) | {"quality_check"}
        both = effective_computed(
            entry,
            {
                "model": "requirement_assessment",
                "include": ["applied_controls", "evidences"],
            },
        )
        assert {"applied_controls", "evidences"} <= set(both)

    def test_effective_computed_names_the_first_unknown(self):
        entry = READABLE_MODELS["requirement_assessment"]
        with pytest.raises(ReadError, match="'bogus' is not includable"):
            effective_computed(
                entry,
                {"model": "requirement_assessment", "include": ["bogus", "worse"]},
            )

    def test_serialize_row_shapes_values_for_json(self):
        domain = make_domain("Domain")
        control = AppliedControl.objects.create(
            name="AC", folder=domain, eta=date(2026, 8, 1), priority=1
        )
        row = serialize_row(control, ["id", "name", "eta", "folder", "expiry_date"])
        assert row == {
            "id": str(control.id),
            "name": "AC",
            "eta": "2026-08-01",
            "folder": {"id": str(domain.id), "str": str(domain)},
            "expiry_date": None,
        }

    def test_computed_values_shadow_columns_and_are_json_coerced(self):
        domain = make_domain("Domain")
        control = AppliedControl.objects.create(name="AC", folder=domain, priority=1)
        entry = READABLE_MODELS["applied_control"]
        row = serialize_row(control, entry.readable_fields(), entry.computed)
        assert row["priority"] == control.get_priority_display()
        extra = serialize_row(control, ["name"], {"when": lambda o: date(2026, 1, 2)})
        assert extra == {"name": "AC", "when": "2026-01-02"}

    def test_a_missing_attribute_reads_as_null(self):
        domain = make_domain("Domain")
        control = AppliedControl.objects.create(name="AC", folder=domain)
        assert serialize_row(control, ["no_such_thing"]) == {"no_such_thing": None}


class TestPageLimit:
    def test_default_and_clamping(self, settings):
        settings.WORKFLOW_READ_MAX_LIMIT = 100
        assert read_max_limit() == 100
        assert page_limit({}) == READ_DEFAULT_LIMIT
        assert page_limit({"limit": None}) == READ_DEFAULT_LIMIT
        assert page_limit({"limit": 0}) == READ_DEFAULT_LIMIT  # falsy: the default
        assert page_limit({"limit": -4}) == 1
        assert page_limit({"limit": "7"}) == 7
        assert page_limit({"limit": 1000}) == 100

    def test_the_cap_is_read_at_call_time(self, settings):
        settings.WORKFLOW_READ_MAX_LIMIT = 3
        assert page_limit({"limit": 50}) == 3
        settings.WORKFLOW_READ_MAX_LIMIT = 4
        assert page_limit({"limit": 50}) == 4


class TestValidateReadConfig:
    def codes(self, config, **kwargs):
        return [code for code, _message in validate_read_config(config, **kwargs)]

    def test_a_clean_config_passes(self):
        assert (
            validate_read_config(
                {
                    "model": "applied_control",
                    "mode": "first",
                    "order_by": "-eta",
                    "limit": 10,
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {"field": "status", "op": "in", "value": ["active"]}
                        ],
                    },
                }
            )
            == []
        )

    def test_an_unknown_model_is_the_only_error_reported(self):
        assert self.codes({"model": "user", "mode": "nope", "limit": 0}) == [
            "action_read_unknown_model"
        ]
        assert self.codes({}) == ["action_read_unknown_model"]

    def test_filter_errors(self):
        base = {"model": "applied_control"}
        assert self.codes({**base, "filters": []}) == ["action_read_invalid_filters"]
        assert self.codes(
            {**base, "filters": {"conditions": [{"field": "folder", "op": "eq"}]}}
        ) == ["action_read_invalid_filters"]
        assert self.codes(
            {**base, "filters": {"conditions": [{"field": "eta", "op": "contains"}]}}
        ) == ["action_read_invalid_filters"]
        assert self.codes(
            {**base, "filters": {"conditions": [{"field": "status", "changed": True}]}}
        ) == ["action_read_invalid_filters"]
        # One code per offending condition, so an author sees them all.
        assert self.codes(
            {
                **base,
                "filters": {
                    "conditions": [
                        {"field": "folder"},
                        {"field": "eta", "op": "contains"},
                    ]
                },
            }
        ) == ["action_read_invalid_filters", "action_read_invalid_filters"]

    def test_a_widened_operator_set_reports_unknown_read_operators_per_condition(self):
        config = {
            "model": "applied_control",
            "filters": {"conditions": [{"field": "status", "op": "custom"}]},
        }
        # Shape-level refusal by default...
        errors = validate_read_config(config)
        assert [c for c, _m in errors] == ["action_read_invalid_filters"]
        assert "Invalid filters" in errors[0][1]
        # ...and a per-condition message once the shape accepts it.
        errors = validate_read_config(config, ops={"custom"})
        assert errors == [("action_read_invalid_filters", "Unknown operator 'custom'")]

    def test_mode_order_and_limit(self):
        base = {"model": "applied_control"}
        assert self.codes({**base, "mode": "all"}) == ["action_read_invalid_mode"]
        assert self.codes({**base, "mode": "first"}) == []
        assert self.codes({**base, "mode": "first"}, modes=("list",)) == [
            "action_read_invalid_mode"
        ]
        assert self.codes({**base, "order_by": "folder"}) == [
            "action_read_invalid_order"
        ]
        assert self.codes({**base, "order_by": 3}) == ["action_read_invalid_order"]
        for limit in (0, -1, "x", read_max_limit() + 1, 1.5e9):
            assert self.codes({**base, "limit": limit}) == [
                "action_read_invalid_limit"
            ], limit
        assert self.codes({**base, "limit": "5"}) == []
        assert self.codes({**base, "limit": read_max_limit()}) == []

    def test_errors_are_reported_together_in_a_stable_order(self):
        assert self.codes(
            {
                "model": "applied_control",
                "mode": "all",
                "order_by": "nope",
                "limit": 0,
                "filters": {"conditions": [{"field": "nope"}]},
            }
        ) == [
            "action_read_invalid_filters",
            "action_read_invalid_mode",
            "action_read_invalid_order",
            "action_read_invalid_limit",
        ]

    @pytest.mark.django_db
    def test_nothing_here_touches_the_database(self, django_assert_num_queries):
        with django_assert_num_queries(0):
            validate_read_config(
                {
                    "model": "compliance_assessment",
                    "filters": {"conditions": [{"field": "status", "value": "done"}]},
                }
            )
