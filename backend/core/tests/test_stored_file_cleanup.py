"""A deleted row must not leave its file in storage, including via cascade."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from automation.models import PostureAssessment, PostureRun
from chat.models import IndexedDocument, QuestionnaireRun
from core.models import (
    Answer,
    AnswerAttachment,
    ComplianceAssessment,
    CustomDocHtmlTemplate,
    CustomWordTemplate,
    Evidence,
    EvidenceRevision,
    Framework,
    Question,
    RequirementAssessment,
    RequirementNode,
    RequirementNodeAttachment,
)
from doc_management.models import (
    DocumentAttachment,
    DocumentContainer,
    DocumentRevision,
    ManagedDocument,
)
from iam.models import Folder, User
from portals.models import PublicDocument


def _domain():
    if Folder.get_root_folder() is None:
        Folder._init_root_folder()
    return Folder.objects.create(
        name="Attachments",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def _upload(name):
    return SimpleUploadedFile(name, b"stored-bytes")


def _stored(obj, attr):
    field = getattr(obj, attr)
    assert field.name and field.storage.exists(field.name)
    return field.storage, field.name


def _gone(stored):
    for storage, name in stored:
        assert not storage.exists(name)


def _evidence_revision():
    folder = _domain()
    evidence = Evidence.objects.create(name="Policy", folder=folder)
    revision = EvidenceRevision.objects.create(
        evidence=evidence, attachment=_upload("policy.pdf")
    )
    return revision, evidence, [_stored(revision, "attachment")]


def _requirement_node_attachment():
    folder = _domain()
    framework = Framework.objects.create(name="Framework", folder=folder)
    node = RequirementNode.objects.create(
        framework=framework,
        urn="urn:test:attachment:node",
        assessable=True,
        folder=folder,
    )
    attachment = RequirementNodeAttachment.objects.create(
        requirement_node=node, framework=framework, file=_upload("splash.png")
    )
    return attachment, node, [_stored(attachment, "file")]


def _answer_attachment():
    folder = _domain()
    framework = Framework.objects.create(name="Framework", folder=folder)
    node = RequirementNode.objects.create(
        framework=framework,
        urn="urn:test:attachment:req",
        assessable=True,
        folder=folder,
    )
    question = Question.objects.create(
        requirement_node=node,
        urn="urn:test:attachment:question",
        text="Attach a file",
        folder=folder,
    )
    audit = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, folder=folder
    )
    assessment = RequirementAssessment.objects.create(
        compliance_assessment=audit, requirement=node, folder=folder
    )
    answer = Answer.objects.create(
        requirement_assessment=assessment, question=question, folder=folder
    )
    attachment = AnswerAttachment.objects.create(
        answer=answer, file=_upload("note.txt"), filename="note.txt"
    )
    return attachment, answer, [_stored(attachment, "file")]


def _custom_word_template():
    folder = _domain()
    template = CustomWordTemplate.objects.create(
        template_key="audit_report",
        language="en",
        folder=folder,
        file=_upload("audit.docx"),
    )
    return template, folder, [_stored(template, "file")]


def _custom_html_template():
    folder = _domain()
    template = CustomDocHtmlTemplate.objects.create(
        template_key="document_pdf",
        language="en",
        folder=folder,
        file=_upload("layout.html"),
    )
    return template, folder, [_stored(template, "file")]


def _document_revision():
    folder = _domain()
    container = DocumentContainer.objects.create(name="Policy", folder=folder)
    document = ManagedDocument.objects.create(
        name="Policy", container=container, folder=folder
    )
    revision = DocumentRevision.objects.create(
        document=document,
        version_number=1,
        source=DocumentRevision.Source.UPLOADED,
        file=_upload("policy.pdf"),
        pdf_snapshot=_upload("policy-preview.pdf"),
    )
    return (
        revision,
        document,
        [_stored(revision, "file"), _stored(revision, "pdf_snapshot")],
    )


def _document_attachment():
    folder = _domain()
    container = DocumentContainer.objects.create(name="Policy", folder=folder)
    document = ManagedDocument.objects.create(
        name="Policy", container=container, folder=folder
    )
    attachment = DocumentAttachment.objects.create(
        document=document, file=_upload("diagram.png")
    )
    return attachment, document, [_stored(attachment, "file")]


def _public_document():
    folder = _domain()
    document = PublicDocument.objects.create(
        name="Policy", folder=folder, file=_upload("public.pdf")
    )
    return document, folder, [_stored(document, "file")]


def _indexed_document():
    folder = _domain()
    document = IndexedDocument.objects.create(
        folder=folder,
        file=_upload("notes.txt"),
        filename="notes.txt",
        content_type="text/plain",
        source_type=IndexedDocument.SourceType.CHAT,
    )
    return document, folder, [_stored(document, "file")]


def _questionnaire_run():
    folder = _domain()
    user = User.objects.create_user(email="runner@example.com")
    run = QuestionnaireRun.objects.create(
        owner=user,
        folder=folder,
        file=_upload("questions.xlsx"),
        filename="questions.xlsx",
    )
    return run, folder, [_stored(run, "file")]


def _posture_run():
    folder = _domain()
    framework = Framework.objects.create(name="CIS", folder=folder)
    assessment = PostureAssessment.objects.create(
        name="Scan", framework=framework, folder=folder
    )
    run = PostureRun.objects.create(
        posture_assessment=assessment,
        started_at=timezone.now(),
        attachment=_upload("scan.txt"),
    )
    return run, assessment, [_stored(run, "attachment")]


CASES = {
    "evidence revision": _evidence_revision,
    "requirement node attachment": _requirement_node_attachment,
    "answer attachment": _answer_attachment,
    "custom word template": _custom_word_template,
    "custom html template": _custom_html_template,
    "document revision": _document_revision,
    "document attachment": _document_attachment,
    "public document": _public_document,
    "indexed document": _indexed_document,
    "questionnaire run": _questionnaire_run,
    "posture run": _posture_run,
}


@pytest.mark.django_db
@pytest.mark.parametrize("label", CASES)
def test_deleting_the_row_removes_its_file(
    settings, tmp_path, label, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    row, _parent, stored = CASES[label]()
    with django_capture_on_commit_callbacks(execute=True):
        row.delete()
    _gone(stored)


@pytest.mark.django_db
@pytest.mark.parametrize("label", CASES)
def test_deleting_the_parent_removes_its_file(
    settings, tmp_path, label, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    _row, parent, stored = CASES[label]()
    with django_capture_on_commit_callbacks(execute=True):
        parent.delete()
    _gone(stored)


@pytest.mark.django_db
def test_an_index_row_does_not_remove_the_evidence_file(
    settings, tmp_path, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    folder = _domain()
    evidence = Evidence.objects.create(name="Policy", folder=folder)
    revision = EvidenceRevision.objects.create(
        evidence=evidence, attachment=_upload("policy.txt")
    )
    storage, name = _stored(revision, "attachment")
    with django_capture_on_commit_callbacks(execute=True):
        IndexedDocument.objects.create(
            folder=folder,
            file=name,
            filename="policy.txt",
            content_type="text/plain",
            source_type=IndexedDocument.SourceType.EVIDENCE,
        ).delete()
    assert storage.exists(name)
    with django_capture_on_commit_callbacks(execute=True):
        evidence.delete()
    assert not storage.exists(name)


@pytest.mark.django_db
def test_a_rolled_back_delete_keeps_the_file(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    document, _folder, stored = _public_document()
    storage, name = stored[0]
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            document.delete()
            raise RuntimeError("nope")
    assert storage.exists(name)


@pytest.mark.django_db
def test_queryset_delete_of_rows_sharing_a_file_removes_it(
    settings, tmp_path, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    folder = _domain()
    first = PublicDocument.objects.create(
        name="One", folder=folder, file=_upload("shared.pdf")
    )
    storage, name = _stored(first, "file")
    second = PublicDocument(name="Two", folder=folder)
    second.file = name
    second.save()
    assert second.file.name == name
    with django_capture_on_commit_callbacks(execute=True):
        PublicDocument.objects.filter(pk__in=(first.pk, second.pk)).delete()
    assert not storage.exists(name)


@pytest.mark.django_db
def test_recreating_the_row_with_the_same_pk_keeps_the_file(
    settings, tmp_path, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    document, _folder, stored = _public_document()
    storage, name = stored[0]
    pk = document.pk
    with django_capture_on_commit_callbacks(execute=True):
        with transaction.atomic():
            document.delete()
            revived = PublicDocument(id=pk, name="Policy", folder_id=document.folder_id)
            revived.file = name
            revived.save()
    assert storage.exists(name)
    assert PublicDocument.objects.get(pk=pk).file.name == name


@pytest.mark.django_db
def test_deleting_the_last_owner_removes_the_file(
    settings, tmp_path, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = str(tmp_path)
    document, _folder, stored = _public_document()
    storage, name = stored[0]
    with django_capture_on_commit_callbacks(execute=True):
        document.delete()
    assert not storage.exists(name)
