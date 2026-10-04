"""Framework scoring properties (score_scale_locked, score_calculation_method,
anchor_na_to_target, target_score), declared in the framework section of a
library."""

import pytest

from core.models import Framework, LoadedLibrary, StoredLibrary

FRAMEWORK_URN = "urn:test:risk:framework:scoring-props"
PROPERTIES = (
    "    score_scale_locked: true\n"
    "    score_calculation_method: average_of_averages\n"
    "    anchor_na_to_target: true\n"
    "    target_score: 3\n"
)


def library(version, framework_properties=""):
    return f"""
urn: urn:test:risk:library:scoring-props
locale: en
ref_id: SCORING-PROPS
name: Scoring properties test library
description: test
version: {version}
publication_date: 2026-10-03
copyright: test
provider: test
packager: test
objects:
  framework:
    urn: {FRAMEWORK_URN}
    ref_id: SCORING-PROPS
    name: Scoring properties test framework
    description: test
    min_score: 1
    max_score: 5
{framework_properties}    requirement_nodes:
    - urn: urn:test:risk:req_node:scoring-props:1
      assessable: true
      depth: 1
      ref_id: '1'
      name: Requirement one
""".lstrip().encode("utf-8")


def load(content):
    stored, error = StoredLibrary.store_library_content(content)
    assert error is None, error
    assert stored.load() is None
    return Framework.objects.get(urn=FRAMEWORK_URN)


@pytest.mark.django_db
class TestFrameworkScoringProperties:
    def test_declared_properties_are_imported(self):
        framework = load(library(1, PROPERTIES))
        assert framework.score_scale_locked is True
        assert framework.is_scale_bound
        assert framework.default_scoring == {
            "score_calculation_method": "average_of_averages",
            "anchor_na_to_target": True,
            "target_score": 3,
        }

    def test_omitted_properties_keep_the_defaults(self):
        framework = load(library(1))
        assert framework.score_scale_locked is False
        assert not framework.is_scale_bound
        assert framework.score_calculation_method == "average"
        assert framework.anchor_na_to_target is False
        assert framework.target_score is None

    def test_unknown_method_is_rejected(self):
        with pytest.raises(ValueError, match="score_calculation_method"):
            load(library(1, "    score_calculation_method: median\n"))

    def test_update_resets_properties_removed_from_the_framework(self):
        load(library(1, PROPERTIES))
        StoredLibrary.store_library_content(library(2))
        loaded = LoadedLibrary.objects.get(urn="urn:test:risk:library:scoring-props")
        assert loaded.update(strategy="clamp") is None

        framework = Framework.objects.get(urn=FRAMEWORK_URN)
        assert framework.score_scale_locked is False
        assert framework.score_calculation_method == "average"
        assert framework.anchor_na_to_target is False
        assert framework.target_score is None


def _convert(tmp_path, framework_meta, groups, *, outcomes=()):
    """YAML framework the v2 converter makes of a workbook with these framework
    meta entries, implementation groups (ref_id, target_score) and outcomes
    (ref_id, expression, annotation, annotation[fr])."""
    import importlib.util
    from pathlib import Path

    import openpyxl
    import yaml

    script = Path(__file__).resolve().parents[2] / "scripts" / "convert_library_v2.py"
    spec = importlib.util.spec_from_file_location("convert_library_v2", script)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)

    wb = openpyxl.Workbook()
    sheets = {
        "library_meta": [
            ("type", "library"),
            ("urn", "urn:test:risk:library:converted-scoring"),
            ("locale", "en"),
            ("ref_id", "CONVERTED-SCORING"),
            ("name", "Converted scoring"),
            ("description", "test"),
            ("copyright", "test"),
            ("version", "1"),
            ("publication_date", "2026-10-04"),
            ("provider", "test"),
            ("packager", "test"),
        ],
        "framework_meta": [
            ("type", "framework"),
            ("urn", "urn:test:risk:framework:converted-scoring"),
            ("ref_id", "CONVERTED-SCORING"),
            ("name", "Converted scoring"),
            ("description", "test"),
            ("base_urn", "urn:test:risk:req_node:converted-scoring"),
            ("min_score", 1),
            ("max_score", 5),
            ("implementation_groups_definition", "IG"),
            *framework_meta,
        ],
        "framework_content": [
            ("assessable", "depth", "ref_id", "name", "implementation_groups"),
            ("x", 1, "1", "Requirement", "B"),
        ],
        "IG_meta": [("type", "implementation_groups"), ("name", "IG")],
        "IG_content": [("ref_id", "name", "target_score"), *groups],
    }
    if outcomes:
        sheets["framework_meta"].append(("outcomes_definition", "outcomes"))
        sheets["outcomes_meta"] = [("type", "outcomes"), ("name", "outcomes")]
        sheets["outcomes_content"] = [
            ("ref_id", "expression", "annotation", "annotation[fr]"),
            *outcomes,
        ]
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        for row in rows:
            ws.append(row)
    source, output = tmp_path / "library.xlsx", tmp_path / "library.yaml"
    wb.save(source)
    converter.create_library(str(source), str(output))
    return yaml.safe_load(output.read_text())["objects"]["framework"]


class TestConverter:
    def test_scoring_defaults_and_group_targets(self, tmp_path):
        framework = _convert(
            tmp_path,
            [("anchor_na_to_target", "x"), ("target_score", 3)],
            [("B", "basic", 2.5), ("E", "essential", None)],
        )
        assert framework["anchor_na_to_target"] is True
        assert framework["target_score"] == 3.0
        targets = {
            group["ref_id"]: group.get("target_score")
            for group in framework["implementation_groups_definition"]
        }
        assert targets == {"B": 2.5, "E": None}

    def test_group_target_without_framework_target_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="framework needs one too"):
            _convert(tmp_path, [], [("B", "basic", 2.5)])

    def test_outcomes(self, tmp_path):
        framework = _convert(
            tmp_path,
            [],
            [("B", "basic", None)],
            outcomes=[
                ("passed", "assessment.maturity_score >= 3.0", "Passed", "Réussi")
            ],
        )
        assert framework["outcomes_definition"] == [
            {
                "ref_id": "passed",
                "expression": "assessment.maturity_score >= 3.0",
                "annotation": "Passed",
                "translations": {"fr": {"annotation": "Réussi"}},
            }
        ]

    def test_outcome_without_expression_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="needs a ref_id and an expression"):
            _convert(
                tmp_path,
                [],
                [("B", "basic", None)],
                outcomes=[("passed", None, "Passed", None)],
            )
