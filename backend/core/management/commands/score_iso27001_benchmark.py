"""Score a review run against the benchmark's answer key.

The companion to populate_iso27001_benchmark: that command seeds data whose
answers are known, this one says how a run did against them. Lives here rather
than in a scratch script because the point of a benchmark is to be re-run —
against another model, after a prompt change, or to prove a refactor moved
nothing.

    python manage.py score_iso27001_benchmark --truth /tmp/truth.json

Three things are reported, and the first two are the ones that matter:

    the counted half   requirements a quality rule flagged. These never reach a
                       model, so a miss here means the workflow's routing broke,
                       not that a model was wrong
    the judged half    requirements the rules passed. Only these are a model's
                       to get right
    completeness       every collected record must reach the document. A right
                       verdict that never appears on the page helps nobody, and
                       a section writer has dropped records before.
"""

import json
from collections import Counter

from django.core.management.base import BaseCommand

from doc_management.models import ManagedDocument
from automation.workflows.models import WorkflowInstance

BUCKETS = ("concern", "needs_look", "backed")


class Command(BaseCommand):
    help = "Scores an audit review run against the seeded answer key"

    def add_arguments(self, parser):
        parser.add_argument(
            "--truth", required=True, help="The answer key written by --out"
        )
        parser.add_argument(
            "--instance",
            help="Workflow instance to score (default: the latest run over the audit)",
        )

    def handle(self, *args, **options):
        with open(options["truth"]) as handle:
            truth = json.load(handle)

        instance = self._instance(options.get("instance"), truth["audit_id"])
        if instance is None:
            self.stderr.write(self.style.ERROR("No run found over that audit."))
            return

        loop = instance.node_outputs.get("per_requirement") or {}
        records = [row for row in (loop.get("results") or []) if isinstance(row, dict)]
        got = {row.get("ref_id", ""): row.get("bucket", "?") for row in records}
        expected = truth["expected"]

        self.stdout.write(f"run      : {instance.status}  {instance.id}")
        self.stdout.write(
            f"collected: {len(records)}  failed: {len(loop.get('errors') or [])}"
        )

        hits = [ref for ref in expected if got.get(ref) == expected[ref]]
        self.stdout.write(f"score    : {len(hits)}/{len(expected)}")

        # A rule either fires or it does not, so this half is the workflow's
        # wiring rather than a model's judgement.
        counted = [ref for ref in expected if expected[ref] == "concern"]
        judged = [ref for ref in expected if expected[ref] != "concern"]
        for label, refs in (("counted (rules)", counted), ("judged (model)", judged)):
            right = sum(1 for ref in refs if got.get(ref) == expected[ref])
            self.stdout.write(f"  {label:<17} {right}/{len(refs)}")

        absent = [ref for ref in expected if ref not in got]
        if absent:
            self.stderr.write(
                self.style.WARNING(f"  never collected: {', '.join(sorted(absent))}")
            )
        leaked = [ref for ref in truth.get("excluded", {}) if ref in got]
        if leaked:
            self.stderr.write(
                self.style.ERROR(
                    f"  LEAKED (outside the filter): {', '.join(sorted(leaked))}"
                )
            )

        self.stdout.write("\nconfusion (expected -> got):")
        matrix = Counter((expected[ref], got.get(ref, "absent")) for ref in expected)
        for bucket in BUCKETS:
            row = {got_: n for (exp, got_), n in matrix.items() if exp == bucket}
            detail = "  ".join(f"{k}:{v}" for k, v in sorted(row.items()))
            self.stdout.write(f"  {bucket:<12} n={sum(row.values()):<3} {detail}")

        self._report_document(instance, records)

        misses = [ref for ref in expected if ref in got and got[ref] != expected[ref]]
        if misses:
            self.stdout.write("\nmisses:")
            for ref in sorted(misses):
                self.stdout.write(
                    f"  {ref:<8} expected {expected[ref]:<11} got {got[ref]:<11} "
                    f"— {truth['why'][ref]}"
                )

    def _instance(self, instance_id, audit_id):
        if instance_id:
            return WorkflowInstance.objects.filter(id=instance_id).first()
        from core.models import ComplianceAssessment

        audit = ComplianceAssessment.objects.filter(id=audit_id).first()
        if audit is None:
            return None
        return (
            WorkflowInstance.objects.filter(folder=audit.folder)
            .order_by("-created_at")
            .first()
        )

    def _report_document(self, instance, records):
        # Only a document this run produced: a failed run leaves the previous
        # one in place, and reading that reports an old run's drops as this
        # one's.
        document = (
            ManagedDocument.objects.filter(
                folder=instance.folder, created_at__gte=instance.created_at
            )
            .order_by("-created_at")
            .first()
        )
        if document is None or document.current_revision is None:
            self.stdout.write("\ndocument : none produced by this run")
            return
        content = document.current_revision.content
        dropped = [row["ref_id"] for row in records if row["ref_id"] not in content]
        if dropped:
            self.stderr.write(
                self.style.ERROR(
                    f"\nDROPPED FROM THE DOCUMENT: {', '.join(sorted(dropped))}"
                )
            )
        else:
            self.stdout.write(
                f"\ndocument : every collected record appears ({len(records)})"
            )
