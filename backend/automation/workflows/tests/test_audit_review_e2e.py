"""The shipped `Audit — AI evidence challenge` library, run end to end.

test_shipped_libraries proves it publishes. This proves it *works*: a real
audit, a well-backed requirement and a thin one, a stubbed model, and a Record
document at the end — with the audit's own results untouched, which is the
whole claim the sample makes.
"""

import json
from datetime import date, timedelta
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

# Only the backed requirement reaches the model: the other one is settled by
# counting, which is the point of the routing.
JUDGEMENT = json.dumps(
    {
        "reasoning": "The control names an access review and the evidence has a link.",
        "shows": "The signed access review is attached and dated this quarter.",
        "missing": "",
    }
)
# The working-out fills `reasoning` and the reviewer-facing field stays a
# sentence. Neither is capped: a cap severs the sentence at the limit.
THINKS_ALOUD = json.dumps(
    {
        "reasoning": (
            "analysis<|message|>We need an answer. The control names an access "
            "review and the evidence carries a link, so it is attached. " + "x" * 400
        ),
        "shows": "The signed access review is attached and dated this quarter.",
        "missing": "",
    }
)
# One canned answer per question the review asks.
PARTIAL_JUDGEMENT = json.dumps(
    {
        "reasoning": "The observation names the two lab segments still outside the rollout.",
        "shows": "Rolled out everywhere except the two lab segments, which the observation names.",
        "missing": "",
    }
)
EXCLUSION_JUDGEMENT = json.dumps(
    {
        "reasoning": "The organisation operates no industrial control systems at all.",
        "shows": "Excluded because the organisation operates no industrial control systems.",
        "missing": "",
    }
)
# No section stubs: the document is assembled from the records, so the only
# completions a run needs are its judgements.


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
        # A fixture that trips a rule never reaches the model: the defaults
        # (`--`, `draft`) trip CompliantNoActiveControl and EvidenceAllDraft.
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


