"""Aggregate mode at the core boundary: the function registry, spec
normalization, the database and worker engines, group-by breakdowns, the
row ceiling, annotations as aggregatable fields, and the validator."""

import uuid
from datetime import date

import pytest

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from core.reads import (
    AGGREGATES,
    ENGINE_DB,
    ENGINE_PYTHON,
    MAX_AGGREGATES,
    READABLE_MODELS,
    ReadError,
    ReadScope,
    aggregate_max_rows,
    build_queryset,
    function_catalog,
    normalize_aggregate,
    normalize_aggregates,
    run_aggregate_read,
    subtree_folder_ids,
    validate_read_config,
)
from iam.models import Folder

CONTROL = READABLE_MODELS["applied_control"]
AUDIT = READABLE_MODELS["compliance_assessment"]


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def scope_of(folder):
    return ReadScope(folder_ids=subtree_folder_ids(folder))


def aggregate(model, aggregates, scope, **extra):
    return run_aggregate_read(
        {"model": model, "mode": "aggregate", "aggregates": aggregates, **extra}, scope
    )


def make_controls(domain, rows):
    """rows: (name, status, priority) triples."""
    return [
        AppliedControl.objects.create(
            name=name, folder=domain, status=status, priority=priority
        )
        for name, status, priority in rows
    ]


def make_audit(domain, statuses=()):
    """Audit progress is status-driven by default: a requirement counts as
    assessed when its status is done."""
    suffix = uuid.uuid4().hex[:8]
    framework = Framework.objects.create(
        name="FW", urn=f"urn:test:fw-{suffix}", folder=Folder.get_root_folder()
    )
    perimeter = Perimeter.objects.create(name=f"P {suffix}", folder=domain)
    audit = ComplianceAssessment.objects.create(
        name=f"Audit {suffix}", framework=framework, perimeter=perimeter, folder=domain
    )
    for index, status in enumerate(statuses):
        requirement = RequirementNode.objects.create(
            name=f"Req {index}",
            urn=f"urn:test:fw-{suffix}:req{index}",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=requirement,
            folder=domain,
            status=status,
            result="compliant" if status == "done" else "not_assessed",
        )
    return audit


class TestRegistry:
    def test_every_function_has_one_engine_and_the_matching_callable(self):
        for fn in AGGREGATES.values():
            assert fn.engine in (ENGINE_DB, ENGINE_PYTHON)
            assert (fn.build is not None) == (fn.engine == ENGINE_DB), fn.name
            assert fn.fold is not None, fn.name  # any function can run in the worker
            assert fn.needs_field or fn.name == "count"

    def test_the_catalog_is_what_the_editor_needs(self):
        catalog = {entry["name"]: entry for entry in function_catalog()}
        assert set(catalog) == set(AGGREGATES)
        assert catalog["count"]["needs_field"] is False
        assert catalog["avg"]["accepts"] == ["numeric"]
        assert catalog["min"]["accepts"] == ["date", "numeric"]
        assert catalog["count_distinct"]["accepts"] == sorted(
            ["bool", "relation", "numeric", "date", "text"]
        )
        assert catalog["percentile"]["params"] == ["p"]
        assert catalog["median"]["engine"] == "python"


