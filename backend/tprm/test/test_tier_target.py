"""`entity.tier`: an accepted response sets its vendor's tier through score
bands and/or outcome mapping, highest tier winning."""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    Question,
    QuickForm,
    QuickFormApplication,
    QuickFormPublication,
    QuickFormResponse,
    StoredLibrary,
    User,
)
from core.quick_form_apply import plan, validate_on_accept
from core.utils import apply_answers_dict
from iam.models import Folder, UserGroup
from tprm.models import Entity, EntityTierChange, Tier, TierSource
from tprm.tier_target import EntityTierTarget
from tprm.tiers import set_entity_tier

FORM = "urn:test:risk:quick_form:tiering"
PAGE = "urn:test:risk:qf_page:tiering:p"
Q_VENDOR = f"{PAGE}:question:vendor"
Q_RISK = f"{PAGE}:question:risk"
Q_PII = f"{PAGE}:question:pii"

LIBRARY_YAML = f"""
urn: urn:test:risk:library:tiering
locale: en
ref_id: tiering
name: Tiering
description: test
copyright: test
version: 1
provider: test
packager: test
objects:
  quick_forms:
    - urn: {FORM}
      ref_id: tiering
      name: Tiering
      subject_question_urn: {Q_VENDOR}
      scores_definition:
        min: 0
        max: 4
        aggregation: sum
      outcomes_definition:
        - ref_id: risk
          kind: number
          expression: 'pages["p"].score'
        - ref_id: pii
          expression: '"p:question:pii:choice:yes" in answers["p:question:pii"].selected_choices'
      pages:
        - urn: {PAGE}
          ref_id: p
          name: P
          aggregation: max
          questions:
            {Q_VENDOR}:
              type: object_reference
              text: Vendor
              config:
                model: entity
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
            {Q_PII}:
              type: unique_choice
              text: PII?
              choices:
                - urn: {Q_PII}:choice:yes
                  value: Yes
                - urn: {Q_PII}:choice:no
                  value: No
"""


def _tier(name):
    return Tier.objects.get(name=name)


def _config():
    return {
        "bands": {
            "outcome": "risk",
            "thresholds": [
                {"tier": str(_tier("high").id), "min": 3},
                {"tier": str(_tier("medium").id), "min": 2},
                {"tier": str(_tier("low").id)},
            ],
        },
        "mapping": [{"outcome": "pii", "tier": str(_tier("critical").id)}],
    }


@pytest.fixture
def setup():
    startup(sender=None, **{})
    stored, error = StoredLibrary.store_library_content(LIBRARY_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    form = QuickForm.objects.get(urn=FORM)
    domain = Folder.objects.create(
        name="tiering",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    acme = Entity.objects.create(name="Acme", folder=domain)
    publication = QuickFormPublication.objects.create(
        name="Tier a vendor",
        quick_form=form,
        folder=domain,
        on_accept=[{"target": "entity.tier", "config": _config()}],
    )
    return {"form": form, "domain": domain, "acme": acme, "publication": publication}


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


def _response(setup, risk="three", pii="no"):
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
            Q_VENDOR: [str(setup["acme"].id)],
            Q_RISK: f"{Q_RISK}:choice:{risk}",
            Q_PII: f"{Q_PII}:choice:{pii}",
        },
    )
    response.recompute()
    requester, _ = User.objects.get_or_create(email="tier-requester@test.local")
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.SUBMITTED, submitted_by=requester
    )
    response.refresh_from_db()
    return response


def _accept(client, response, **extra):
    return client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": "accepted", **extra},
        format="json",
    )


@pytest.mark.django_db
class TestConfig:
    def test_valid(self, setup):
        assert (
            validate_on_accept(
                [{"target": "entity.tier", "config": _config()}], setup["form"]
            )
            == []
        )

    def _errors(self, setup, config):
        return EntityTierTarget().validate_config(config, setup["form"])

    def test_needs_bands_or_mapping(self, setup):
        assert self._errors(setup, {}) == ["bandsOrMappingRequired"]

    def test_band_outcome_must_be_numeric(self, setup):
        config = _config()
        config["bands"]["outcome"] = "pii"
        assert "bandsOutcomeNotNumeric" in self._errors(setup, config)

    def test_thresholds_descend(self, setup):
        config = _config()
        config["bands"]["thresholds"] = [
            {"tier": str(_tier("medium").id), "min": 2},
            {"tier": str(_tier("high").id), "min": 3},
        ]
        errors = self._errors(setup, config)
        assert "thresholdsMustDescendByRank" in errors
        assert "thresholdsMustDescendByMin" in errors

    def test_only_the_last_threshold_may_omit_min(self, setup):
        config = _config()
        config["bands"]["thresholds"][0].pop("min")
        assert "thresholdMinRequired" in self._errors(setup, config)

    def test_mapping_needs_a_yes_no_rule_and_a_known_tier(self, setup):
        config = {"mapping": [{"outcome": "risk", "tier": "nope"}]}
        assert self._errors(setup, config) == ["mappingOutcomeUnknown", "unknownTier"]


