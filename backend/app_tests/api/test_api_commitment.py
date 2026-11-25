from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory

from core.models import (
    Actor,
    AppliedControl,
    Comment,
    Commitment,
    Finding,
    FindingsAssessment,
    TaskNode,
    TaskTemplate,
)
from core.commitment import apply_transition
from core.serializers import TaskTemplateWriteSerializer
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


def set_flag(enabled: bool):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    value = dict(gs.value or {})
    value["commitment_management"] = enabled
    gs.value = value
    gs.save()
    clear_feature_flags_cache()


@pytest.fixture
def setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root,
        name="Commitment Domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    set_flag(True)

    manager = User.objects.create_superuser("commitment-manager@tests.com")
    owner_user = User.objects.create_superuser("commitment-owner@tests.com")
    owner_actor = Actor.get_all_for_user(owner_user)[0]

    control = AppliedControl.objects.create(name="Patch the thing", folder=domain)
    control.owner.set([owner_actor])

    manager_client = APIClient()
    manager_client.force_authenticate(manager)
    owner_client = APIClient()
    owner_client.force_authenticate(owner_user)

    yield {
        "domain": domain,
        "control": control,
        "owner_actor": owner_actor,
        "manager": manager_client,
        "owner": owner_client,
    }
    set_flag(False)


def hide_all_actors():
    """Make every Actor invisible while leaving other models' scoping intact."""
    real = RoleAssignment.get_viewable_object_ids

    def only_non_actors(user, model, folder=None):
        if model is Actor:
            return Actor.objects.none().values_list("id", flat=True)
        return real(user, model, folder)

    return patch.object(
        RoleAssignment, "get_viewable_object_ids", side_effect=only_non_actors
    )


def patch_control(client, control, **payload):
    return client.patch(f"/api/applied-controls/{control.id}/", payload, format="json")


def drive_to(setup, state, eta="2026-12-01"):
    """Walk the happy path up to *state*, returning the control."""
    control = setup["control"]
    patch_control(setup["manager"], control, commitment_state="in_negotiation")
    if state == "in_negotiation":
        return control
    patch_control(setup["owner"], control, commitment_state="committed", eta=eta)
    return control


class TestFeatureFlag:
    def test_fields_absent_when_the_flag_is_off(self, setup):
        set_flag(False)
        body = (
            setup["manager"].get(f"/api/applied-controls/{setup['control'].id}/").json()
        )
        assert "commitment_state" not in body
        assert "committed_eta" not in body

    def test_fields_present_when_the_flag_is_on(self, setup):
        body = (
            setup["manager"].get(f"/api/applied-controls/{setup['control'].id}/").json()
        )
        assert body["commitment_state"] == "--"
        assert body["committed_eta"] is None

    def test_transitions_endpoint_is_gated(self, setup):
        set_flag(False)
        res = setup["manager"].get(
            f"/api/applied-controls/{setup['control'].id}/commitment_transitions/"
        )
        assert res.status_code == 403


