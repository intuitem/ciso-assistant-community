"""Tests for RequirementNodeImporter importing questions and choices from YAML-style dicts."""

import pytest
from core.models import (
    Framework,
    LoadedLibrary,
    Question,
    QuestionChoice,
    RequirementNode,
)
from iam.models import Folder
from library.utils import RequirementNodeImporter


@pytest.fixture
def library_framework(db):
    """Creates a LoadedLibrary, Framework, and provides a helper to call the importer."""
    folder = Folder.get_root_folder()
    lib = LoadedLibrary.objects.create(
        name="Test Question Import Library",
        urn="urn:test:qimport:lib",
        ref_id="QIMP-LIB",
        version=1,
        locale="en",
        default_locale=True,
        folder=folder,
        is_published=True,
    )
    fw = Framework.objects.create(
        name="Question Import Framework",
        urn="urn:test:qimport:fw",
        folder=folder,
        library=lib,
        status=Framework.Status.DRAFT,
        is_published=True,
        locale="en",
        default_locale=True,
    )

    def import_node(requirement_data, index=0):
        importer = RequirementNodeImporter(requirement_data, index)
        err = importer.is_valid()
        assert err is None, f"Validation failed: {err}"
        importer.import_requirement_node(fw)
        return RequirementNode.objects.get(urn=requirement_data["urn"].lower())

    return {"framework": fw, "library": lib, "import_node": import_node}


