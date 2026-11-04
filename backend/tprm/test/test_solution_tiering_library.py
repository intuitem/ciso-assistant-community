"""The shipped `quick-form-solution-tiering` starter: the vendor tiering method
applied to a solution, so it shares that form's rules and expectations."""

import itertools
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from core.cel_service import (
    evaluate_quick_form_document,
    validate_quick_form_expressions,
)
from core.models import QuickForm, StoredLibrary
from core.quick_form_apply import on_accept_health
from tprm.models import Tier
from tprm.test.test_vendor_tiering_library import CHOICES, _expected_tier
from tprm.tier_target import SolutionTierTarget

LIBRARY = (
    Path(__file__).resolve().parents[2]
    / "library"
    / "libraries"
    / "quick-form-solution-tiering.yaml"
)
URN = "urn:intuitem:risk:library:solution-tiering"
P = "urn:intuitem:risk:qf_page:solution-tiering"


@pytest.fixture(scope="module")
def form() -> dict:
    return yaml.safe_load(LIBRARY.read_text())["objects"]["quick_forms"][0]


def _answers(levels: tuple[int, ...], regulated: str) -> dict:
    answers = {
        f"{P}:context:question:regulated": (
            f"{P}:context:question:regulated:choice:{regulated}"
        )
    }
    for (question, choices), level in zip(CHOICES.items(), levels):
        answers[f"{P}:{question}"] = f"{P}:{question}:choice:{choices[level - 1]}"
    return answers


def test_rules_pass_the_builder_check(form):
    assert validate_quick_form_expressions(form) == []


@pytest.mark.django_db
def test_library_loads_onto_solutions(form):
    stored = StoredLibrary.objects.filter(urn=URN).first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(LIBRARY.read_bytes())
        assert error is None, error
    assert stored.load() is None
    quick_form = QuickForm.objects.get(
        urn="urn:intuitem:risk:quick_form:solution-tiering"
    )
    assert quick_form.subject_question_urn.endswith(":context:question:solution")
    assert [a["target"] for a in quick_form.on_accept] == ["solution.tier"]
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    assert on_accept_health(quick_form)[0]["problems"] == []


def test_french_reaches_every_text(form):
    assert form["translations"]["fr"]["name"] == "Criticité des solutions"
    for page in form["pages"]:
        assert page["translations"]["fr"]["name"]
        for question in page["questions"].values():
            assert question["translations"]["fr"]["text"]
            for choice in question.get("choices") or []:
                assert choice["translations"]["fr"]["value"]


@pytest.mark.django_db
def test_every_combination_matches_the_rules(form):
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    config = form["on_accept"][0]["config"]
    target = SolutionTierTarget()
    mismatches = []
    for levels in itertools.product(range(1, 5), repeat=len(CHOICES)):
        for regulated in ("no", "yes"):
            result = evaluate_quick_form_document(form, _answers(levels, regulated))
            proposal = target.resolve(
                SimpleNamespace(
                    computed_values=result["computed_values"],
                    computed_outcome=result["computed_outcome"],
                ),
                config,
            )
            expected = _expected_tier(levels, regulated)
            if not proposal.ok or proposal.display != expected:
                mismatches.append((levels, regulated, expected, proposal.display))
    assert not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}"