def make_claims_audit(domain):
    """One requirement per result the review knows how to question, each built
    so the quality rules pass it — a rule finding would settle the verdict by
    counting and the requirement would never reach its prompt."""
    framework = Framework.objects.create(
        name="FW claims",
        urn="urn:test:audit-claims:fw",
        folder=Folder.get_root_folder(),
    )
    perimeter = Perimeter.objects.create(name="P claims", folder=domain)
    audit = ComplianceAssessment.objects.create(
        name="ISO 27001 — claims",
        framework=framework,
        perimeter=perimeter,
        folder=domain,
    )
    Result = RequirementAssessment.Result
    plan = date.today() + timedelta(days=90)
    rows = []
    for ref_id, result in (
        ("C.1", Result.COMPLIANT),
        ("C.2", Result.PARTIALLY_COMPLIANT),
        ("C.3", Result.NOT_APPLICABLE),
        ("C.4", Result.NON_COMPLIANT),
    ):
        requirement = RequirementNode.objects.create(
            name=f"Requirement {ref_id}",
            ref_id=ref_id,
            description="The organisation restricts and reviews access.",
            urn=f"urn:test:audit-claims:fw:{ref_id}",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        assessment = RequirementAssessment.objects.create(
            compliance_assessment=audit,
            requirement=requirement,
            folder=domain,
            result=result,
            observation="Checked with the platform team.",
        )
        # Non-compliance describes itself: no control, no evidence, and no rule
        # has anything to say about it.
        if result in (Result.COMPLIANT, Result.PARTIALLY_COMPLIANT):
            control = AppliedControl.objects.create(
                name=f"Control {ref_id}",
                folder=domain,
                status="active",
                # A partial claim with no date anywhere trips PartialNoPlan.
                eta=plan if result == Result.PARTIALLY_COMPLIANT else None,
            )
            assessment.applied_controls.add(control)
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
    # The publisher becomes the version's run identity, which every read and
    # write is checked against.
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
        # A drained call can enqueue another; stop when the queue stops growing.
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
        fake = FakeLLM(JUDGEMENT)
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
        # Only the requirement the rules pass needs one, and nothing writes
        # the document.
        assert len(fake.calls) == 1

        container = DocumentContainer.objects.get(folder=domain)
        assert container.document_type == DocumentContainer.DocumentType.RECORD
        assert "ISO 27001 — 2026" in container.name

        document = ManagedDocument.objects.get(container=container)
        revision = document.current_revision
        assert revision.version_number == 1
        assert revision.status == "draft"
        content = revision.content
        assert "## Needs a look" in content
        # Assembled from the records, each under its own heading.
        assert "A.5.2" in content and "has no evidence attached" in content
        assert "The signed access review is attached" in content
        # The audit is reachable from the record, via a plain internal link.
        assert f"(/compliance-assessments/{audit.id})" in content

    def test_each_requirement_is_collected_as_a_record(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        """Which section a requirement lands in is a fact in the data, not
        something the write-up infers from a sentence."""
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
        """`on_item_error: continue` keeps the sweep going and `collect` skips
        the failed iteration, so the record has to say so — otherwise the page
        reads as though that requirement was reviewed and found fine."""
        fake = FakeLLM(
            "not json at all",
            "not json at all",  # max_attempts: 2
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
        assert "absent from the lists above: []" in content
        # The four sections are the document's shape, whatever the model wrote
        # inside them.
        for heading in (
            "## Concerns",
            "## Needs a look",
            "## Known gaps",
            "## Backed by the record",
        ):
            assert heading in content
        # Counted by the database, not written by anyone: two compliant, and a
        # zero in every other row.
        assert "| Compliant | 2 |" in content
        assert "| **Total assessable** | **2** |" in content

    def test_the_working_out_goes_to_reasoning_and_never_to_the_page(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """What keeps deliberation off the page is the schema having a field for
        it, not a length limit on the note — the limits are gone, and `reasoning`
        can run as long as the model needs."""
        fake = FakeLLM(THINKS_ALOUD)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review thinks",
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
        assert "The signed access review is attached" in " ".join(notes)

        content = ManagedDocument.objects.get(
            container__folder=domain
        ).current_revision.content
        # The record carries only the note, so nothing the model thought reaches
        # the document — no channel markers, no padding.
        assert "<|message|>" not in content
        assert "xxxx" not in content

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

    def test_each_claim_gets_its_own_question(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """Three results assert something, and each is wrong in its own way, so
        each has its own prompt and its own set of answers. A non-compliant
        requirement asserts nothing and is never sent anywhere."""
        fake = FakeLLM(JUDGEMENT, PARTIAL_JUDGEMENT, EXCLUSION_JUDGEMENT)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review claims",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_claims_audit(domain)
        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, fake
        )

        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        records = instance.node_outputs["per_requirement"]["results"]
        assert [(r["ref_id"], r["bucket"]) for r in records] == [
            ("C.1", "backed"),
            ("C.2", "known_gap"),
            ("C.3", "backed"),
        ]
        # Three judgements, one per claim. The non-compliant one is not fetched,
        # and no call writes the document.
        assert len(fake.calls) == 3
        asked = [call["prompt"] for call in fake.calls[:3]]
        assert "does what is attached actually show" in asked[0]
        assert 'is "partially compliant" actually the right answer' in asked[1]
        assert "whether it holds" in asked[2]

    def test_a_non_compliant_requirement_is_never_fetched(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """It asserts nothing, so the read filters it out before the loop sees
        it. It still has to be visible somewhere, and that somewhere is the
        breakdown table, which counts the audit rather than the review."""
        fake = FakeLLM(JUDGEMENT, PARTIAL_JUDGEMENT, EXCLUSION_JUDGEMENT)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review counted",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_claims_audit(domain)
        instance, fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, fake
        )

        # Three claims entered the review; the audit has four requirements.
        assert instance.node_outputs["per_requirement"]["count"] == 3
        # C.4 is in no prompt the model ever saw.
        assert not any("C.4" in call["context"] for call in fake.calls)
        assert len(fake.calls) == 3

        content = ManagedDocument.objects.get(
            container__folder=domain
        ).current_revision.content
        assert "3 requirement(s) entered the review" in content
        # Counted from the audit, so the one nobody reviewed is still on the page.
        assert "| Non-compliant | 1 |" in content
        assert "| Not applicable | 1 |" in content
        assert "| **Total assessable** | **4** |" in content

    def test_a_section_cannot_lose_a_record(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """The reason the sections are assembled rather than written: a model
        asked to render two dozen records has dropped one, and the page looked
        finished either way."""
        fake = FakeLLM(JUDGEMENT, PARTIAL_JUDGEMENT, EXCLUSION_JUDGEMENT)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review assembled",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_claims_audit(domain)
        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, fake
        )

        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        content = ManagedDocument.objects.get(
            container__folder=domain
        ).current_revision.content
        for record in instance.node_outputs["per_requirement"]["results"]:
            assert record["ref_id"] in content, record["ref_id"]
        # Each note reaches the page verbatim — nothing paraphrased it.
        assert "two lab segments" in content
        assert "no industrial control systems" in content

    def test_a_reassuring_sentence_never_outranks_a_request(
        self, dispatch, django_capture_on_commit_callbacks, monkeypatch
    ):
        """Two models have returned a positive answer beside a sentence asking
        for the evidence. There is no positive answer to return any more: what
        is in `missing` decides the section on its own, and `shows` is only ever
        the wording of a requirement that had nothing missing."""
        asks_for_more = json.dumps(
            {
                "reasoning": "The register is named but I have not seen it.",
                "shows": "The control names an annual awareness programme.",
                "missing": "Ask for the 2026 completion register; it is named but not attached.",
            }
        )
        fake = FakeLLM(asks_for_more)
        monkeypatch.setattr("chat.providers.get_llm_strict", lambda: fake, raising=True)
        domain = Folder.objects.create(
            name="Audit review asks",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, fake
        )

        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        judged = [
            record
            for record in instance.node_outputs["per_requirement"]["results"]
            if record["note"]
        ]
        assert [record["bucket"] for record in judged] == ["needs_look"]
        assert "Ask for the 2026 completion register" in judged[0]["note"]

        content = ManagedDocument.objects.get(
            container__folder=domain
        ).current_revision.content
        look = content.split("## Needs a look")[1].split("##")[0]
        assert "Ask for the 2026 completion register" in look
        # The reassuring sentence belongs to a requirement that had nothing
        # missing, so it is nowhere on this page.
        assert "The control names an annual awareness programme" not in content

    def test_it_hands_the_document_to_the_audit_s_reviewers(
        self, dispatch, django_capture_on_commit_callbacks, llm
    ):
        """The run ends by asking a person to read what it wrote."""
        from core.models import Actor, TaskNode, TaskTemplate
        from iam.models import User

        domain = Folder.objects.create(
            name="Audit review handover",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        audit, _rows = make_audit(domain)
        reviewer = Actor.objects.get(
            user=User.objects.create(email="reviewer@test.example")
        )
        audit.reviewers.add(reviewer)

        instance, _fake = self.run_it(
            domain, audit, dispatch, django_capture_on_commit_callbacks, llm
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables

        task = TaskTemplate.objects.get(folder=domain)
        assert list(task.assigned_to.all()) == [reviewer]
        assert list(task.compliance_assessments.all()) == [audit]
        assert audit.name in task.name

        container = DocumentContainer.objects.get(folder=domain)
        assert list(task.documents.all()) == [container]

        occurrence = TaskNode.objects.get(task_template=task)
        assert occurrence.due_date == date.today() + timedelta(days=14)
