"""attach_evidence: the one action that writes a file, so the file never
travels through the run context."""

import uuid

import pytest

from core.models import Evidence
from iam.models import Folder
from automation.workflows.actions import (
    required_permissions,
    validate_attach_evidence_config,
)
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowVersion,
)
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def attach_flow(folder, config):
    workflow = Workflow.objects.create(name=f"Attach {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    act = node(
        "action", label="Attach", action_config={"type": "attach_evidence", **config}
    )
    end = node("end")
    save_graph(
        version,
        {"nodes": [start, act, end], "edges": [edge(start, act), edge(act, end)]},
    )
    return version


class FakeResponse:
    def __init__(self, payload=b"report", status_code=200):
        self.payload = payload
        self.status_code = status_code

    def iter_content(self, size):
        for start in range(0, len(self.payload), size):
            yield self.payload[start : start + size]


@pytest.mark.django_db
class TestAttachEvidence:
    def test_writes_rendered_text_as_a_file(self):
        domain = make_domain("Text attach")
        evidence = Evidence.objects.create(name="Weekly report", folder=domain)
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "text",
                "filename": "digest.csv",
                "text": "name,status\nthing,ok\n",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        revision = evidence.revisions.order_by("-version").first()
        assert revision.attachment.read() == b"name,status\nthing,ok\n"
        assert instance.node_outputs["attach"]["bytes"] == 21

    def test_fetches_a_url_without_following_redirects(self, monkeypatch):
        domain = make_domain("Url attach")
        evidence = Evidence.objects.create(name="Scan report", folder=domain)
        seen = {}

        def fake_get(url, **kwargs):
            seen.update({"url": url, **kwargs})
            return FakeResponse(b"%PDF-1.7 fake")

        monkeypatch.setattr("requests.get", fake_get)
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "url",
                "url": "https://example.com/report.pdf",
                "filename": "report.pdf",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert seen["allow_redirects"] is False
        assert seen["stream"] is True
        revision = evidence.revisions.order_by("-version").first()
        assert revision.attachment.read() == b"%PDF-1.7 fake"

    def test_a_blocked_host_fails_the_node(self, monkeypatch):
        from core.net_safety import BlockedRequestError

        domain = make_domain("Blocked")
        evidence = Evidence.objects.create(name="Internal", folder=domain)

        def blocked(*args, **kwargs):
            raise BlockedRequestError("nope")

        monkeypatch.setattr("core.net_safety.assert_public_url_unless_dev", blocked)
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "url",
                "url": "http://169.254.169.254/latest/meta-data/",
                "filename": "meta.txt",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not evidence.revisions.exclude(attachment="").exists()

    def test_an_extension_outside_the_upload_allowlist_is_refused(self):
        domain = make_domain("Bad extension")
        evidence = Evidence.objects.create(name="Payload", folder=domain)
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "text",
                "filename": "payload.exe",
                "text": "whatever",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not evidence.revisions.exclude(attachment="").exists()

    def test_evidence_outside_scope_is_refused(self):
        domain = make_domain("Here attach")
        elsewhere = make_domain("Elsewhere attach")
        evidence = Evidence.objects.create(name="Foreign", folder=elsewhere)
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "text",
                "filename": "note.txt",
                "text": "hello",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_it_needs_the_change_permission(self):
        assert required_permissions({"type": "attach_evidence"}) == ["change_evidence"]


class TestAttachValidation:
    def _node(self, config):
        return WorkflowNode(action_config=config)

    def test_missing_pieces_are_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_attach_evidence_config(
                self._node({"type": "attach_evidence", "source": "url"})
            )
        }
        assert codes == {
            "action_attach_missing_evidence",
            "action_attach_missing_filename",
            "action_attach_missing_url",
        }

    def test_a_sound_config_passes(self):
        assert (
            validate_attach_evidence_config(
                self._node(
                    {
                        "type": "attach_evidence",
                        "evidence": "{{nodes.make.created_object_id}}",
                        "source": "text",
                        "filename": "digest-{{today}}.csv",
                        "text": "{{nodes.fetch.results}}",
                    }
                )
            )
            == []
        )


@pytest.mark.django_db
class TestCredentialsNeedHttps:
    """A secret or an Authorization header must not travel over cleartext,
    whatever the SSRF guard allows for plain http."""

    def test_a_secret_over_http_is_refused(self, monkeypatch):
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )
        domain = make_domain("Cleartext")
        evidence = Evidence.objects.create(name="Report", folder=domain)
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "url",
                "url": "http://example.com/report.pdf",
                "filename": "report.pdf",
                "headers": {"Authorization": "Bearer {{secrets.token}}"},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not evidence.revisions.exclude(attachment="").exists()

    def test_the_same_call_over_https_is_allowed(self, monkeypatch):
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )
        monkeypatch.setattr("requests.get", lambda url, **kw: FakeResponse(b"ok"))
        domain = make_domain("Encrypted")
        evidence = Evidence.objects.create(name="Report", folder=domain)
        version = attach_flow(
            domain,
            {
                "evidence": str(evidence.id),
                "source": "url",
                "url": "https://example.com/report.pdf",
                "filename": "report.pdf",
                "headers": {"Authorization": "Bearer token"},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED
