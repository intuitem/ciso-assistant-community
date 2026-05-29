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
RESULT_UPDATE_FIELDS = ["score", "result", "is_scored"]


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

    def handle(self, *args, **options):
        ca_uuid = options.get("compliance_assessment")
        dry_run = options.get("dry_run", False)

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

        self.stdout.write(
            f"Processing {total} requirement assessment(s)"
            + (" [DRY RUN]" if dry_run else "")
        )

        changed = 0
        unchanged = 0
        skipped = 0
        batch = []

        with transaction.atomic():
            for ra in queryset.iterator(chunk_size=BATCH_SIZE):
                if not ra.requirement.questions.exists():
                    skipped += 1
                    continue

                previous = (ra.score, ra.result, ra.is_scored)
                ra.recompute_assessment()
                current = (ra.score, ra.result, ra.is_scored)

                if previous == current:
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

                if dry_run:
                    continue

                batch.append(ra)
                if len(batch) >= BATCH_SIZE:
                    RequirementAssessment.objects.bulk_update(batch, RESULT_UPDATE_FIELDS)
                    batch = []

            if batch and not dry_run:
                RequirementAssessment.objects.bulk_update(batch, RESULT_UPDATE_FIELDS)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. changed={changed} unchanged={unchanged} skipped={skipped}"
                + (" (rolled back, dry run)" if dry_run else "")
            )
        )
