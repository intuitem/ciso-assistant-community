"""Uploading files against an answer, and promoting them to evidence.

Uploading is the answerer's act, promotion the reviewer's: the second creates a governed,
folder-scoped `Evidence` and the first must not require folder rights.
"""

import hashlib
import mimetypes

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Answer, AnswerAttachment, Evidence, EvidenceRevision, Question

#: Extension and magic are both checked — a renamed .exe is still an .exe.
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


def _accepts(filename: str, allowed: list[str]) -> bool:
    """Match a filename against an HTML `accept` list.

    It carries three shapes — `.pdf`, `image/png`, `image/*` — and only the first is a
    suffix. The MIME comes from the extension, never from the uploading client.
    """
    guessed = (mimetypes.guess_type(filename)[0] or "").lower()
    for entry in allowed:
        if entry == "*/*":
            return True
        if entry.startswith("."):
            if filename.endswith(entry):
                return True
        elif entry.endswith("/*"):
            if guessed.startswith(entry[:-1]):
                return True
        elif "/" in entry:
            if guessed == entry:
                return True
        elif filename.endswith(f".{entry.lstrip('.')}"):
            # A bare extension without its dot, which authors write by hand.
            return True
    return False


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
        if allowed and not _accepts(lowered, allowed):
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
    """Attachment -> Evidence, idempotent. On the audit side it also lands on the
    requirement assessment."""
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


def answer_for_upload(response, question_urn):
    """The Answer row a file attaches to. Created on demand: a file question has no
    value, so nothing else would have made one."""
    question = Question.objects.filter(
        page__quick_form_id=response.quick_form_id, urn=question_urn
    ).first()
    if question is None:
        return None
    answer, _ = Answer.objects.get_or_create(
        response=response, question=question, defaults={"folder": response.folder}
    )
    return answer


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


#: Safe to render in-tab. Excludes SVG and HTML/XML: both execute script, and the
#: uploader is less trusted than the reviewer who opens it.
INLINE_SAFE_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "text/plain",
}


def _safe_filename_header(disposition, filename):
    """A Content-Disposition value that a filename cannot break out of."""
    from urllib.parse import quote

    ascii_name = "".join(
        c
        for c in filename.encode("ascii", "ignore").decode("ascii")
        # Control characters would let a filename shape the header itself; a quote
        # would close the quoted-string early.
        if c.isprintable() and c not in '"\\'
    ).strip()
    ascii_name = ascii_name or "attachment"
    # RFC 5987 for the real name; the quoted form is the fallback for old clients.
    return (
        f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
    )


def serve(attachment):
    """Stream one attachment back. The stored `mime_type` is the client's claim, so the
    type is re-derived and allowlisted; anything else downloads."""
    from django.http import FileResponse

    guessed = mimetypes.guess_type(attachment.filename)[0]
    inline = guessed in INLINE_SAFE_TYPES
    content_type = guessed if inline else "application/octet-stream"

    body = FileResponse(attachment.file, content_type=content_type)
    body["Content-Disposition"] = _safe_filename_header(
        "inline" if inline else "attachment", attachment.filename
    )
    body["X-Content-Type-Options"] = "nosniff"
    body["Content-Security-Policy"] = "sandbox; default-src 'none'; object-src 'none'"
    body["Referrer-Policy"] = "no-referrer"
    return body


def attachments_for(answers_qs):
    """{question urn: [serialized attachment]} for a whole response or assessment."""
    out = {}
    for attachment in AnswerAttachment.objects.filter(
        answer__in=answers_qs
    ).select_related("answer__question", "uploaded_by"):
        out.setdefault(attachment.answer.question.urn, []).append(serialize(attachment))
    return out