class TestTransitions:
    def test_the_happy_path(self, setup):
        control = drive_to(setup, "committed")
        control.refresh_from_db()
        assert control.commitment_state == "committed"

    def test_an_illegal_jump_is_rejected(self, setup):
        res = patch_control(
            setup["manager"], setup["control"], commitment_state="committed"
        )
        assert res.status_code == 400
        assert "commitment_state" in res.json()

    def test_an_owner_side_move_is_refused_to_a_non_owner(self, setup):
        control = drive_to(setup, "in_negotiation")
        res = patch_control(
            setup["manager"], control, commitment_state="committed", eta="2026-12-01"
        )
        assert res.status_code == 400
        control.refresh_from_db()
        assert control.commitment_state == "in_negotiation"

    def test_an_owner_cannot_close_their_own_commitment(self, setup):
        control = drive_to(setup, "committed")
        res = patch_control(setup["owner"], control, commitment_state="fulfilled")
        assert res.status_code == 400
        control.refresh_from_db()
        assert control.commitment_state == "committed"

        res = patch_control(setup["manager"], control, commitment_state="fulfilled")
        assert res.status_code == 200

    def test_a_note_is_required_where_the_map_says_so(self, setup):
        control = drive_to(setup, "committed")

        res = patch_control(setup["owner"], control, commitment_state="in_negotiation")
        assert res.status_code == 400
        assert "commitment_notes" in res.json()

        res = patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="Vendor slipped the delivery",
        )
        assert res.status_code == 200

    def test_either_side_can_reopen(self, setup):
        control = drive_to(setup, "committed")
        res = patch_control(
            setup["manager"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="that date is too far out",
        )
        assert res.status_code == 200, res.json()

    def test_a_date_is_required_to_commit(self, setup):
        control = drive_to(setup, "in_negotiation")
        res = patch_control(setup["owner"], control, commitment_state="committed")
        assert res.status_code == 400

    def test_the_batch_action_cannot_bypass_the_map(self, setup):
        res = setup["manager"].post(
            "/api/applied-controls/batch-action/",
            {
                "action": "change_field",
                "ids": [str(setup["control"].id)],
                "field": "commitment_state",
                "value": "committed",
            },
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["failed"], "an illegal state change must not succeed"
        setup["control"].refresh_from_db()
        assert setup["control"].commitment_state == "--"


class TestTheFrozenPromise:
    def test_the_moment_of_the_promise_is_recorded(self, setup):
        control = drive_to(setup, "committed", eta="2027-01-01")
        entry = control.commitment
        # The date promised and the moment it was promised are different facts.
        assert entry.committed_at is not None
        assert str(entry.committed_eta) == "2027-01-01"

        body = (
            setup["manager"]
            .get(f"/api/applied-controls/{control.id}/commitment_transitions/")
            .json()
        )
        assert body["committed_at"] is not None

    def test_sign_off_freezes_the_date(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        control.refresh_from_db()
        assert str(control.committed_eta) == "2026-12-01"
        assert control.committed_by == setup["owner_actor"]

    def test_committed_eta_is_not_writable(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        patch_control(setup["manager"], control, committed_eta="2027-06-01")
        control.refresh_from_db()
        assert str(control.committed_eta) == "2026-12-01"

    def test_pushing_the_date_out_is_a_slip(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        assert not control.commitment_has_slipped

        patch_control(setup["manager"], control, eta="2027-06-01")
        control.refresh_from_db()
        assert control.commitment_has_slipped
        # The promise itself is untouched by moving the working date.
        assert str(control.committed_eta) == "2026-12-01"

    def test_a_past_promise_is_breached(self, setup):
        control = drive_to(setup, "committed", eta="2020-01-01")
        control.refresh_from_db()
        assert control.commitment_is_breached

    def test_reopening_keeps_the_original_promise_visible_and_counts(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="slipping",
        )
        control.refresh_from_db()
        # The broken promise stays on the record: it is what separates a renegotiation
        # from a commitment that never happened, and it keeps a breach visible.
        assert str(control.committed_eta) == "2026-12-01"
        assert control.commitment_reopen_count == 1

        patch_control(
            setup["owner"], control, commitment_state="committed", eta="2027-03-01"
        )
        control.refresh_from_db()
        assert str(control.committed_eta) == "2027-03-01"
        assert not control.commitment_has_slipped
        assert control.commitment_reopen_count == 1

    def test_the_reopen_count_is_not_writable(self, setup):
        control = drive_to(setup, "committed")
        patch_control(setup["manager"], control, commitment_reopen_count=7)
        control.refresh_from_db()
        assert control.commitment_reopen_count == 0

    def test_each_cycle_is_its_own_row(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="slipping",
        )
        patch_control(
            setup["owner"], control, commitment_state="committed", eta="2027-03-01"
        )

        entries = list(Commitment.objects.filter(object_id=control.id))
        assert len(entries) == 2
        # Every promise keeps its own date instead of the last one overwriting it.
        assert [str(e.committed_eta) for e in entries] == ["2026-12-01", "2027-03-01"]
        assert [e.is_current for e in entries] == [False, True]

    def test_a_reopened_breach_stays_visible(self, setup):
        control = drive_to(setup, "committed", eta="2020-01-01")
        assert control.commitment_is_breached

        patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="missed it",
        )
        control.refresh_from_db()
        # Reopening must not be a way out of a broken promise.
        assert control.commitment_is_breached
        assert str(control.committed_eta) == "2020-01-01"

    def test_only_one_cycle_is_current(self, setup):
        control = drive_to(setup, "committed")
        for _ in range(3):
            patch_control(
                setup["owner"],
                control,
                commitment_state="in_negotiation",
                commitment_notes="again",
            )
            patch_control(
                setup["owner"], control, commitment_state="committed", eta="2027-01-01"
            )
        assert Commitment.objects.filter(object_id=control.id).count() == 4
        assert (
            Commitment.objects.filter(object_id=control.id, is_current=True).count()
            == 1
        )
        control.refresh_from_db()
        assert control.commitment_reopen_count == 3

    def test_history_is_exposed(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="slipping",
        )
        body = (
            setup["manager"]
            .get(f"/api/applied-controls/{control.id}/commitment_transitions/")
            .json()
        )
        assert len(body["history"]) == 1
        assert body["history"][0]["state"] == "committed"
        assert str(body["history"][0]["committed_eta"]) == "2026-12-01"


class TestDetailPayload:
    def test_committed_by_is_expanded_for_the_panel(self, setup):
        control = drive_to(setup, "committed")
        body = setup["manager"].get(f"/api/applied-controls/{control.id}/").json()
        assert body["committed_by"]["id"] == str(setup["owner_actor"].id)
        assert body["committed_by"]["str"]

    def test_task_template_detail_carries_the_commitment(self, setup):
        task = TaskTemplate.objects.create(
            name="Rotate the key", folder=setup["domain"], is_recurrent=False
        )
        setup["manager"].patch(
            f"/api/task-templates/{task.id}/",
            {"commitment_state": "in_negotiation"},
            format="json",
        )
        body = setup["manager"].get(f"/api/task-templates/{task.id}/").json()
        assert body["commitment_state"] == "in_negotiation"
        assert "committed_by" in body


class TestTransitionsEndpoint:
    def endpoint(self, control, model="applied-controls"):
        return f"/api/{model}/{control.id}/commitment_transitions/"

    def targets(self, client, control):
        body = client.get(self.endpoint(control)).json()
        return {t["value"]: t for t in body["transitions"]}

    def test_lists_only_the_legal_next_states(self, setup):
        res = setup["manager"].get(self.endpoint(setup["control"]))
        assert res.status_code == 200
        body = res.json()
        assert [t["value"] for t in body["transitions"]] == ["in_negotiation"]
        assert body["state"] == "--"
        assert body["date_field"] == "eta"

    def test_marks_owner_moves_a_non_owner_cannot_make(self, setup):
        control = drive_to(setup, "in_negotiation")
        by_value = self.targets(setup["manager"], control)
        assert by_value["committed"]["side"] == "owner"
        assert by_value["committed"]["allowed"] is False
        assert by_value["committed"]["requires_date"] is True
        assert by_value["declined"]["requires_note"] is True

        assert self.targets(setup["owner"], control)["committed"]["allowed"] is True

    def test_marks_the_close_step_the_owner_may_not_take(self, setup):
        control = drive_to(setup, "committed")
        assert self.targets(setup["owner"], control)["fulfilled"]["allowed"] is False
        assert self.targets(setup["manager"], control)["fulfilled"]["allowed"] is True

    def test_posting_a_transition_takes_it(self, setup):
        res = setup["manager"].post(
            self.endpoint(setup["control"]),
            {"commitment_state": "in_negotiation", "commitment_notes": "please commit"},
            format="json",
        )
        assert res.status_code == 200, res.json()
        assert res.json()["state"] == "in_negotiation"
        setup["control"].refresh_from_db()
        assert setup["control"].commitment_notes == "please commit"

    def test_posting_carries_the_promised_date(self, setup):
        control = drive_to(setup, "in_negotiation")
        res = setup["owner"].post(
            self.endpoint(control),
            {"commitment_state": "committed", "commitment_date": "2027-02-01"},
            format="json",
        )
        assert res.status_code == 200, res.json()
        control.refresh_from_db()
        # The date lands on the object itself and is frozen in the same step.
        assert str(control.eta) == "2027-02-01"
        assert str(control.committed_eta) == "2027-02-01"

    def test_posting_an_illegal_transition_is_refused(self, setup):
        res = setup["manager"].post(
            self.endpoint(setup["control"]),
            {"commitment_state": "committed"},
            format="json",
        )
        assert res.status_code == 400
        assert "commitment_state" in res.json()

    def test_posting_an_owner_move_as_a_non_owner_is_refused(self, setup):
        control = drive_to(setup, "in_negotiation")
        res = setup["manager"].post(
            self.endpoint(control),
            {"commitment_state": "committed", "commitment_date": "2027-02-01"},
            format="json",
        )
        assert res.status_code == 400


class TestListSurface:
    def test_the_list_carries_the_current_state_without_a_column(self, setup):
        drive_to(setup, "committed", eta="2027-05-05")
        res = setup["manager"].get("/api/applied-controls/")
        assert res.status_code == 200
        row = next(
            r for r in res.json()["results"] if r["id"] == str(setup["control"].id)
        )
        assert row["commitment_state"] == "committed"
        assert row["committed_eta"] == "2027-05-05"

    def test_filtering_reaches_through_to_the_live_cycle(self, setup):
        other = AppliedControl.objects.create(name="Untouched", folder=setup["domain"])
        drive_to(setup, "committed")

        res = setup["manager"].get("/api/applied-controls/?commitment_state=committed")
        ids = {r["id"] for r in res.json()["results"]}
        assert str(setup["control"].id) in ids
        assert str(other.id) not in ids

    def test_a_closed_cycle_does_not_match_the_filter(self, setup):
        control = drive_to(setup, "committed")
        patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="reopening",
        )
        # The old cycle is still `committed`, but it is no longer the live one.
        res = setup["manager"].get("/api/applied-controls/?commitment_state=committed")
        assert str(control.id) not in {r["id"] for r in res.json()["results"]}

        res = setup["manager"].get(
            "/api/applied-controls/?commitment_state=in_negotiation"
        )
        assert str(control.id) in {r["id"] for r in res.json()["results"]}


class TestChoicesEndpoint:
    def test_commitment_state_choices(self, setup):
        res = setup["manager"].get("/api/applied-controls/commitment_state/")
        assert res.status_code == 200
        assert set(res.json()) == {
            "--",
            "in_negotiation",
            "committed",
            "declined",
            "fulfilled",
        }

    def test_filtering_by_commitment_state(self, setup):
        other = AppliedControl.objects.create(name="Untouched", folder=setup["domain"])
        drive_to(setup, "in_negotiation")

        res = setup["manager"].get(
            "/api/applied-controls/?commitment_state=in_negotiation"
        )
        assert res.status_code == 200
        ids = {r["id"] for r in res.json()["results"]}
        assert str(setup["control"].id) in ids
        assert str(other.id) not in ids


class TestTaskTemplateComments:
    def test_a_comment_can_be_attached_to_a_task_template(self, setup):
        task = TaskTemplate.objects.create(name="Rotate", folder=setup["domain"])
        res = setup["manager"].post(
            "/api/comments/",
            {"body": "Chased the owner", "task_template": str(task.id)},
            format="json",
        )
        assert res.status_code == 201, res.json()
        comment = Comment.objects.get(id=res.json()["id"])
        assert comment.parent_object == task
        # The folder is resolved from the parent so RBAC checks the right one.
        assert comment.folder == setup["domain"]

    def test_two_parents_are_still_refused(self, setup):
        task = TaskTemplate.objects.create(name="Rotate", folder=setup["domain"])
        res = setup["manager"].post(
            "/api/comments/",
            {
                "body": "Nope",
                "task_template": str(task.id),
                "applied_control": str(setup["control"].id),
            },
            format="json",
        )
        assert res.status_code == 400

    def test_comments_are_listed_for_their_task_template(self, setup):
        task = TaskTemplate.objects.create(name="Rotate", folder=setup["domain"])
        setup["manager"].post(
            "/api/comments/",
            {"body": "Chased the owner", "task_template": str(task.id)},
            format="json",
        )
        res = setup["manager"].get(f"/api/comments/?task_template={task.id}")
        assert res.status_code == 200
        assert [c["body"] for c in res.json()["results"]] == ["Chased the owner"]


class TestFindingsActionPlan:
    """The binder's action plan lists both remediation vehicles."""

    def make_binder_with_finding(self, setup):
        binder = FindingsAssessment.objects.create(
            name="Pentest 2027", folder=setup["domain"]
        )
        finding = Finding.objects.create(
            name="Weak cipher", folder=setup["domain"], findings_assessment=binder
        )
        return binder, finding

    def test_applied_controls_reach_the_plan_through_a_finding(self, setup):
        binder, finding = self.make_binder_with_finding(setup)
        finding.applied_controls.set([setup["control"]])

        res = setup["manager"].get(
            f"/api/applied-controls/?findings_assessments={binder.id}"
        )
        assert res.status_code == 200
        assert [r["id"] for r in res.json()["results"]] == [str(setup["control"].id)]

    def test_tasks_reach_the_plan_from_the_binder_or_from_a_finding(self, setup):
        binder, finding = self.make_binder_with_finding(setup)
        on_binder = TaskTemplate.objects.create(name="Retest", folder=setup["domain"])
        on_binder.findings_assessment.set([binder])
        on_finding = TaskTemplate.objects.create(name="Rotate", folder=setup["domain"])
        on_finding.findings.set([finding])
        TaskTemplate.objects.create(name="Unrelated", folder=setup["domain"])

        res = setup["manager"].get(
            f"/api/task-templates/?findings_assessments={binder.id}"
        )
        assert res.status_code == 200
        assert {r["name"] for r in res.json()["results"]} == {"Retest", "Rotate"}

    def test_the_control_list_serves_the_findings_themselves(self, setup):
        binder, finding = self.make_binder_with_finding(setup)
        finding.applied_controls.set([setup["control"]])

        row = (
            setup["manager"]
            .get(f"/api/applied-controls/?findings_assessments={binder.id}")
            .json()["results"][0]
        )
        # The list serializer drops `findings_count`, so the plan column asked for a
        # field that was never emitted; it shows the findings instead.
        assert "findings_count" not in row
        assert [f["str"] for f in row["findings"]] == ["Weak cipher"]

    def test_both_plan_tables_carry_the_commitment_state(self, setup):
        binder, finding = self.make_binder_with_finding(setup)
        finding.applied_controls.set([setup["control"]])
        task = TaskTemplate.objects.create(name="Retest", folder=setup["domain"])
        task.findings_assessment.set([binder])

        for url in (
            f"/api/applied-controls/?findings_assessments={binder.id}",
            f"/api/task-templates/?findings_assessments={binder.id}",
        ):
            row = setup["manager"].get(url).json()["results"][0]
            assert "commitment_state" in row
            assert "committed_eta" in row


class TestTaskAnalytics:
    def test_aggregates_the_filtered_queryset(self, setup):
        binder = FindingsAssessment.objects.create(name="Plan", folder=setup["domain"])
        task = TaskTemplate.objects.create(
            name="Retest", folder=setup["domain"], task_date="2020-01-01"
        )
        # The occurrence the editor creates with a one-time task, still open.
        TaskNode.objects.create(
            task_template=task,
            due_date="2020-01-01",
            scheduled_date="2020-01-01",
            folder=setup["domain"],
        )
        task.findings_assessment.set([binder])
        task.assigned_to.set([setup["owner_actor"]])
        TaskTemplate.objects.create(name="Elsewhere", folder=setup["domain"])

        res = setup["manager"].get(
            f"/api/task-templates/analytics/?findings_assessments={binder.id}"
        )
        assert res.status_code == 200, res.json()
        body = res.json()
        assert body["count"] == 1
        assert {b["key"]: b["count"] for b in body["due_buckets"]}["overdue"] == 1
        assert body["by_assignee"][0]["count"] == 1
        assert body["recurrence"] == {"one_time": 1, "recurrent": 0}

    def test_hidden_assignees_are_merged_into_one_anonymous_bucket(self, setup):
        """analytics builds its payload by hand, so it misses the masking that
        _filter_related_fields applies on list/retrieve. Actor visibility is its
        own policy and genuinely diverges from the tasks' one."""
        task = TaskTemplate.objects.create(name="Retest", folder=setup["domain"])
        task.assigned_to.set([setup["owner_actor"]])
        label = str(setup["owner_actor"])

        named = setup["manager"].get("/api/task-templates/analytics/").json()
        assert [b["label"] for b in named["by_assignee"]] == [label]

        with hide_all_actors():
            res = setup["manager"].get("/api/task-templates/analytics/")

        assert res.status_code == 200, res.json()
        body = res.json()
        assert label not in res.content.decode()
        assert body["by_assignee"] == [
            {
                "key": "_restricted",
                "label": None,
                "count": 1,
                "status_breakdown": [{"key": "_unset", "count": 1}],
            }
        ]

    def test_commitment_section_follows_the_flag(self, setup):
        task = TaskTemplate.objects.create(name="Retest", folder=setup["domain"])
        setup["manager"].patch(
            f"/api/task-templates/{task.id}/",
            {"commitment_state": "in_negotiation"},
            format="json",
        )

        body = setup["manager"].get("/api/task-templates/analytics/").json()
        assert body["commitment"]["by_state"]

        set_flag(False)
        assert (
            "commitment"
            not in setup["manager"].get("/api/task-templates/analytics/").json()
        )


class TestAppliedControlAnalytics:
    def test_hidden_owners_are_merged_into_one_anonymous_bucket(self, setup):
        label = str(setup["owner_actor"])

        named = setup["manager"].get("/api/applied-controls/analytics/").json()
        assert label in [b["label"] for b in named["top_owners"]]

        with hide_all_actors():
            res = setup["manager"].get("/api/applied-controls/analytics/")

        assert res.status_code == 200, res.json()
        assert label not in res.content.decode()
        buckets = res.json()["top_owners"]
        assert [b["key"] for b in buckets] == ["_restricted"]
        assert buckets[0]["label"] is None
        assert buckets[0]["count"] == 1


class TestRegister:
    def test_lists_promises_across_models(self, setup):
        drive_to(setup, "committed", eta="2027-04-04")
        task = TaskTemplate.objects.create(
            name="Rotate the key", folder=setup["domain"], is_recurrent=False
        )
        setup["manager"].patch(
            f"/api/task-templates/{task.id}/",
            {"commitment_state": "in_negotiation"},
            format="json",
        )

        res = setup["manager"].get("/api/commitments/")
        assert res.status_code == 200
        rows = {r["target"]["str"]: r for r in res.json()["results"]}
        assert set(rows) == {"Patch the thing", "Rotate the key"}
        assert rows["Patch the thing"]["target_type"] == "appliedcontrol"
        assert rows["Rotate the key"]["target_type"] == "tasktemplate"
        assert rows["Patch the thing"]["committed_eta"] == "2027-04-04"

    def test_closed_cycles_are_listed_too(self, setup):
        control = drive_to(setup, "committed", eta="2026-12-01")
        patch_control(
            setup["owner"],
            control,
            commitment_state="in_negotiation",
            commitment_notes="reopening",
        )
        res = setup["manager"].get("/api/commitments/")
        assert len(res.json()["results"]) == 2
        assert {r["is_current"] for r in res.json()["results"]} == {True, False}

        res = setup["manager"].get("/api/commitments/?is_current=true")
        assert len(res.json()["results"]) == 1

    def test_the_register_is_read_only(self, setup):
        drive_to(setup, "committed")
        entry = Commitment.objects.first()
        created = setup["manager"].post("/api/commitments/", {}, format="json")
        assert created.status_code == 405
        patched = setup["manager"].patch(
            f"/api/commitments/{entry.id}/", {"state": "fulfilled"}, format="json"
        )
        assert patched.status_code == 405
        deleted = setup["manager"].delete(f"/api/commitments/{entry.id}/")
        assert deleted.status_code == 405

    @pytest.mark.parametrize("role", ["BI-RL-AUD", "BI-RL-APP"])
    def test_a_reader_can_read_the_transitions_of_a_task(self, setup, role):
        """Reading the legal steps is part of reading the object. A role without
        `transition_commitment` that was refused here got a panel claiming
        "not started" next to a commitment row saying otherwise.

        Uses a task template rather than a control so the read is decided by the
        caller's own role on the domain, not by any ambient visibility.
        """
        domain = setup["domain"]
        task = TaskTemplate.objects.create(name="Read me", folder=domain)
        user = User.objects.create_user(f"commitment-{role.lower()}@tests.com")
        group = UserGroup.objects.create(name=f"grp-{role}", folder=domain)
        group.user_set.add(user)
        assignment = RoleAssignment.objects.create(
            user_group=group,
            role=Role.objects.get(name=role),
            folder=domain,
            is_recursive=True,
        )
        assignment.perimeter_folders.add(domain)
        client = APIClient()
        client.force_authenticate(user)

        url = f"/api/task-templates/{task.id}/commitment_transitions/"
        read = client.get(url)
        assert read.status_code == 200
        assert [t["allowed"] for t in read.json()["transitions"]] == [False]
        # Taking a step stays its own right.
        taken = client.post(url, {"commitment_state": "in_negotiation"}, format="json")
        assert taken.status_code == 403

    def test_the_register_is_gated_by_the_flag(self, setup):
        set_flag(False)
        assert setup["manager"].get("/api/commitments/").status_code == 403

    def test_a_commitment_is_scoped_to_its_object_folder(self, setup):
        drive_to(setup, "committed")
        entry = Commitment.objects.get()
        assert entry.folder == setup["domain"]

    def test_moving_the_object_moves_its_commitments(self, setup):
        control = drive_to(setup, "committed")
        elsewhere = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Elsewhere",
            content_type=Folder.ContentType.DOMAIN,
        )
        patch_control(setup["manager"], control, folder=str(elsewhere.id))
        assert Commitment.objects.get().folder == elsewhere


class TestTaskTemplates:
    def test_a_one_time_task_carries_a_commitment(self, setup):
        task = TaskTemplate.objects.create(
            name="Rotate the key", folder=setup["domain"], is_recurrent=False
        )
        res = setup["manager"].patch(
            f"/api/task-templates/{task.id}/",
            {"commitment_state": "in_negotiation"},
            format="json",
        )
        assert res.status_code == 200, res.json()
        task.refresh_from_db()
        assert task.commitment_state == "in_negotiation"

    def test_a_recurrent_task_hides_the_fields_entirely(self, setup):
        task = TaskTemplate.objects.create(
            name="Quarterly review",
            folder=setup["domain"],
            is_recurrent=True,
            schedule={"interval": 3, "frequency": "MONTHLY"},
        )
        body = setup["manager"].get(f"/api/task-templates/{task.id}/").json()
        assert "commitment_state" not in body

    def test_a_recurrent_task_refuses_a_commitment(self, setup):
        task = TaskTemplate.objects.create(
            name="Quarterly review",
            folder=setup["domain"],
            is_recurrent=True,
            schedule={"interval": 3, "frequency": "MONTHLY"},
        )
        res = setup["manager"].patch(
            f"/api/task-templates/{task.id}/",
            {"commitment_state": "in_negotiation"},
            format="json",
        )
        # The field is popped for a recurrent template, so the state cannot move.
        task.refresh_from_db()
        assert task.commitment_state == "--"
        assert res.status_code in (200, 400)

    def test_transitions_endpoint_is_empty_for_a_recurrent_task(self, setup):
        task = TaskTemplate.objects.create(
            name="Quarterly review",
            folder=setup["domain"],
            is_recurrent=True,
            schedule={"interval": 3, "frequency": "MONTHLY"},
        )
        res = setup["manager"].get(
            f"/api/task-templates/{task.id}/commitment_transitions/"
        )
        assert res.status_code == 200
        assert res.json()["transitions"] == []


def respondent_on(folder: Folder, user: User, role: str) -> APIClient:
    group = UserGroup.objects.create(name=f"grp-{user.email}", folder=folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role),
        folder=folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(folder)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def vendor_task(setup: dict) -> dict:
    """A remediation task the reviewer raised in a third party's workspace."""
    workspace = Folder.objects.create(
        parent_folder=setup["domain"],
        name="Vendor workspace",
        content_type=Folder.ContentType.ENCLAVE,
    )
    respondent = User.objects.create_user("commitment-respondent@tests.com")
    respondent_client = respondent_on(workspace, respondent, "BI-RL-TPR")
    task = TaskTemplate.objects.create(name="Adopt a security policy", folder=workspace)
    task.assigned_to.set(Actor.get_all_for_user(respondent))
    return {
        "workspace": workspace,
        "task": task,
        "respondent": respondent_client,
        "reviewer": setup["manager"],
    }


class TestVendorTaskSteps:
    """The reviewer drives the commitment, the respondent only answers it."""

    @staticmethod
    def step(
        client: APIClient, task: TaskTemplate, state: str, **extra: str
    ) -> Response:
        return client.post(
            f"/api/task-templates/{task.id}/commitment_transitions/",
            {"commitment_state": state, **extra},
            format="json",
        )

    def drive(self, vendor_task: dict, *steps: tuple[str, str, dict]) -> None:
        for side, state, extra in steps:
            res = self.step(vendor_task[side], vendor_task["task"], state, **extra)
            assert res.status_code == 200, res.json()

    OPEN = ("reviewer", "in_negotiation", {})
    COMMIT = ("respondent", "committed", {"commitment_date": "2027-03-31"})
    DECLINE = ("respondent", "declined", {"commitment_notes": "not this year"})
    FULFIL = ("reviewer", "fulfilled", {})
    REOPEN_NOTE = {"commitment_notes": "the policy was withdrawn"}

    def test_the_respondent_cannot_open_a_negotiation(self, vendor_task: dict) -> None:
        res = self.step(
            vendor_task["respondent"], vendor_task["task"], "in_negotiation"
        )
        assert res.status_code == 400

    def test_the_respondent_answers_the_reviewer(self, vendor_task: dict) -> None:
        self.drive(vendor_task, self.OPEN, self.COMMIT)

    def test_only_the_reviewer_relaunches_after_a_decline(
        self, vendor_task: dict
    ) -> None:
        self.drive(vendor_task, self.OPEN, self.DECLINE)
        task = vendor_task["task"]
        assert (
            self.step(vendor_task["respondent"], task, "in_negotiation").status_code
            == 400
        )
        assert (
            self.step(vendor_task["reviewer"], task, "in_negotiation").status_code
            == 200
        )

    def test_only_the_reviewer_reopens_a_fulfilled_commitment(
        self, vendor_task: dict
    ) -> None:
        self.drive(vendor_task, self.OPEN, self.COMMIT, self.FULFIL)
        task = vendor_task["task"]
        assert (
            self.step(
                vendor_task["respondent"], task, "in_negotiation", **self.REOPEN_NOTE
            ).status_code
            == 400
        )
        assert (
            self.step(
                vendor_task["reviewer"], task, "in_negotiation", **self.REOPEN_NOTE
            ).status_code
            == 200
        )
        task.refresh_from_db()
        assert task.commitment_reopen_count == 1

    def test_reopening_a_fulfilled_commitment_starts_without_the_promised_date(
        self, vendor_task: dict
    ) -> None:
        commit_in_the_past = (
            "respondent",
            "committed",
            {"commitment_date": "2020-01-31"},
        )
        self.drive(vendor_task, self.OPEN, commit_in_the_past, self.FULFIL)
        task = vendor_task["task"]
        self.step(vendor_task["reviewer"], task, "in_negotiation", **self.REOPEN_NOTE)
        task.refresh_from_db()
        assert task.committed_eta is None
        assert not task.commitment_is_breached
        assert [cycle.committed_eta for cycle in task.commitment_history] == [
            date(2020, 1, 31)
        ]

    def test_the_respondent_cannot_open_in_a_sub_folder_of_the_workspace(
        self, vendor_task: dict
    ) -> None:
        sub_folder = Folder.objects.create(
            parent_folder=vendor_task["workspace"],
            name="Vendor sub-folder",
            content_type=Folder.ContentType.DOMAIN,
        )
        task = TaskTemplate.objects.create(name="Nested", folder=sub_folder)
        task.assigned_to.set(vendor_task["task"].assigned_to.all())
        res = self.step(vendor_task["respondent"], task, "in_negotiation")
        assert res.status_code == 400
        assert res.json() == {"commitment_state": ["onlyTheReviewerCanDoThis"]}

    def test_reopening_a_fulfilled_commitment_needs_a_note(
        self, vendor_task: dict
    ) -> None:
        self.drive(vendor_task, self.OPEN, self.COMMIT, self.FULFIL)
        res = self.step(vendor_task["reviewer"], vendor_task["task"], "in_negotiation")
        assert res.json() == {"commitment_notes": ["aNoteIsRequiredForThisTransition"]}

    def test_the_respondent_cannot_launch_by_creating_the_task(
        self, vendor_task: dict
    ) -> None:
        res = vendor_task["respondent"].post(
            "/api/task-templates/",
            {
                "name": "Self-raised",
                "folder": str(vendor_task["workspace"].id),
                "commitment_state": "in_negotiation",
            },
            format="json",
        )
        assert res.json() == {"commitment_state": ["onlyTheReviewerCanDoThis"]}
        assert not TaskTemplate.objects.filter(name="Self-raised").exists()

    @staticmethod
    def analyst_elsewhere(vendor_task: dict) -> tuple[APIClient, Folder]:
        """A respondent of the workspace who is also an analyst in an unrelated domain."""
        elsewhere = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Unrelated domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        user = User.objects.create_user("commitment-analyst-respondent@tests.com")
        respondent_on(elsewhere, user, "BI-RL-ANA")
        return respondent_on(vendor_task["workspace"], user, "BI-RL-TPR"), elsewhere

    @staticmethod
    def move(
        client: APIClient, task: TaskTemplate, folder: Folder, state: str
    ) -> Response:
        return client.patch(
            f"/api/task-templates/{task.id}/",
            {"folder": str(folder.id), "commitment_state": state},
            format="json",
        )

    def test_the_respondent_cannot_launch_by_moving_a_task_in(
        self, vendor_task: dict
    ) -> None:
        client, elsewhere = self.analyst_elsewhere(vendor_task)
        task = TaskTemplate.objects.create(name="Moved in", folder=elsewhere)
        res = self.move(client, task, vendor_task["workspace"], "in_negotiation")
        assert res.status_code == 400
        assert res.json() == {"commitment_state": ["onlyTheReviewerCanDoThis"]}
        task.refresh_from_db()
        assert task.folder_id == elsewhere.id

    def test_the_respondent_cannot_launch_by_moving_a_task_out(
        self, vendor_task: dict
    ) -> None:
        client, elsewhere = self.analyst_elsewhere(vendor_task)
        task = vendor_task["task"]
        res = self.move(client, task, elsewhere, "in_negotiation")
        assert res.status_code == 400
        assert res.json() == {"commitment_state": ["onlyTheReviewerCanDoThis"]}
        task.refresh_from_db()
        assert task.folder_id == vendor_task["workspace"].id

    def test_the_respondent_cannot_fulfil_by_moving_a_task_in(
        self, vendor_task: dict
    ) -> None:
        client, elsewhere = self.analyst_elsewhere(vendor_task)
        task = TaskTemplate.objects.create(name="Promised", folder=elsewhere)
        task.assigned_to.set(vendor_task["task"].assigned_to.all())
        apply_transition(task, "in_negotiation")
        apply_transition(task, "committed", promised_date=date(2027, 3, 31))
        res = self.move(client, task, vendor_task["workspace"], "fulfilled")
        assert res.status_code == 400
        assert res.json() == {
            "commitment_state": ["theAccountableActorCannotCloseTheirOwnCommitment"]
        }
        task.refresh_from_db()
        assert task.commitment_state == "committed"

    def delay_validated_as_respondent(
        self, task: TaskTemplate
    ) -> TaskTemplateWriteSerializer:
        request = Request(APIRequestFactory().post("/"))
        request.user = User.objects.get(email="commitment-respondent@tests.com")
        delay = TaskTemplateWriteSerializer(
            task,
            data={
                "commitment_state": "in_negotiation",
                "commitment_notes": "late",
                "name": "Renamed with the delay",
            },
            partial=True,
            context={"request": request, "commitment_transition": True},
        )
        assert delay.is_valid(), delay.errors
        return delay

    def test_a_delay_does_not_overwrite_a_fulfilment_made_meanwhile(
        self, vendor_task: dict
    ) -> None:
        self.drive(vendor_task, self.OPEN, self.COMMIT)
        task = vendor_task["task"]
        delay = self.delay_validated_as_respondent(task)
        apply_transition(task, "fulfilled")

        with pytest.raises(ValidationError) as refused:
            delay.save()
        assert refused.value.detail == {
            "commitment_state": ["commitmentChangedMeanwhile"]
        }
        task.refresh_from_db()
        assert task.commitment_state == "fulfilled"
        assert task.name == "Adopt a security policy"

    def test_two_first_openings_at_once_refuse_the_second(
        self, vendor_task: dict
    ) -> None:
        task = vendor_task["task"]
        request = Request(APIRequestFactory().post("/"))
        request.user = User.objects.get(email="commitment-manager@tests.com")
        second = TaskTemplateWriteSerializer(
            task,
            data={"commitment_state": "in_negotiation"},
            partial=True,
            context={"request": request, "commitment_transition": True},
        )
        assert second.is_valid(), second.errors
        Commitment.objects.create(target=task, state="in_negotiation")
        # The first opening committed after the second read "no row": nothing was
        # there to lock, so the second's locked read still finds nothing.
        unlocked = MagicMock()
        unlocked.filter.return_value.first.return_value = None
        with patch.object(
            Commitment.objects, "select_for_update", return_value=unlocked
        ):
            with pytest.raises(ValidationError) as refused:
                second.save()
        assert refused.value.detail == {
            "commitment_state": ["commitmentChangedMeanwhile"]
        }

    def test_the_respondent_can_still_ask_for_a_delay(self, vendor_task: dict) -> None:
        self.drive(vendor_task, self.OPEN, self.COMMIT)
        res = self.step(
            vendor_task["respondent"],
            vendor_task["task"],
            "in_negotiation",
            commitment_notes="supplier delay",
        )
        assert res.status_code == 200, res.json()

    def test_the_offered_steps_match_what_the_respondent_may_take(
        self, vendor_task: dict
    ) -> None:
        self.drive(vendor_task, self.OPEN, self.DECLINE)
        body = (
            vendor_task["respondent"]
            .get(
                f"/api/task-templates/{vendor_task['task'].id}/commitment_transitions/"
            )
            .json()
        )
        assert {t["value"]: t["allowed"] for t in body["transitions"]} == {
            "in_negotiation": False
        }

    def test_an_internal_auditee_still_opens_a_negotiation_on_their_control(
        self, setup: dict
    ) -> None:
        auditee = User.objects.create_user("commitment-auditee@tests.com")
        client = respondent_on(setup["domain"], auditee, "BI-RL-ADE")
        setup["control"].owner.set(Actor.get_all_for_user(auditee))
        res = patch_control(client, setup["control"], commitment_state="in_negotiation")
        assert res.status_code == 200, res.json()
