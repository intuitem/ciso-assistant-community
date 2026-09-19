import hashlib

import structlog
from django.core.files.storage import default_storage
from django.db import migrations

logger = structlog.get_logger(__name__)

READ_CHUNK_SIZE = 1024 * 1024
BATCH_SIZE = 500


def backfill_attachment_hash(apps, schema_editor):
    EvidenceRevision = apps.get_model("core", "EvidenceRevision")

    pks = list(
        EvidenceRevision.objects.exclude(attachment="")
        .exclude(attachment__isnull=True)
        .filter(attachment_hash__isnull=True)
        .order_by("pk")
        .values_list("pk", flat=True)
    )

    for start in range(0, len(pks), BATCH_SIZE):
        hashed = []
        revisions = EvidenceRevision.objects.filter(
            pk__in=pks[start : start + BATCH_SIZE]
        ).only("attachment", "attachment_hash")
        for revision in revisions:
            try:
                if not default_storage.exists(revision.attachment.name):
                    continue
                hash_obj = hashlib.sha256()
                with default_storage.open(revision.attachment.name, "rb") as f:
                    for chunk in iter(lambda: f.read(READ_CHUNK_SIZE), b""):
                        hash_obj.update(chunk)
            except Exception as e:
                logger.warning(
                    "Failed to backfill attachment hash",
                    revision_id=revision.pk,
                    error=str(e),
                )
                continue
            revision.attachment_hash = hash_obj.hexdigest()
            hashed.append(revision)
        if hashed:
            EvidenceRevision.objects.bulk_update(hashed, ["attachment_hash"])


class Migration(migrations.Migration):
    # Data-only backfill that reads every attachment from storage: keeping it out of
    # a single transaction lets each batch commit as it goes, so a deploy-time
    # timeout doesn't discard the work. Re-running is safe, the queryset only picks
    # up revisions that still have no hash.
    atomic = False

    dependencies = [
        ("core", "0188_quickformpublication_quickformresponse_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_attachment_hash, migrations.RunPython.noop),
    ]
