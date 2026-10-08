"""The former 1-4 criticality of entity assessments and solutions, carried
over to the criticality scale; solutions keep a tier of their own."""

import importlib

import pytest
from django.apps import apps
from rest_framework import status

from iam.models import Folder
from tprm.models import Entity, EntityAssessment, EntityTierChange, Solution, Tier
from tprm.tiers import set_entity_tier, tier_for_criticality

carry_over = importlib.import_module(
    "tprm.migrations.0025_criticality_carry_over"
).carry_over

SOLUTIONS_URL = "/api/solutions/"


@pytest.fixture(autouse=True)
def default_scale(db):
    Tier.objects.all().delete()
    Tier.create_default_tiers()


@pytest.fixture
def domain(db):
    return Folder.objects.create(
        name="criticality-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


def _assess(entity, criticality):
    return EntityAssessment.objects.create(
        name=f"EA {criticality}",
        folder=entity.folder,
        entity=entity,
        criticality=criticality,
    )


def _tier(key):
    return Tier.objects.get(key=key)


@pytest.mark.django_db
class TestCarryOver:
    def test_the_highest_assessment_criticality_becomes_the_tier(self, domain):
        acme = Entity.objects.create(name="Acme", folder=domain)
        for criticality in (2, 4, 1):
            _assess(acme, criticality)
        carry_over(apps, None)
        acme.refresh_from_db()
        assert (acme.tier, acme.tier_source) == (_tier("critical"), "manual")
        change = EntityTierChange.objects.get(entity=acme)
        assert change.note == "Set from the highest previous criticality (4)"
        assert change.folder == domain

    def test_an_existing_tier_is_kept(self, domain):
        acme = Entity.objects.create(name="Acme", folder=domain)
        set_entity_tier(acme, _tier("low-impact"))
        _assess(acme, 4)
        carry_over(apps, None)
        acme.refresh_from_db()
        assert acme.tier == _tier("low-impact")

    def test_not_set_means_no_tier(self, domain):
        acme = Entity.objects.create(name="Acme", folder=domain)
        _assess(acme, 0)
        carry_over(apps, None)
        acme.refresh_from_db()
        assert acme.tier is None

    def test_solutions_keep_their_own_value(self, domain):
        acme = Entity.objects.create(name="Acme", folder=domain)
        rated = Solution.objects.create(
            name="Payroll", provider_entity=acme, criticality=3
        )
        unrated = Solution.objects.create(name="Wiki", provider_entity=acme)
        carry_over(apps, None)
        rated.refresh_from_db()
        unrated.refresh_from_db()
        assert (rated.tier, unrated.tier) == (_tier("important"), None)
        # The old value stays where it was, hidden in the UI.
        assert rated.criticality == 3

    def test_seeds_the_default_scale_when_there_is_none(self, domain):
        Tier.objects.all().delete()
        acme = Entity.objects.create(name="Acme", folder=domain)
        Solution.objects.create(name="Payroll", provider_entity=acme, criticality=1)
        carry_over(apps, None)
        assert list(Tier.objects.values_list("key", flat=True)) == [
            "critical",
            "important",
            "standard",
            "low-impact",
        ]
        assert Solution.objects.get(name="Payroll").tier == _tier("low-impact")


@pytest.mark.django_db
class TestSolutionTier:
    def test_set_read_and_filter(self, authenticated_client, domain):
        acme = Entity.objects.create(name="Acme", folder=domain)
        payroll = Solution.objects.create(name="Payroll", provider_entity=acme)
        Solution.objects.create(name="Wiki", provider_entity=acme)
        result = authenticated_client.patch(
            f"{SOLUTIONS_URL}{payroll.id}/",
            {"tier": str(_tier("critical").id)},
            format="json",
        )
        assert result.status_code == status.HTTP_200_OK, result.json()
        read = authenticated_client.get(f"{SOLUTIONS_URL}{payroll.id}/").json()
        assert read["tier"]["key"] == "critical"

        def names(tier):
            rows = authenticated_client.get(SOLUTIONS_URL, {"tier": tier}).json()
            return {r["name"] for r in rows["results"]}

        assert names(str(_tier("critical").id)) == {"Payroll"}
        assert "Wiki" in names("--") and "Payroll" not in names("--")

    def test_a_hidden_tier_is_not_picked_anew(self, authenticated_client, domain):
        acme = Entity.objects.create(name="Acme", folder=domain)
        payroll = Solution.objects.create(name="Payroll", provider_entity=acme)
        Tier.objects.filter(key="standard").update(is_visible=False)
        result = authenticated_client.patch(
            f"{SOLUTIONS_URL}{payroll.id}/",
            {"tier": str(_tier("standard").id)},
            format="json",
        )
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    def test_a_tier_in_use_by_a_solution_cannot_be_deleted(
        self, authenticated_client, domain
    ):
        custom = Tier.objects.create(name="Vital", rank=9)
        acme = Entity.objects.create(name="Acme", folder=domain)
        Solution.objects.create(name="Payroll", provider_entity=acme, tier=custom)
        listed = next(
            t
            for t in authenticated_client.get("/api/tiers/").json()["results"]
            if t["id"] == str(custom.id)
        )
        assert listed["solutions_count"] == 1
        result = authenticated_client.delete(f"/api/tiers/{custom.id}/")
        assert result.status_code == status.HTTP_409_CONFLICT
        assert result.json() == {"error": "tierInUseCannotDelete"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "value,key",
    [(4, "critical"), ("3", "important"), (1, "low-impact"), (0, None), ("x", None)],
)
def test_import_maps_the_former_criticality(value, key):
    tier = tier_for_criticality(value)
    assert (tier.key if tier else None) == key
