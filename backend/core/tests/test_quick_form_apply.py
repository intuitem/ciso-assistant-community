"""Apply on accept: an accepted response writes through the targets its
publication lists. Exercised with a test-only target that copies a numeric
rule's value into an entity's `mission`."""

import pytest
from django.contrib.auth.models import Permission
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
from core.quick_form_apply import (
    on_accept_health,
    plan,
    serialize_plan,
    validate_on_accept,
)
from core.quick_form_targets import TARGETS, Proposal, Target, register
from core.utils import apply_answers_dict
from iam.models import Folder, Role, RoleAssignment, UserGroup
from tprm.models import Entity

FORM = "urn:test:risk:quick_form:apply"
PAGE = "urn:test:risk:qf_page:apply:p"
Q_VENDOR = f"{PAGE}:question:vendor"
Q_LEVEL = f"{PAGE}:question:level"

LIBRARY_YAML = f"""
urn: urn:test:risk:library:apply
locale: en
ref_id: apply
name: Apply
description: test
copyright: test
version: 1
provider: test
packager: test
objects:
  quick_forms:
    - urn: {FORM}
      ref_id: apply
      name: Apply
      subject_question_urn: {Q_VENDOR}
      scores_definition:
        aggregation: sum
      outcomes_definition:
        - ref_id: level
          kind: number
          expression: response.score
      pages:
        - urn: {PAGE}
          ref_id: p
          name: P
          questions:
            {Q_VENDOR}:
              type: object_reference
              text: Vendor
              config:
                model: entity
            {Q_LEVEL}:
              type: unique_choice
              text: Level
              choices:
                - urn: {Q_LEVEL}:choice:three
                  value: Three
                  add_score: 3
"""


class MissionTarget(Target):
    key = "test.entity_mission"
    subject_model = "tprm.Entity"
    permission = "change_entity"
    label = "mission"

    def validate_config(self, config, quick_form):
        numeric = {
            r.get("ref_id")
            for r in quick_form.outcomes_definition or []
            if r.get("kind") == "number"
        }
        return [] if config.get("value") in numeric else ["unknownValue"]

    def current(self, subject):
        return subject.mission, subject.mission

    def resolve(self, response, config, override=None):
        if override:
            if not override.get("note"):
                return Proposal.refuse("noteRequired")
            return Proposal(
                ok=True,
                value=override["value"],
                display=override["value"],
                overridden=True,
                note=override["note"],
            )
        value = (response.computed_values or {}).get(config["value"])
        if value is None:
            return Proposal.refuse("valueMissing")
        return Proposal(ok=True, value=f"level {value:g}", display=f"level {value:g}")

    def apply(self, subject, proposal, *, response, user):
        if proposal.value == "explode":
            raise RuntimeError("boom")
        subject.mission = proposal.value
        subject.save(update_fields=["mission"])
        if proposal.value == "half":
            raise RuntimeError("failed after writing")


@pytest.fixture(autouse=True)
def mission_target():
    register(MissionTarget)
    yield
    TARGETS.pop(MissionTarget.key, None)


ON_ACCEPT = [{"target": MissionTarget.key, "config": {"value": "level"}}]


@pytest.fixture
def setup():
    startup(sender=None, **{})
    stored, error = StoredLibrary.store_library_content(LIBRARY_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    form = QuickForm.objects.get(urn=FORM)
    domain = Folder.objects.create(
        name="apply-domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    acme = Entity.objects.create(name="Acme", folder=domain, mission="before")
    publication = QuickFormPublication.objects.create(
        name="Assess", quick_form=form, folder=domain, on_accept=ON_ACCEPT
    )
    return {"form": form, "domain": domain, "acme": acme, "publication": publication}


def _client(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


def _admin():
    user = User.objects.create_user(email="qf-apply@test.local", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return user, _client(user)


def _reviewer_without_entity_rights(folder):
    """May view and decide on responses, may not change entities."""
    user = User.objects.create_user(email="qf-reviewer@test.local", is_published=True)
    role = Role.objects.create(name="qf-reviewer-only")
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_quickformresponse",
                "approve_quickformresponse",
                "view_entity",
            ]
        )
    )
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
    )
    assignment.perimeter_folders.add(folder)
    return user, _client(user)


