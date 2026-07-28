"""Tests for tabular digestion, the document import workflow, and the
consumer-backed importer (dry-run + apply)."""

import io
import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from openpyxl import Workbook

from chat.tabular import (
    TABULAR_CONTENT_TYPES,
    detect_target,
    digest_document,
    extract_records,
    header_signature,
    map_columns,
)
from chat.workflows.base import WorkflowContext
from chat.workflows.import_document import ImportDocumentWorkflow

XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

CONTROL_ROWS = [
    ["Name", "Description", "Status", "Impact", "Ref_Id", "Custom Col"],
    ["MFA", "Enforce MFA", "active", 3, "CTL-1", "x"],
    ["Backups", "Daily backups", "in_progress", 4, "CTL-2", "y"],
]


class _StubFieldFile:
    def __init__(self, raw: bytes):
        self._raw = raw

    def open(self, mode="rb"):
        return io.BytesIO(self._raw)


class _StubDocument:
    def __init__(self, raw: bytes, content_type: str, filename: str):
        self.id = uuid.uuid4()
        self.file = _StubFieldFile(raw)
        self.content_type = content_type
        self.filename = filename


class _StubSession:
    def __init__(self):
        self.workflow_state = {}

    def save(self, update_fields=None):
        pass


def _xlsx_bytes(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _controls_doc() -> _StubDocument:
    return _StubDocument(_xlsx_bytes(CONTROL_ROWS), XLSX_CT, "controls.xlsx")


def _ctx(documents=None, message="", session=None, request=None, folder_ids=None):
    return WorkflowContext(
        user_message=message,
        parsed_context=None,
        accessible_folder_ids=folder_ids or [],
        llm=None,
        session=session,
        documents=documents or [],
        request=request,
    )


def _run(workflow, ctx):
    return list(workflow.run(ctx))


# ── DB fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def admin_request(db):
    from core.apps import startup

    startup(sender=None)

    from rest_framework.test import APIRequestFactory

    from iam.models import User, UserGroup

    admin = User.objects.create_superuser("admin@chat-import.test")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    request = APIRequestFactory().post("/")
    request.user = admin
    return request


@pytest.fixture
def domain(admin_request):
    from iam.models import Folder

    return Folder.objects.create(
        name="Chat Import Tests",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


@pytest.fixture
def controls_document(domain):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from chat.models import IndexedDocument

    return IndexedDocument.objects.create(
        folder=domain,
        file=SimpleUploadedFile("controls.xlsx", _xlsx_bytes(CONTROL_ROWS)),
        filename="controls.xlsx",
        content_type=XLSX_CT,
        source_type=IndexedDocument.SourceType.CHAT,
    )


@pytest.fixture
def chat_session(admin_request, domain):
    from chat.models import ChatSession

    return ChatSession.objects.create(owner=admin_request.user)


# ── tabular (pure) ───────────────────────────────────────────────────


def test_digest_xlsx():
    digest = digest_document(_controls_doc())
    assert not digest.error
    assert digest.headers[0] == "Name"
    assert digest.normalized_headers == [
        "name",
        "description",
        "status",
        "impact",
        "ref_id",
        "custom col",
    ]
    assert digest.row_count == 2
    assert digest.sample_rows[0]["name"] == "MFA"
    assert digest.signature == header_signature(digest.normalized_headers)


def test_digest_csv_semicolon():
    raw = b"name;severity;status\nSQLi;critical;identified\n"
    doc = _StubDocument(raw, "text/csv", "findings.csv")
    digest = digest_document(doc)
    assert not digest.error
    assert digest.normalized_headers == ["name", "severity", "status"]
    assert digest.row_count == 1


def test_digest_empty_file_errors():
    doc = _StubDocument(_xlsx_bytes([]), XLSX_CT, "empty.xlsx")
    assert digest_document(doc).error


def test_signature_order_insensitive():
    assert header_signature(["b", "a"]) == header_signature(["a", "b"])
    assert header_signature(["a"]) != header_signature(["a", "b"])


def test_map_columns_aliases():
    mapped, unmapped = map_columns(["name", "impact", "custom col"], "applied_control")
    assert mapped == {"name": "name", "impact": "control_impact"}
    assert unmapped == ["custom col"]


def test_extract_records_renames_and_drops():
    mapped, _ = map_columns(
        ["name", "description", "status", "impact", "ref_id", "custom col"],
        "applied_control",
    )
    records = extract_records(_controls_doc(), mapped)
    assert len(records) == 2
    assert records[0]["name"] == "MFA"
    assert records[0]["control_impact"] == 3
    assert "custom col" not in records[0]


def test_detect_target_prefers_applied_control():
    headers = ["name", "status", "impact", "effort", "ref_id", "eta"]
    scores = detect_target(headers)
    assert scores[0][0] == "applied_control"


def test_detect_target_prefers_asset():
    headers = ["name", "type", "parent_assets", "ref_id"]
    scores = detect_target(headers)
    assert scores[0][0] == "asset"


# ── workflow turns without a document (pure) ─────────────────────────


def test_no_document_no_state_guides_user():
    events = _run(ImportDocumentWorkflow(), _ctx(message="import my file"))
    assert any(e.type == "token" for e in events)


def test_ambiguous_headers_ask_for_target():
    raw = _xlsx_bytes([["name", "status", "description"], ["a", "b", "c"]])
    doc = _StubDocument(raw, XLSX_CT, "ambiguous.xlsx")
    session = _StubSession()
    events = _run(ImportDocumentWorkflow(), _ctx(documents=[doc], session=session))
    assert any(e.type == "pending_choice" for e in events)
    assert session.workflow_state["step"] == "awaiting_target"


def test_cancel_clears_state():
    session = _StubSession()
    session.workflow_state = {
        "workflow": "import_document",
        "step": "import_review",
        "data": {},
    }
    events = _run(ImportDocumentWorkflow(), _ctx(message="cancel", session=session))
    assert session.workflow_state == {}
    assert any(e.type == "token" for e in events)


def test_tabular_content_types_match_upload_validation():
    from chat.upload_validation import CHAT_UPLOAD_CONTENT_TYPES

    assert TABULAR_CONTENT_TYPES <= set(CHAT_UPLOAD_CONTENT_TYPES.values())


# ── importer (DB) ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestImporter:
    def _mapping(self):
        mapped, _ = map_columns(
            ["name", "description", "status", "impact", "ref_id", "custom col"],
            "applied_control",
        )
        return mapped

    def test_dry_run_counts_without_writing(
        self, admin_request, domain, controls_document
    ):
        from chat.importer import run_import
        from core.models import AppliedControl

        report = run_import(
            admin_request,
            controls_document,
            self._mapping(),
            "applied_control",
            folder_id=str(domain.id),
            dry_run=True,
        )
        assert report["created"] == 2
        assert report["updated"] == 0
        assert report["failed"] == 0
        assert AppliedControl.objects.count() == 0

    def test_apply_then_reapply_updates(self, admin_request, domain, controls_document):
        from chat.importer import run_import
        from core.models import AppliedControl

        report = run_import(
            admin_request,
            controls_document,
            self._mapping(),
            "applied_control",
            folder_id=str(domain.id),
            dry_run=False,
        )
        assert report["created"] == 2
        controls = AppliedControl.objects.filter(folder=domain)
        assert controls.count() == 2
        assert controls.get(ref_id="CTL-1").name == "MFA"

        # Re-importing the same file matches on ref_id and updates in place.
        report = run_import(
            admin_request,
            controls_document,
            self._mapping(),
            "applied_control",
            folder_id=str(domain.id),
            dry_run=False,
        )
        assert report["created"] == 0
        assert report["updated"] == 2
        assert AppliedControl.objects.filter(folder=domain).count() == 2

    def test_findings_update_existing_assessment(self, admin_request, domain):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from chat.importer import run_import
        from chat.models import IndexedDocument
        from core.models import Finding, FindingsAssessment

        assessment = FindingsAssessment.objects.create(name="Q1 Pentest", folder=domain)
        Finding.objects.create(
            findings_assessment=assessment,
            name="Old SQLi",
            ref_id="F-1",
            folder=domain,
        )

        doc = IndexedDocument.objects.create(
            folder=domain,
            file=SimpleUploadedFile(
                "findings.xlsx",
                _xlsx_bytes(
                    [
                        ["ref_id", "name", "severity"],
                        ["F-1", "SQL injection (retested)", "high"],
                        ["F-2", "XSS on login", "medium"],
                    ]
                ),
            ),
            filename="findings.xlsx",
            content_type=XLSX_CT,
            source_type=IndexedDocument.SourceType.CHAT,
        )
        mapped, _ = map_columns(["ref_id", "name", "severity"], "finding")

        report = run_import(
            admin_request,
            doc,
            mapped,
            "finding",
            folder_id=str(domain.id),
            dry_run=False,
            target_id=str(assessment.id),
        )
        assert report["updated"] == 1
        assert report["created"] == 1
        # No new assessment was created; both findings live in the target.
        assert FindingsAssessment.objects.count() == 1
        assert assessment.findings.count() == 2
        assert assessment.findings.get(ref_id="F-1").name == "SQL injection (retested)"


# ── workflow turns with a real document (DB) ─────────────────────────


@pytest.mark.django_db
class TestWorkflowWithDocument:
    def test_digest_turn_dry_runs_and_proposes(
        self, admin_request, domain, controls_document, chat_session
    ):
        from core.models import AppliedControl

        ctx = _ctx(
            documents=[controls_document],
            session=chat_session,
            request=admin_request,
            folder_ids=[str(domain.id)],
        )
        events = _run(ImportDocumentWorkflow(), ctx)

        mapping_requests = [e for e in events if e.type == "mapping_request"]
        assert len(mapping_requests) == 1
        assert mapping_requests[0].content["signature"]

        narration = "".join(
            e.content
            for e in events
            if e.type == "token" and isinstance(e.content, str)
        )
        assert "controls.xlsx" in narration
        assert "custom col" in narration  # exceptions-first: ignored column named

        actions = [e for e in events if e.type == "pending_action"]
        assert len(actions) == 1
        assert actions[0].content["action"] == "import"
        assert actions[0].content["created"] == 2
        assert actions[0].content["updated"] == 0
        assert actions[0].content["folder_id"] == str(domain.id)

        chat_session.refresh_from_db()
        assert chat_session.workflow_state["step"] == "import_review"
        state_data = chat_session.workflow_state["data"]
        assert state_data["target"] == "applied_control"
        assert state_data["mapping"]["impact"] == "control_impact"

        # Dry-run must not have written anything
        assert AppliedControl.objects.count() == 0

    def test_stated_target_beats_detection(
        self, admin_request, domain, controls_document, chat_session
    ):
        ctx = _ctx(
            documents=[controls_document],
            message="import these as pentest findings",
            session=chat_session,
            request=admin_request,
            folder_ids=[str(domain.id)],
        )
        _run(ImportDocumentWorkflow(), ctx)
        chat_session.refresh_from_db()
        assert chat_session.workflow_state["data"]["target"] == "finding"

    def test_findings_flow_asks_for_container_then_updates(
        self, admin_request, domain, controls_document, chat_session
    ):
        from core.models import FindingsAssessment

        assessment = FindingsAssessment.objects.create(name="Q1 Pentest", folder=domain)

        workflow = ImportDocumentWorkflow()
        events = _run(
            workflow,
            _ctx(
                documents=[controls_document],
                message="import these as pentest findings",
                session=chat_session,
                request=admin_request,
                folder_ids=[str(domain.id)],
            ),
        )
        choices = [e for e in events if e.type == "pending_choice"]
        assert len(choices) == 1
        names = [i["name"] for i in choices[0].content["items"]]
        assert "Q1 Pentest" in names
        assert "Create a new assessment" in names
        chat_session.refresh_from_db()
        assert chat_session.workflow_state["step"] == "awaiting_container"

        events = _run(
            workflow,
            _ctx(
                message="Q1 Pentest",
                session=chat_session,
                request=admin_request,
                folder_ids=[str(domain.id)],
            ),
        )
        chat_session.refresh_from_db()
        assert chat_session.workflow_state["step"] == "import_review"
        assert chat_session.workflow_state["data"]["container_id"] == str(assessment.id)
        actions = [e for e in events if e.type == "pending_action"]
        assert actions[0].content["target_name"] == "Q1 Pentest"

    def test_target_reply_resumes_and_dry_runs(
        self, admin_request, domain, chat_session
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from chat.models import IndexedDocument

        doc = IndexedDocument.objects.create(
            folder=domain,
            file=SimpleUploadedFile(
                "ambiguous.xlsx",
                _xlsx_bytes([["name", "status", "description"], ["a", "b", "c"]]),
            ),
            filename="ambiguous.xlsx",
            content_type=XLSX_CT,
            source_type=IndexedDocument.SourceType.CHAT,
        )
        workflow = ImportDocumentWorkflow()
        _run(
            workflow,
            _ctx(
                documents=[doc],
                session=chat_session,
                request=admin_request,
                folder_ids=[str(domain.id)],
            ),
        )
        chat_session.refresh_from_db()
        assert chat_session.workflow_state["step"] == "awaiting_target"

        events = _run(
            workflow,
            _ctx(
                message="Assets",
                session=chat_session,
                request=admin_request,
                folder_ids=[str(domain.id)],
            ),
        )
        chat_session.refresh_from_db()
        assert chat_session.workflow_state["step"] == "import_review"
        assert chat_session.workflow_state["data"]["target"] == "asset"
        assert any(e.type == "pending_action" for e in events)


# ── apply endpoint guards (DB) ───────────────────────────────────────


@pytest.mark.django_db
class TestApplyImportGuards:
    @pytest.fixture
    def api_client(self, admin_request):
        from knox.models import AuthToken
        from rest_framework.test import APIClient

        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(admin_request.user)[1]}"
        )
        return client

    def _stage(self, session, doc, **overrides):
        mapped, _ = map_columns(
            ["name", "description", "status", "impact", "ref_id", "custom col"],
            "applied_control",
        )
        session.workflow_state = {
            "workflow": "import_document",
            "step": "import_review",
            "data": {
                "document_id": str(doc.id),
                "target": "applied_control",
                "mapping": mapped,
                **overrides,
            },
        }
        session.save(update_fields=["workflow_state"])

    def _session_with_doc(self, chat_session, controls_document):
        controls_document.source_content_type = ContentType.objects.get_for_model(
            type(chat_session)
        )
        controls_document.source_object_id = chat_session.id
        controls_document.save()
        return chat_session

    def test_second_confirm_is_rejected(
        self, api_client, chat_session, controls_document, domain
    ):
        from core.models import AppliedControl

        session = self._session_with_doc(chat_session, controls_document)
        self._stage(session, controls_document)
        url = f"/api/chat/sessions/{session.id}/import/"

        first = api_client.post(url, {}, format="json")
        assert first.status_code == 200, first.data
        assert AppliedControl.objects.filter(folder=domain).count() == 2

        second = api_client.post(url, {}, format="json")
        assert second.status_code == 400
        assert AppliedControl.objects.filter(folder=domain).count() == 2

    def test_malformed_state_returns_400(
        self, api_client, chat_session, controls_document
    ):
        session = self._session_with_doc(chat_session, controls_document)
        self._stage(session, controls_document)
        state = session.workflow_state
        del state["data"]["mapping"]
        session.workflow_state = state
        session.save(update_fields=["workflow_state"])

        resp = api_client.post(
            f"/api/chat/sessions/{session.id}/import/", {}, format="json"
        )
        assert resp.status_code == 400

    def test_unknown_target_returns_400(
        self, api_client, chat_session, controls_document
    ):
        session = self._session_with_doc(chat_session, controls_document)
        self._stage(session, controls_document, target="no_such_model")

        resp = api_client.post(
            f"/api/chat/sessions/{session.id}/import/", {}, format="json"
        )
        assert resp.status_code == 400
