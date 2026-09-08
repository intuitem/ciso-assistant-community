"""Storage and multipart support for a versioned set of evidence files."""

import hashlib
import json
from contextlib import contextmanager

from django.db import transaction
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.parsers import MultiPartParser

MAX_EVIDENCE_FILES = 10


class EvidenceMultipartParser(MultiPartParser):
    """Keep JSON types (including empty relations) alongside uploaded files.

    Ordinary multipart API clients can still submit individual form fields.
    The frontend sends metadata as JSON in `payload` and repeats `attachments`.
    """

    def parse(self, stream, media_type=None, parser_context=None):
        parsed = super().parse(stream, media_type, parser_context)
        if "payload" not in parsed.data:
            return parsed
        try:
            data = json.loads(parsed.data["payload"])
        except (ValueError, TypeError) as exc:
            raise ParseError("Invalid evidence metadata.") from exc
        if not isinstance(data, dict):
            raise ParseError("Evidence metadata must be an object.")
        for key in parsed.files:
            data[key] = (
                parsed.files.getlist(key) if key == "attachments" else parsed.files[key]
            )
        return data


def hash_file(file):
    digest = hashlib.sha256()
    for chunk in file.chunks():
        digest.update(chunk)
    file.seek(0)
    return digest.hexdigest()


@contextmanager
def attachment_transaction():
    """Roll back newly stored files as well as database rows on failure."""
    written = []
    try:
        with transaction.atomic():
            yield written
    except Exception:
        for field in written:
            if field.name and field._committed:
                field.storage.delete(field.name)
        raise


def append_attachments(revision, files, written):
    from core.models import Evidence, EvidenceRevision, EvidenceAttachment

    # All writers serialize on the parent, including creation of new versions.
    evidence = Evidence.objects.select_for_update().get(pk=revision.evidence_id)
    revision = EvidenceRevision.objects.select_for_update().get(pk=revision.pk)
    count = bool(revision.attachment) + revision.additional_attachments.count()
    if count + len(files) > MAX_EVIDENCE_FILES:
        raise ValidationError(
            {"attachments": "A revision can contain at most 10 files."}
        )
    for file in files:
        if not revision.attachment:
            revision.attachment = file
            written.append(revision.attachment)
            revision.save()
        else:
            item = EvidenceAttachment(revision=revision, attachment=file)
            written.append(item.attachment)
            item.save()
    if files:
        evidence.status = Evidence.Status.IN_REVIEW
        evidence.save(update_fields=["status", "updated_at"])
    return revision


def attachment_metadata(revision):
    if revision is None:
        return []
    return [
        {
            "id": str(item.pk),
            "revision_id": str(revision.pk),
            "filename": item.filename(),
            "size": item.get_size(),
            "attachment_hash": item.attachment_hash,
        }
        for item in revision.attachment_items()
    ]


def get_backup_attachment(pk):
    """Backup IDs identify either a legacy primary file or an additional file."""
    from core.models import EvidenceRevision, EvidenceAttachment

    try:
        return EvidenceRevision.objects.select_related("evidence").get(pk=pk)
    except EvidenceRevision.DoesNotExist:
        try:
            return EvidenceAttachment.objects.select_related("revision__evidence").get(
                pk=pk
            )
        except EvidenceAttachment.DoesNotExist as exc:
            raise EvidenceRevision.DoesNotExist from exc
