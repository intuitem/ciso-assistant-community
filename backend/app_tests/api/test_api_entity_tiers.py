import pytest
from rest_framework import status

from api.test_utils import EndpointTestsUtils
from iam.models import Folder
from tprm.models import Entity, EntityTierChange, Tier, TierSource
from tprm.tiers import set_entity_tier

TIERS_URL = "/api/tiers/"
ENTITIES_URL = "/api/entities/"


def _tier(name):
    return Tier.objects.get(name=name)


@pytest.fixture
def entity(authenticated_client):
    folder = Folder.objects.create(
        name="tier-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    return Entity.objects.create(name="Acme", folder=folder)


@pytest.mark.django_db
class TestTierScale:
    def test_default_scale_is_seeded_most_critical_first(self, authenticated_client):
        response = authenticated_client.get(TIERS_URL)
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert [t["name"] for t in results] == ["critical", "high", "medium", "low"]
        assert [t["rank"] for t in results] == [4, 3, 2, 1]
        assert all(t["builtin"] for t in results)

    def test_reseeding_keeps_the_organisation_scale(self, authenticated_client):
        high = _tier("high")
        high.name = "Important"
        high.save()
        Tier.objects.filter(name="medium").update(is_visible=False)

        Tier.create_default_tiers()

        assert Tier.objects.count() == 4
        assert Tier.objects.filter(name="Important").exists()
        assert not Tier.objects.filter(name="high").exists()
        assert not _tier("medium").is_visible

    def test_builtin_tier_can_be_renamed_and_recoloured(self, authenticated_client):
        high = _tier("high")
        response = authenticated_client.patch(
            f"{TIERS_URL}{high.id}/",
            {"name": "Important", "hexcolor": "#000000"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        high.refresh_from_db()
        assert (high.name, high.hexcolor) == ("Important", "#000000")

    def test_new_tiers_go_to_the_bottom_in_entry_order(self, authenticated_client):
        for name in ("Tier A", "Tier B"):
            response = authenticated_client.post(
                TIERS_URL, {"name": name}, format="json"
            )
            assert response.status_code == status.HTTP_201_CREATED, response.json()
        assert list(Tier.objects.order_by("-rank").values_list("name", flat=True)) == [
            "critical",
            "high",
            "medium",
            "low",
            "Tier A",
            "Tier B",
        ]
        assert list(Tier.objects.order_by("-rank").values_list("rank", flat=True)) == [
            6,
            5,
            4,
            3,
            2,
            1,
        ]

    def test_duplicate_rank_is_refused(self, authenticated_client):
        response = authenticated_client.post(
            TIERS_URL, {"name": "Vital", "rank": 2}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reorder_renumbers_every_tier(self, authenticated_client):
        order = [_tier(n).id for n in ["low", "critical", "high", "medium"]]
        response = authenticated_client.post(
            f"{TIERS_URL}reorder/", {"ids": [str(i) for i in order]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        assert [t["name"] for t in response.json()] == [
            "low",
            "critical",
            "high",
            "medium",
        ]
        assert _tier("low").rank == 4
        assert _tier("medium").rank == 1

    def test_reorder_refuses_a_partial_list(self, authenticated_client):
        response = authenticated_client.post(
            f"{TIERS_URL}reorder/", {"ids": [str(_tier("low").id)]}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _tier("low").rank == 1

    def test_reorder_refuses_a_non_list_payload(self, authenticated_client):
        for ids in (5, "abc", {"a": 1}):
            response = authenticated_client.post(
                f"{TIERS_URL}reorder/", {"ids": ids}, format="json"
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST, ids

    def test_builtin_tier_cannot_be_deleted(self, authenticated_client):
        response = authenticated_client.delete(f"{TIERS_URL}{_tier('low').id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tier_in_use_cannot_be_deleted(self, authenticated_client, entity):
        custom = Tier.objects.create(name="Vital", rank=Tier.next_rank())
        set_entity_tier(entity, custom)
        response = authenticated_client.delete(f"{TIERS_URL}{custom.id}/")
        assert response.status_code == status.HTTP_409_CONFLICT
        assert Tier.objects.filter(id=custom.id).exists()

    def test_entities_count(self, authenticated_client, entity):
        set_entity_tier(entity, _tier("high"))
        results = authenticated_client.get(TIERS_URL).json()["results"]
        counts = {t["name"]: t["entities_count"] for t in results}
        assert counts == {"critical": 0, "high": 1, "medium": 0, "low": 0}


@pytest.mark.django_db
class TestEntityTier:
    def _patch(self, client, entity, payload):
        return client.patch(f"{ENTITIES_URL}{entity.id}/", payload, format="json")

    def test_setting_a_tier_records_the_change(self, authenticated_client, entity):
        high = _tier("high")
        response = self._patch(
            authenticated_client,
            entity,
            {"tier": str(high.id), "tier_note": "Hosts PII"},
        )
        assert response.status_code == status.HTTP_200_OK, response.json()

        entity.refresh_from_db()
        assert entity.tier == high
        assert entity.tier_source == TierSource.MANUAL
        assert entity.tier_set_at is not None

        change = EntityTierChange.objects.get(entity=entity)
        assert change.tier == high
        assert change.previous_tier is None
        assert change.source == TierSource.MANUAL
        assert change.note == "Hosts PII"
        assert change.changed_by.email == "admin@tests.com"
        assert change.folder == entity.folder

    def test_tier_is_returned_with_rank_and_colour(self, authenticated_client, entity):
        set_entity_tier(entity, _tier("critical"))
        data = authenticated_client.get(f"{ENTITIES_URL}{entity.id}/").json()
        assert data["tier"]["name"] == "critical"
        assert data["tier"]["rank"] == 4
        assert data["tier"]["hexcolor"]
        assert data["tier_source"] == TierSource.MANUAL

    def test_same_tier_again_is_not_a_change(self, authenticated_client, entity):
        high = _tier("high")
        self._patch(authenticated_client, entity, {"tier": str(high.id)})
        self._patch(authenticated_client, entity, {"tier": str(high.id)})
        assert EntityTierChange.objects.filter(entity=entity).count() == 1

    def test_editing_other_fields_leaves_the_tier_alone(
        self, authenticated_client, entity
    ):
        set_entity_tier(entity, _tier("high"))
        self._patch(authenticated_client, entity, {"mission": "Payments"})
        entity.refresh_from_db()
        assert entity.tier == _tier("high")
        assert EntityTierChange.objects.filter(entity=entity).count() == 1

    def test_clearing_the_tier(self, authenticated_client, entity):
        set_entity_tier(entity, _tier("high"))
        response = self._patch(authenticated_client, entity, {"tier": None})
        assert response.status_code == status.HTTP_200_OK, response.json()

        entity.refresh_from_db()
        assert entity.tier is None
        assert entity.tier_source == ""
        assert entity.tier_set_at is None
        latest = EntityTierChange.objects.filter(entity=entity).first()
        assert latest.tier is None
        assert latest.previous_tier == _tier("high")

    def test_source_is_read_only(self, authenticated_client, entity):
        self._patch(
            authenticated_client,
            entity,
            {"tier": str(_tier("low").id), "tier_source": TierSource.ASSESSMENT},
        )
        entity.refresh_from_db()
        assert entity.tier_source == TierSource.MANUAL

    def test_hidden_tier_cannot_be_picked(self, authenticated_client, entity):
        Tier.objects.filter(name="medium").update(is_visible=False)
        response = self._patch(
            authenticated_client, entity, {"tier": str(_tier("medium").id)}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_selectable_offers_the_hidden_current_tier(self, authenticated_client):
        Tier.objects.filter(name="medium").update(is_visible=False)
        medium = _tier("medium")
        names = lambda url: sorted(  # noqa: E731
            t["name"] for t in authenticated_client.get(url).json()["results"]
        )
        # A picker for an entity whose current tier is hidden still offers it,
        # so opening and saving the entity does not clear it.
        assert names(f"{TIERS_URL}?selectable={medium.id}") == [
            "critical",
            "high",
            "low",
            "medium",
        ]
        assert names(f"{TIERS_URL}?selectable=") == ["critical", "high", "low"]
        assert names(f"{TIERS_URL}?selectable=not-a-uuid") == [
            "critical",
            "high",
            "low",
        ]

    def test_hidden_tier_stays_on_entities_that_have_it(
        self, authenticated_client, entity
    ):
        set_entity_tier(entity, _tier("medium"))
        Tier.objects.filter(name="medium").update(is_visible=False)
        response = self._patch(
            authenticated_client,
            entity,
            {"tier": str(_tier("medium").id), "mission": "Payments"},
        )
        assert response.status_code == status.HTTP_200_OK, response.json()

    def test_tier_set_on_creation(self, authenticated_client, entity):
        response = authenticated_client.post(
            ENTITIES_URL,
            {
                "name": "Globex",
                "folder": str(entity.folder_id),
                "tier": str(_tier("low").id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.json()
        created = Entity.objects.get(name="Globex")
        assert created.tier == _tier("low")
        assert EntityTierChange.objects.filter(entity=created).count() == 1

    def test_batch_change_records_each_entity(self, authenticated_client, entity):
        other = Entity.objects.create(name="Initech", folder=entity.folder)
        response = authenticated_client.post(
            f"{ENTITIES_URL}batch-action/",
            {
                "action": "change_field",
                "ids": [str(entity.id), str(other.id)],
                "field": "tier",
                "value": str(_tier("critical").id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        for e in (entity, other):
            e.refresh_from_db()
            assert e.tier == _tier("critical")
            assert EntityTierChange.objects.filter(entity=e).count() == 1

    def test_list_sorts_by_rank_with_untiered_last(self, authenticated_client, entity):
        folder = entity.folder
        low = Entity.objects.create(name="Low one", folder=folder)
        crit = Entity.objects.create(name="Crit one", folder=folder)
        set_entity_tier(low, _tier("low"))
        set_entity_tier(crit, _tier("critical"))

        names = [
            e["name"]
            for e in authenticated_client.get(
                f"{ENTITIES_URL}?folder={folder.id}&ordering=-tier"
            ).json()["results"]
        ]
        assert names == ["Crit one", "Low one", "Acme"]

    def test_filter_by_tier(self, authenticated_client, entity):
        set_entity_tier(entity, _tier("high"))
        Entity.objects.create(name="Untiered", folder=entity.folder)
        results = authenticated_client.get(
            f"{ENTITIES_URL}?folder={entity.folder_id}&tier={_tier('high').id}"
        ).json()["results"]
        assert [e["name"] for e in results] == ["Acme"]

    def test_filter_the_untiered(self, authenticated_client, entity):
        set_entity_tier(entity, _tier("high"))
        Entity.objects.create(name="Untiered", folder=entity.folder)
        base = f"{ENTITIES_URL}?folder={entity.folder_id}"

        untiered = authenticated_client.get(f"{base}&tier=--").json()["results"]
        assert [e["name"] for e in untiered] == ["Untiered"]

        both = authenticated_client.get(
            f"{base}&tier=--&tier={_tier('high').id}"
        ).json()["results"]
        assert sorted(e["name"] for e in both) == ["Acme", "Untiered"]

    def test_history_is_read_only(self, authenticated_client, entity):
        set_entity_tier(entity, _tier("high"))
        response = authenticated_client.get(
            f"/api/entity-tier-changes/?entity={entity.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
        response = authenticated_client.post(
            "/api/entity-tier-changes/",
            {"entity": str(entity.id), "source": "manual"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestTierPermissions:
    @pytest.fixture
    def analyst(self, authenticated_client):
        client, folder, _ = EndpointTestsUtils.get_test_client_and_folder(
            authenticated_client, "BI-UG-ANA", "test"
        )
        return client, folder

    def test_analyst_sets_a_tier_on_an_entity_of_their_domain(self, analyst):
        client, folder = analyst
        entity = Entity.objects.create(name="Acme", folder=folder)
        response = client.patch(
            f"{ENTITIES_URL}{entity.id}/",
            {"tier": str(_tier("high").id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        entity.refresh_from_db()
        assert entity.tier == _tier("high")

    def test_analyst_sees_the_scale(self, analyst):
        client, _ = analyst
        response = client.get(TIERS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 4

    def test_analyst_cannot_edit_the_scale(self, analyst):
        client, _ = analyst
        response = client.patch(
            f"{TIERS_URL}{_tier('high').id}/", {"name": "Nope"}, format="json"
        )
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
        assert _tier("high").name == "high"

    def test_analyst_cannot_reorder(self, analyst):
        client, _ = analyst
        ids = [str(t.id) for t in Tier.objects.order_by("rank")]
        response = client.post(f"{TIERS_URL}reorder/", {"ids": ids}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert _tier("low").rank == 1