class TestNormalize:
    def norm(self, spec, entry=CONTROL, config=None, taken=()):
        return normalize_aggregate(spec, entry, config or {"model": "x"}, taken)

    def test_count_needs_nothing_and_defaults_its_alias(self):
        spec = self.norm({"fn": "count"})
        assert (spec.alias, spec.engine, spec.field, spec.group_by) == (
            "count",
            "db",
            None,
            None,
        )

    def test_default_aliases(self):
        assert self.norm({"fn": "avg", "field": "priority"}).alias == "avg_priority"
        assert self.norm({"fn": "count", "group_by": "status"}).alias == "by_status"
        assert (
            self.norm({"fn": "max", "field": "eta", "group_by": "status"}).alias
            == "max_eta_by_status"
        )
        assert (
            self.norm({"fn": "avg", "field": "progress"}, AUDIT).alias == "avg_progress"
        )

    def test_an_explicit_alias_wins_and_must_be_an_identifier(self):
        assert self.norm({"fn": "count", "as": "total"}).alias == "total"
        for bad in ("1st", "a-b", "a b", "é"):
            with pytest.raises(ReadError, match="not a valid alias"):
                self.norm({"fn": "count", "as": bad})

    def test_aliases_cannot_repeat_or_shadow_a_field(self):
        with pytest.raises(ReadError, match="used twice"):
            self.norm({"fn": "count"}, taken=["count"])
        with pytest.raises(ReadError, match="name of a field"):
            self.norm({"fn": "count", "as": "status"})
        with pytest.raises(ReadError, match="name of a field"):
            self.norm({"fn": "count", "as": "folder"})

    def test_functions_need_a_field_of_the_right_kind(self):
        with pytest.raises(ReadError, match="'avg' needs a field"):
            self.norm({"fn": "avg"})
        with pytest.raises(ReadError, match="'count' takes no field"):
            self.norm({"fn": "count", "field": "priority"})
        with pytest.raises(ReadError, match="cannot run on 'status' \\(text field\\)"):
            self.norm({"fn": "avg", "field": "status"})
        with pytest.raises(ReadError, match="cannot run on 'eta' \\(date field\\)"):
            self.norm({"fn": "sum", "field": "eta"})
        assert self.norm({"fn": "max", "field": "eta"}).engine == "db"
        assert self.norm({"fn": "count_distinct", "field": "status"}).engine == "db"
        with pytest.raises(ReadError, match="is not a field 'avg' can run on"):
            self.norm({"fn": "avg", "field": "folder"})
        with pytest.raises(ReadError, match="unknown aggregate function 'mode'"):
            self.norm({"fn": "mode", "field": "priority"})
        with pytest.raises(ReadError, match="must be a mapping"):
            self.norm("count")

    def test_an_annotation_is_a_field_like_any_other(self):
        spec = self.norm({"fn": "avg", "field": "evidences_count"})
        assert spec.engine == "db" and spec.computed is None

    def test_a_computed_value_forces_the_worker(self):
        spec = self.norm({"fn": "avg", "field": "progress"}, AUDIT)
        assert spec.engine == "python" and spec.computed == ("progress", [])
        spec = self.norm({"fn": "max", "field": "scores.global"}, AUDIT)
        assert spec.computed == ("scores", ["global"])
        with pytest.raises(ReadError, match="runs on a column"):
            self.norm({"fn": "count_distinct", "field": "progress"}, AUDIT)

    def test_an_opt_in_computed_value_needs_the_include(self):
        with pytest.raises(ReadError, match="is not a field"):
            self.norm({"fn": "avg", "field": "quality_check.count"}, AUDIT)
        spec = self.norm(
            {"fn": "avg", "field": "quality_check.count"},
            AUDIT,
            {"model": "compliance_assessment", "include": ["quality_check"]},
        )
        assert spec.computed == ("quality_check", ["count"])

    def test_group_by_is_a_column_never_an_annotation(self):
        assert self.norm({"fn": "count", "group_by": "status"}).group_by == "status"
        with pytest.raises(ReadError, match="not a field to group by"):
            self.norm({"fn": "count", "group_by": "folder"})
        with pytest.raises(ReadError, match="is an annotation"):
            self.norm({"fn": "count", "group_by": "evidences_count"})

    def test_percentile_needs_a_p_in_range(self):
        with pytest.raises(ReadError, match="needs 'p'"):
            self.norm({"fn": "percentile", "field": "priority"})
        for bad in (-1, 101, "x", None):
            with pytest.raises(ReadError, match="between 0 and 100"):
                self.norm({"fn": "percentile", "field": "priority", "p": bad})
        assert self.norm(
            {"fn": "percentile", "field": "priority", "p": "95"}
        ).params == {"p": 95.0}

    def test_unknown_keys_are_refused(self):
        with pytest.raises(ReadError, match="unknown aggregate key 'limit'"):
            self.norm({"fn": "count", "limit": 5})

    def test_the_list_as_a_whole(self):
        with pytest.raises(ReadError, match="at least one"):
            normalize_aggregates([], CONTROL, {})
        with pytest.raises(ReadError, match="at least one"):
            normalize_aggregates(None, CONTROL, {})
        with pytest.raises(ReadError, match=f"at most {MAX_AGGREGATES}"):
            normalize_aggregates(
                [{"fn": "count", "as": f"c{i}"} for i in range(MAX_AGGREGATES + 1)],
                CONTROL,
                {},
            )
        specs = normalize_aggregates(
            [{"fn": "count"}, {"fn": "avg", "field": "priority"}], CONTROL, {}
        )
        assert [s.alias for s in specs] == ["count", "avg_priority"]
        with pytest.raises(ReadError, match="used twice"):
            normalize_aggregates([{"fn": "count"}, {"fn": "count"}], CONTROL, {})


