from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from core.models import Actor, AppliedControl
from crq.models import (
    QuantitativeRiskHypothesis,
    QuantitativeRiskScenario,
    QuantitativeRiskStudy,
)
from iam.models import Folder, RoleAssignment, User


@pytest.fixture
def setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root, name="CRQ Domain", content_type=Folder.ContentType.DOMAIN
    )
    study = QuantitativeRiskStudy.objects.create(name="CRQ study", folder=domain)
    scenario = QuantitativeRiskScenario.objects.create(
        name="Ransomware", quantitative_risk_study=study, folder=domain
    )
    selected = QuantitativeRiskHypothesis.objects.create(
        name="With EDR", quantitative_risk_scenario=scenario, is_selected=True
    )
    discarded = QuantitativeRiskHypothesis.objects.create(
        name="With SOC", quantitative_risk_scenario=scenario, is_selected=False
    )

    admin = User.objects.create_superuser("crq-admin@tests.com")
    owner_actor = Actor.get_all_for_user(admin)[0]

    edr = AppliedControl.objects.create(
        name="EDR", folder=domain, cost={"run": {"fixed_cost": 1200}}
    )
    edr.owner.set([owner_actor])
    selected.added_applied_controls.set([edr])
    soc = AppliedControl.objects.create(
        name="SOC", folder=domain, cost={"run": {"fixed_cost": 99000}}
    )
    discarded.added_applied_controls.set([soc])

    client = APIClient()
    client.force_authenticate(admin)
    return {"study": study, "owner_actor": owner_actor, "client": client}


def budget_url(study):
    return f"/api/crq/quantitative-risk-studies/{study.id}/action-plan/budget-overview/"


def hide_all_actors():
    real = RoleAssignment.get_viewable_object_ids

    def only_non_actors(user, model, folder=None):
        if model is Actor:
            return Actor.objects.none().values_list("id", flat=True)
        return real(user, model, folder)

    return patch.object(
        RoleAssignment, "get_viewable_object_ids", side_effect=only_non_actors
    )


class TestQuantitativeRiskStudyBudgetOverview:
    def test_empty_study_returns_an_empty_overview(self, setup):
        study = QuantitativeRiskStudy.objects.create(
            name="Empty", folder=setup["study"].folder
        )
        res = setup["client"].get(budget_url(study))
        assert res.status_code == 200, res.content
        assert res.json()["count"] == 0

    def test_only_controls_of_selected_hypotheses_are_counted(self, setup):
        res = setup["client"].get(budget_url(setup["study"]))
        assert res.status_code == 200, res.content
        body = res.json()
        assert body["count"] == 1
        assert body["total_annual_cost"] == 1200

    def test_hidden_owners_are_merged_into_one_anonymous_bucket(self, setup):
        label = str(setup["owner_actor"])
        named = setup["client"].get(budget_url(setup["study"])).json()
        assert label in [b["label"] for b in named["top_owners"]]

        with hide_all_actors():
            res = setup["client"].get(budget_url(setup["study"]))

        assert res.status_code == 200, res.content
        assert label not in res.content.decode()
        assert [b["key"] for b in res.json()["top_owners"]] == ["_restricted"]

    def test_a_user_without_access_to_the_study_is_refused(self, setup):
        outsider = User.objects.create_user("crq-outsider@tests.com")
        client = APIClient()
        client.force_authenticate(outsider)
        res = client.get(budget_url(setup["study"]))
        assert res.status_code == 403
