"""The CEL evaluator on its own: JSON-shaped values in, JSON-shaped values
out, every failure an ExpressionError with a message an author can act on.
No database, no workflow: the workflow engine's compute action and anything
else that evaluates an expression share exactly this behaviour."""

import datetime

import celpy.celtypes as celtypes
import pytest

from core.expressions import (
    FUNCTIONS,
    MAX_MACRO_DEPTH,
    OPERATORS,
    ExpressionError,
    compile_expression,
    evaluate,
    from_cel,
    referenced_paths,
    to_cel,
)


class TestEvaluate:
    """Types in, JSON-shaped values out."""

    def test_int_arithmetic_stays_int(self):
        assert evaluate("(a + b) * 2", {"a": 3, "b": 4}) == 14
        assert isinstance(evaluate("a / 2", {"a": 7}), int)

    def test_mixing_int_and_double_promotes_to_double(self):
        # A `number` variable does not say int or double; the payload decides.
        context = {"count": 3, "weight": 2.5}
        assert evaluate("count * weight", context) == 7.5
        assert evaluate("weight + count > 5", context) is True
        assert evaluate("count == 3.0", context) is True
        # Promoted comparisons still feed CEL's own logic and ternary.
        assert evaluate("count > weight ? 'more' : 'less'", context) == "more"
        assert evaluate("count < weight || count == 3.0", context) is True
        assert evaluate("double(count) * weight", context) == 7.5
        # All-int expressions keep CEL's int semantics, so indexes still work.
        assert evaluate("[9, 8][count - 2]", context) == 8
        with pytest.raises(ExpressionError, match="cannot combine int and string"):
            evaluate("count + 'x'", context)

    def test_every_promoted_operator(self):
        context = {"i": 3, "d": 1.5}
        assert evaluate("i + d", context) == 4.5
        assert evaluate("i - d", context) == 1.5
        assert evaluate("i * d", context) == 4.5
        assert evaluate("i / d", context) == 2.0
        assert evaluate("d < i", context) is True
        assert evaluate("d <= i", context) is True
        assert evaluate("i > d", context) is True
        assert evaluate("i >= d", context) is True
        assert evaluate("i == 3.0", context) is True
        assert evaluate("i != 3.0", context) is False
        assert set(OPERATORS) == {
            "_+_",
            "_-_",
            "_*_",
            "_/_",
            "_%_",
            "_<_",
            "_<=_",
            "_>_",
            "_>=_",
            "_==_",
            "_!=_",
        }

    def test_promotion_never_touches_non_numbers(self):
        assert evaluate("'a' + 'b'", {}) == "ab"
        assert evaluate("[1] + [2]", {}) == [1, 2]
        assert evaluate("'a' < 'b'", {}) is True
        assert evaluate("true == true", {}) is True

    def test_dotted_paths_reach_node_outputs_and_lists(self):
        context = {"nodes": {"fetch": {"count": 7, "results": [{"score": 3}]}}}
        assert evaluate("nodes.fetch.count * 2", context) == 14
        assert evaluate("nodes.fetch.results[0].score", context) == 3

    def test_aggregates_over_lists(self):
        rows = {"rows": [{"score": 3}, {"score": 5}], "empty": []}
        assert evaluate("sum(rows.map(r, r.score))", rows) == 8
        assert evaluate("avg(rows.map(r, r.score))", rows) == 4.0
        assert evaluate("max(rows.map(r, r.score))", rows) == 5
        assert evaluate("min(rows.map(r, r.score))", rows) == 3
        assert evaluate("size(rows)", rows) == 2
        assert evaluate("sum(empty)", rows) == 0
        with pytest.raises(ExpressionError, match="empty list"):
            evaluate("avg(empty)", rows)
        with pytest.raises(ExpressionError, match="empty list"):
            evaluate("max(empty)", rows)
        assert evaluate("sum([1, 2.5])", {}) == 3.5
        assert evaluate("max([1, 2.5])", {}) == 2.5
        assert isinstance(evaluate("sum([1, 2])", {}), int)
        assert isinstance(evaluate("avg([1, 3])", {}), float)
        assert set(FUNCTIONS) == {
            "sum",
            "avg",
            "min",
            "max",
            "round",
            "floor",
            "ceil",
            "abs",
        }

    def test_helpers_refuse_non_lists_and_non_numbers(self):
        with pytest.raises(ExpressionError, match=r"sum\(\) takes a list"):
            evaluate("sum(3)", {})
        with pytest.raises(ExpressionError, match="takes a list of numbers"):
            evaluate("avg(['a'])", {})
        with pytest.raises(ExpressionError, match="numbers, strings or timestamps"):
            evaluate("max([true])", {})
        with pytest.raises(ExpressionError, match=r"round\(\) takes a number"):
            evaluate("round('x')", {})
        with pytest.raises(ExpressionError, match="digits must be an int"):
            evaluate("round(2.5, 1.0)", {})

    def test_min_and_max_over_strings_and_timestamps(self):
        dates = {"dates": ["2026-03-01", "2026-01-15"]}
        assert evaluate("max(dates)", dates) == "2026-03-01"
        assert evaluate("min(dates)", dates) == "2026-01-15"
        assert (
            evaluate("max(dates.map(d, timestamp(d + 'T00:00:00Z')))", dates)
            == "2026-03-01T00:00:00+00:00"
        )
        with pytest.raises(ExpressionError, match="one kind"):
            evaluate("max(['a', 1])", {})
        with pytest.raises(ExpressionError, match="takes a list of numbers"):
            evaluate("sum(['a', 'b'])", {})

    def test_rounding_helpers(self):
        assert evaluate("round(2.567, 2)", {}) == 2.57
        assert evaluate("round(2.5)", {}) == 3  # half up, not banker's
        assert evaluate("floor(2.7)", {}) == 2
        assert evaluate("ceil(2.1)", {}) == 3
        assert evaluate("abs(-3)", {}) == 3
        assert evaluate("abs(-2.5)", {}) == 2.5
        assert isinstance(evaluate("round(2.5)", {}), int)
        assert isinstance(evaluate("round(2.5, 0)", {}), float)
        assert isinstance(evaluate("abs(-3)", {}), int)

    def test_conditionals_and_strings(self):
        context = {"severity": "critical", "n": 3}
        assert evaluate("severity == 'critical' ? 1 : 30", context) == 1
        assert evaluate("string(n) + ' items'", context) == "3 items"
        assert evaluate("n > 2 && severity != 'low'", context) is True
        assert evaluate("severity.startsWith('crit')", context) is True
        assert evaluate("'crit' in ['crit', 'low']", context) is True
        assert evaluate("'x' in {'x': 1}", context) is True

    def test_macros(self):
        context = {"items": [1, 2, 3, 4]}
        assert evaluate("items.filter(x, x % 2 == 0)", context) == [2, 4]
        assert evaluate("items.all(x, x > 0)", context) is True
        assert evaluate("items.exists(x, x == 3)", context) is True
        assert evaluate("items.exists_one(x, x > 3)", context) is True
        assert evaluate("items.map(x, x * 2)", context) == [2, 4, 6, 8]

    def test_null_is_a_value(self):
        assert evaluate("missing == null", {"missing": None}) is True
        assert evaluate("has(m.x) ? m.x : 0", {"m": {}}) == 0
        assert evaluate("x", {"x": None}) is None
        with pytest.raises(ExpressionError, match="null value has no fields"):
            evaluate("x.y", {"x": None})

    def test_runtime_failures_are_named(self):
        with pytest.raises(ExpressionError, match="division by zero"):
            evaluate("1 / n", {"n": 0})
        with pytest.raises(ExpressionError, match="not a variable"):
            evaluate("unknown + 1", {})
        with pytest.raises(ExpressionError, match="sub-expression of '\\?:'"):
            evaluate("unknown > 1 ? 'a' : 'b'", {})
        with pytest.raises(ExpressionError, match="no field 'x'"):
            evaluate("m.x", {"m": {}})
        with pytest.raises(ExpressionError, match="integer overflow"):
            evaluate("9223372036854775807 + 1", {})
        with pytest.raises(ExpressionError, match="syntax error"):
            evaluate("1 +", {})
        with pytest.raises(ExpressionError, match="empty"):
            evaluate("  ", {})
        with pytest.raises(ExpressionError, match="empty"):
            evaluate(None, {})
        with pytest.raises(ExpressionError, match="list index out of range"):
            evaluate("[1][3]", {})

    def test_results_are_json_shaped(self):
        assert evaluate("[1, 2]", {}) == [1, 2]
        assert evaluate("{'a': 1}", {}) == {"a": 1}
        assert evaluate("timestamp('2026-01-01T00:00:00Z') + duration('72h')", {}) == (
            "2026-01-04T00:00:00+00:00"
        )
        assert evaluate("duration('90m')", {}) == 5400.0
        assert evaluate("b'ab'", {}) == "ab"
        assert evaluate("uint(3)", {}) == 3
        nested = evaluate("{'a': [1, {'b': 2.5}]}", {})
        assert nested == {"a": [1, {"b": 2.5}]}
        assert type(nested["a"][0]) is int and type(nested["a"][1]["b"]) is float

    def test_context_keys_and_map_keys_are_strings(self):
        assert evaluate("m['1']", {"m": {1: "one"}}) == "one"

    def test_non_json_context_values_read_as_strings(self):
        assert evaluate("when", {"when": datetime.date(2026, 1, 2)}) == "2026-01-02"
        assert evaluate("size(items)", {"items": (1, 2)}) == 2

    def test_bool_is_not_a_number(self):
        assert evaluate("flag", {"flag": True}) is True
        with pytest.raises(ExpressionError, match="takes a number"):
            evaluate("abs(flag)", {"flag": True})
        with pytest.raises(ExpressionError, match="takes a list of numbers"):
            evaluate("sum([true])", {})


