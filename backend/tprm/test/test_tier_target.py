"""`entity.tier`: an accepted response sets its vendor's tier through score
bands and/or outcome mapping, highest tier winning."""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    Actor,
    Question,
    QuickForm,
    QuickFormApplication,
    QuickFormPublication,
    QuickFormResponse,
    StoredLibrary,
    User,
)
from core.quick_form_apply import on_accept_health, plan
from core.utils import apply_answers_dict
from iam.models import Folder, Role, RoleAssignment, UserGroup
from tprm.models import Entity, EntityTierChange, Tier, TierSource
from tprm.testing import seed_four_level_scale
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
                {"tier": "high", "min": 3},
                {"tier": "medium", "min": 2},
                {"tier": "low"},
            ],
        },
        "mapping": [{"outcome": "pii", "tier": "critical"}],
    }


def _set_config(setup, config):
    QuickForm.objects.filter(pk=setup["form"].pk).update(
        on_accept=[{"target": "entity.tier", "config": config}]
    )


@pytest.fixture
def setup():
    startup(sender=None, **{})
    seed_four_level_scale()
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
    setup = {"form": form, "domain": domain, "acme": acme}
    _set_config(setup, _config())
    setup["publication"] = QuickFormPublication.objects.create(
        name="Tier a vendor", quick_form=form, folder=domain
    )
    return setup


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
        setup["form"].refresh_from_db()
        assert on_accept_health(setup["form"]) == [
            {"target": "entity.tier", "label": "tier", "problems": []}
        ]

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
            {"tier": "medium", "min": 2},
            {"tier": "high", "min": 3},
        ]
        assert "thresholdsMustDescendByMin" in self._errors(setup, config)
        # Ranks are the instance's: checked against this scale, not on save.
        assert "thresholdsMustDescendByRank" in EntityTierTarget().health(
            config, setup["form"]
        )

    def test_only_the_last_threshold_may_omit_min(self, setup):
        config = _config()
        config["bands"]["thresholds"][0].pop("min")
        assert "thresholdMinRequired" in self._errors(setup, config)

    def test_mapping_needs_a_yes_no_rule(self, setup):
        config = {"mapping": [{"outcome": "risk", "tier": "nope"}]}
        assert self._errors(setup, config) == ["mappingOutcomeUnknown"]

    def test_a_key_missing_from_the_scale_is_a_health_problem(self, setup):
        config = {"mapping": [{"outcome": "pii", "tier": "nope"}]}
        assert self._errors(setup, config) == []
        assert EntityTierTarget().health(config, setup["form"]) == ["unknownTier"]


