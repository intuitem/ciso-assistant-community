import pytest

from core.cel_service import evaluate_quick_form_document
from core.quick_form_ratings import evaluate_ratings, expand_scales, scales_error

LEVELS = [{"ref_id": "low", "label": "Low"}, {"ref_id": "high", "label": "High"}]
PAGE = "urn:t:risk:qf_page:f:p1"


def _form(**rating):
    return {
        "scales_definition": [
            {"ref_id": "impact", "levels": LEVELS},
            {"ref_id": "effort", "levels": LEVELS},
            {
                "ref_id": "threat",
                "levels": [{**LEVELS[0], "value": 1}, {**LEVELS[1], "value": 4}],
            },
        ],
        "outcomes_definition": [
            {
                "ref_id": "priority",
                "kind": "rating",
                "dimensions": ["impact", "effort"],
                "levels": [{"ref_id": "later"}, {"ref_id": "now"}],
                **(rating or {"grid": [["later", "later"], ["now", "later"]]}),
            }
        ],
        "pages": [
            {
                "urn": PAGE,
                "questions": {
                    f"{PAGE}:question:impact": {
                        "type": "unique_choice",
                        "config": {"scale": "impact"},
                    },
                    f"{PAGE}:question:effort": {
                        "type": "unique_choice",
                        "config": {"scale": "effort"},
                    },
                },
            }
        ],
    }


def _page(urn=PAGE, **levels):
    return {
        "urn": urn,
        "answers": [({"scale": s}, f"x:choice:{lvl}") for s, lvl in levels.items()],
    }


def test_a_scale_becomes_choices():
    form = expand_scales(_form())
    choices = form["pages"][0]["questions"][f"{PAGE}:question:impact"]["choices"]
    assert [c["urn"].rsplit(":", 1)[-1] for c in choices] == ["low", "high"]
    assert scales_error(form) is None


def test_a_broken_rating_is_named():
    assert "grid or rules" in scales_error(_form(grid=None))
    assert "grid" in scales_error(_form(grid=[["later", "later"]]))
    assert "one of its levels" in scales_error(_form(grid=[["x", "x"], ["now", "x"]]))
    assert "exactly two" in scales_error(
        _form(dimensions=["impact"], grid=[["later"], ["now"]])
    )
    assert "not valid CEL" in scales_error(
        _form(rules=[{"level": "now", "when": "1 +"}])
    )


def test_a_grid_rates_two_dimensions():
    values, (result,) = evaluate_ratings(_form(), [_page(impact="high", effort="low")])
    (point,) = result["points"]
    assert (point["level"], point["rank"], point["stage"]) == ("now", 2, "current")
    assert point["dims"]["impact"] == {"level": "high", "rank": 2.0, "value": 2.0}
    assert values == {"priority": 2.0}


def test_rules_rate_any_number_of_dimensions():
    # A MONARC-like product of three factors, the threat weighted by its values.
    form = _form(
        dimensions=["impact", "effort", "threat"],
        rules=[
            {
                "level": "now",
                "when": "dims.impact.rank * dims.effort.rank * dims.threat.value >= 8.0",
            },
            {"level": "later", "when": "true"},
        ],
    )
    assert scales_error(form) is None
    _, (result,) = evaluate_ratings(
        form,
        [
            _page(impact="high", effort="high", threat="high"),
            _page(
                urn="urn:t:risk:qf_page:f:p2",
                impact="high",
                effort="high",
                threat="low",
            ),
        ],
    )
    assert [p["level"] for p in result["points"]] == ["now", "later"]


def test_a_rating_reads_only_its_pages():
    form = _form(pages=["p2"], grid=[["later", "later"], ["now", "later"]])
    p2 = "urn:t:risk:qf_page:f:p2"
    form["pages"].append({**form["pages"][0], "urn": p2})
    assert scales_error(form) is None
    _, (result,) = evaluate_ratings(
        form,
        [_page(impact="high", effort="low"), _page(p2, impact="high", effort="low")],
    )
    assert [p["page"] for p in result["points"]] == [p2]
    form["outcomes_definition"][0]["pages"] = ["nope"]
    assert "unknown page" in scales_error(form)


def test_the_builder_keeps_scales_ratings_and_facts():
    from pathlib import Path

    import yaml

    from library.quick_form_editor import (
        editor_doc_to_quick_form_object,
        quick_form_to_editor_doc,
    )

    source = Path(__file__).resolve().parents[2] / (
        "library/libraries/quick-form-dpia.yaml"
    )
    form = yaml.safe_load(source.read_text())["objects"]["quick_forms"][0]
    saved = editor_doc_to_quick_form_object(
        quick_form_to_editor_doc(form), existing=form
    )
    assert saved["scales_definition"] == form["scales_definition"]
    assert saved["outcomes_definition"] == form["outcomes_definition"]
    assert scales_error(saved) is None
    severity = "urn:intuitem:risk:qf_page:dpia:illegitimate_access:question:severity"
    (page,) = [p for p in saved["pages"] if severity in p["questions"]]
    assert page["questions"][severity]["config"]["scale"] == "severity"
    assert not page["questions"][severity].get("choices")
    # Pages keep the facts they show.
    assert [p.get("facts") for p in saved["pages"]] == [
        p.get("facts") for p in form["pages"]
    ]


@pytest.mark.parametrize(
    "scales",
    [
        [{"ref_id": "s", "levels": [{"label": "no id"}]}],
        [{"ref_id": "s", "levels": ["low", "high"]}],
        [{"ref_id": "s"}],
        "not a list",
    ],
)
def test_malformed_scales_are_refused_not_crashed(scales):
    from library.utils import QuickFormImporter

    form = {
        "urn": "urn:test:risk:quick_form:broken",
        "ref_id": "broken",
        "scales_definition": scales,
        "pages": [
            {
                "urn": "urn:test:risk:qf_page:broken:p",
                "ref_id": "p",
                "questions": {
                    "urn:test:risk:qf_page:broken:p:question:q": {
                        "type": "unique_choice",
                        "text": "Q",
                        "config": {"scale": "s"},
                    }
                },
            }
        ],
    }
    error = QuickFormImporter(form).init()
    assert error and error.startswith("[QUICK_FORM_ERROR]"), error


def test_a_rating_scoped_to_a_malformed_page_list_is_refused():
    form = {
        "scales_definition": [
            {"ref_id": "a", "levels": [{"ref_id": "1"}]},
            {"ref_id": "b", "levels": [{"ref_id": "1"}]},
        ],
        "pages": [],
        "outcomes_definition": [
            {
                "ref_id": "r",
                "kind": "rating",
                "dimensions": ["a", "b"],
                "levels": [{"ref_id": "x"}],
                "grid": [["x"]],
                "pages": [["nested"]],
            }
        ],
    }
    assert "pages must be a list" in scales_error(form)


def test_preview_survives_a_broken_draft():
    form = {
        "scales_definition": [{"ref_id": "severity", "levels": [{"label": "Low"}]}],
        "outcomes_definition": [
            {
                "ref_id": "risk",
                "kind": "rating",
                "dimensions": ["severity"],
                "levels": [{"label": "Low"}],
            }
        ],
        "pages": [
            {
                "urn": "urn:test:qf_page:p",
                "questions": {
                    "urn:test:qf_page:p:question:q": {
                        "type": "unique_choice",
                        "config": {"scale": "severity"},
                    }
                },
            }
        ],
    }
    assert "hidden_pages" in evaluate_quick_form_document(form, {})
