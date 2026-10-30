import importlib

import pytest
from django.apps import apps
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from iam.models import Folder, RoleAssignment
from tprm.models import Entity, Solution, SolutionTierChange, Tier, TierSource
from tprm.testing import seed_four_level_scale
from tprm.tiers import set_solution_tier

TIERS_URL = "/api/tiers/"
SOLUTIONS_URL = "/api/solutions/"
HISTORY_URL = "/api/solution-tier-changes/"


def _tier(name):
    return Tier.objects.get(name=name)


@pytest.fixture(autouse=True)
def four_level_scale(db):
    seed_four_level_scale()


@pytest.fixture
def solution(authenticated_client):
    folder = Folder.objects.create(
        name="tier-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    acme = Entity.objects.create(name="Acme", folder=folder)
    return Solution.objects.create(name="Payroll", provider_entity=acme)


@pytest.mark.django_db
class TestSolutionTier:
    def test_setting_a_tier_records_the_change(self, authenticated_client, solution):
        response = authenticated_client.patch(
            f"{SOLUTIONS_URL}{solution.id}/",
            {"tier": str(_tier("high").id), "tier_note": "Payroll data"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        solution.refresh_from_db()
        assert solution.tier == _tier("high")
        assert solution.tier_source == TierSource.MANUAL
        assert solution.tier_set_at is not None
        change = SolutionTierChange.objects.get(solution=solution)
        assert (change.tier, change.previous_tier, change.note) == (
            _tier("high"),
            None,
            "Payroll data",
        )
        assert (
            RoleAssignment.get_iam_folder_id(change)
            == solution.provider_entity.folder_id
        )

    def test_same_tier_again_is_not_a_change(self, authenticated_client, solution):
        set_solution_tier(solution, _tier("high"))
        authenticated_client.patch(
            f"{SOLUTIONS_URL}{solution.id}/",
            {"tier": str(_tier("high").id), "name": "Payroll v2"},
            format="json",
        )
        assert SolutionTierChange.objects.filter(solution=solution).count() == 1

    def test_clearing_the_tier(self, authenticated_client, solution):
        set_solution_tier(solution, _tier("high"))
        response = authenticated_client.patch(
            f"{SOLUTIONS_URL}{solution.id}/", {"tier": None}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        solution.refresh_from_db()
        assert (solution.tier, solution.tier_source, solution.tier_set_at) == (
            None,
            "",
            None,
        )
        assert SolutionTierChange.objects.filter(solution=solution).count() == 2

    def test_source_is_read_only(self, authenticated_client, solution):
        authenticated_client.patch(
            f"{SOLUTIONS_URL}{solution.id}/",
            {"tier_source": TierSource.ASSESSMENT},
            format="json",
        )
        solution.refresh_from_db()
        assert solution.tier_source == ""

    def test_hidden_tier_cannot_be_picked(self, authenticated_client, solution):
        Tier.objects.filter(name="medium").update(is_visible=False)
        response = authenticated_client.patch(
            f"{SOLUTIONS_URL}{solution.id}/",
            {"tier": str(_tier("medium").id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_tier_set_on_creation(self, authenticated_client, solution):
        response = authenticated_client.post(
            SOLUTIONS_URL,
            {
                "name": "Badges",
                "provider_entity": str(solution.provider_entity_id),
                "tier": str(_tier("low").id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.json()
        created = Solution.objects.get(name="Badges")
        assert created.tier == _tier("low")
        assert SolutionTierChange.objects.filter(solution=created).count() == 1

    def test_batch_change_records_each_solution(self, authenticated_client, solution):
        other = Solution.objects.create(
            name="Badges", provider_entity=solution.provider_entity
        )
        response = authenticated_client.post(
            f"{SOLUTIONS_URL}batch-action/",
            {
                "action": "change_field",
                "ids": [str(solution.id), str(other.id)],
                "field": "tier",
                "value": str(_tier("critical").id),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.json()
        for s in (solution, other):
            s.refresh_from_db()
            assert s.tier == _tier("critical")
            assert SolutionTierChange.objects.filter(solution=s).count() == 1

    def test_history_is_listed_and_read_only(self, authenticated_client, solution):
        set_solution_tier(solution, _tier("high"))
        response = authenticated_client.get(HISTORY_URL, {"solution": str(solution.id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
        change = SolutionTierChange.objects.get(solution=solution)
        assert (
            authenticated_client.delete(f"{HISTORY_URL}{change.id}/").status_code
            == status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_history_queries_do_not_grow_with_rows(
        self, authenticated_client, solution
    ):
        def add(count):
            for i in range(count):
                vendor = Entity.objects.create(
                    name=f"Vendor {Entity.objects.count()}",
                    folder=solution.provider_entity.folder,
                )
                other = Solution.objects.create(
                    name=f"Solution {Solution.objects.count()}", provider_entity=vendor
                )
                set_solution_tier(other, _tier("high"))

        def queries():
            with CaptureQueriesContext(connection) as context:
                assert authenticated_client.get(HISTORY_URL).status_code == 200
            return len(context)

        add(2)
        queries()
        few = queries()
        add(8)
        assert queries() == few

    def test_tier_in_the_solution_history_cannot_be_deleted(
        self, authenticated_client, solution
    ):
        custom = Tier.objects.create(name="Vital", rank=Tier.next_rank())
        set_solution_tier(solution, custom)
        set_solution_tier(solution, None)
        response = authenticated_client.delete(f"{TIERS_URL}{custom.id}/")
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"] == "tierInHistoryCannotDelete"


@pytest.mark.django_db
def test_carried_over_tier_history_matches_the_tier_date(solution):
    carry_over = importlib.import_module(
        "tprm.migrations.0027_solution_tier_carry_over"
    ).carry_over
    Solution.objects.filter(pk=solution.pk).update(tier=_tier("high"), tier_source="")
    carry_over(apps, None)
    solution.refresh_from_db()
    change = SolutionTierChange.objects.get(solution=solution)
    assert solution.tier_source == "manual"
    assert change.created_at == solution.tier_set_at == solution.updated_at
