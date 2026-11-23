"""The filter tree on its own: shape validation and compilation to Q, with
no database behind it. Every operator, every column type gate, every
guard, so a consumer other than the workflow engine can rely on the same
answers."""

from datetime import date

import pytest
from django.db.models import Q

from core.models import AppliedControl, RiskScenario
from core.reads import (
    MAX_FILTER_DEPTH,
    OP_LOOKUPS,
    READABLE_MODELS,
    ReadError,
    allowed_ops,
    condition_to_q,
    filters_to_q,
    get_model_field,
    group_to_q,
    validate_filter_tree,
    walk_conditions,
)
from tprm.models import Entity

CONTROL = READABLE_MODELS["applied_control"]
CONTROL_FIELDS = set(CONTROL.readable_fields())
SCENARIO = READABLE_MODELS["risk_scenario"]
SCENARIO_FIELDS = set(SCENARIO.readable_fields())


def cond(field, op="eq", value=None, **extra):
    return {"field": field, "op": op, "value": value, **extra}


class TestValidateFilterTree:
    def test_empty_trees_are_fine(self):
        validate_filter_tree(None)
        validate_filter_tree({})

    def test_a_well_formed_tree_passes(self):
        validate_filter_tree(
            {
                "operator": "and",
                "conditions": [cond("status", "eq", "active")],
                "children": [
                    {"operator": "or", "conditions": [cond("name", "contains", "x")]},
                    {"operator": "not", "conditions": [cond("eta", "is_null")]},
                ],
            }
        )

    def test_every_read_operator_is_accepted_by_default(self):
        for op in OP_LOOKUPS:
            validate_filter_tree({"conditions": [cond("f", op, "v")]})

    def test_depth_is_capped(self):
        tree = {"conditions": [cond("f")]}
        for _ in range(MAX_FILTER_DEPTH):
            tree = {"children": [tree]}
        validate_filter_tree(tree)
        with pytest.raises(ValueError, match="too deep"):
            validate_filter_tree({"children": [tree]})

    @pytest.mark.parametrize(
        "tree, message",
        [
            ([], "group must be a mapping"),
            ({"operator": "xor"}, "invalid operator"),
            ({"conditions": "nope"}, "conditions and children must be lists"),
            ({"children": {}}, "conditions and children must be lists"),
            ({"conditions": ["nope"]}, "invalid condition"),
            ({"conditions": [{"op": "eq"}]}, "invalid condition"),
            ({"conditions": [cond("")]}, "invalid condition"),
            ({"conditions": [cond("f", "like")]}, "invalid condition"),
            ({"conditions": [cond("f", changed="yes")]}, "invalid condition"),
            ({"children": [["nested"]]}, "group must be a mapping"),
        ],
    )
    def test_bad_shapes_are_named(self, tree, message):
        with pytest.raises(ValueError, match=message):
            validate_filter_tree(tree)

    def test_the_operator_set_can_be_widened_by_the_caller(self):
        tree = {"conditions": [cond("f", "custom")]}
        with pytest.raises(ValueError, match="invalid condition"):
            validate_filter_tree(tree)
        validate_filter_tree(tree, ops={"custom"})
        # Widening is also narrowing: the default set is no longer implied.
        with pytest.raises(ValueError, match="invalid condition"):
            validate_filter_tree({"conditions": [cond("f", "eq")]}, ops={"custom"})

    def test_a_changed_flag_is_shape_valid_when_boolean(self):
        validate_filter_tree({"conditions": [cond("f", changed=True)]})


class TestWalkConditions:
    def test_flattens_depth_first(self):
        tree = {
            "conditions": [cond("a")],
            "children": [
                {"conditions": [cond("b")], "children": [{"conditions": [cond("c")]}]},
                {"conditions": [cond("d")]},
            ],
        }
        assert [c["field"] for c in walk_conditions(tree)] == ["a", "b", "c", "d"]

    def test_an_empty_group_yields_nothing(self):
        assert list(walk_conditions({})) == []


