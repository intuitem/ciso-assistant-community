"""Regression tests for question and choice translation.

Verifies that get_questions_translated (used by the serializer, Excel exports,
tree helpers, and report generation) returns translated text when a non-default
locale is active, and falls back to default text otherwise.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils.translation import override as translation_override

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
)
from core.serializers import RequirementNodeReadSerializer
from iam.models import Folder


@pytest.fixture
def translated_node(db):
    """RequirementNode with questions and choices that have French translations."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Translation Test FW",
        folder=folder,
        is_published=True,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:trans:req:001",
        ref_id="TR-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )

    q_sc = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:trans:qsc",
        ref_id="TR-QSC",
        text="Pick one color",
        type=Question.Type.UNIQUE_CHOICE,
        order=0,
        folder=folder,
        is_published=True,
        translations={"fr": {"text": "Choisissez une couleur"}},
    )
    c1 = QuestionChoice.objects.create(
        question=q_sc,
        urn="urn:test:trans:choice:sc1",
        ref_id="TR-SC1",
        value="Red",
        description="A red choice",
        order=0,
        folder=folder,
        is_published=True,
        translations={"fr": {"value": "Rouge", "description": "Un choix rouge"}},
    )
    c2 = QuestionChoice.objects.create(
        question=q_sc,
        urn="urn:test:trans:choice:sc2",
        ref_id="TR-SC2",
        value="Blue",
        order=1,
        folder=folder,
        is_published=True,
        translations={"fr": {"value": "Bleu"}},
    )

    q_text = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:trans:qtxt",
        ref_id="TR-QTXT",
        text="Describe your approach",
        type=Question.Type.TEXT,
        order=1,
        folder=folder,
        is_published=True,
        translations={"fr": {"text": "Décrivez votre approche"}},
    )

    perimeter = Perimeter.objects.create(name="Trans Perim", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Trans CA",
        framework=fw,
        folder=folder,
        perimeter=perimeter,
        is_published=True,
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn,
        folder=folder,
    )

    return {
        "rn": rn,
        "fw": fw,
        "ca": ca,
        "ra": ra,
        "q_sc": q_sc,
        "c1": c1,
        "c2": c2,
        "q_text": q_text,
    }


@pytest.mark.django_db
class TestGetQuestionsTranslated:
    """Tests for RequirementNode.get_questions_translated property."""

    def test_returns_french_question_text(self, translated_node):
        rn = translated_node["rn"]
        with translation_override("fr"):
            result = rn.get_questions_translated
        assert result["urn:test:trans:qsc"]["text"] == "Choisissez une couleur"
        assert result["urn:test:trans:qtxt"]["text"] == "Décrivez votre approche"

    def test_returns_french_choice_value(self, translated_node):
        rn = translated_node["rn"]
        with translation_override("fr"):
            result = rn.get_questions_translated
        choices = result["urn:test:trans:qsc"]["choices"]
        assert choices[0]["value"] == "Rouge"
        assert choices[1]["value"] == "Bleu"

    def test_returns_french_choice_description(self, translated_node):
        rn = translated_node["rn"]
        with translation_override("fr"):
            result = rn.get_questions_translated
        choices = result["urn:test:trans:qsc"]["choices"]
        assert choices[0]["description"] == "Un choix rouge"

    def test_falls_back_to_default_when_no_translation(self, translated_node):
        """When language has no translation entry, return the default (English) values."""
        rn = translated_node["rn"]
        with translation_override("de"):
            result = rn.get_questions_translated
        assert result["urn:test:trans:qsc"]["text"] == "Pick one color"
        choices = result["urn:test:trans:qsc"]["choices"]
        assert choices[0]["value"] == "Red"
        assert choices[0]["description"] == "A red choice"

    def test_returns_default_for_english(self, translated_node):
        rn = translated_node["rn"]
        with translation_override("en"):
            result = rn.get_questions_translated
        assert result["urn:test:trans:qsc"]["text"] == "Pick one color"
        assert result["urn:test:trans:qtxt"]["text"] == "Describe your approach"
        choices = result["urn:test:trans:qsc"]["choices"]
        assert choices[0]["value"] == "Red"

    def test_returns_none_for_no_questions(self, db):
        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name="Empty Trans FW", folder=folder, is_published=True
        )
        rn = RequirementNode.objects.create(
            framework=fw,
            urn="urn:test:trans:empty",
            ref_id="TR-EMPTY",
            assessable=True,
            folder=folder,
            is_published=True,
        )
        with translation_override("fr"):
            assert rn.get_questions_translated is None


