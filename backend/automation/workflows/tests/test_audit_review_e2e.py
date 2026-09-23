"""The shipped `Audit — AI evidence challenge` library, run end to end.

test_shipped_libraries proves it publishes. This proves it *works*: a real
audit, a well-backed requirement and a thin one, a stubbed model, and a Record
document at the end — with the audit's own results untouched, which is the
whole claim the sample makes.
"""

import json
from pathlib import Path

import pytest
import yaml

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from doc_management.models import DocumentContainer, ManagedDocument
from iam.models import Folder
from automation.workflows import actions as workflow_actions
from automation.workflows import tasks as workflow_tasks
from automation.workflows.engine import create_instance, run_instance
from automation.workflows.import_export import import_workflow
from automation.workflows.models import WorkflowInstance
from automation.workflows.tests.helpers import publisher_user

LIBRARY = (
    Path(__file__).resolve().parents[3]
    / "library"
    / "libraries"
    / "workflow-compliance-audit-ai-review.yaml"
)

# Only the backed requirement reaches the model: the other one's verdict is
# settled by counting, which is the point of the routing.
JUDGEMENT = json.dumps(
    {
        "reasoning": "The control names an access review and the evidence has a link.",
        "verdict": "backed",
        "note": "The signed access review is attached and dated this quarter.",
    }
)
# What a reasoning model does when the schema gives it nowhere to think: the
# working-out lands in the reviewer-facing field. Over the cap, so it is
# refused and retried rather than filed as a finding.
SPILLED = json.dumps(
    {
        "reasoning": "",
        "verdict": "needs_look",
        "note": "analysis<|message|>We need to answer verdict and note. " + "x" * 300,
    }
)
CONCERNS_SECTION = "- A.5.2 — evidence has not left draft."
LOOK_SECTION = "Nothing in this group."
BACKED_SECTION = "- A.5.1 — the signed access review is attached."
SECTIONS = [CONCERNS_SECTION, LOOK_SECTION, BACKED_SECTION]


class FakeLLM:
    """Replays queued completions, and records what it was asked."""

    def __init__(self, *completions):
        self.completions = list(completions)
        self.calls = []

    def generate(self, prompt, context, history=None, directives="", **kwargs):  # noqa: ARG002
        self.calls.append({"prompt": prompt, "context": context, **kwargs})
        return self.completions.pop(0) if self.completions else ""


@pytest.fixture
def dispatch(monkeypatch):
    """Capture ai_call_task enqueues; drain() runs each one as it appears —
    a loop enqueues the next iteration's call only once this one lands."""
    captured = []
    call = workflow_tasks.ai_call_task.call_local
    monkeypatch.setattr(
        workflow_actions, "ai_call_task", lambda **kwargs: captured.append(kwargs)
    )

    class Dispatch:
        calls = captured

        @staticmethod
        def drain(limit=20):
            done = 0
            while done < len(captured):
                if done >= limit:  # pragma: no cover - runaway guard
                    raise AssertionError("more AI calls than the sample should make")
                call(**captured[done])
                done += 1
            return done

    return Dispatch


def make_audit(domain):
    """An audit claiming two requirements are met: one with a control and an
    attached evidence, one with a control and nothing behind it."""
    framework = Framework.objects.create(
        name="FW", urn="urn:test:audit-review:fw", folder=Folder.get_root_folder()
    )
    perimeter = Perimeter.objects.create(name="P", folder=domain)
    audit = ComplianceAssessment.objects.create(
        name="ISO 27001 — 2026", framework=framework, perimeter=perimeter, folder=domain
    )
    rows = []
    for ref_id, backed in (("A.5.1", True), ("A.5.2", False)):
        requirement = RequirementNode.objects.create(
            name=f"Requirement {ref_id}",
            ref_id=ref_id,
            description="The organisation restricts and reviews access.",
            urn=f"urn:test:audit-review:fw:{ref_id}",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        assessment = RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=requirement,
            folder=domain,
            result=RequirementAssessment.Result.COMPLIANT,
            observation="Checked with the platform team.",
        )
        # `active` and `approved` are what the quality rules look for: the
        # defaults (`--` and `draft`) trip CompliantNoActiveControl and
        # EvidenceAllDraft, and a fixture that trips a rule never reaches the
        # model at all.
        control = AppliedControl.objects.create(
            name=f"Control {ref_id}", folder=domain, status="active"
        )
        assessment.applied_controls.add(control)
        if backed:
            evidence = Evidence.objects.create(
                name=f"Review {ref_id}", folder=domain, status="approved"
            )
            EvidenceRevision.objects.create(
                evidence=evidence, version=1, link="https://example.test/review"
            )
            control.evidences.add(evidence)
        rows.append(assessment)
    return audit, rows


def install(domain):
    document = yaml.safe_load(LIBRARY.read_text())
    entry = document["objects"]["workflows"][0]
    workflow, _warnings = import_workflow(entry, domain, user=publisher_user())
    version = workflow.draft_version
    # Publishing is what attaches authority: the publisher becomes the version's
    # run identity, which is the identity every read and write is checked against.
    version.publish(publisher_user())
    workflow.refresh_from_db()
    return workflow.published_version