@pytest.mark.django_db
class TestDatabaseEngine:
    def test_scalars_in_one_query(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        domain = make_domain("Domain")
        make_controls(
            domain, [("a", "active", 1), ("b", "active", 3), ("c", "to_do", 2)]
        )
        specs = [
            {"fn": "count"},
            {"fn": "avg", "field": "priority"},
            {"fn": "sum", "field": "priority"},
            {"fn": "min", "field": "priority"},
            {"fn": "max", "field": "priority", "as": "top"},
            {"fn": "count_distinct", "field": "status"},
        ]
        scope = scope_of(domain)  # resolving the subtree is the caller's query
        with CaptureQueriesContext(connection) as ctx:
            result = aggregate("applied_control", specs, scope)
        assert len(ctx) == 1, [q["sql"] for q in ctx]
        assert result == {
            "count": 3,
            "avg_priority": 2.0,
            "sum_priority": 6,
            "min_priority": 1,
            "top": 3,
            "count_distinct_status": 2,
        }

    def test_results_keep_spec_order(self):
        domain = make_domain("Domain")
        make_controls(domain, [("a", "active", 1)])
        result = aggregate(
            "applied_control",
            [{"fn": "max", "field": "priority"}, {"fn": "count"}],
            scope_of(domain),
        )
        assert list(result) == ["max_priority", "count"]

    def test_empty_matches(self):
        domain = make_domain("Domain")
        result = aggregate(
            "applied_control",
            [
                {"fn": "count"},
                {"fn": "avg", "field": "priority"},
                {"fn": "count", "group_by": "status"},
                {"fn": "avg", "field": "priority", "group_by": "status"},
            ],
            scope_of(domain),
        )
        assert result["count"] == 0
        assert result["avg_priority"] is None
        # A count over a choice field keeps every choice, zeroes included.
        assert set(result["by_status"]) == {
            value for value, _label in AppliedControl.Status.choices
        }
        assert set(result["by_status"].values()) == {0}
        assert result["avg_priority_by_status"] == {}

    def test_filters_and_scope_apply(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        make_controls(mine, [("a", "active", 1), ("b", "to_do", 2)])
        make_controls(parent, [("outside", "active", 9)])
        result = aggregate(
            "applied_control",
            [{"fn": "count"}, {"fn": "max", "field": "priority"}],
            scope_of(mine),
            filters={
                "conditions": [{"field": "status", "op": "eq", "value": "active"}]
            },
        )
        assert result == {"count": 1, "max_priority": 1}

    def test_group_by_breakdowns(self):
        domain = make_domain("Domain")
        make_controls(
            domain,
            [
                ("a", "active", 1),
                ("b", "active", 3),
                ("c", "to_do", 2),
                ("d", "to_do", None),
            ],
        )
        result = aggregate(
            "applied_control",
            [
                {"fn": "count", "group_by": "status"},
                {"fn": "avg", "field": "priority", "group_by": "status"},
                {"fn": "count", "group_by": "priority", "as": "per_priority"},
            ],
            scope_of(domain),
        )
        assert result["by_status"]["active"] == 2
        assert result["by_status"]["to_do"] == 2
        assert result["by_status"]["deprecated"] == 0
        # Averages ignore empty values; groups without a value do not appear.
        assert result["avg_priority_by_status"] == {"active": 2.0, "to_do": 2.0}
        # Empty values group under "null"; numbers key as their text, and a
        # choice column lists every choice.
        assert result["per_priority"] == {"1": 1, "2": 1, "3": 1, "4": 0, "null": 1}

    def test_dates_and_relations(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="a", folder=domain, eta=date(2026, 1, 1))
        AppliedControl.objects.create(name="b", folder=domain, eta=date(2026, 3, 1))
        AppliedControl.objects.create(name="c", folder=domain)
        result = aggregate(
            "applied_control",
            [
                {"fn": "min", "field": "eta"},
                {"fn": "max", "field": "eta"},
                {"fn": "count_distinct", "field": "name"},
                {"fn": "count", "group_by": "eta"},
            ],
            scope_of(domain),
        )
        assert result["min_eta"] == "2026-01-01"
        assert result["max_eta"] == "2026-03-01"
        assert result["count_distinct_name"] == 3
        assert result["by_eta"] == {"2026-01-01": 1, "2026-03-01": 1, "null": 1}

    def test_annotations_aggregate_filter_and_do_not_disturb_grouping(self):
        domain = make_domain("Domain")
        backed, _bare, other = make_controls(
            domain,
            [("backed", "active", 1), ("bare", "active", 1), ("other", "to_do", 1)],
        )
        for name in ("e1", "e2"):
            evidence = Evidence.objects.create(name=name, folder=domain)
            backed.evidences.add(evidence)
        other.evidences.add(Evidence.objects.create(name="e3", folder=domain))
        result = aggregate(
            "applied_control",
            [
                {"fn": "sum", "field": "evidences_count"},
                {"fn": "avg", "field": "evidences_count"},
                {"fn": "count", "group_by": "status"},
            ],
            scope_of(domain),
        )
        assert result["sum_evidences_count"] == 3
        assert result["avg_evidences_count"] == 1.0
        assert result["by_status"]["active"] == 2 and result["by_status"]["to_do"] == 1
        # "Controls with no evidence", with the grouping still by status only.
        result = aggregate(
            "applied_control",
            [{"fn": "count"}, {"fn": "count", "group_by": "status"}],
            scope_of(domain),
            filters={
                "conditions": [{"field": "evidences_count", "op": "eq", "value": 0}]
            },
        )
        assert result["count"] == 1
        assert result["by_status"]["active"] == 1 and result["by_status"]["to_do"] == 0

    def test_list_mode_rows_carry_the_annotation(self):
        domain = make_domain("Domain")
        (control,) = make_controls(domain, [("a", "active", 1)])
        control.evidences.add(Evidence.objects.create(name="e", folder=domain))
        _entry, fields, queryset = build_queryset(
            {"model": "applied_control"}, scope_of(domain)
        )
        assert "evidences_count" in fields
        assert queryset.get().evidences_count == 1
        _entry, fields, queryset = build_queryset(
            {"model": "applied_control", "order_by": "-evidences_count"},
            scope_of(domain),
        )
        assert queryset.query.order_by == ("-evidences_count", "id")


@pytest.mark.django_db
class TestWorkerEngine:
    def test_median_percentile_and_stddev(self):
        domain = make_domain("Domain")
        make_controls(
            domain, [(str(i), "active", p) for i, p in enumerate([1, 2, 3, 4, 10])]
        )
        result = aggregate(
            "applied_control",
            [
                {"fn": "median", "field": "priority"},
                {"fn": "percentile", "field": "priority", "p": 50},
                {"fn": "percentile", "field": "priority", "p": 90, "as": "p90"},
                {"fn": "stddev", "field": "priority"},
            ],
            scope_of(domain),
        )
        assert result["median_priority"] == 3
        assert result["percentile_priority"] == 3.0
        assert result["p90"] == pytest.approx(7.6)
        assert result["stddev_priority"] == pytest.approx(10**0.5)  # population

    def test_the_worker_pass_costs_the_same_queries_whatever_the_row_count(
        self, django_assert_num_queries
    ):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        specs = [
            {"fn": "median", "field": "priority"},
            {"fn": "stddev", "field": "priority"},
        ]
        small = make_domain("Small")
        make_controls(small, [(str(i), "active", i) for i in range(3)])
        scope = scope_of(small)
        with CaptureQueriesContext(connection) as few:
            aggregate("applied_control", specs, scope)
        large = make_domain("Large")
        make_controls(large, [(str(i), "active", i) for i in range(40)])
        scope = scope_of(large)
        with CaptureQueriesContext(connection) as many:
            aggregate("applied_control", specs, scope)
        # The ceiling count, then one streaming pass.
        assert len(few) == len(many) == 2

    def test_empty_values_are_skipped_and_nothing_is_none(self):
        domain = make_domain("Domain")
        make_controls(domain, [("a", "active", None), ("b", "active", 4)])
        assert aggregate(
            "applied_control", [{"fn": "median", "field": "priority"}], scope_of(domain)
        ) == {"median_priority": 4}
        make_controls(domain, [("c", "to_do", None)])
        assert aggregate(
            "applied_control",
            [{"fn": "median", "field": "priority", "group_by": "status"}],
            scope_of(domain),
        ) == {"median_priority_by_status": {"active": 4}}
        assert aggregate(
            "applied_control",
            [{"fn": "stddev", "field": "priority"}],
            scope_of(make_domain("Empty")),
        ) == {"stddev_priority": None}

    def test_both_engines_in_one_read(self):
        domain = make_domain("Domain")
        make_controls(domain, [("a", "active", 1), ("b", "active", 3)])
        result = aggregate(
            "applied_control",
            [
                {"fn": "count"},
                {"fn": "median", "field": "priority"},
                {"fn": "avg", "field": "priority"},
            ],
            scope_of(domain),
        )
        assert result == {"count": 2, "median_priority": 2, "avg_priority": 2.0}
        assert list(result) == ["count", "median_priority", "avg_priority"]

    def test_computed_values_are_aggregated_through_the_product_code(self):
        domain = make_domain("Domain")
        make_audit(domain, ["done", "done", "to_do", "to_do"])
        make_audit(domain, ["done", "done"])
        result = aggregate(
            "compliance_assessment",
            [
                {"fn": "avg", "field": "progress"},
                {"fn": "max", "field": "requirements.compliant"},
                {"fn": "sum", "field": "requirements.total", "as": "requirements"},
                {"fn": "avg", "field": "progress", "group_by": "status"},
            ],
            scope_of(domain),
        )
        assert result["avg_progress"] == 75.0
        assert result["max_requirements_compliant"] == 2
        assert result["requirements"] == 6
        assert result["avg_progress_by_status"] == {"planned": 75.0}

    def test_a_relation_groups_by_its_id_whichever_way_the_rows_load(self):
        """A computed spec makes the worker load objects; a relation column
        must still key by the stored id, as the values path and the database
        engine do, never by the related object's name."""
        domain = make_domain("Domain")
        first = make_audit(domain, ["done", "to_do"])
        second = make_audit(make_domain("Sub", domain), ["done"])
        # Two perimeters named alike must not collapse into one bucket.
        second.perimeter.name = first.perimeter.name
        second.perimeter.save()
        by_perimeter = {"fn": "median", "field": "progress", "group_by": "perimeter"}
        with_objects = aggregate(
            "compliance_assessment", [by_perimeter], scope_of(domain)
        )
        db_keys = aggregate(
            "compliance_assessment",
            [{"fn": "count", "group_by": "perimeter"}],
            scope_of(domain),
        )
        expected = {str(first.perimeter_id), str(second.perimeter_id)}
        assert set(with_objects["median_progress_by_perimeter"]) == expected
        assert set(db_keys["by_perimeter"]) == expected
        assert with_objects["median_progress_by_perimeter"] == {
            str(first.perimeter_id): 50.0,
            str(second.perimeter_id): 100.0,
        }

    def test_a_non_numeric_computed_value_is_refused(self):
        domain = make_domain("Domain")
        make_audit(domain, ["done"])
        with pytest.raises(ReadError, match="non-numeric value"):
            aggregate(
                "compliance_assessment",
                [{"fn": "avg", "field": "requirements"}],
                scope_of(domain),
            )

    def test_the_ceiling_fails_the_read_instead_of_truncating(self, settings):
        domain = make_domain("Domain")
        make_controls(domain, [(str(i), "active", i) for i in range(5)])
        settings.WORKFLOW_AGGREGATE_MAX_ROWS = 4
        assert aggregate_max_rows() == 4
        with pytest.raises(ReadError, match="5 rows exceed the ceiling of 4"):
            aggregate(
                "applied_control",
                [{"fn": "median", "field": "priority"}],
                scope_of(domain),
            )
        # Database functions have no ceiling.
        assert aggregate("applied_control", [{"fn": "count"}], scope_of(domain)) == {
            "count": 5
        }
        settings.WORKFLOW_AGGREGATE_MAX_ROWS = 5
        assert aggregate(
            "applied_control", [{"fn": "median", "field": "priority"}], scope_of(domain)
        ) == {"median_priority": 2}


class TestValidation:
    def codes(self, config):
        return [code for code, _m in validate_read_config(config)]

    def messages(self, config):
        return [message for _c, message in validate_read_config(config)]

    def test_a_clean_aggregate_config_passes(self):
        assert (
            validate_read_config(
                {
                    "model": "applied_control",
                    "mode": "aggregate",
                    "filters": {"conditions": [{"field": "status", "value": "active"}]},
                    "aggregates": [
                        {"fn": "count"},
                        {"fn": "avg", "field": "priority", "group_by": "status"},
                        {"fn": "percentile", "field": "priority", "p": 90, "as": "p90"},
                    ],
                }
            )
            == []
        )

    def test_row_only_keys_are_errors(self):
        config = {
            "model": "applied_control",
            "mode": "aggregate",
            "aggregates": [{"fn": "count"}],
            "limit": 25,
            "offset": "3",
            "order_by": "-created_at",
            "include": ["x"],
        }
        assert self.codes(config) == ["action_read_invalid_aggregate"] * 4
        assert all(
            "does not apply in aggregate mode" in m for m in self.messages(config)
        )
        # Empty values count as absent, so a form that leaves blanks passes.
        config.update({"limit": None, "offset": "", "order_by": "", "include": []})
        assert self.codes(config) == []

    def test_missing_or_malformed_aggregates(self):
        base = {"model": "applied_control", "mode": "aggregate"}
        assert self.codes(base) == ["action_read_invalid_aggregate"]
        assert self.codes({**base, "aggregates": []}) == [
            "action_read_invalid_aggregate"
        ]
        assert self.codes({**base, "aggregates": "count"}) == [
            "action_read_invalid_aggregate"
        ]
        # One error per bad aggregate, good ones pass in between.
        config = {
            **base,
            "aggregates": [
                {"fn": "avg"},
                {"fn": "count"},
                {"fn": "nope"},
                {"fn": "count"},
            ],
        }
        assert self.codes(config) == ["action_read_invalid_aggregate"] * 3
        assert self.messages(config) == [
            "'avg' needs a field",
            "unknown aggregate function 'nope'",
            "alias 'count' is used twice",
        ]

    def test_aggregates_outside_aggregate_mode_are_an_error(self):
        assert self.codes(
            {
                "model": "applied_control",
                "mode": "list",
                "aggregates": [{"fn": "count"}],
            }
        ) == ["action_read_invalid_aggregate"]
        assert self.codes({"model": "applied_control", "aggregates": []}) == []

    def test_filters_are_still_checked_in_aggregate_mode(self):
        assert self.codes(
            {
                "model": "applied_control",
                "mode": "aggregate",
                "aggregates": [{"fn": "count"}],
                "filters": {"conditions": [{"field": "nope"}]},
            }
        ) == ["action_read_invalid_filters"]

    def test_annotations_filter_with_numeric_operators(self):
        assert (
            self.codes(
                {
                    "model": "applied_control",
                    "filters": {
                        "conditions": [
                            {"field": "evidences_count", "op": "gte", "value": 1}
                        ]
                    },
                }
            )
            == []
        )
        assert self.codes(
            {
                "model": "applied_control",
                "filters": {
                    "conditions": [
                        {"field": "evidences_count", "op": "contains", "value": "1"}
                    ]
                },
            }
        ) == ["action_read_invalid_filters"]

    def test_the_caller_can_withhold_aggregate_mode(self):
        config = {
            "model": "applied_control",
            "mode": "aggregate",
            "aggregates": [{"fn": "count"}],
        }
        assert self.codes(config) == []
        assert [
            c for c, _m in validate_read_config(config, modes=("list", "first"))
        ] == ["action_read_invalid_mode"]