@pytest.mark.django_db
class TestResolution:
    def _proposal(self, setup, **answers):
        user, _ = _admin()
        return plan(_response(setup, **answers), user)[0]["proposal"]

    def test_band(self, setup):
        proposal = self._proposal(setup, risk="three")
        assert proposal.display == "high"
        assert proposal.value == {"tier": str(_tier("high").id), "value": 3.0}

    def test_lowest_band_catches_the_rest(self, setup):
        assert self._proposal(setup, risk="one").display == "low"

    def test_mapped_outcome_wins_when_higher(self, setup):
        proposal = self._proposal(setup, risk="one", pii="yes")
        assert proposal.display == "critical"
        # The band did not produce the winning tier, so no value is kept.
        assert proposal.value["value"] is None

    def test_nothing_resolved_writes_nothing(self, setup):
        config = {"mapping": [{"outcome": "pii", "tier": str(_tier("critical").id)}]}
        QuickFormPublication.objects.filter(pk=setup["publication"].pk).update(
            on_accept=[{"target": "entity.tier", "config": config}]
        )
        assert self._proposal(setup).reason == "noTierResolved"


@pytest.mark.django_db
class TestAccept:
    def test_accept_sets_the_tier(self, setup):
        user, client = _admin()
        response = _response(setup, risk="three")
        result = _accept(client, response)
        assert result.status_code == 200, result.json()
        assert result.json()["on_accept"][0]["applied"]

        acme = Entity.objects.get(pk=setup["acme"].pk)
        assert acme.tier == _tier("high")
        assert acme.tier_source == TierSource.ASSESSMENT
        assert acme.tier_value == 3.0
        assert acme.tier_response_id == response.id
        change = EntityTierChange.objects.get(entity=acme)
        assert (change.source, change.value, change.response_id) == (
            TierSource.ASSESSMENT,
            3.0,
            response.id,
        )
        assert change.changed_by == user

    def test_override_with_a_note(self, setup):
        _user, client = _admin()
        response = _response(setup, risk="one")
        result = _accept(
            client,
            response,
            overrides={
                "entity.tier": {
                    "tier": str(_tier("critical").id),
                    "note": "Single supplier",
                }
            },
        )
        assert result.status_code == 200, result.json()
        acme = Entity.objects.get(pk=setup["acme"].pk)
        assert acme.tier == _tier("critical")
        assert acme.tier_source == TierSource.OVERRIDE
        assert acme.tier_value is None
        assert EntityTierChange.objects.get(entity=acme).note == "Single supplier"
        assert QuickFormApplication.objects.get(response=response).overridden

    def test_override_without_a_note_is_refused(self, setup):
        _user, client = _admin()
        response = _response(setup)
        result = _accept(
            client,
            response,
            overrides={"entity.tier": {"tier": str(_tier("critical").id)}},
        )
        assert result.status_code == 400
        assert result.json()["reason"] == "noteRequired"

    def test_override_to_a_hidden_tier_is_refused(self, setup):
        _user, client = _admin()
        Tier.objects.filter(name="critical").update(is_visible=False)
        result = _accept(
            client,
            _response(setup),
            overrides={"entity.tier": {"tier": str(_tier("critical").id), "note": "x"}},
        )
        assert result.status_code == 400
        assert result.json()["reason"] == "unknownTier"

    def test_an_assessment_confirming_the_tier_is_recorded(self, setup):
        _user, client = _admin()
        set_entity_tier(setup["acme"], _tier("high"))
        _accept(client, _response(setup, risk="three"))
        acme = Entity.objects.get(pk=setup["acme"].pk)
        assert acme.tier_source == TierSource.ASSESSMENT
        assert EntityTierChange.objects.filter(entity=acme).count() == 2

    def test_a_manual_change_clears_the_assessment_link(self, setup):
        _user, client = _admin()
        _accept(client, _response(setup, risk="three"))
        client.patch(
            f"/api/entities/{setup['acme'].id}/",
            {"tier": str(_tier("low").id)},
            format="json",
        )
        acme = Entity.objects.get(pk=setup["acme"].pk)
        assert (acme.tier_source, acme.tier_value, acme.tier_response) == (
            TierSource.MANUAL,
            None,
            None,
        )

    def test_entity_shows_where_its_tier_came_from(self, setup):
        _user, client = _admin()
        response = _response(setup, risk="three")
        _accept(client, response)
        data = client.get(f"/api/entities/{setup['acme'].id}/").json()
        assert data["tier_value"] == 3.0
        assert data["tier_response"]["id"] == str(response.id)


@pytest.mark.django_db
class TestEndpoints:
    def test_fed_by(self, setup):
        _user, client = _admin()
        QuickFormPublication.objects.create(
            name="Unrelated", quick_form=setup["form"], folder=setup["domain"]
        )
        rows = client.get("/api/tiers/fed-by/").json()
        assert [(r["name"], r["problems"]) for r in rows] == [("Tier a vendor", [])]

    def test_fed_by_reports_a_broken_config(self, setup):
        _user, client = _admin()
        QuickForm.objects.filter(pk=setup["form"].pk).update(outcomes_definition=[])
        rows = client.get("/api/tiers/fed-by/").json()
        assert "bandsOutcomeNotNumeric" in rows[0]["problems"]

    def test_mine_lists_targets(self, setup):
        _user, client = _admin()
        rows = client.get("/api/quick-form-publications/mine/").json()
        row = next(r for r in rows if r["id"] == str(setup["publication"].id))
        assert row["targets"] == ["entity.tier"]
