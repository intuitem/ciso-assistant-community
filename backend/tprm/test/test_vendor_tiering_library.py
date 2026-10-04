"""The shipped `quick-form-vendor-tiering` starter: each dimension is the mean
of its three 1-4 answers, the inherent risk is the higher of the two, banded
Critical >= 3.3 / High >= 2.6 / Medium >= 2.0 / Low, and four answers act as
floors (regulated function and single point of failure to Critical,
special-category data and privileged access to High).

The tier goes through the real `entity.tier` resolution, with the publication
setup the library suggests."""

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
from core.quick_form_apply import suggested_on_accept
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
RANKS = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@pytest.fixture(scope="module")
def form() -> dict:
    return yaml.safe_load(LIBRARY.read_text())["objects"]["quick_forms"][0]


def _config():
    tier = {t.name: str(t.id) for t in Tier.objects.all()}
    return {
        "bands": {
            "outcome": "inherent",
            "thresholds": [
                {"tier": tier["critical"], "min": 3.3},
                {"tier": tier["high"], "min": 2.6},
                {"tier": tier["medium"], "min": 2.0},
                {"tier": tier["low"]},
            ],
        },
        "mapping": [
            {"outcome": "regulated_function", "tier": tier["critical"]},
            {"outcome": "single_point_of_failure", "tier": tier["critical"]},
            {"outcome": "special_data", "tier": tier["high"]},
            {"outcome": "privileged_access", "tier": tier["high"]},
        ],
    }


def _expected_tier(levels: tuple[int, ...], regulated: str) -> str:
    b1, b2, b3, d1, d2, d3 = levels
    inherent = max((b1 + b2 + b3) / 3, (d1 + d2 + d3) / 3)
    if inherent >= 10 / 3:
        tier = "critical"
    elif inherent >= 8 / 3:
        tier = "high"
    elif inherent >= 2:
        tier = "medium"
    else:
        tier = "low"
    floors = []
    if regulated == "yes" or (b1 == 4 and b3 == 4):
        floors.append("critical")
    if d1 == 4 or d3 == 4:
        floors.append("high")
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
def test_library_loads():
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
    # The suggestion, made concrete on the default scale, is the setup the
    # combinations below are checked against.
    assert suggested_on_accept(quick_form) == [
        {"target": "entity.tier", "config": _config()}
    ]


@pytest.mark.django_db
def test_every_combination_matches_the_rules(form):
    Tier.create_default_tiers()
    config = _config()
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