class TestConversions:
    def test_to_cel_maps_json_types(self):
        assert isinstance(to_cel(True), celtypes.BoolType)
        assert not isinstance(to_cel(True), celtypes.IntType)
        assert isinstance(to_cel(1), celtypes.IntType)
        assert isinstance(to_cel(1.0), celtypes.DoubleType)
        assert isinstance(to_cel("s"), celtypes.StringType)
        assert to_cel(None) is None
        mapping = to_cel({"a": [1, {"b": None}], 2: "two"})
        assert isinstance(mapping, celtypes.MapType)
        assert set(map(str, mapping)) == {"a", "2"}
        assert isinstance(mapping[celtypes.StringType("a")], celtypes.ListType)
        assert isinstance(to_cel((1, 2)), celtypes.ListType)
        assert to_cel(datetime.date(2026, 1, 2)) == celtypes.StringType("2026-01-02")

    def test_from_cel_round_trips(self):
        value = {"a": [1, 2.5, "s", True, None, {"b": [False]}]}
        assert from_cel(to_cel(value)) == value
        assert from_cel(None) is None
        assert from_cel(celtypes.UintType(4)) == 4
        assert from_cel(celtypes.BytesType(b"ok")) == "ok"
        assert from_cel(celtypes.DurationType(seconds=90)) == 90.0
        stamp = celtypes.TimestampType(
            datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        )
        assert from_cel(stamp) == "2026-01-01T00:00:00+00:00"
        # Plain Python spellings pass through unchanged.
        assert from_cel(3) == 3 and from_cel(2.5) == 2.5 and from_cel("x") == "x"
        assert from_cel([1, (2, 3)]) == [1, [2, 3]]
        assert from_cel({"k": 1}) == {"k": 1}
        assert from_cel(object()).startswith("<object")