@pytest.mark.django_db
class TestResolution:
    def _proposal(self, setup, **answers):
        user, _ = _admin()
        return plan(_response(setup, **answers), user)[0]["proposal"]

    def test_band(self, setup):
        proposal = self._proposal(setup, risk="three")
        assert proposal.display == "high"
        assert proposal.value == {"tier": str(_tier("high").id), "value": 3.0}
        assert (proposal.extra["band"], proposal.extra["outcomes"]) == ("risk", [])

    def test_lowest_band_catches_the_rest(self, setup):
        assert self._proposal(setup, risk="one").display == "low"

    def test_mapped_outcome_wins_when_higher(self, setup):
        proposal = self._proposal(setup, risk="one", pii="yes")
        assert proposal.display == "critical"
        # The band did not produce the winning tier, so no value is kept.
        assert proposal.value["value"] is None
        assert proposal.extra["outcomes"] == ["pii"]
        assert "band" not in proposal.extra

    def test_a_lower_mapped_outcome_is_not_the_reason(self, setup):
        config = _config()
        config["mapping"] = [{"outcome": "pii", "tier": "low"}]
        _set_config(setup, config)
        proposal = self._proposal(setup, risk="three", pii="yes")
        assert (proposal.display, proposal.extra["outcomes"]) == ("high", [])

    def test_a_hidden_tier_is_never_proposed(self, setup):
        Tier.objects.filter(name="high").update(is_visible=False)
        assert self._proposal(setup, risk="three").reason == "tierHidden"

    def test_nothing_resolved_writes_nothing(self, setup):
        _set_config(setup, {"mapping": [{"outcome": "pii", "tier": "critical"}]})
        assert self._proposal(setup).reason == "noTierResolved"

    def test_a_key_missing_from_the_scale_is_never_guessed(self, setup):
        # Without "high", the "medium" band would match a 3: refused instead.
        Tier.objects.filter(key="high").update(key="elevated")
        assert self._proposal(setup, risk="three").reason == "unknownTier"

    def test_renaming_and_reordering_the_scale_keep_the_form_pointing_right(
        self, setup
    ):
        Tier.objects.filter(key="high").update(name="Vital", rank=9)
        proposal = self._proposal(setup, risk="three")
        assert (proposal.ok, proposal.display) == (True, "Vital")


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
    def _row(self, client, setup):
        rows = client.get("/api/tiers/fed-by/").json()
        return next(r for r in rows if r["id"] == str(setup["form"].id))

    def test_fed_by(self, setup):
        _user, client = _admin()
        row = self._row(client, setup)
        assert (row["name"], row["problems"]) == ("Tiering", [])

    def test_fed_by_reports_a_hidden_tier(self, setup):
        Tier.objects.filter(name="critical").update(is_visible=False)
        _user, client = _admin()
        assert self._row(client, setup)["problems"] == ["tierHidden"]

    def test_fed_by_reports_a_key_missing_from_the_scale(self, setup):
        Tier.objects.filter(key="low").update(key="minor")
        _user, client = _admin()
        assert self._row(client, setup)["problems"] == ["unknownTier"]

    def test_fed_by_reports_a_broken_config(self, setup):
        _user, client = _admin()
        QuickForm.objects.filter(pk=setup["form"].pk).update(outcomes_definition=[])
        assert "bandsOutcomeNotNumeric" in self._row(client, setup)["problems"]

    def test_mine_lists_targets(self, setup):
        _user, client = _admin()
        rows = client.get("/api/quick-form-publications/mine/").json()
        row = next(r for r in rows if r["id"] == str(setup["publication"].id))
        assert row["targets"] == ["entity.tier"]


@pytest.mark.django_db
class TestKeys:
    def test_a_new_tier_gets_a_key_from_its_name(self, setup):
        _user, client = _admin()
        for name in ("Tier 1", "Tier-1"):
            assert (
                client.post("/api/tiers/", {"name": name}, format="json").status_code
                == 201
            )
        assert Tier.objects.get(name="Tier 1").key == "tier-1"
        assert Tier.objects.get(name="Tier-1").key == "tier-1-2"
        listed = client.get("/api/tiers/").json()["results"]
        assert "tier-1" in [t["key"] for t in listed]

    def test_the_key_never_changes(self, setup):
        _user, client = _admin()
        tier = _tier("high")
        client.patch(
            f"/api/tiers/{tier.id}/", {"name": "Vital", "key": "vital"}, format="json"
        )
        tier.refresh_from_db()
        assert (tier.name, tier.key) == ("Vital", "high")


