import pytest
from rest_framework.test import APIClient

from core.models import (
    Actor,
    AppliedControl,
    Comment,
    Commitment,
    Finding,
    FindingsAssessment,
    TaskTemplate,
)
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, User


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
        assert (
            setup["manager"].post("/api/commitments/", {}, format="json").status_code
            == 405
        )
        assert (
            setup["manager"]
            .patch(
                f"/api/commitments/{entry.id}/", {"state": "fulfilled"}, format="json"
            )
            .status_code
            == 405
        )
        assert (
            setup["manager"].delete(f"/api/commitments/{entry.id}/").status_code == 405
        )

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
