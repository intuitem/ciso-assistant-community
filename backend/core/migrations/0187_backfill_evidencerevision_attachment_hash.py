import hashlib
import logging

from django.core.files.storage import default_storage
from django.db import migrations

logger = logging.getLogger(__name__)


def backfill_attachment_hash(apps, schema_editor):
    EvidenceRevision = apps.get_model("core", "EvidenceRevision")

    revisions = EvidenceRevision.objects.exclude(attachment="").exclude(
        attachment__isnull=True
    ).filter(attachment_hash__isnull=True)

    for revision in revisions:
        if not default_storage.exists(revision.attachment.name):
            continue
        try:
            hash_obj = hashlib.sha256()
            with default_storage.open(revision.attachment.name, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    hash_obj.update(chunk)
            revision.attachment_hash = hash_obj.hexdigest()
            revision.save(update_fields=["attachment_hash"])
        except Exception as e:
            logger.warning(
                "Failed to backfill attachment hash",
                revision_id=revision.pk,
                error=str(e),
            )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0186_commitment_remove_comment_comment_exactly_one_parent_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_attachment_hash, migrations.RunPython.noop),
    ]