@pytest.mark.django_db
class TestLibraryImportQuestions:
    def test_import_single_choice_question(self, library_framework):
        """YAML-style dict with type: 'unique_choice', 2 choices -> proper DB objects."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:sc",
                "ref_id": "SC-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_sc": {
                        "type": "unique_choice",
                        "text": "Pick one",
                        "choices": [
                            {
                                "urn": "urn:test:qimport:c1",
                                "value": "Yes",
                                "add_score": 10,
                                "compute_result": "true",
                            },
                            {
                                "urn": "urn:test:qimport:c2",
                                "value": "No",
                                "add_score": 0,
                                "compute_result": "false",
                            },
                        ],
                    }
                },
            }
        )

        q = rn.questions.first()
        assert q is not None
        # unique_choice -> single_choice mapping
        assert q.type == "single_choice"
        assert q.annotation == "Pick one"
        assert q.choices.count() == 2

        c1 = q.choices.get(ref_id="c1")
        assert c1.annotation == "Yes"
        assert c1.add_score == 10
        assert c1.compute_result == "true"
        assert c1.order == 0

        c2 = q.choices.get(ref_id="c2")
        assert c2.annotation == "No"
        assert c2.add_score == 0
        assert c2.compute_result == "false"
        assert c2.order == 1

    def test_import_multiple_choice_question(self, library_framework):
        """type: 'multiple_choice' preserved as-is."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:mc",
                "ref_id": "MC-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_mc": {
                        "type": "multiple_choice",
                        "text": "Select all",
                        "choices": [
                            {"urn": "urn:test:qimport:mc1", "value": "A"},
                            {"urn": "urn:test:qimport:mc2", "value": "B"},
                        ],
                    }
                },
            }
        )

        q = rn.questions.first()
        assert q.type == "multiple_choice"

    def test_import_question_with_depends_on(self, library_framework):
        """Question dict includes depends_on -> persisted correctly."""
        depends_on = {
            "question": "q_parent",
            "answers": ["c1", "c2"],
            "condition": "any",
        }
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:dep",
                "ref_id": "DEP-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_dep": {
                        "type": "text",
                        "text": "Follow-up",
                        "depends_on": depends_on,
                    }
                },
            }
        )

        q = rn.questions.first()
        assert q.depends_on == depends_on

    def test_import_compute_result_bool_to_str(self, library_framework):
        """YAML compute_result: true (bool) -> stored as 'true' (string)."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:boolcr",
                "ref_id": "BOOLCR-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_boolcr": {
                        "type": "unique_choice",
                        "text": "Bool test",
                        "choices": [
                            {
                                "urn": "urn:test:qimport:boolcr_t",
                                "value": "Yes",
                                "compute_result": True,
                            },
                            {
                                "urn": "urn:test:qimport:boolcr_f",
                                "value": "No",
                                "compute_result": False,
                            },
                        ],
                    }
                },
            }
        )

        q = rn.questions.first()
        c_true = q.choices.get(ref_id="boolcr_t")
        c_false = q.choices.get(ref_id="boolcr_f")
        assert c_true.compute_result == "true"
        assert c_false.compute_result == "false"

    def test_import_compute_result_string_passthrough(self, library_framework):
        """YAML compute_result: 'custom_value' -> stored as 'custom_value'."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:strcr",
                "ref_id": "STRCR-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_strcr": {
                        "type": "unique_choice",
                        "text": "String test",
                        "choices": [
                            {
                                "urn": "urn:test:qimport:strcr1",
                                "value": "Custom",
                                "compute_result": "custom_value",
                            },
                            {
                                "urn": "urn:test:qimport:strcr2",
                                "value": "Other",
                            },
                        ],
                    }
                },
            }
        )

        q = rn.questions.first()
        c = q.choices.get(ref_id="strcr1")
        assert c.compute_result == "custom_value"

    def test_import_choice_with_all_optional_fields(self, library_framework):
        """Choice with description, color, select_implementation_groups, translations."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:allopt",
                "ref_id": "ALLOPT-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_allopt": {
                        "type": "unique_choice",
                        "text": "Full options",
                        "choices": [
                            {
                                "urn": "urn:test:qimport:allopt1",
                                "value": "Rich choice",
                                "add_score": 5,
                                "compute_result": "true",
                                "description": "A detailed description",
                                "color": "#00FF00",
                                "select_implementation_groups": ["advanced", "expert"],
                                "translations": {"fr": {"value": "Choix riche"}},
                            },
                            {
                                "urn": "urn:test:qimport:allopt2",
                                "value": "Plain",
                            },
                        ],
                    }
                },
            }
        )

        q = rn.questions.first()
        c = q.choices.get(ref_id="allopt1")
        assert c.description == "A detailed description"
        assert c.color == "#00FF00"
        assert c.select_implementation_groups == ["advanced", "expert"]
        assert c.translations == {"fr": {"value": "Choix riche"}}

    def test_import_choice_missing_optional_fields(self, library_framework):
        """Choice with only urn and value -> optional fields are None/defaults."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:minopt",
                "ref_id": "MINOPT-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_minopt": {
                        "type": "unique_choice",
                        "text": "Minimal",
                        "choices": [
                            {"urn": "urn:test:qimport:minopt1", "value": "A"},
                            {"urn": "urn:test:qimport:minopt2", "value": "B"},
                        ],
                    }
                },
            }
        )

        q = rn.questions.first()
        c = q.choices.get(ref_id="minopt1")
        assert c.add_score is None
        assert c.compute_result is None
        assert c.description is None
        assert c.color is None
        assert c.select_implementation_groups is None

    def test_import_ref_id_extracted_from_urn(self, library_framework):
        """Question URN 'urn:test:fw:req:q1' -> ref_id='q1' (last segment after ':')."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:refid",
                "ref_id": "REFID-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:fw:req:q1": {
                        "type": "text",
                        "text": "URN test",
                    }
                },
            }
        )

        q = rn.questions.first()
        assert q.ref_id == "q1"  # Last segment after ':'

    def test_import_question_ordering(self, library_framework):
        """Two questions in dict -> order=0 and order=1. Choices also ordered."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:order",
                "ref_id": "ORDER-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_first": {
                        "type": "unique_choice",
                        "text": "First",
                        "choices": [
                            {"urn": "urn:test:qimport:ord_c1", "value": "A"},
                            {"urn": "urn:test:qimport:ord_c2", "value": "B"},
                            {"urn": "urn:test:qimport:ord_c3", "value": "C"},
                        ],
                    },
                    "urn:test:qimport:q_second": {
                        "type": "text",
                        "text": "Second",
                    },
                },
            }
        )

        questions = list(rn.questions.order_by("order"))
        assert len(questions) == 2
        assert questions[0].order == 0
        assert questions[1].order == 1

        # Check choice ordering within first question
        choices = list(questions[0].choices.order_by("order"))
        assert len(choices) == 3
        assert choices[0].order == 0
        assert choices[1].order == 1
        assert choices[2].order == 2

    def test_import_question_with_no_choices(self, library_framework):
        """Question dict with no 'choices' key -> Question created, 0 choices."""
        rn = library_framework["import_node"](
            {
                "urn": "urn:test:qimport:req:nochoice",
                "ref_id": "NOCHOICE-REQ",
                "assessable": True,
                "questions": {
                    "urn:test:qimport:q_nochoice": {
                        "type": "text",
                        "text": "Open-ended question",
                    }
                },
            }
        )

        q = rn.questions.first()
        assert q is not None
        assert q.type == "text"
        assert q.choices.count() == 0
