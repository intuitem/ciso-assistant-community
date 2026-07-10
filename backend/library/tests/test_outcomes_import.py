import pytest
from core.models import (
    Framework,
    LoadedLibrary,
    StoredLibrary,
)

SAMPLE_FRAMEWORK_WITH_OUTCOMES_YAML = """
urn: urn:intuitem:test:library:framework-with-outcomes
locale: en
ref_id: FW-OUTCOMES
name: Framework with Outcomes
description: A framework with outcomes definition
copyright: Test
version: 1
publication_date: 2026-03-06
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:framework-with-outcomes
    ref_id: FW-OUTCOMES
    name: Framework with Outcomes
    description: A framework with outcomes
    outcomes_definition:
      - ref_id: outcome_1
        annotation: Outcome 1
        color: "#FF0000"
        expression: "score > 80"
        translations:
          fr:
            annotation: Résultat 1
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:fw-outcomes:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
      description: A requirement
""".lstrip()

SAMPLE_FRAMEWORK_WITHOUT_OUTCOMES_YAML = """
urn: urn:intuitem:test:library:framework-without-outcomes
locale: en
ref_id: FW-NO-OUTCOMES
name: Framework without Outcomes
description: A framework without outcomes definition
copyright: Test
version: 1
publication_date: 2026-03-06
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:framework-without-outcomes
    ref_id: FW-NO-OUTCOMES
    name: Framework without Outcomes
    description: A framework without outcomes
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:fw-no-outcomes:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
      description: A requirement
""".lstrip()

SAMPLE_FRAMEWORK_V2_WITH_OUTCOMES_YAML = """
urn: urn:intuitem:test:library:framework-without-outcomes
locale: en
ref_id: FW-NO-OUTCOMES
name: Framework updated with Outcomes
description: A framework updated with outcomes
copyright: Test
version: 2
publication_date: 2026-03-06
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:framework-without-outcomes
    ref_id: FW-NO-OUTCOMES
    name: Framework updated with Outcomes
    description: A framework updated with outcomes
    outcomes_definition:
      - ref_id: outcome_new
        expression: 'true'
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:fw-no-outcomes:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
      description: A requirement
""".lstrip()


@pytest.mark.django_db
class TestOutcomesImport:
    """Tests for importing frameworks with outcomes_definition."""

    def test_import_framework_with_outcomes(self):
        """Test that outcomes_definition is correctly imported and stored."""
        stored, error = StoredLibrary.store_library_content(
            SAMPLE_FRAMEWORK_WITH_OUTCOMES_YAML.encode("utf-8")
        )
        assert error is None
        assert stored is not None

        load_error = stored.load()
        assert load_error is None

        fw = Framework.objects.get(
            urn="urn:intuitem:test:framework:framework-with-outcomes"
        )
        assert fw.outcomes_definition == [
            {
                "ref_id": "outcome_1",
                "annotation": "Outcome 1",
                "color": "#FF0000",
                "expression": "score > 80",
                "translations": {"fr": {"annotation": "Résultat 1"}},
            }
        ]

    def test_import_framework_without_outcomes(self):
        """Test that outcomes_definition defaults to an empty list when missing."""
        stored, error = StoredLibrary.store_library_content(
            SAMPLE_FRAMEWORK_WITHOUT_OUTCOMES_YAML.encode("utf-8")
        )
        assert error is None
        assert stored is not None

        load_error = stored.load()
        assert load_error is None

        fw = Framework.objects.get(
            urn="urn:intuitem:test:framework:framework-without-outcomes"
        )
        assert fw.outcomes_definition == []

    def test_update_framework_with_outcomes(self):
        """Test that outcomes_definition is updated via LibraryUpdater."""
        # 1. Load v1 without outcomes
        stored_v1, _ = StoredLibrary.store_library_content(
            SAMPLE_FRAMEWORK_WITHOUT_OUTCOMES_YAML.encode("utf-8")
        )
        stored_v1.load()

        fw_v1 = Framework.objects.get(
            urn="urn:intuitem:test:framework:framework-without-outcomes"
        )
        assert fw_v1.outcomes_definition == []

        # 2. Load v2 with outcomes
        stored_v2, _ = StoredLibrary.store_library_content(
            SAMPLE_FRAMEWORK_V2_WITH_OUTCOMES_YAML.encode("utf-8")
        )

        loaded_lib = LoadedLibrary.objects.get(urn=stored_v1.urn)
        # LibraryUpdater is called during update
        error = loaded_lib.update(strategy="clamp")
        assert error is None

        fw_v2 = Framework.objects.get(
            urn="urn:intuitem:test:framework:framework-without-outcomes"
        )
        assert fw_v2.name == "Framework updated with Outcomes"
        assert fw_v2.outcomes_definition == [
            {"ref_id": "outcome_new", "expression": "true"}
        ]
