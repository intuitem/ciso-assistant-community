"""One-shot recompute for RequirementAssessment.result.

Use when a tenant has audits built with the framework builder UI (or Excel
imports using the semantic compute_result vocabulary) and the stored results
were aggregated under the older boolean-collapse logic.

The command is idempotent: re-running on already-aligned data is a no-op.
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import ComplianceAssessment, RequirementAssessment

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
RESULT_UPDATE_FIELDS = ["score", "result", "is_scored", "updated_at"]


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class Command(BaseCommand):
    help = (
        "Recompute RequirementAssessment.result/score for existing audits using the "
        "current semantic compute_result aggregation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--compliance-assessment",
            type=str,
            default=None,
            help="UUID of a single compliance assessment to recompute (default: all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database.",
        )
        parser.add_argument(
            "--atomic",
            action="store_true",
            help="Wrap the full run in a single transaction (default: commit per batch).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=BATCH_SIZE,
            help=f"Batch size for bulk_update (default: {BATCH_SIZE}).",
        )

    def _flush_batch(self, batch, fields, dry_run):
        if not batch or dry_run:
            batch.clear()
            return
        with transaction.atomic():
            RequirementAssessment.objects.bulk_update(batch, fields)
        batch.clear()

    def handle(self, *args, **options):
        ca_uuid = options.get("compliance_assessment")
        dry_run = options.get("dry_run", False)
        run_atomic = options.get("atomic", False)
        batch_size = options.get("batch_size") or BATCH_SIZE

        queryset = RequirementAssessment.objects.select_related(
            "compliance_assessment", "requirement"
        )

        if ca_uuid:
            try:
                ca = ComplianceAssessment.objects.get(pk=ca_uuid)
            except ComplianceAssessment.DoesNotExist as exc:
                raise CommandError(
                    f"ComplianceAssessment {ca_uuid} not found"
                ) from exc
            queryset = queryset.filter(compliance_assessment=ca)
            self.stdout.write(f"Scoped to compliance assessment {ca_uuid}")

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No requirement assessments to process."))
            return

        mode_label = []
        if dry_run:
            mode_label.append("DRY RUN")
        if run_atomic:
            mode_label.append("ATOMIC")
        suffix = f" [{', '.join(mode_label)}]" if mode_label else ""
        self.stdout.write(f"Processing {total} requirement assessment(s){suffix}")

        changed = 0
        unchanged = 0
        seen_per_ca: dict[str, int] = {}
        batch: list[RequirementAssessment] = []

        outer = transaction.atomic() if run_atomic else _NullContext()

        with outer:
            for ra in queryset.iterator(chunk_size=batch_size):
                ca_key = str(ra.compliance_assessment_id)
                seen_per_ca[ca_key] = seen_per_ca.get(ca_key, 0) + 1

                previous = (ra.score, ra.result, ra.is_scored)
                ra.recompute_assessment()
                current = (ra.score, ra.result, ra.is_scored)

                if previous == current:
                    # recompute_assessment() short-circuits when a requirement has
                    # no questions, so "unchanged" covers both that case and rows
                    # already aligned with the current logic.
                    unchanged += 1
                    continue

                changed += 1
                logger.debug(
                    "RA %s: result %s -> %s, score %s -> %s",
                    ra.pk,
                    previous[1],
                    current[1],
                    previous[0],
                    current[0],
                )

                batch.append(ra)
                if len(batch) >= batch_size:
                    self._flush_batch(batch, RESULT_UPDATE_FIELDS, dry_run)

            self._flush_batch(batch, RESULT_UPDATE_FIELDS, dry_run)

            if run_atomic and dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. compliance_assessments={len(seen_per_ca)} "
                f"changed={changed} unchanged={unchanged}"
                + (" (no writes, dry run)" if dry_run else "")
            )
        )