class TestColumns:
    def test_concrete_columns_resolve_and_the_rest_do_not(self):
        assert get_model_field(AppliedControl, "status").name == "status"
        assert get_model_field(AppliedControl, "folder").name == "folder"
        assert get_model_field(AppliedControl, "evidences") is None  # to-many
        assert get_model_field(AppliedControl, "no_such_column") is None
        assert get_model_field(AppliedControl, "folder__name") is None

    def test_operators_follow_the_column_type(self):
        assert allowed_ops(get_model_field(Entity, "is_active")) == {
            "eq",
            "neq",
            "is_null",
        }
        assert allowed_ops(get_model_field(AppliedControl, "folder")) == {
            "eq",
            "neq",
            "in",
            "not_in",
            "is_null",
        }
        assert allowed_ops(get_model_field(AppliedControl, "id")) == {
            "eq",
            "neq",
            "in",
            "not_in",
            "is_null",
        }
        assert allowed_ops(get_model_field(AppliedControl, "eta")) == set(
            OP_LOOKUPS
        ) - {"contains"}
        assert allowed_ops(get_model_field(RiskScenario, "current_level")) == set(
            OP_LOOKUPS
        ) - {"contains"}
        assert allowed_ops(get_model_field(AppliedControl, "name")) == set(OP_LOOKUPS)

    def test_an_unknown_column_allows_nothing(self):
        assert allowed_ops(None) == set()


