"""Framework scoring properties: score_scale_locked and score_calculation_method,
declared in the framework section of a library."""

import pytest

from core.models import Framework, LoadedLibrary, StoredLibrary

FRAMEWORK_URN = "urn:test:risk:framework:scoring-props"
PROPERTIES = (
    "    score_scale_locked: true\n    score_calculation_method: average_of_averages\n"
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
            "score_calculation_method": "average_of_averages"
        }

    def test_omitted_properties_keep_the_defaults(self):
        framework = load(library(1))
        assert framework.score_scale_locked is False
        assert not framework.is_scale_bound
        assert framework.score_calculation_method == "average"

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