class TestCompile:
    def test_returns_an_ast_for_valid_text(self):
        assert compile_expression("1 + 1") is not None

    def test_syntax_errors_carry_the_label(self):
        with pytest.raises(ExpressionError, match="syntax error"):
            compile_expression("(1 +")

    def test_empty_or_non_text_is_refused(self):
        for value in ("", "   ", None, 3, ["a"]):
            with pytest.raises(ExpressionError, match="empty"):
                compile_expression(value)

    def test_macro_nesting_is_capped(self):
        assert MAX_MACRO_DEPTH == 2
        compile_expression("a.map(x, b.filter(y, y > x))")
        compile_expression("a.map(x, x).filter(y, y > 1).all(z, z > 0)")
        with pytest.raises(ExpressionError, match="nested at most"):
            compile_expression("a.map(x, b.map(y, c.exists(z, z == y)))")


class TestReferencedPaths:
    def test_paths_and_prefixes_without_function_names_or_literals(self):
        paths = referenced_paths(
            "nodes.fetch.count * weight + size(rows) + 'nodes.fake.z' + double(n)"
        )
        assert {"nodes.fetch.count", "weight", "rows", "n"} <= paths
        assert "size" not in paths and "double" not in paths
        assert "nodes.fake.z" not in paths and "nodes.fake" not in paths

    def test_unparsable_expression_references_nothing(self):
        assert referenced_paths("a +") == set()
        assert referenced_paths("") == set()

    def test_index_access_is_a_path(self):
        assert referenced_paths("nodes['ai'].answer") == {"nodes.ai.answer"}
        assert referenced_paths('nodes["a"]["b"]') == {"nodes.a.b"}

    def test_a_computed_index_is_a_wildcard(self):
        assert referenced_paths("nodes[key].x") == {"nodes.*.x", "key"}
        assert referenced_paths("items[0]") == {"items.*"}

    def test_an_escaped_or_triple_quoted_index_is_a_wildcard(self):
        assert referenced_paths("nodes['cl\\x61ssify'].severity") == {
            "nodes.*.severity"
        }
        assert referenced_paths("nodes['''ai'''].severity") == {"nodes.*.severity"}

    def test_paths_are_maximal_chains_including_function_arguments(self):
        assert referenced_paths("size(items.filter(x, x.score > limit))") == {
            "items",
            "x.score",
            "limit",
        }
        assert referenced_paths("has(nodes.fetch.count)") == {"nodes.fetch.count"}

    def test_method_receivers_are_paths_methods_are_not(self):
        assert referenced_paths("name.startsWith('a')") == {"name"}
        assert referenced_paths("a.b.c.size()") == {"a.b.c"}


