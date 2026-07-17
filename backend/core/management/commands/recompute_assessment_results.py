"""One-shot recompute for RequirementAssessment.result.

Use when a tenant has audits built with the framework builder UI (or Excel
imports using the semantic compute_result vocabulary) and the stored results
were aggregated under the older boolean-collapse logic.

The command is idempotent: re-running on already-aligned data is a no-op.

Scope
-----
Only requirement assessments whose requirement has at least one question
choice with a *resolvable* `compute_result` (via `resolve_compute_result`)
are considered. Score-only or questionnaire-only audits without any
compute_result-bearing choice are left alone, so a stored manual result is
not silently reset to `not_assessed`.

Post-processing
---------------
`bulk_update` bypasses `RequirementAssessment.save()`, which would normally
defer `ComplianceAssessment.upsert_daily_metrics` and CEL outcome evaluation.
After writes, the command explicitly re-triggers both hooks for each touched
compliance assessment so metrics and CEL outcomes don't go stale. Use
`--skip-post-hooks` to opt out (e.g. when chaining with another job that will
recompute them).
"""

import logging
from contextlib import nullcontext

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import ComplianceAssessment, QuestionChoice, RequirementAssessment
from core.utils import resolve_compute_result

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
RESULT_UPDATE_FIELDS = ["score", "result", "is_scored", "updated_at"]


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
        parser.add_argument(
            "--skip-post-hooks",
            action="store_true",
            help=(
                "Skip re-triggering ComplianceAssessment metrics and CEL outcome "
                "evaluation for touched audits."
            ),
        )

    def _resolvable_requirement_ids(
        self, scoped_ca: "ComplianceAssessment | None"
    ) -> set:
        """Return requirement node IDs that carry at least one choice with a
        compute_result value resolvable by `resolve_compute_result`.

        We pull (requirement_id, compute_result) pairs in one query and resolve
        in Python, since the resolver normalizes whitespace and handles
        unknown / legacy values that pure SQL cannot match cleanly.

        When scoped to a single compliance assessment, the scan is restricted
        to requirement nodes that audit references, so single-CA runs don't
        pay the full-tenant cost. We avoid the ORM reverse path through
        `RequirementAssessment` because `RequirementAssessment.requirement`
        has no `related_name`, so resolving the join name implicitly is
        fragile and easy to break with future model edits.
        """
        choices_qs = QuestionChoice.objects.filter(compute_result__isnull=False)
        if scoped_ca is not None:
            scoped_requirement_ids = RequirementAssessment.objects.filter(
                compliance_assessment=scoped_ca,
            ).values_list("requirement_id", flat=True)
            choices_qs = choices_qs.filter(
                question__requirement_node_id__in=scoped_requirement_ids,
            )
        pairs = choices_qs.values_list(
            "question__requirement_node_id", "compute_result"
        ).distinct()
        return {
            req_id
            for req_id, cr in pairs
            if req_id is not None and resolve_compute_result(cr) is not None
        }

    def _flush_batch(self, batch, fields, dry_run):
        if not batch or dry_run:
            batch.clear()
            return
        with transaction.atomic():
            RequirementAssessment.objects.bulk_update(batch, fields)
        batch.clear()

    def _run_post_hooks(self, ca_ids: set, dry_run: bool, skip: bool):
        if dry_run or skip or not ca_ids:
            return
        from core.cel_service import evaluate_outcomes

        failures: list[str] = []
        for ca in ComplianceAssessment.objects.filter(pk__in=ca_ids):
            try:
                ca.upsert_daily_metrics()
            except Exception as exc:
                logger.exception("upsert_daily_metrics failed for CA %s", ca.pk)
                failures.append(f"upsert_daily_metrics CA={ca.pk}: {exc}")
            try:
                evaluate_outcomes(ca)
            except Exception as exc:
                logger.exception("evaluate_outcomes failed for CA %s", ca.pk)
                failures.append(f"evaluate_outcomes CA={ca.pk}: {exc}")

        if failures:
            # Hard-fail: stored results were rewritten but CA-level metrics /
            # CEL outcomes may now be stale. Surface this to the operator so
            # they can rerun the relevant jobs, instead of letting the command
            # finish in apparent success.
            joined = "\n  - ".join(failures)
            raise CommandError(
                "Stored results were updated, but CA post-hooks failed for "
                f"{len(failures)} call(s). Metrics / CEL outcomes may be stale.\n"
                f"Re-run hooks, or invoke the command with --skip-post-hooks if "
                f"you handle them separately.\n  - {joined}"
            )

    def handle(self, *args, **options):
        ca_uuid = options.get("compliance_assessment")
        dry_run = options.get("dry_run", False)
        run_atomic = options.get("atomic", False)
        batch_size = options.get("batch_size") or BATCH_SIZE
        skip_post_hooks = options.get("skip_post_hooks", False)

        scoped_ca = None
        if ca_uuid:
            try:
                scoped_ca = ComplianceAssessment.objects.get(pk=ca_uuid)
            except (ComplianceAssessment.DoesNotExist, ValidationError) as exc:
                raise CommandError(
                    f"ComplianceAssessment {ca_uuid!r} not found or not a valid UUID"
                ) from exc
            self.stdout.write(f"Scoped to compliance assessment {ca_uuid}")

        resolvable_req_ids = self._resolvable_requirement_ids(scoped_ca)
        if not resolvable_req_ids:
            self.stdout.write(
                self.style.WARNING(
                    "No requirement node carries a resolvable compute_result; nothing to do."
                )
            )
            return

        queryset = RequirementAssessment.objects.select_related(
            "compliance_assessment", "requirement"
        ).filter(requirement_id__in=resolvable_req_ids)

        if scoped_ca is not None:
            queryset = queryset.filter(compliance_assessment=scoped_ca)

        total = queryset.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No requirement assessments in scope (no compute_result-driven requirement found)."
                )
            )
            return

        mode_label = []
        if dry_run:
            mode_label.append("DRY RUN")
        if run_atomic:
            mode_label.append("ATOMIC")
        if skip_post_hooks:
            mode_label.append("NO POST-HOOKS")
        suffix = f" [{', '.join(mode_label)}]" if mode_label else ""
        self.stdout.write(f"Processing {total} requirement assessment(s){suffix}")

        changed = 0
        unchanged = 0
        seen_per_ca: dict[str, int] = {}
        touched_ca_ids: set = set()
        batch: list[RequirementAssessment] = []

        outer = transaction.atomic() if run_atomic else nullcontext()

        with outer:
            for ra in queryset.iterator(chunk_size=batch_size):
                ca_key = str(ra.compliance_assessment_id)
                seen_per_ca[ca_key] = seen_per_ca.get(ca_key, 0) + 1

                previous = (ra.score, ra.result, ra.is_scored)
                ra.recompute_assessment()
                current = (ra.score, ra.result, ra.is_scored)

                if previous == current:
                    unchanged += 1
                    continue

                changed += 1
                # bulk_update bypasses auto_now, so refresh updated_at by hand
                # to keep the timestamp aligned with the rewrite.
                ra.updated_at = timezone.now()
                touched_ca_ids.add(ra.compliance_assessment_id)
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

        self._run_post_hooks(touched_ca_ids, dry_run, skip_post_hooks)

        hooks_label = ""
        if dry_run:
            hooks_label = " (no writes, dry run)"
        elif skip_post_hooks:
            hooks_label = " (post-hooks skipped)"
        elif touched_ca_ids:
            hooks_label = f" (post-hooks ran on {len(touched_ca_ids)} CA)"

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. compliance_assessments={len(seen_per_ca)} "
                f"changed={changed} unchanged={unchanged}{hooks_label}"
            )
        )
