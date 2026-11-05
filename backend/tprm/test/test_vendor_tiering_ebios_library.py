"""The shipped `quick-form-vendor-tiering-ebios-rm` starter: the four EBIOS RM
stakeholder criteria rated 1-4, the threat level dependency × penetration ÷
(maturity × trust), banded on the default scale with the default zones of the
EBIOS RM ecosystem map: Critical >= 2.5 / Important >= 0.9 / Standard >= 0.2 /
Low impact.

The tier goes through the real `entity.tier` resolution, with the setup the
form carries."""

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
from tprm.tier_target import EntityTierTarget

LIBRARY = (
    Path(__file__).resolve().parents[2]
    / "library"
    / "libraries"
    / "quick-form-vendor-tiering-ebios-rm.yaml"
)
URN = "urn:intuitem:risk:library:vendor-tiering-ebios-rm"
P = "urn:intuitem:risk:qf_page:vendor-tiering-ebios-rm"
QUESTIONS = (
    "exposure:question:dependency",
    "exposure:question:penetration",
    "reliability:question:maturity",
    "reliability:question:trust",
)


@pytest.fixture(scope="module")
def form() -> dict:
    return yaml.safe_load(LIBRARY.read_text())["objects"]["quick_forms"][0]


def _answers(levels) -> dict:
    return {
        f"{P}:{question}": f"{P}:{question}:choice:l{level}"
        for question, level in zip(QUESTIONS, levels)
    }


def _expected_tier(levels) -> str:
    dependency, penetration, maturity, trust = levels
    threat = dependency * penetration / (maturity * trust)
    if threat >= 2.5:
        return "critical"
    if threat >= 0.9:
        return "important"
    if threat >= 0.2:
        return "standard"
    return "low-impact"


def _load():
    stored = StoredLibrary.objects.filter(urn=URN).first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(LIBRARY.read_bytes())
        assert error is None, error
    if not stored.is_loaded:
        assert stored.load() is None
    return QuickForm.objects.get(
        urn="urn:intuitem:risk:quick_form:vendor-tiering-ebios-rm"
    )


def test_rules_pass_the_builder_check(form):
    assert validate_quick_form_expressions(form) == []


@pytest.mark.django_db
def test_library_loads_with_a_healthy_setup(form):
    quick_form = _load()
    assert quick_form.subject_question_urn.endswith(":context:question:vendor")
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    assert on_accept_health(quick_form)[0]["problems"] == []


@pytest.mark.django_db
def test_the_guidance_reaches_respondents_in_french(form):
    from django.utils import translation

    for page in form["pages"]:
        assert page["translations"]["fr"]["name"]
        for question in page["questions"].values():
            assert question["translations"]["fr"]["text"]
            for choice in question.get("choices") or []:
                assert choice["description"]
                assert choice["translations"]["fr"]["value"]
                assert choice["translations"]["fr"]["description"]
    page = _load().pages.get(ref_id="exposure")
    with translation.override("fr"):
        dependency = page.get_questions_translated()[f"{P}:{QUESTIONS[0]}"]
    assert dependency["text"].startswith("La relation avec ce fournisseur")
    assert dependency["choices"][3]["value"] == "4 – Indispensable, irremplaçable"
    assert dependency["choices"][3]["description"].startswith(
        "Le lien est indispensable"
    )


def test_the_threat_level_and_levels_are_shown(form):
    result = evaluate_quick_form_document(form, _answers((4, 3, 2, 1)))
    assert result["computed_values"] == {
        "dependency": 4.0,
        "penetration": 3.0,
        "maturity": 2.0,
        "trust": 1.0,
        "threat_level": 6.0,
    }
    assert result["score"] is None


@pytest.mark.django_db
def test_every_combination_matches_the_ebios_zones(form):
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    config = form["on_accept"][0]["config"]
    target = EntityTierTarget()
    mismatches = []
    for levels in itertools.product(range(1, 5), repeat=4):
        result = evaluate_quick_form_document(form, _answers(levels))
        response = SimpleNamespace(
            computed_values=result["computed_values"],
            computed_outcome=result["computed_outcome"],
            score=None,
        )
        proposal = target.resolve(response, config)
        expected = _expected_tier(levels)
        if not proposal.ok or proposal.display != expected:
            mismatches.append((levels, expected, proposal.display or proposal.reason))
    assert not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}"