@pytest.mark.django_db
class TestAssessFromTheObject:
    def _options(self, client, setup):
        return client.get(
            "/api/quick-forms/assess-options/",
            {"target": "entity.tier", "subject": str(setup["acme"].id)},
        ).json()

    def _start(self, client, setup):
        return client.post(
            f"/api/quick-forms/{setup['form'].id}/start/",
            {"subject": str(setup["acme"].id)},
            format="json",
        )

    def _auditor(self, setup):
        user = User.objects.create_user(
            email="tier-auditor@test.local", is_published=True
        )
        assignment = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name="BI-RL-AUD"),
            folder=setup["domain"],
            is_recursive=True,
        )
        assignment.perimeter_folders.add(setup["domain"])
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
        )
        return client

    def test_someone_who_may_create_responses_gets_the_form(self, setup):
        _user, client = _admin()
        assert self._options(client, setup) == [
            {"kind": "form", "id": str(setup["form"].id), "name": "Tiering"}
        ]

    def test_start_files_in_the_subjects_domain_without_a_publication(self, setup):
        user, client = _admin()
        result = self._start(client, setup)
        assert result.status_code == 200, result.json()
        response = QuickFormResponse.objects.get(
            pk=result.json()["redirect"].rsplit("/", 1)[1]
        )
        assert (response.publication, response.folder) == (None, setup["domain"])
        assert str(response.subject_object_id) == str(setup["acme"].id)
        # Same caller, same vendor: the draft is resumed, not duplicated.
        assert self._start(client, setup).json()["resumed"] is True

    def test_the_in_house_assessment_applies_on_submit(self, setup):
        _user, client = _admin()
        response_id = self._start(client, setup).json()["redirect"].rsplit("/", 1)[1]
        response = QuickFormResponse.objects.get(pk=response_id)
        questions = {
            q.urn: q for q in Question.objects.filter(page__quick_form=setup["form"])
        }
        apply_answers_dict(
            "response",
            response,
            questions,
            {Q_RISK: f"{Q_RISK}:choice:three", Q_PII: f"{Q_PII}:choice:no"},
        )
        response.recompute()
        content = client.get(f"/api/my-requests/{response.id}/content/").json()
        assert content["projection"][0]["proposed"] == "high"
        assert content["on_submit"] == "apply"
        result = client.post(
            f"/api/my-requests/{response.id}/submit/", {}, format="json"
        )
        assert result.status_code == 200, result.json()
        setup["acme"].refresh_from_db()
        assert setup["acme"].tier == _tier("high")

    def test_a_reader_is_offered_the_publication_and_cannot_start_directly(self, setup):
        client = self._auditor(setup)
        assert self._options(client, setup) == [
            {
                "kind": "publication",
                "id": str(setup["publication"].id),
                "name": "Tier a vendor",
            }
        ]
        # 404 when the form itself is out of sight, 403 when only the right
        # to file in the vendor's domain is missing.
        assert self._start(client, setup).status_code in (403, 404)
        assert not QuickFormResponse.objects.filter(publication=None).exists()

    def test_an_unreadable_subject_offers_nothing(self, setup):
        hidden = Entity.objects.create(
            name="Hidden",
            folder=Folder.objects.create(
                name="elsewhere",
                content_type=Folder.ContentType.DOMAIN,
                parent_folder=Folder.get_root_folder(),
            ),
        )
        client = self._auditor(setup)
        assert (
            client.get(
                "/api/quick-forms/assess-options/",
                {"target": "entity.tier", "subject": str(hidden.id)},
            ).json()
            == []
        )


@pytest.mark.django_db
class TestSelfAssessment:
    def test_an_assessment_by_someone_who_may_set_the_tier_applies_on_submit(
        self, setup
    ):
        user, client = _admin()
        response = _response(setup, risk="three")
        QuickFormResponse.objects.filter(pk=response.pk).update(
            status=QuickFormResponse.Status.DRAFT, submitted_by=None
        )
        response.respondents.add(Actor.objects.get(user=user, entity__isnull=True))

        result = client.post(
            f"/api/my-requests/{response.id}/submit/", {}, format="json"
        )
        assert result.status_code == 200, result.json()

        setup["acme"].refresh_from_db()
        assert setup["acme"].tier == _tier("high")
        assert setup["acme"].tier_source == TierSource.ASSESSMENT
        change = EntityTierChange.objects.get(entity=setup["acme"])
        assert change.response_id == response.id
        response.refresh_from_db()
        assert response.resolution == QuickFormResponse.Resolution.ACCEPTED


@pytest.mark.django_db
class TestDomainManagerScale:
    def _domain_manager(self, folder, email):
        user = User.objects.create_user(email=email, is_published=True)
        assignment = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name="BI-RL-DMA"),
            folder=folder,
            is_recursive=True,
        )
        assignment.perimeter_folders.add(folder)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
        )
        return client

    def test_a_domain_manager_of_global_edits_the_scale(self, setup):
        client = self._domain_manager(Folder.get_root_folder(), "dm-global@test.local")
        created = client.post("/api/tiers/", {"name": "Vital"}, format="json")
        assert created.status_code == 201, created.json()

    def test_a_domain_manager_of_one_domain_does_not(self, setup):
        client = self._domain_manager(setup["domain"], "dm-local@test.local")
        assert (
            client.post("/api/tiers/", {"name": "Vital"}, format="json").status_code
            == 403
        )


