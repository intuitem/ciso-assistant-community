import io
import os
import zipfile
from typing import Optional, BinaryIO

import structlog
from django.core.files.storage import default_storage
from django.db.models import QuerySet

from core.models import Evidence, EvidenceRevision

logger = structlog.get_logger(__name__)


class AttachmentExporter:
    def collect_all_attachments(self, scope: Optional[QuerySet] = None) -> QuerySet:
        if scope is None:
            revisions = EvidenceRevision.objects.all()
        else:
            revisions = scope

        return revisions.filter(attachment__isnull=False).select_related(
            "evidence", "folder"
        )

    def package_attachments_to_zip(
        self, revisions: QuerySet, zipf: zipfile.ZipFile
    ) -> int:
        count = 0

        for revision in revisions:
            if revision.attachment and default_storage.exists(revision.attachment.name):
                try:
                    with default_storage.open(revision.attachment.name, "rb") as file:
                        file_content = file.read()

                        filename = (
                            f"{revision.evidence_id}_v{revision.version}_"
                            f"{os.path.basename(revision.attachment.name)}"
                        )

                        zip_path = os.path.join(
                            "attachments", "evidence-revisions", filename
                        )

                        zipf.writestr(zip_path, file_content)
                        count += 1

                except Exception as e:
                    logger.error(
                        "Failed to add attachment to ZIP",
                        revision_id=revision.id,
                        evidence_id=revision.evidence_id,
                        attachment_name=revision.attachment.name,
                        error=str(e),
                    )
                    continue

        return count

    def create_attachments_zip(
        self, revisions: Optional[QuerySet] = None
    ) -> tuple[io.BytesIO, int]:
        if revisions is None:
            revisions = self.collect_all_attachments()

        logger.info("Creating attachments ZIP", total_revisions=revisions.count())

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            count = self.package_attachments_to_zip(revisions, zipf)

        zip_buffer.seek(0)

        logger.info(
            "Attachments ZIP created successfully",
            attachments_count=count,
            zip_size=len(zip_buffer.getvalue()),
        )

        return zip_buffer, count


class AttachmentImporter:
    def extract_attachments_from_zip(
        self, zip_file: BinaryIO, dry_run: bool = False
    ) -> dict:
        stats = {"processed": 0, "restored": 0, "errors": []}

        try:
            with zipfile.ZipFile(zip_file, "r") as zipf:
                attachment_files = [
                    f
                    for f in zipf.namelist()
                    if f.startswith("attachments/evidence-revisions/")
                    and not f.endswith("/")
                ]

                stats["processed"] = len(attachment_files)

                logger.info(
                    "Starting attachment import",
                    total_files=stats["processed"],
                    dry_run=dry_run,
                )

                for file_path in attachment_files:
                    try:
                        filename = os.path.basename(file_path)
                        parts = filename.split("_", 2)

                        if len(parts) < 3:
                            stats["errors"].append(
                                f"Invalid filename format: {filename}"
                            )
                            continue

                        evidence_id = parts[0]
                        version_str = parts[1]
                        original_filename = parts[2]

                        if not version_str.startswith("v"):
                            stats["errors"].append(
                                f"Invalid version format in: {filename}"
                            )
                            continue

                        version = int(version_str[1:])

                        if not dry_run:
                            # Find the corresponding EvidenceRevision
                            try:
                                revision = EvidenceRevision.objects.get(
                                    evidence_id=evidence_id, version=version
                                )

                                file_content = zipf.read(file_path)

                                storage_path = (
                                    f"evidence-revisions/{evidence_id}/"
                                    f"v{version}/{original_filename}"
                                )

                                saved_path = default_storage.save(
                                    storage_path, io.BytesIO(file_content)
                                )

                                revision.attachment = saved_path
                                revision.save(update_fields=["attachment"])

                                stats["restored"] += 1

                            except EvidenceRevision.DoesNotExist:
                                stats["errors"].append(
                                    f"EvidenceRevision not found: "
                                    f"evidence_id={evidence_id}, version={version}"
                                )
                            except Exception as e:
                                stats["errors"].append(
                                    f"Failed to restore {filename}: {str(e)}"
                                )
                        else:
                            stats["restored"] += 1

                    except Exception as e:
                        stats["errors"].append(
                            f"Error processing {file_path}: {str(e)}"
                        )
                        continue

        except zipfile.BadZipFile:
            stats["errors"].append("Invalid ZIP file")
        except Exception as e:
            stats["errors"].append(f"Unexpected error: {str(e)}")

        logger.info(
            "Attachment import completed",
            processed=stats["processed"],
            restored=stats["restored"],
            errors_count=len(stats["errors"]),
            dry_run=dry_run,
        )

        return stats
