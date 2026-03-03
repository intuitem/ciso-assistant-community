"""Tests for _sync_questions_from_data — upsert/prune of Question and QuestionChoice rows during library updates."""

import pytest
from core.models import (
    Framework,
    LoadedLibrary,
    Question,
    QuestionChoice,
    RequirementNode,
    _sync_questions_from_data,
)
from iam.models import Folder


@pytest.fixture
def requirement_node(db):
    """Create a RequirementNode ready for question sync tests."""
    folder = Folder.get_root_folder()
    lib = LoadedLibrary.objects.create(
        name="Sync Test Library",
        urn="urn:test:sync:lib",
        ref_id="SYNC-LIB",
        version=1,
        locale="en",
        default_locale=True,
        folder=folder,
        is_published=True,
    )
    fw = Framework.objects.create(
        name="Sync Test Framework",
        urn="urn:test:sync:fw",
        folder=folder,
        library=lib,
        status=Framework.Status.PUBLISHED,
        is_published=True,
        locale="en",
        default_locale=True,
    )
    return RequirementNode.objects.create(
        urn="urn:test:sync:req:1",
        ref_id="SYNC-REQ-1",
        framework=fw,
        folder=folder,
        is_published=True,
        assessable=True,
    )


def _make_choice(ref_suffix, value="Choice", **extra):
    """Helper to build a choice dict with a URN derived from ref_suffix."""
    d = {"urn": f"urn:test:sync:{ref_suffix}", "value": value}
    d.update(extra)
    return d


@pytest.mark.django_db
class TestSyncQuestionsCreation:
    """Sync on a node with no prior questions — behaves like pure creation."""

    def test_creates_question_and_choices(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Pick one",
                    "choices": [
                        _make_choice("c1", "Yes", add_score=10, compute_result=True),
                        _make_choice("c2", "No", add_score=0, compute_result=False),
                    ],
                }
            },
        )

        assert requirement_node.questions.count() == 1
        q = requirement_node.questions.get()
        assert q.urn == "urn:test:sync:q1"
        assert q.type == "unique_choice"
        assert q.annotation == "Pick one"
        assert q.choices.count() == 2
        assert q.choices.get(ref_id="c1").annotation == "Yes"
        assert q.choices.get(ref_id="c2").annotation == "No"

    def test_single_choice_normalized_to_unique_choice(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "single_choice",
                    "text": "Normalized",
                }
            },
        )

        assert requirement_node.questions.get().type == "unique_choice"

    def test_creates_multiple_questions_with_ordering(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q_first": {"type": "text", "text": "First"},
                "urn:test:sync:q_second": {"type": "number", "text": "Second"},
                "urn:test:sync:q_third": {"type": "boolean", "text": "Third"},
            },
        )

        questions = list(requirement_node.questions.order_by("order"))
        assert len(questions) == 3
        assert [q.order for q in questions] == [0, 1, 2]
        assert [q.annotation for q in questions] == ["First", "Second", "Third"]

    def test_ref_id_extracted_from_urn(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {"urn:test:sync:fw:deep:q1": {"type": "text", "text": "URN test"}},
        )

        assert requirement_node.questions.get().ref_id == "q1"