@pytest.mark.django_db
def test_a_hidden_tier_sends_a_self_assessment_to_review(setup):
    user, client = _admin()
    Tier.objects.filter(name="high").update(is_visible=False)
    response = _response(setup, risk="three")
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.DRAFT, submitted_by=None
    )
    response.respondents.add(Actor.objects.get(user=user, entity__isnull=True))
    client.post(f"/api/my-requests/{response.id}/submit/", {}, format="json")
    response.refresh_from_db()
    assert response.status == QuickFormResponse.Status.SUBMITTED


@pytest.mark.django_db
def test_skipped_scored_questions_send_a_self_assessment_to_review(setup):
    """Optional scored questions left blank score 0 and would read as the
    lowest tier: never applied without a reviewer."""
    user, client = _admin()
    Question.objects.filter(urn__in=[Q_RISK, Q_PII]).update(required=False)
    response = QuickFormResponse.objects.create(
        name="partial",
        quick_form=setup["form"],
        folder=setup["domain"],
        publication=setup["publication"],
    )
    response.seed_answers()
    questions = {
        q.urn: q for q in Question.objects.filter(page__quick_form=setup["form"])
    }
    apply_answers_dict(
        "response", response, questions, {Q_VENDOR: [str(setup["acme"].id)]}
    )
    response.respondents.add(Actor.objects.get(user=user, entity__isnull=True))
    response.recompute()

    content = client.get(f"/api/my-requests/{response.id}/content/").json()
    assert content["on_submit"] == "review"
    client.post(f"/api/my-requests/{response.id}/submit/", {}, format="json")
    response.refresh_from_db()
    assert response.status == QuickFormResponse.Status.SUBMITTED
    setup["acme"].refresh_from_db()
    assert setup["acme"].tier is None


@pytest.mark.django_db
class TestReviewFeedback:
    def _reader_of(self, folder, email):
        user = User.objects.create_user(email=email, is_published=True)
        assignment = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name="BI-RL-AUD"),
            folder=folder,
            is_recursive=True,
        )
        assignment.perimeter_folders.add(folder)
        # The scale lives in Global: reading it is a separate, narrow right.
        from django.contrib.auth.models import Permission

        scale_reader = Role.objects.create(name=f"scale-reader-{email}")
        scale_reader.permissions.set(Permission.objects.filter(codename="view_tier"))
        on_global = RoleAssignment.objects.create(
            user=user, role=scale_reader, folder=Folder.get_root_folder()
        )
        on_global.perimeter_folders.add(Folder.get_root_folder())
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
        )
        return client

    def test_tier_counts_cover_only_what_the_viewer_sees(self, setup):
        elsewhere = Folder.objects.create(
            name="elsewhere",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
        )
        vital = Tier.objects.create(name="Vital", rank=9)
        set_entity_tier(setup["acme"], vital)
        set_entity_tier(Entity.objects.create(name="Hidden", folder=elsewhere), vital)
        client = self._reader_of(setup["domain"], "tier-reader@test.local")
        rows = client.get("/api/tiers/").json()["results"]
        assert next(r for r in rows if r["key"] == "vital")["entities_count"] == 1
        _user, admin = _admin()
        rows = admin.get("/api/tiers/").json()["results"]
        assert next(r for r in rows if r["key"] == "vital")["entities_count"] == 2

    def test_a_tier_used_out_of_sight_still_cannot_be_deleted(self, setup):
        elsewhere = Folder.objects.create(
            name="elsewhere",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
        )
        vital = Tier.objects.create(name="Vital", rank=9)
        hidden = Entity.objects.create(name="Hidden", folder=elsewhere)
        Entity.objects.filter(pk=hidden.pk).update(tier=vital)
        _user, admin = _admin()
        result = admin.delete(f"/api/tiers/{vital.id}/")
        assert result.status_code == 409
        assert Tier.objects.filter(pk=vital.pk).exists()

    def test_a_target_failing_to_plan_sends_the_submit_to_review(
        self, setup, monkeypatch
    ):
        def boom(*args, **kwargs):
            raise RuntimeError("unreadable")

        monkeypatch.setattr(EntityTierTarget, "current", boom)
        user, client = _admin()
        response = _response(setup, risk="three")
        QuickFormResponse.objects.filter(pk=response.pk).update(
            status=QuickFormResponse.Status.DRAFT, submitted_by=None
        )
        response.respondents.add(Actor.objects.get(user=user, entity__isnull=True))
        content = client.get(f"/api/my-requests/{response.id}/content/").json()
        assert content["on_submit"] == "review"
        result = client.post(
            f"/api/my-requests/{response.id}/submit/", {}, format="json"
        )
        assert result.status_code == 200, result.json()
        response.refresh_from_db()
        assert response.status == QuickFormResponse.Status.SUBMITTED

    def test_a_rank_taken_meanwhile_is_a_400(self, setup, monkeypatch):
        taken = Tier.objects.order_by("rank").first().rank
        monkeypatch.setattr(
            Tier, "make_room_at_the_bottom", classmethod(lambda cls: taken)
        )
        _user, client = _admin()
        result = client.post("/api/tiers/", {"name": "Late"}, format="json")
        assert result.status_code == 400
        assert not Tier.objects.filter(name="Late").exists()