@pytest.mark.django_db
class TestAuditReviewSample:
    def run_it(self, domain, audit, dispatch, capture, llm):
        version = install(domain)
        with capture(execute=True):
            instance = create_instance(
                version,
                initiated_by=publisher_user(),
                initial_variables={"audit_id": str(audit.id)},
            )
            run_instance(instance)
        # Each drained call lets the engine take the next step, which may
        # enqueue another; keep going until the queue stops growing.
        while True:
            before = len(dispatch.calls)
            with capture(execute=True):
                dispatch.drain()
            if len(dispatch.calls) == before:
                break
        instance.refresh_from_db()
        return instance, llm

    @pytest.fixture
    def llm(self, monkeypatch):
        fake = FakeLLM(JUDGEMENT, *SECTIONS)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        return fake

    def test_it_files_the_review_as_a_record(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        domain = Folder.objects.create(
            name="Audit review e2e",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, rows = make_audit(domain)
        instance, fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, llm
        )

        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        # One judgement — only the requirement the rules pass needs one — plus
        # the three section writers. The flagged one never reaches the model.
        assert len(fake.calls) == 4

        container = DocumentContainer.objects.get(folder=domain)
        assert container.document_type == DocumentContainer.DocumentType.RECORD
        assert "ISO 27001 — 2026" in container.name

        document = ManagedDocument.objects.get(container=container)
        revision = document.current_revision
        assert revision.version_number == 1
        assert revision.status == "draft"
        content = revision.content
        assert "## Needs a look" in content
        # The audit is reachable from the record, via a plain internal link.
        assert f"(/compliance-assessments/{audit.id})" in content

    def test_each_requirement_is_collected_as_a_record(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        """The loop collects structured records, so which section a requirement
        lands in is a fact in the data rather than something the write-up has to
        infer from a sentence."""
        domain = Folder.objects.create(
            name="Audit review records",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, llm
        )
        records = instance.node_outputs["per_requirement"]["results"]
        assert [r["ref_id"] for r in records] == ["A.5.1", "A.5.2"]
        assert [r["bucket"] for r in records] == ["backed", "concern"]
        assert all(
            set(r)
            == {"ref_id", "name", "claimed", "bucket", "note", "errors", "warnings"}
            for r in records
        )
        assert records[0]["claimed"] == "compliant"
        # The flagged one carries the rule's own finding and no model prose.
        assert records[1]["note"] == ""
        # No evidence at all on this one, so this is the rule that speaks.
        assert "requirementAssessmentCompliantNoEvidence" in records[1]["warnings"]

    def test_the_audit_itself_is_untouched(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        """The claim the sample makes out loud: it questions the results, it
        cannot change them."""
        domain = Folder.objects.create(
            name="Audit review untouched",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, rows = make_audit(domain)
        before = [(row.result, row.score, row.observation) for row in rows]
        self.run_it(domain, audit, dispatch, django_capture_on_commit_callbacks, llm)
        for row, was in zip(rows, before):
            row.refresh_from_db()
            assert (row.result, row.score, row.observation) == was

    def test_a_requirement_the_model_failed_on_is_named_as_missing(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """`on_item_error: continue` keeps the sweep going, and `collect` skips
        the iteration that failed — so the failed requirement is absent from the
        write-up. The record has to say that happened, or it reads as though the
        requirement was reviewed and found fine."""
        fake = FakeLLM(
            "not json at all",
            "not json at all",  # max_attempts: 2
            *SECTIONS,
        )
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review partial",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, fake
        )

        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        loop_output = instance.node_outputs["per_requirement"]
        assert loop_output["count"] == 2
        # The rule-flagged one still lands; only the judged one is lost.
        assert [r["bucket"] for r in loop_output["results"]] == ["concern"]
        assert len(loop_output["errors"]) == 1

        content = ManagedDocument.objects.get(
            container__folder=domain
        ).current_revision.content
        assert "2 requirement(s) entered the review" in content
        # The failure is on the page, not swallowed.
        assert "did not return valid JSON" in content

    def test_a_clean_run_says_nothing_failed(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        domain = Folder.objects.create(
            name="Audit review clean",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        self.run_it(domain, audit, dispatch, django_capture_on_commit_callbacks, llm)
        content = ManagedDocument.objects.get(
            container__folder=domain
        ).current_revision.content
        assert "2 requirement(s) entered the review" in content
        assert "absent from the list above: []" in content
        # The three sections are the document's shape, whatever the model wrote
        # inside them.
        for heading in (
            "## Concerns",
            "## Needs a look",
            "## Backed by evidence",
        ):
            assert heading in content

    def test_a_note_that_spills_the_working_out_is_refused_and_retried(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """The cap lives in the schema, so an over-long note fails validation
        and buys a retry (max_attempts: 2). The prompt asking for brevity is
        not what enforces it."""
        fake = FakeLLM(SPILLED, JUDGEMENT, *SECTIONS)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review spill",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, fake
        )

        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        loop_output = instance.node_outputs["per_requirement"]
        assert loop_output["errors"] == []
        notes = [record["note"] for record in loop_output["results"]]
        # The retry's answer is what was collected; the spill never reached it.
        assert not any("<|message|>" in note for note in notes)
        assert any("The signed access review is attached" in note for note in notes)

    def test_the_model_is_shown_the_evidence_on_the_control(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        """Indirect evidence is the point of the read-side work: evidence
        attached to a control, not to the requirement, still has to reach the
        prompt — and an evidence with nothing behind it must be visible as
        such."""
        domain = Folder.objects.create(
            name="Audit review inputs",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        _instance, fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, llm
        )
        backed = fake.calls[0]["context"]
        assert "Review A.5.1" in backed
        assert '"attached": true' in backed
        assert "The organisation restricts and reviews access." in backed
        assert "Checked with the platform team." in backed
        # The flagged requirement is never put to the model as a *judgement*:
        # a rule already answered it, so asking would only invite it to be
        # overruled. (The section writers do see every record — they are writing
        # prose about them, not deciding them, which is why the schema is what
        # tells the two kinds of call apart.)
        judgements = [call for call in fake.calls if call.get("schema")]
        assert len(judgements) == 1
        assert "A.5.2" not in judgements[0]["context"]