class TestConditionToQ:
    def test_each_operator_compiles_to_its_lookup(self):
        assert condition_to_q(
            cond("status", "eq", "active"), CONTROL, CONTROL_FIELDS
        ) == Q(status__exact="active")
        assert condition_to_q(
            cond("status", "neq", "active"), CONTROL, CONTROL_FIELDS
        ) == ~Q(status__exact="active")
        for op in ("gt", "lt", "gte", "lte"):
            assert condition_to_q(
                cond("eta", op, date(2026, 1, 1)), CONTROL, CONTROL_FIELDS
            ) == Q(**{f"eta__{op}": date(2026, 1, 1)})
        assert condition_to_q(
            cond("name", "contains", "fire"), CONTROL, CONTROL_FIELDS
        ) == Q(name__icontains="fire")

    def test_in_accepts_a_list_a_json_array_or_a_comma_string(self):
        expected = Q(status__in=["active", "to_do"])
        for value in (["active", "to_do"], '["active", "to_do"]', "active, to_do"):
            assert (
                condition_to_q(cond("status", "in", value), CONTROL, CONTROL_FIELDS)
                == expected
            )
        assert (
            condition_to_q(
                cond("status", "not_in", "active,to_do"), CONTROL, CONTROL_FIELDS
            )
            == ~expected
        )
        # An empty string is an empty list, not a one-item list.
        assert condition_to_q(cond("status", "in", ""), CONTROL, CONTROL_FIELDS) == Q(
            status__in=[]
        )

    def test_in_refuses_a_scalar(self):
        with pytest.raises(ReadError, match="'in' needs a list value"):
            condition_to_q(cond("status", "in", 5), CONTROL, CONTROL_FIELDS)
        # A JSON scalar in a string is a one-item comma list, not an error.
        assert condition_to_q(cond("status", "in", "5"), CONTROL, CONTROL_FIELDS) == Q(
            status__in=["5"]
        )

    def test_is_null_defaults_to_true_and_reads_truthy_strings(self):
        assert condition_to_q(cond("eta", "is_null"), CONTROL, CONTROL_FIELDS) == Q(
            eta__isnull=True
        )
        assert condition_to_q(cond("eta", "is_null", ""), CONTROL, CONTROL_FIELDS) == Q(
            eta__isnull=True
        )
        for value in (False, "false", "no", "0", "anything"):
            assert condition_to_q(
                cond("eta", "is_null", value), CONTROL, CONTROL_FIELDS
            ) == Q(eta__isnull=False)
        for value in (True, "true", "YES", "1"):
            assert condition_to_q(
                cond("eta", "is_null", value), CONTROL, CONTROL_FIELDS
            ) == Q(eta__isnull=True)

    def test_the_default_operator_is_eq(self):
        assert condition_to_q(
            {"field": "status", "value": "active"}, CONTROL, CONTROL_FIELDS
        ) == Q(status__exact="active")

    def test_values_go_through_resolve(self):
        resolved = condition_to_q(
            cond("status", "eq", "{{wanted}}"),
            CONTROL,
            CONTROL_FIELDS,
            resolve=lambda value: value.replace("{{wanted}}", "active"),
        )
        assert resolved == Q(status__exact="active")

    def test_unknown_fields_and_operators_are_refused(self):
        with pytest.raises(ReadError, match="'folder' is not a filterable field"):
            condition_to_q(cond("folder", "eq", "x"), CONTROL, CONTROL_FIELDS)
        with pytest.raises(ReadError, match="'evidences' is not a filterable field"):
            condition_to_q(cond("evidences", "eq", "x"), CONTROL, CONTROL_FIELDS)
        with pytest.raises(ReadError, match="unknown operator 'like'"):
            condition_to_q(cond("name", "like", "x"), CONTROL, CONTROL_FIELDS)

    def test_an_operator_the_column_cannot_carry_is_refused(self):
        with pytest.raises(ReadError, match="'contains' is not valid for field 'eta'"):
            condition_to_q(cond("eta", "contains", "2026"), CONTROL, CONTROL_FIELDS)
        with pytest.raises(ReadError, match="'gt' is not valid for field 'id'"):
            condition_to_q(cond("id", "gt", "x"), CONTROL, CONTROL_FIELDS)

    def test_the_whitelist_is_the_callers_not_the_models(self):
        # `folder` is a real column, but the entry does not list it.
        with pytest.raises(ReadError, match="not a filterable field"):
            condition_to_q(cond("folder", "eq", "x"), CONTROL, CONTROL_FIELDS)
        # Handed a wider whitelist, the same condition compiles.
        assert condition_to_q(
            cond("folder", "eq", "x"), CONTROL, CONTROL_FIELDS | {"folder"}
        ) == Q(folder__exact="x")


class TestUnratedGuard:
    """Level columns hold -1 until rated; ranges and negations must not match
    those rows, while an explicit eq -1 still does."""

    def test_ranges_carry_the_guard(self):
        for op in ("gt", "lt", "gte", "lte"):
            assert condition_to_q(
                cond("current_level", op, 1), SCENARIO, SCENARIO_FIELDS
            ) == Q(**{f"current_level__{op}": 1}) & Q(current_level__gte=0)

    def test_negations_carry_the_guard_after_the_negation(self):
        assert condition_to_q(
            cond("current_level", "neq", 1), SCENARIO, SCENARIO_FIELDS
        ) == ~Q(current_level__exact=1) & Q(current_level__gte=0)
        assert condition_to_q(
            cond("current_level", "not_in", [1, 2]), SCENARIO, SCENARIO_FIELDS
        ) == ~Q(current_level__in=[1, 2]) & Q(current_level__gte=0)

    def test_eq_and_in_do_not(self):
        assert condition_to_q(
            cond("current_level", "eq", -1), SCENARIO, SCENARIO_FIELDS
        ) == Q(current_level__exact=-1)
        assert condition_to_q(
            cond("current_level", "in", [-1, 0]), SCENARIO, SCENARIO_FIELDS
        ) == Q(current_level__in=[-1, 0])

    def test_only_the_sentinel_columns_are_guarded(self):
        assert condition_to_q(
            cond("name", "neq", "x"), SCENARIO, SCENARIO_FIELDS
        ) == ~Q(name__exact="x")

    def test_a_not_group_reasserts_the_guard_for_every_sentinel_it_touches(self):
        tree = {
            "operator": "not",
            "conditions": [cond("current_level", "lte", 2)],
            "children": [{"conditions": [cond("residual_level", "eq", 1)]}],
        }
        inner = (Q(current_level__lte=2) & Q(current_level__gte=0)) & Q(
            residual_level__exact=1
        )
        result = group_to_q(tree, SCENARIO, SCENARIO_FIELDS)
        assert result.connector == "AND" and not result.negated
        assert result.children[0] == ~inner
        assert set(result.children[1:]) == {
            ("current_level__gte", 0),
            ("residual_level__gte", 0),
        }