def _submitted_response(setup, answered=True):
    response = QuickFormResponse.objects.create(
        name="r",
        quick_form=setup["form"],
        folder=setup["domain"],
        publication=setup["publication"],
        status=QuickFormResponse.Status.SUBMITTED,
    )
    response.seed_answers()
    questions = {
        q.urn: q for q in Question.objects.filter(page__quick_form=setup["form"])
    }
    answers = {Q_VENDOR: [str(setup["acme"].id)]}
    if answered:
        answers[Q_LEVEL] = f"{Q_LEVEL}:choice:three"
    apply_answers_dict("response", response, questions, answers)
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.DRAFT
    )
    response.refresh_from_db()
    response.recompute()
    requester, _ = User.objects.get_or_create(email="qf-requester@test.local")
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.SUBMITTED, submitted_by=requester
    )
    response.refresh_from_db()
    return response


def _decide(client, response, resolution, **extra):
    return client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": resolution, **extra},
        format="json",
    )


@pytest.mark.django_db
class TestValidation:
    def test_valid(self, setup):
        assert validate_on_accept(ON_ACCEPT, setup["form"]) == []

    @pytest.mark.parametrize(
        "on_accept,expected",
        [
            ("nope", ["onAcceptMustBeAList"]),
            ([{"target": "nope"}], ["unknownOnAcceptTarget:nope"]),
            (ON_ACCEPT + ON_ACCEPT, [f"duplicateOnAcceptTarget:{MissionTarget.key}"]),
            (
                [{"target": MissionTarget.key, "config": {"value": "x"}}],
                [f"{MissionTarget.key}:unknownValue"],
            ),
        ],
    )
    def test_invalid(self, setup, on_accept, expected):
        assert validate_on_accept(on_accept, setup["form"]) == expected

    def test_form_without_a_matching_subject(self, setup):
        QuickForm.objects.filter(pk=setup["form"].pk).update(subject_question_urn="")
        setup["form"].refresh_from_db()
        assert validate_on_accept(ON_ACCEPT, setup["form"]) == [
            f"subjectModelMismatch:{MissionTarget.key}"
        ]

    def test_api_refuses_a_bad_config(self, setup):
        _user, client = _admin()
        response = client.patch(
            f"/api/quick-form-publications/{setup['publication'].id}/",
            {"on_accept": [{"target": "nope"}]},
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["on_accept"] == ["unknownOnAcceptTarget:nope"]

    def test_health_flags_what_an_upgrade_broke(self, setup):
        assert on_accept_health(setup["publication"])[0]["problems"] == []
        QuickForm.objects.filter(pk=setup["form"].pk).update(outcomes_definition=[])
        setup["publication"].quick_form.refresh_from_db()
        health = on_accept_health(setup["publication"])
        assert health[0]["problems"] == ["unknownValue"]

    def test_targets_are_listed(self, setup):
        _user, client = _admin()
        keys = [
            t["key"]
            for t in client.get(
                "/api/quick-form-publications/on-accept-targets/"
            ).json()
        ]
        assert MissionTarget.key in keys


@pytest.mark.django_db
class TestPlan:
    def test_ready(self, setup):
        user, _ = _admin()
        rows = serialize_plan(plan(_submitted_response(setup), user))
        assert rows == [
            {
                "target": MissionTarget.key,
                "label": "mission",
                "subject": "Acme",
                "ok": True,
                "reason": "",
                "current": "before",
                "proposed": "level 3",
                "overridden": False,
            }
        ]

    def test_no_publication_no_targets(self, setup):
        user, _ = _admin()
        response = _submitted_response(setup)
        QuickFormResponse.objects.filter(pk=response.pk).update(publication=None)
        response.refresh_from_db()
        assert plan(response, user) == []

    def test_no_subject(self, setup):
        user, _ = _admin()
        response = _submitted_response(setup)
        QuickFormResponse.objects.filter(pk=response.pk).update(
            subject_content_type=None, subject_object_id=None
        )
        response.refresh_from_db()
        assert plan(response, user)[0]["proposal"].reason == "noSubject"

    def test_missing_value_fails_closed(self, setup):
        user, _ = _admin()
        response = _submitted_response(setup)
        QuickFormResponse.objects.filter(pk=response.pk).update(computed_values={})
        response.refresh_from_db()
        assert plan(response, user)[0]["proposal"].reason == "valueMissing"

    def test_preview_hides_a_subject_the_caller_cannot_see(self, setup):
        # May view and decide on responses, may not view entities.
        user = User.objects.create_user(email="qf-blind@test.local", is_published=True)
        role = Role.objects.create(name="qf-blind")
        role.permissions.set(
            Permission.objects.filter(
                codename__in=["view_quickformresponse", "approve_quickformresponse"]
            )
        )
        assignment = RoleAssignment.objects.create(
            user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
        )
        assignment.perimeter_folders.add(setup["domain"])
        response = _submitted_response(setup)
        rows = (
            _client(user)
            .get(f"/api/quick-form-responses/{response.id}/accept-preview/")
            .json()
        )
        assert rows[0]["reason"] == "subjectPermissionRequired"
        assert rows[0]["subject"] is None
        assert rows[0]["current"] is None
        assert "Acme" not in str(rows) and "before" not in str(rows)

    def test_preview_endpoint(self, setup):
        _user, client = _admin()
        response = _submitted_response(setup)
        rows = client.get(
            f"/api/quick-form-responses/{response.id}/accept-preview/"
        ).json()
        assert rows[0]["proposed"] == "level 3"


@pytest.mark.django_db
class TestAccept:
    def test_accept_writes_and_logs(self, setup):
        user, client = _admin()
        response = _submitted_response(setup)
        result = _decide(client, response, "accepted")
        assert result.status_code == 200, result.json()
        assert result.json()["on_accept"][0]["applied"] is True

        setup["acme"].refresh_from_db()
        assert setup["acme"].mission == "level 3"
        application = QuickFormApplication.objects.get(response=response)
        assert application.target == MissionTarget.key
        assert application.subject == setup["acme"]
        assert (application.previous_display, application.new_display) == (
            "before",
            "level 3",
        )
        assert application.applied_by == user
        assert application.folder == response.folder

        content = client.get(f"/api/quick-form-responses/{response.id}/content/").json()
        assert content["applications"][0]["new"] == "level 3"

    def test_reject_writes_nothing(self, setup):
        _user, client = _admin()
        response = _submitted_response(setup)
        result = _decide(client, response, "rejected")
        assert result.status_code == 200, result.json()
        assert "on_accept" not in result.json()
        setup["acme"].refresh_from_db()
        assert setup["acme"].mission == "before"
        assert not QuickFormApplication.objects.exists()

    def test_reviewer_without_rights_on_the_subject(self, setup):
        _user, client = _reviewer_without_entity_rights(setup["domain"])
        response = _submitted_response(setup)
        result = _decide(client, response, "accepted")
        assert result.status_code == 200, result.json()
        row = result.json()["on_accept"][0]
        assert (row["applied"], row["reason"]) == (False, "subjectPermissionRequired")
        response.refresh_from_db()
        assert response.status == QuickFormResponse.Status.CLOSED
        setup["acme"].refresh_from_db()
        assert setup["acme"].mission == "before"

    def test_override_with_a_note(self, setup):
        _user, client = _admin()
        response = _submitted_response(setup)
        result = _decide(
            client,
            response,
            "accepted",
            overrides={MissionTarget.key: {"value": "custom", "note": "Known vendor"}},
        )
        assert result.status_code == 200, result.json()
        application = QuickFormApplication.objects.get(response=response)
        assert application.overridden and application.note == "Known vendor"
        setup["acme"].refresh_from_db()
        assert setup["acme"].mission == "custom"

    def test_override_without_a_note_refuses_the_accept(self, setup):
        _user, client = _admin()
        response = _submitted_response(setup)
        result = _decide(
            client,
            response,
            "accepted",
            overrides={MissionTarget.key: {"value": "custom"}},
        )
        assert result.status_code == 400
        assert result.json() == {
            "error": "invalidOverride",
            "target": MissionTarget.key,
            "reason": "noteRequired",
        }
        response.refresh_from_db()
        assert response.status == QuickFormResponse.Status.SUBMITTED

    def test_a_target_failing_after_writing_leaves_nothing_behind(self, setup):
        _user, client = _admin()
        response = _submitted_response(setup)
        result = _decide(
            client,
            response,
            "accepted",
            overrides={MissionTarget.key: {"value": "half", "note": "x"}},
        )
        assert result.status_code == 200, result.json()
        assert result.json()["on_accept"][0]["reason"] == "targetError"
        setup["acme"].refresh_from_db()
        assert setup["acme"].mission == "before"
        assert not QuickFormApplication.objects.exists()

    def test_a_failing_target_does_not_block_the_accept(self, setup):
        _user, client = _admin()
        response = _submitted_response(setup)
        result = _decide(
            client,
            response,
            "accepted",
            overrides={MissionTarget.key: {"value": "explode", "note": "x"}},
        )
        assert result.status_code == 200, result.json()
        row = result.json()["on_accept"][0]
        assert (row["applied"], row["reason"]) == (False, "targetError")
        response.refresh_from_db()
        assert response.status == QuickFormResponse.Status.CLOSED
        assert not QuickFormApplication.objects.exists()
