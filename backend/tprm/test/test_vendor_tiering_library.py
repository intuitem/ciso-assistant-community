"""The shipped `quick-form-vendor-risk-tiering` library against the source
workbook ("Supplier risk framework"): per category the highest rung answered
Yes, the tier from the average of the five (<= 1.5 / 2.5 / 3.5), and Yes to
"critical data like PII, PCI, PHI" as a knock-out to Critical.

The tier goes through the real `entity.tier` resolution, with the publication
setup the library's annotation documents."""

import itertools
import random
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from core.cel_service import (
    evaluate_quick_form_document,
    validate_quick_form_expressions,
)
from core.models import QuickForm, StoredLibrary
from tprm.models import Tier
from tprm.tier_target import EntityTierTarget

LIBRARY = (
    Path(__file__).resolve().parents[2]
    / "library"
    / "libraries"
    / "quick-form-vendor-risk-tiering.yaml"
)
CATEGORIES = [
    "data_access",
    "network_access",
    "compliance_level",
    "business_impact",
    "potential_equivalent_loss",
]
P = "urn:intuitem:risk:qf_page:vendor-risk-tiering"


@pytest.fixture(scope="module")
def form() -> dict:
    return yaml.safe_load(LIBRARY.read_text())["objects"]["quick_forms"][0]


def _config():
    tier = {t.name: str(t.id) for t in Tier.objects.all()}
    return {
        "bands": {
            "outcome": "average",
            "thresholds": [
                {"tier": tier["critical"], "min": 3.6},
                {"tier": tier["high"], "min": 2.6},
                {"tier": tier["medium"], "min": 1.6},
                {"tier": tier["low"]},
            ],
        },
        "mapping": [{"outcome": "critical_data", "tier": tier["critical"]}],
    }


def _workbook_tier(yes: dict[str, set[int]]) -> str:
    average = sum(max(yes[c], default=0) for c in CATEGORIES) / len(CATEGORIES)
    if 4 in yes["data_access"]:
        return "critical"
    for limit, name in ((1.5, "low"), (2.5, "medium"), (3.5, "high")):
        if average <= limit:
            return name
    return "critical"


def _answers(yes: dict[str, set[int]]) -> dict:
    return {
        f"{P}:{c}:question:q{r}": (
            f"{P}:{c}:question:q{r}:choice:{'yes' if r in yes[c] else 'no'}"
        )
        for c in CATEGORIES
        for r in range(1, 5)
    }


def _scenarios():
    for levels in itertools.product(range(5), repeat=len(CATEGORIES)):
        yield {c: ({lv} if lv else set()) for c, lv in zip(CATEGORIES, levels)}
    rng = random.Random(306)
    for _ in range(300):
        yield {c: {r for r in range(1, 5) if rng.random() < 0.4} for c in CATEGORIES}


def test_rules_pass_the_builder_check(form):
    assert validate_quick_form_expressions(form) == []


@pytest.mark.django_db
def test_library_loads():
    # Shipped libraries are stored at setup; storing it again is refused.
    stored = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:vendor-risk-tiering"
    ).first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(LIBRARY.read_bytes())
        assert error is None, error
    assert stored.load() is None
    quick_form = QuickForm.objects.get(
        urn="urn:intuitem:risk:quick_form:vendor-risk-tiering"
    )
    assert quick_form.subject_question_urn.endswith(":vendor:question:vendor")
    assert (
        list(quick_form.pages.order_by("order").values_list("aggregation", flat=True))
        == ["sum"] + ["max"] * 5
    )


@pytest.mark.django_db
def test_every_scenario_matches_the_workbook(form):
    Tier.create_default_tiers()
    config = _config()
    target = EntityTierTarget()
    mismatches = []
    count = 0
    for yes in _scenarios():
        count += 1
        result = evaluate_quick_form_document(form, _answers(yes))
        response = SimpleNamespace(
            computed_values=result["computed_values"],
            computed_outcome=result["computed_outcome"],
        )
        proposal = target.resolve(response, config)
        expected = _workbook_tier(yes)
        if not proposal.ok or proposal.display != expected:
            mismatches.append((yes, expected, proposal.display or proposal.reason))
        category_scores = [max(yes[c], default=0) for c in CATEGORIES]
        assert [result["computed_values"][c] for c in CATEGORIES] == category_scores
    assert count == 5**5 + 300
    assert not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}"