class TestReviewRegressions:
    """Behaviours pinned by the review of the compute action."""

    def test_round_is_half_up(self):
        assert evaluate("round(2.5)", {}) == 3
        assert evaluate("round(-2.5)", {}) == -3
        assert evaluate("round(0.125, 2)", {}) == 0.13
        assert evaluate("round(1234.5, -2)", {}) == 1200.0

    def test_modulo_is_int_only_with_a_hint(self):
        assert evaluate("7 % 2", {}) == 1
        with pytest.raises(ExpressionError, match=r"int\(\.\.\.\)"):
            evaluate("7 % 2.5", {})

    def test_non_finite_results_are_refused(self):
        for expression in ["1.0 / 0.0", "0.0 / 0.0", "[1.0 / 0.0]", "{'a': 0.0 / 0.0}"]:
            with pytest.raises(ExpressionError, match="not a finite number"):
                evaluate(expression, {})

    def test_helpers_on_non_finite_input_are_an_expression_error(self):
        # floor(inf) raised a single-arg OverflowError that _describe mishandled.
        for expression in ["floor(1.0 / 0.0)", "ceil(0.0 / 0.0)", "round(x / 0.0)"]:
            with pytest.raises(ExpressionError, match="non-finite"):
                evaluate(expression, {"x": 1.0})
