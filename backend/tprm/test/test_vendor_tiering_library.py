"""The shipped `quick-form-vendor-tiering` starter: each dimension is the mean
of its three 1-4 answers, the inherent risk is the higher of the two, banded on
the default scale Critical >= 3.3 / Important >= 2.6 / Standard >= 2.0 /
Low impact, and four answers act as floors (regulated function and single point of failure to
Critical, special-category data and privileged access to Important).

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
    / "quick-form-vendor-tiering.yaml"
)
P = "urn:intuitem:risk:qf_page:vendor-tiering"
CHOICES = {
    "business:question:b1": ["negligible", "workaround", "disruption", "stops"],
    "business:question:b2": ["month", "weeks", "days", "hours"],
    "business:question:b3": ["easy", "weeks", "months", "sole"],
    "data:question:d1": ["public", "internal", "confidential", "special"],
    "data:question:d2": ["none", "small", "medium", "large"],
    "data:question:d3": ["none", "portal", "integration", "privileged"],
}
RANKS = {"low-impact": 1, "standard": 2, "important": 3, "critical": 4}


@pytest.fixture(scope="module")
def form() -> dict:
    return yaml.safe_load(LIBRARY.read_text())["objects"]["quick_forms"][0]


def _config(form) -> dict:
    return form["on_accept"][0]["config"]


def _expected_tier(levels: tuple[int, ...], regulated: str) -> str:
    b1, b2, b3, d1, d2, d3 = levels
    inherent = max((b1 + b2 + b3) / 3, (d1 + d2 + d3) / 3)
    if inherent >= 10 / 3:
        tier = "critical"
    elif inherent >= 8 / 3:
        tier = "important"
    elif inherent >= 2:
        tier = "standard"
    else:
        tier = "low-impact"
    floors = []
    if regulated == "yes" or (b1 == 4 and b3 == 4):
        floors.append("critical")
    if d1 == 4 or d3 == 4:
        floors.append("important")
    return max([tier, *floors], key=RANKS.__getitem__)


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
def test_library_loads(form):
    # Shipped libraries are stored at setup; storing it again is refused.
    stored = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:vendor-tiering"
    ).first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(LIBRARY.read_bytes())
        assert error is None, error
    assert stored.load() is None
    quick_form = QuickForm.objects.get(
        urn="urn:intuitem:risk:quick_form:vendor-tiering"
    )
    assert quick_form.subject_question_urn.endswith(":context:question:vendor")
    assert list(
        quick_form.pages.order_by("order").values_list("aggregation", flat=True)
    ) == ["sum", "mean", "mean"]
    assert quick_form.on_accept == [{"target": "entity.tier", "config": _config(form)}]
    # Every tier it names is on the default scale.
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    assert on_accept_health(quick_form)[0]["problems"] == []


@pytest.mark.django_db
def test_every_combination_matches_the_rules(form):
    Tier.objects.all().delete()
    Tier.create_default_tiers()
    config = _config(form)
    target = EntityTierTarget()
    mismatches = []
    count = 0
    for levels in itertools.product(range(1, 5), repeat=len(CHOICES)):
        # The regulated answer only adds a floor, so "unsure" and "no" share a
        # path; both are still checked against the all-ones and all-fours ends.
        extremes = set(levels) <= {1} or set(levels) <= {4}
        for regulated in ("no", "yes", "unsure") if extremes else ("no", "yes"):
            count += 1
            result = evaluate_quick_form_document(form, _answers(levels, regulated))
            response = SimpleNamespace(
                computed_values=result["computed_values"],
                computed_outcome=result["computed_outcome"],
            )
            proposal = target.resolve(response, config)
            expected = _expected_tier(levels, regulated)
            if not proposal.ok or proposal.display != expected:
                mismatches.append(
                    (levels, regulated, expected, proposal.display or proposal.reason)
                )
    assert count == 2 * 4**6 + 2
    assert not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}"


def test_unsure_flags_without_raising(form):
    result = evaluate_quick_form_document(form, _answers((1,) * 6, "unsure"))
    fired = result["computed_outcome"]
    assert "regulated_unsure" in fired
    assert "regulated_function" not in fired