class TestGroupToQ:
    def test_and_is_the_default_and_chains_conditions_and_children(self):
        tree = {
            "conditions": [
                cond("status", "eq", "active"),
                cond("name", "contains", "a"),
            ],
            "children": [{"conditions": [cond("eta", "is_null")]}],
        }
        assert group_to_q(tree, CONTROL, CONTROL_FIELDS) == (
            Q(status__exact="active") & Q(name__icontains="a") & Q(eta__isnull=True)
        )

    def test_or(self):
        tree = {
            "operator": "or",
            "conditions": [cond("status", "eq", "a"), cond("status", "eq", "b")],
        }
        assert group_to_q(tree, CONTROL, CONTROL_FIELDS) == (
            Q(status__exact="a") | Q(status__exact="b")
        )

    def test_not_negates_the_conjunction(self):
        tree = {
            "operator": "not",
            "conditions": [cond("status", "eq", "a"), cond("name", "eq", "b")],
        }
        assert group_to_q(tree, CONTROL, CONTROL_FIELDS) == ~(
            Q(status__exact="a") & Q(name__exact="b")
        )

    def test_nesting_mixes_operators(self):
        tree = {
            "operator": "and",
            "conditions": [cond("status", "eq", "active")],
            "children": [
                {
                    "operator": "or",
                    "conditions": [
                        cond("name", "contains", "a"),
                        cond("name", "contains", "b"),
                    ],
                }
            ],
        }
        assert group_to_q(tree, CONTROL, CONTROL_FIELDS) == Q(
            status__exact="active"
        ) & (Q(name__icontains="a") | Q(name__icontains="b"))

    def test_empty_groups_match_everything(self):
        assert group_to_q({}, CONTROL, CONTROL_FIELDS) == Q()
        assert group_to_q({"operator": "not"}, CONTROL, CONTROL_FIELDS) == Q()
        assert group_to_q({"children": [{}]}, CONTROL, CONTROL_FIELDS) == Q()

    def test_a_bad_condition_anywhere_in_the_tree_is_refused(self):
        tree = {"children": [{"children": [{"conditions": [cond("nope")]}]}]}
        with pytest.raises(ReadError, match="'nope' is not a filterable field"):
            group_to_q(tree, CONTROL, CONTROL_FIELDS)


class TestFiltersToQ:
    def test_none_and_empty_match_everything(self):
        assert filters_to_q(None, CONTROL, CONTROL_FIELDS) == Q()
        assert filters_to_q({}, CONTROL, CONTROL_FIELDS) == Q()

    def test_a_tree_compiles(self):
        assert filters_to_q(
            {"conditions": [cond("status", "eq", "active")]}, CONTROL, CONTROL_FIELDS
        ) == Q(status__exact="active")

    def test_resolve_reaches_every_condition(self):
        seen = []

        def resolve(value):
            seen.append(value)
            return value

        filters_to_q(
            {
                "conditions": [cond("status", "eq", "a")],
                "children": [{"conditions": [cond("name", "eq", "b")]}],
            },
            CONTROL,
            CONTROL_FIELDS,
            resolve,
        )
        assert seen == ["a", "b"]
