import pytest
from rest_framework import status

from iam.models import Folder
from tprm.models import Entity, EntityTierChange, Solution, Tier, TierSource
from tprm.testing import seed_four_level_scale
from tprm.tiers import set_entity_tier, set_solution_tier

PROPAGATION_URL = "/api/tiers/propagation/"


def _tier(name):
    return Tier.objects.get(name=name)


@pytest.fixture(autouse=True)
def four_level_scale(db):
    seed_four_level_scale()


@pytest.fixture
def acme(authenticated_client):
    folder = Folder.objects.create(
        name="tier-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    return Entity.objects.create(name="Acme", folder=folder)


@pytest.fixture
def payroll(acme):
    return Solution.objects.create(name="Payroll", provider_entity=acme)


def _mode(client, mode):
    response = client.put(PROPAGATION_URL, {"mode": mode}, format="json")
    assert response.status_code == status.HTTP_200_OK, response.json()


@pytest.mark.django_db
class TestTierPropagation:
    def test_mode_defaults_to_off_and_is_validated(self, authenticated_client):
        assert authenticated_client.get(PROPAGATION_URL).json()["mode"] == "off"
        response = authenticated_client.put(
            PROPAGATION_URL, {"mode": "always"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        _mode(authenticated_client, "floor")
        assert authenticated_client.get(PROPAGATION_URL).json()["mode"] == "floor"

    def test_off_leaves_the_entity_alone(self, authenticated_client, acme, payroll):
        set_solution_tier(payroll, _tier("critical"))
        acme.refresh_from_db()
        assert acme.tier is None

    def test_floor_raises_the_entity(self, authenticated_client, acme, payroll):
        _mode(authenticated_client, "floor")
        set_entity_tier(acme, _tier("medium"))
        set_solution_tier(payroll, _tier("critical"))
        acme.refresh_from_db()
        assert (acme.tier, acme.tier_source) == (_tier("critical"), TierSource.ROLLUP)
        change = EntityTierChange.objects.filter(entity=acme).first()
        assert (change.previous_tier, change.note) == (_tier("medium"), "Payroll")

    def test_floor_never_lowers(self, authenticated_client, acme, payroll):
        _mode(authenticated_client, "floor")
        set_entity_tier(acme, _tier("critical"))
        set_solution_tier(payroll, _tier("low"))
        acme.refresh_from_db()
        assert acme.tier == _tier("critical")

    def test_manual_below_the_floor_stays_until_a_solution_event(
        self, authenticated_client, acme, payroll
    ):
        _mode(authenticated_client, "floor")
        set_solution_tier(payroll, _tier("high"))
        authenticated_client.patch(
            f"/api/entities/{acme.id}/",
            {"tier": str(_tier("medium").id)},
            format="json",
        )
        acme.refresh_from_db()
        assert acme.tier == _tier("medium")
        assert authenticated_client.get(f"/api/entities/{acme.id}/").json()[
            "tier_floor"
        ]["tier"]["id"] == str(_tier("high").id)

        other = Solution.objects.create(
            name="Badges", provider_entity=acme, is_active=False
        )
        set_solution_tier(other, _tier("high"))
        acme.refresh_from_db()
        assert acme.tier == _tier("high")

    def test_inactive_solutions_do_not_count(self, authenticated_client, acme, payroll):
        _mode(authenticated_client, "floor")
        payroll.is_active = False
        payroll.save()
        set_solution_tier(payroll, _tier("critical"))
        acme.refresh_from_db()
        assert acme.tier is None

    def test_reactivating_a_solution_raises(self, authenticated_client, acme, payroll):
        payroll.is_active = False
        payroll.save()
        set_solution_tier(payroll, _tier("critical"))
        _mode(authenticated_client, "floor")
        response = authenticated_client.patch(
            f"/api/solutions/{payroll.id}/", {"is_active": True}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        acme.refresh_from_db()
        assert acme.tier == _tier("critical")

    def test_suggest_only_reports(self, authenticated_client, acme, payroll):
        _mode(authenticated_client, "suggest")
        set_solution_tier(payroll, _tier("critical"))
        acme.refresh_from_db()
        assert acme.tier is None
        floor = authenticated_client.get(f"/api/entities/{acme.id}/").json()[
            "tier_floor"
        ]
        assert floor["mode"] == "suggest"
        assert floor["solution"]["str"] == "Payroll"

    def test_no_floor_when_off_or_already_above(
        self, authenticated_client, acme, payroll
    ):
        set_solution_tier(payroll, _tier("medium"))
        url = f"/api/entities/{acme.id}/"
        assert authenticated_client.get(url).json()["tier_floor"] is None
        _mode(authenticated_client, "suggest")
        set_entity_tier(acme, _tier("critical"))
        assert authenticated_client.get(url).json()["tier_floor"] is None

    def test_switching_to_floor_raises_the_vendors_below_it(
        self, authenticated_client, acme, payroll
    ):
        set_solution_tier(payroll, _tier("high"))
        set_entity_tier(acme, _tier("low"))
        above = Entity.objects.create(name="Above", folder=acme.folder)
        set_entity_tier(above, _tier("critical"))
        Solution.objects.create(name="Mail", provider_entity=above, tier=_tier("low"))
        assert authenticated_client.get(PROPAGATION_URL).json()["below_floor"] == 1

        response = authenticated_client.put(
            PROPAGATION_URL, {"mode": "floor"}, format="json"
        )
        assert response.json() == {"mode": "floor", "below_floor": 0, "raised": 1}
        acme.refresh_from_db()
        above.refresh_from_db()
        assert (acme.tier, acme.tier_source) == (_tier("high"), TierSource.ROLLUP)
        assert above.tier == _tier("critical")

        set_entity_tier(acme, _tier("low"))
        response = authenticated_client.put(
            PROPAGATION_URL, {"mode": "floor"}, format="json"
        )
        assert response.json()["raised"] == 0

    def test_import_path_does_not_propagate(self, authenticated_client, acme, payroll):
        _mode(authenticated_client, "floor")
        set_entity_tier(acme, _tier("low"))
        set_solution_tier(payroll, _tier("critical"), propagate=False)
        acme.refresh_from_db()
        assert acme.tier == _tier("low")

    def test_applying_the_suggested_floor_records_a_rollup(
        self, authenticated_client, acme, payroll
    ):
        _mode(authenticated_client, "suggest")
        set_solution_tier(payroll, _tier("high"))
        response = authenticated_client.patch(
            f"/api/entities/{acme.id}/", {"apply_tier_floor": True}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        acme.refresh_from_db()
        assert (acme.tier, acme.tier_source) == (_tier("high"), TierSource.ROLLUP)
        change = EntityTierChange.objects.filter(entity=acme).first()
        assert (change.source, change.note) == (TierSource.ROLLUP, "Payroll")
        assert change.changed_by is not None