@pytest.mark.django_db
class TestSubjectLock:
    def _started(self, client, setup):
        result = client.post(
            f"/api/quick-forms/{setup['form'].id}/start/",
            {"subject": str(setup["acme"].id)},
            format="json",
        )
        return QuickFormResponse.objects.get(
            pk=result.json()["redirect"].rsplit("/", 1)[1]
        )

    def _other_vendor(self, setup):
        return Entity.objects.create(name="Other", folder=setup["domain"])

    def test_starting_from_the_vendor_locks_the_subject(self, setup):
        _user, client = _admin()
        response = self._started(client, setup)
        assert response.subject_locked
        other = self._other_vendor(setup)
        url = f"/api/my-requests/{response.id}/answers/"
        refused = client.patch(
            url, {"answers": {Q_VENDOR: [str(other.id)]}}, format="json"
        )
        assert refused.status_code == 400
        assert refused.json()["error"] == "subjectLocked"
        # Re-sending the same vendor, alongside other answers, is not a change.
        kept = client.patch(
            url,
            {
                "answers": {
                    Q_VENDOR: [str(setup["acme"].id)],
                    Q_RISK: f"{Q_RISK}:choice:one",
                }
            },
            format="json",
        )
        assert kept.status_code == 200, kept.json()
        response.refresh_from_db()
        assert str(response.subject_object_id) == str(setup["acme"].id)

    def test_the_folder_rights_path_is_locked_too(self, setup):
        _user, client = _admin()
        response = self._started(client, setup)
        other = self._other_vendor(setup)
        refused = client.patch(
            f"/api/quick-form-responses/{response.id}/",
            {"answers": {Q_VENDOR: [str(other.id)]}},
            format="json",
        )
        assert refused.status_code == 400
        assert "subjectLocked" in str(refused.json())

    def test_a_clone_keeps_the_lock(self, setup):
        _user, client = _admin()
        response = self._started(client, setup)
        result = client.post(
            f"/api/my-requests/{response.id}/clone/", {}, format="json"
        )
        assert result.status_code in (200, 201), result.json()
        clone = QuickFormResponse.objects.get(cloned_from=response)
        assert clone.subject_locked

    def test_a_response_started_without_a_subject_stays_free(self, setup):
        user, client = _admin()
        result = client.post(
            f"/api/quick-form-publications/{setup['publication'].id}/start/",
            {},
            format="json",
        )
        assert result.status_code == 200, result.json()
        response = QuickFormResponse.objects.get(
            pk=result.json()["redirect"].rsplit("/", 1)[1]
        )
        assert not response.subject_locked
        other = self._other_vendor(setup)
        changed = client.patch(
            f"/api/my-requests/{response.id}/answers/",
            {"answers": {Q_VENDOR: [str(other.id)]}},
            format="json",
        )
        assert changed.status_code == 200, changed.json()