@pytest.mark.django_db
class TestSyncQuestionsUpdate:
    """Sync on a node that already has questions — upsert + prune."""

    def _seed(self, requirement_node):
        """Seed two questions with choices."""
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Original Q1",
                    "weight": 2,
                    "choices": [
                        _make_choice("c1", "Alpha", add_score=1),
                        _make_choice("c2", "Beta", add_score=2),
                    ],
                },
                "urn:test:sync:q2": {
                    "type": "text",
                    "text": "Original Q2",
                },
            },
        )
        return requirement_node

    def test_update_question_fields(self, requirement_node):
        self._seed(requirement_node)
        q1_pk = requirement_node.questions.get(urn="urn:test:sync:q1").pk

        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "multiple_choice",
                    "text": "Updated Q1",
                    "weight": 5,
                    "translations": {"fr": {"text": "Q1 mis à jour"}},
                    "choices": [
                        _make_choice("c1", "Alpha", add_score=1),
                        _make_choice("c2", "Beta", add_score=2),
                    ],
                },
                "urn:test:sync:q2": {
                    "type": "text",
                    "text": "Original Q2",
                },
            },
        )

        q1 = requirement_node.questions.get(urn="urn:test:sync:q1")
        assert q1.pk == q1_pk, "Should update in place, not recreate"
        assert q1.type == "multiple_choice"
        assert q1.annotation == "Updated Q1"
        assert q1.weight == 5
        assert q1.translations == {"fr": {"text": "Q1 mis à jour"}}

    def test_add_new_question(self, requirement_node):
        self._seed(requirement_node)
        assert requirement_node.questions.count() == 2

        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Original Q1",
                    "choices": [
                        _make_choice("c1", "Alpha"),
                        _make_choice("c2", "Beta"),
                    ],
                },
                "urn:test:sync:q2": {"type": "text", "text": "Original Q2"},
                "urn:test:sync:q3": {"type": "date", "text": "Brand new Q3"},
            },
        )

        assert requirement_node.questions.count() == 3
        q3 = requirement_node.questions.get(urn="urn:test:sync:q3")
        assert q3.type == "date"
        assert q3.annotation == "Brand new Q3"

    def test_remove_stale_question(self, requirement_node):
        self._seed(requirement_node)
        assert requirement_node.questions.count() == 2

        # Only include q1 in the update — q2 should be deleted
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Original Q1",
                    "choices": [
                        _make_choice("c1", "Alpha"),
                        _make_choice("c2", "Beta"),
                    ],
                },
            },
        )

        assert requirement_node.questions.count() == 1
        assert requirement_node.questions.get().urn == "urn:test:sync:q1"
        assert not Question.objects.filter(urn="urn:test:sync:q2").exists()

    def test_remove_all_questions_not_in_incoming(self, requirement_node):
        self._seed(requirement_node)

        # Completely different set of questions
        _sync_questions_from_data(
            requirement_node,
            {"urn:test:sync:q_new": {"type": "text", "text": "Replacement"}},
        )

        assert requirement_node.questions.count() == 1
        assert requirement_node.questions.get().urn == "urn:test:sync:q_new"


@pytest.mark.django_db
class TestSyncChoicesUpdate:
    """Choice-level upsert and pruning within an existing question."""

    def _seed_with_choices(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice("c1", "Alpha", add_score=1),
                        _make_choice("c2", "Beta", add_score=2),
                        _make_choice("c3", "Gamma", add_score=3),
                    ],
                }
            },
        )
        return requirement_node

    def test_update_existing_choice_fields(self, requirement_node):
        self._seed_with_choices(requirement_node)
        q = requirement_node.questions.get()
        c1_pk = q.choices.get(ref_id="c1").pk

        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice(
                            "c1",
                            "Alpha Updated",
                            add_score=99,
                            description="New desc",
                            color="#FF0000",
                        ),
                        _make_choice("c2", "Beta", add_score=2),
                        _make_choice("c3", "Gamma", add_score=3),
                    ],
                }
            },
        )

        q.refresh_from_db()
        c1 = q.choices.get(ref_id="c1")
        assert c1.pk == c1_pk, "Should update in place, not recreate"
        assert c1.annotation == "Alpha Updated"
        assert c1.add_score == 99
        assert c1.description == "New desc"
        assert c1.color == "#FF0000"

    def test_add_new_choice(self, requirement_node):
        self._seed_with_choices(requirement_node)
        q = requirement_node.questions.get()
        assert q.choices.count() == 3

        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice("c1", "Alpha"),
                        _make_choice("c2", "Beta"),
                        _make_choice("c3", "Gamma"),
                        _make_choice("c4", "Delta", add_score=4),
                    ],
                }
            },
        )

        q.refresh_from_db()
        assert q.choices.count() == 4
        c4 = q.choices.get(ref_id="c4")
        assert c4.annotation == "Delta"
        assert c4.add_score == 4

    def test_remove_stale_choice(self, requirement_node):
        self._seed_with_choices(requirement_node)
        q = requirement_node.questions.get()

        # Remove c2 and c3 from incoming
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [_make_choice("c1", "Alpha")],
                }
            },
        )

        q.refresh_from_db()
        assert q.choices.count() == 1
        assert q.choices.get().ref_id == "c1"
        assert not QuestionChoice.objects.filter(ref_id="c2").exists()
        assert not QuestionChoice.objects.filter(ref_id="c3").exists()

    def test_choice_ordering_updated(self, requirement_node):
        self._seed_with_choices(requirement_node)

        # Reverse the choice order
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice("c3", "Gamma"),
                        _make_choice("c2", "Beta"),
                        _make_choice("c1", "Alpha"),
                    ],
                }
            },
        )

        q = requirement_node.questions.get()
        choices = list(q.choices.order_by("order"))
        assert [c.ref_id for c in choices] == ["c3", "c2", "c1"]
        assert [c.order for c in choices] == [0, 1, 2]

    def test_simultaneous_add_update_remove_choices(self, requirement_node):
        self._seed_with_choices(requirement_node)

        # c1: update, c2: remove, c3: keep, c4: add
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice("c1", "Alpha v2", add_score=100),
                        _make_choice("c3", "Gamma"),
                        _make_choice("c4", "Delta"),
                    ],
                }
            },
        )

        q = requirement_node.questions.get()
        assert q.choices.count() == 3
        assert q.choices.get(ref_id="c1").annotation == "Alpha v2"
        assert q.choices.get(ref_id="c1").add_score == 100
        assert not q.choices.filter(ref_id="c2").exists()
        assert q.choices.get(ref_id="c3").annotation == "Gamma"
        assert q.choices.get(ref_id="c4").annotation == "Delta"