@pytest.mark.django_db
class TestRequirementNodeSerializerTranslation:
    """Tests that the RequirementNodeReadSerializer returns translated questions."""

    def test_serializer_returns_french_questions(self, translated_node):
        rn = translated_node["rn"]
        with translation_override("fr"):
            serializer = RequirementNodeReadSerializer(rn)
            data = serializer.data
        questions = data["questions"]
        assert questions["urn:test:trans:qsc"]["text"] == "Choisissez une couleur"
        choices = questions["urn:test:trans:qsc"]["choices"]
        assert choices[0]["value"] == "Rouge"

    def test_serializer_returns_english_by_default(self, translated_node):
        rn = translated_node["rn"]
        with translation_override("en"):
            serializer = RequirementNodeReadSerializer(rn)
            data = serializer.data
        questions = data["questions"]
        assert questions["urn:test:trans:qsc"]["text"] == "Pick one color"
        choices = questions["urn:test:trans:qsc"]["choices"]
        assert choices[0]["value"] == "Red"


@pytest.mark.django_db
class TestQuestionsTranslatedPrefetchCache:
    """Verify `get_questions_translated` honours the parent queryset's
    prefetch cache for `questions__choices`.

    Before the fix, the property called
    `self.questions.prefetch_related("choices").all()` unconditionally,
    which builds a fresh queryset and bypasses any cache populated by
    the caller — so list serialisation paid 1-2 queries per requirement
    node (N+1).

    The fix uses the prefetched cache when available and falls back to
    the in-property prefetch otherwise. These tests pin both:
      - output equivalence between the cached and uncached path,
      - query count drops to zero when prefetch is present.
    """

    def test_output_matches_uncached_path(self, translated_node):
        """Same node, two access paths (with and without prefetch).
        Output must be identical."""
        rn = translated_node["rn"]
        # Uncached path: hit the property on the model instance directly.
        with translation_override("en"):
            uncached = rn.get_questions_translated

        # Cached path: re-fetch via a queryset that prefetches
        # questions__choices, then read the property.
        rn_cached = RequirementNode.objects.prefetch_related("questions__choices").get(
            pk=rn.pk
        )
        with translation_override("en"):
            cached = rn_cached.get_questions_translated

        assert cached == uncached

    def test_no_queries_when_prefetched(self, translated_node):
        """With prefetch, accessing the property must not hit the DB."""
        rn_cached = RequirementNode.objects.prefetch_related("questions__choices").get(
            pk=translated_node["rn"].pk
        )
        with CaptureQueriesContext(connection) as ctx:
            with translation_override("en"):
                _ = rn_cached.get_questions_translated
        # Zero DB hits — the prefetch cache supplies both questions and
        # their choices.
        assert len(ctx.captured_queries) == 0, [q["sql"] for q in ctx.captured_queries]

    def test_queries_when_not_prefetched(self, translated_node):
        """Without prefetch, the property still works (fallback path)."""
        rn = RequirementNode.objects.get(pk=translated_node["rn"].pk)
        with CaptureQueriesContext(connection) as ctx:
            with translation_override("en"):
                _ = rn.get_questions_translated
        # Non-zero — proves we're not relying on a stale cache.
        assert len(ctx.captured_queries) > 0

    def test_falls_back_when_questions_prefetched_without_choices(
        self, translated_node
    ):
        """If the caller prefetches `questions` but NOT
        `questions__choices`, using the cached questions and then
        accessing `question.choices.all()` per row would N+1. The guard
        must detect the missing `choices` cache and fall back to the
        in-property `prefetch_related("choices")` so the work stays
        bounded."""
        rn_partial = RequirementNode.objects.prefetch_related("questions").get(
            pk=translated_node["rn"].pk
        )
        with CaptureQueriesContext(connection) as ctx:
            with translation_override("en"):
                result = rn_partial.get_questions_translated
        assert result is not None
        # Fallback path runs `self.questions.prefetch_related("choices").all()` —
        # 2 queries (questions + choices via IN), not 1 + N.
        assert len(ctx.captured_queries) <= 2, [
            q["sql"][:120] for q in ctx.captured_queries
        ]
