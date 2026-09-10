"""Uploading files against an answer, and promoting them to evidence.

The two acts are deliberately separate. Uploading is done by whoever answers the
question — a requester on a quick form, an auditee on an audit — and those people
normally hold no permission on the folder the answer lives in. Promotion creates an
`Evidence`, which is governed and folder-scoped, and is therefore a reviewer's act.

Shared by every surface so the rules cannot drift: the callers differ only in how
they establish that this person may touch this answer.
"""

import hashlib

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Answer, AnswerAttachment, Evidence, EvidenceRevision, Question

#: Refused outright. Everything an office worker attaches is fine; executables are
#: not, and a content sniff is cheap insurance against a renamed extension.
BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bat",
    ".cmd",
    ".com",
    ".scr",
    ".msi",
    ".sh",
    ".ps1",
    ".jar",
    ".app",
}
EXECUTABLE_MAGIC = (b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe", b"#!")
MAX_SIZE_BYTES = 25 * 1024 * 1024


class AttachmentError(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code)


def _question_config(question):
    return question.config if isinstance(question.config, dict) else {}


def validate_upload(answer, upload):
    """Size, type and per-question limits. Raises AttachmentError."""
    question = answer.question
    if question.type != Question.Type.FILE:
        raise AttachmentError("questionDoesNotTakeFiles")

    config = _question_config(question)
    name = (upload.name or "file").strip()
    lowered = name.lower()
    if any(lowered.endswith(ext) for ext in BLOCKED_EXTENSIONS):
        raise AttachmentError("executableNotAllowed", name)

    head = upload.read(4)
    upload.seek(0)
    if any(head.startswith(magic) for magic in EXECUTABLE_MAGIC):
        # A renamed .exe is still an .exe; the extension is the claim, not the fact.
        raise AttachmentError("executableNotAllowed", name)

    max_bytes = int(config.get("max_size_mb") or 0) * 1024 * 1024 or MAX_SIZE_BYTES
    if upload.size > max_bytes:
        raise AttachmentError("fileTooLarge", f"{upload.size} > {max_bytes}")

    accept = config.get("accept")
    if accept:
        allowed = [a.strip().lower() for a in str(accept).split(",") if a.strip()]
        if allowed and not any(lowered.endswith(a.lstrip("*")) for a in allowed):
            raise AttachmentError("fileTypeNotAccepted", name)

    existing = answer.attachments.count()
    if not config.get("multiple") and existing >= 1:
        raise AttachmentError("onlyOneFileAllowed")
    max_files = int(config.get("max_files") or 0)
    if max_files and existing >= max_files:
        raise AttachmentError("tooManyFiles", str(max_files))


def add_attachment(answer, upload, user):
    """Store one file against `answer`. The caller has already established that this
    person may answer it."""
    validate_upload(answer, upload)
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return AnswerAttachment.objects.create(
        answer=answer,
        file=upload,
        filename=(upload.name or "file")[:255],
        size=upload.size,
        mime_type=(getattr(upload, "content_type", "") or "")[:127],
        file_hash=digest.hexdigest(),
        uploaded_by=user,
        folder_id=answer.folder_id,
    )


def promote_to_evidence(attachment, user):
    """Turn an attachment into an `Evidence` with its first revision.

    Idempotent: an attachment already promoted returns its evidence rather than
    making a second one. On the audit side the new evidence is also linked to the
    requirement assessment, which is where an auditor expects to find it.
    """
    if attachment.promoted_to_id:
        return attachment.promoted_to, False

    answer = attachment.answer
    parent = answer.owner
    label = getattr(parent, "ref_id", None) or getattr(parent, "name", "") or ""
    question_text = (answer.question.text or answer.question.ref_id or "")[:120]

    with transaction.atomic():
        evidence = Evidence(
            name=f"{label} — {question_text}".strip(" —")[:200] or attachment.filename,
            description=(
                f"Promoted from an answer attachment ({attachment.filename}). "
                f"Question: {question_text}"
            ),
            folder_id=attachment.folder_id,
        )
        try:
            evidence.save()
        except ValidationError:
            # `Evidence.fields_to_check` is ["name"]: a second promotion of the same
            # question needs a distinguishing suffix rather than a failure.
            evidence.name = f"{evidence.name} ({attachment.file_hash[:8]})"[:200]
            evidence.save()

        EvidenceRevision.objects.create(
            evidence=evidence,
            attachment=attachment.file,
            attachment_hash=attachment.file_hash,
            folder_id=attachment.folder_id,
        )
        attachment.promoted_to = evidence
        attachment.save(update_fields=["promoted_to", "updated_at"])

        # An audit answer belongs to a requirement assessment, which already has an
        # evidences relation — that is where an auditor looks for it.
        if answer.requirement_assessment_id:
            answer.requirement_assessment.evidences.add(evidence)
    return evidence, True


def serialize(attachment):
    return {
        "id": str(attachment.id),
        "filename": attachment.filename,
        "size": attachment.size,
        "mime_type": attachment.mime_type,
        "uploaded_by": str(attachment.uploaded_by)
        if attachment.uploaded_by_id
        else None,
        "created_at": attachment.created_at,
        "promoted_to": str(attachment.promoted_to_id)
        if attachment.promoted_to_id
        else None,
    }


def attachments_for(answers_qs):
    """{question urn: [serialized attachment]} for a whole response or assessment."""
    out = {}
    for attachment in AnswerAttachment.objects.filter(
        answer__in=answers_qs
    ).select_related("answer__question", "uploaded_by"):
        out.setdefault(attachment.answer.question.urn, []).append(serialize(attachment))
    return out