@pytest.mark.django_db
class TestSyncNullRefIdChoices:
    """Choices with no URN (NULL ref_id) use a replace strategy."""

    def test_null_ref_id_choices_replaced_on_sync(self, requirement_node):
        # Seed with two NULL ref_id choices
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        {"urn": "", "value": "Old A"},
                        {"urn": "", "value": "Old B"},
                    ],
                }
            },
        )

        q = requirement_node.questions.get()
        assert q.choices.count() == 2

        # Sync with different NULL ref_id choices
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        {"urn": "", "value": "New X"},
                        {"urn": "", "value": "New Y"},
                        {"urn": "", "value": "New Z"},
                    ],
                }
            },
        )

        q.refresh_from_db()
        assert q.choices.count() == 3
        annotations = set(q.choices.values_list("annotation", flat=True))
        assert annotations == {"New X", "New Y", "New Z"}

    def test_mixed_ref_id_and_null_choices(self, requirement_node):
        # Seed with one ref_id choice and one NULL
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice("c1", "Named"),
                        {"urn": "", "value": "Anon old"},
                    ],
                }
            },
        )

        q = requirement_node.questions.get()
        assert q.choices.count() == 2

        # Update: keep c1, replace anonymous
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "Q1",
                    "choices": [
                        _make_choice("c1", "Named Updated"),
                        {"urn": "", "value": "Anon new"},
                    ],
                }
            },
        )

        q.refresh_from_db()
        assert q.choices.count() == 2
        assert q.choices.get(ref_id="c1").annotation == "Named Updated"
        anon = q.choices.get(ref_id=None)
        assert anon.annotation == "Anon new"


@pytest.mark.django_db
class TestSyncQuestionsConfig:
    """Config and depends_on fields are synced correctly."""

    def test_config_persisted_and_updated(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "number",
                    "text": "Score",
                    "config": {"min": 0, "max": 100},
                }
            },
        )

        q = requirement_node.questions.get()
        assert q.config == {"min": 0, "max": 100}

        # Update config
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "number",
                    "text": "Score",
                    "config": {"min": 1, "max": 50, "step": 5},
                }
            },
        )

        q.refresh_from_db()
        assert q.config == {"min": 1, "max": 50, "step": 5}

    def test_depends_on_persisted_and_updated(self, requirement_node):
        depends_v1 = {"question": "q_parent", "answers": ["c1"], "condition": "any"}

        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "text",
                    "text": "Dep test",
                    "depends_on": depends_v1,
                }
            },
        )

        q = requirement_node.questions.get()
        assert q.depends_on == depends_v1

        depends_v2 = {
            "question": "q_other",
            "answers": ["c2", "c3"],
            "condition": "all",
        }
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "text",
                    "text": "Dep test",
                    "depends_on": depends_v2,
                }
            },
        )

        q.refresh_from_db()
        assert q.depends_on == depends_v2


@pytest.mark.django_db
class TestSyncChoicesComputeResult:
    """compute_result bool→str conversion works during sync updates."""

    def test_compute_result_bool_to_str_on_update(self, requirement_node):
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "CR test",
                    "choices": [
                        _make_choice("c1", "Yes", compute_result="true"),
                    ],
                }
            },
        )

        # Update with bool instead of string
        _sync_questions_from_data(
            requirement_node,
            {
                "urn:test:sync:q1": {
                    "type": "unique_choice",
                    "text": "CR test",
                    "choices": [
                        _make_choice("c1", "Yes", compute_result=False),
                    ],
                }
            },
        )

        q = requirement_node.questions.get()
        assert q.choices.get(ref_id="c1").compute_result == "false"
