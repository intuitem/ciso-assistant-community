import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    Question,
    QuickForm,
    QuickFormPublication,
    QuickFormResponse,
    StoredLibrary,
    User,
)
from core.quick_form_apply import on_accept_health
from core.utils import apply_answers_dict
from iam.models import Folder, UserGroup
from tprm.models import Entity, Solution, SolutionTierChange, Tier, TierSource
from tprm.testing import seed_four_level_scale

FORM = "urn:test:risk:quick_form:solution-tiering"
PAGE = "urn:test:risk:qf_page:solution-tiering:p"
Q_SOLUTION = f"{PAGE}:question:solution"
Q_RISK = f"{PAGE}:question:risk"

LIBRARY_YAML = f"""
urn: urn:test:risk:library:solution-tiering
locale: en
ref_id: solution-tiering
name: Solution tiering
description: test
copyright: test
version: 1
provider: test
packager: test
objects:
  quick_forms:
    - urn: {FORM}
      ref_id: solution-tiering
      name: Solution tiering
      subject_question_urn: {Q_SOLUTION}
      scores_definition:
        min: 0
        max: 4
        aggregation: sum
      on_accept:
        - target: solution.tier
          config:
            bands:
              thresholds:
                - {{tier: high, min: 3}}
                - {{tier: low}}
      pages:
        - urn: {PAGE}
          ref_id: p
          name: P
          questions:
            {Q_SOLUTION}:
              type: object_reference
              text: Solution
              config:
                model: solution
            {Q_RISK}:
              type: unique_choice
              text: Risk
              choices:
                - urn: {Q_RISK}:choice:one
                  value: One
                  add_score: 1
                - urn: {Q_RISK}:choice:three
                  value: Three
                  add_score: 3
"""


@pytest.fixture
def setup():
    startup(sender=None, **{})
    seed_four_level_scale()
    stored, error = StoredLibrary.store_library_content(LIBRARY_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    form = QuickForm.objects.get(urn=FORM)
    domain = Folder.objects.create(
        name="solution-tiering",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    acme = Entity.objects.create(name="Acme", folder=domain)
    payroll = Solution.objects.create(name="Payroll", provider_entity=acme)
    publication = QuickFormPublication.objects.create(
        name="Tier a solution", quick_form=form, folder=domain
    )
    return {
        "form": form,
        "domain": domain,
        "payroll": payroll,
        "publication": publication,
    }


def _admin():
    user = User.objects.create_user(email="tier-admin@test.local", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return user, client


def _response(setup, risk):
    response = QuickFormResponse.objects.create(
        name="r",
        quick_form=setup["form"],
        folder=setup["domain"],
        publication=setup["publication"],
    )
    response.seed_answers()
    questions = {
        q.urn: q for q in Question.objects.filter(page__quick_form=setup["form"])
    }
    apply_answers_dict(
        "response",
        response,
        questions,
        {
            Q_SOLUTION: [str(setup["payroll"].id)],
            Q_RISK: f"{Q_RISK}:choice:{risk}",
        },
    )
    response.recompute()
    requester, _ = User.objects.get_or_create(email="tier-requester@test.local")
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.SUBMITTED, submitted_by=requester
    )
    response.refresh_from_db()
    return response


@pytest.mark.django_db
class TestSolutionTierTarget:
    def test_config_is_healthy(self, setup):
        assert on_accept_health(setup["form"]) == [
            {"target": "solution.tier", "label": "tier", "problems": []}
        ]

    def test_the_subject_is_the_solution(self, setup):
        response = _response(setup, "one")
        assert response.subject == setup["payroll"]

    def test_accept_sets_the_solution_tier(self, setup):
        user, client = _admin()
        response = _response(setup, "three")
        result = client.post(
            f"/api/quick-form-responses/{response.id}/set-status/",
            {"status": "closed", "resolution": "accepted"},
            format="json",
        )
        assert result.status_code == 200, result.json()
        assert result.json()["on_accept"][0]["applied"]

        payroll = Solution.objects.get(pk=setup["payroll"].pk)
        assert payroll.tier == Tier.objects.get(name="high")
        assert payroll.tier_source == TierSource.ASSESSMENT
        assert payroll.tier_response_id == response.id
        change = SolutionTierChange.objects.get(solution=payroll)
        assert (change.source, change.changed_by) == (TierSource.ASSESSMENT, user)

    def test_assess_options_offer_the_form_for_a_solution(self, setup):
        _user, client = _admin()
        result = client.get(
            "/api/quick-forms/assess-options/",
            {"target": "solution.tier", "subject": str(setup["payroll"].id)},
        )
        assert result.status_code == 200, result.json()
        assert str(setup["form"].id) in [row["id"] for row in result.json()]
