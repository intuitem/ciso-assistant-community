"""Seed a labelled ISO 27001 audit for benchmarking the AI evidence review.

The point is the *mix*. A dataset where nothing is evidenced makes any reviewer
look right for saying so, which is exactly what made the first live sweep
uninformative. Here every requirement carries a known answer, so a run can be
scored instead of admired:

    concern      the platform's own quality rules flag it — no control, no
                 evidence, evidence expired or still in draft, a control not yet
                 active. Deterministic: the rule either trips or it does not
    needs_look   the rules pass it and a reader would still object: evidence
                 about a different subject, or too old to describe the present.
                 Three cases here are seeded RULE GAPS, where a human would
                 object and no rule fires — the model is the only backstop
    backed       the rules pass it and the evidence really does show what the
                 requirement asks for

Only `needs_look` and `backed` are the model's to decide; `concern` is settled
before any call is made. Which rule fires on which case was measured, not
assumed — see the `why` on each.

    python manage.py populate_iso27001_benchmark --fresh --out /tmp/truth.json
"""

import json
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
)
from iam.models import Folder

PREFIX = "BENCH-"
FRAMEWORK_URN = "urn:intuitem:risk:framework:iso27001-2022"
LINK = "https://evidence.example.test/"


@dataclass
class Doc:
    name: str
    description: str
    #: attached  — a link stands in for a file: what matters to a reader is
    #: whether anything is behind the title.
    #: empty     — the record exists and holds nothing. The most common real
    #:             shape, and the one worth catching.
    #: expired   — attached, but past its expiry date.
    state: str = "attached"
    #: Evidence.Status: draft, missing, in_review, approved, rejected, expired.
    #: A record can be attached and still not be approved, which is its own
    #: kind of not-quite-support.
    status: str = "approved"


@dataclass
class Case:
    ref_id: str
    result: str
    #: One of supported / thin / unsupported, or "" for a case the sweep must
    #: never reach — its result puts it outside the filter.
    expected: str
    why: str
    observation: str = ""
    #: (name, status) — a control that is only planned supports nothing yet.
    controls: list[tuple] = field(default_factory=list)
    #: Evidence hanging off the requirement itself.
    evidences: list[Doc] = field(default_factory=list)
    #: Evidence hanging off the first control — the indirect path, which counts
    #: exactly as much and is the reason the read layer walks it.
    control_evidences: list[Doc] = field(default_factory=list)
    score: int | None = None
    documentation_score: int | None = None


CASES = [
    # ================= supported: the claim is carried ======================
    Case(
        ref_id="A.5.1",
        result="compliant",
        expected="backed",
        why="approved policy attached and on subject",
        observation="Policy set reviewed with the CISO on 2026-02-10; approved by the board.",
        controls=[
            ("Information security policy set, approved and published", "active")
        ],
        evidences=[
            Doc(
                "Information security policy v4.2 (approved 2026-02-10)",
                "Board-approved policy set covering the ISMS scope, published on the intranet.",
            )
        ],
        score=4,
        documentation_score=4,
    ),
    Case(
        ref_id="A.6.3",
        result="compliant",
        expected="backed",
        why="the register is attached to the control, not the requirement",
        observation="Awareness campaign ran in March and September.",
        controls=[("Annual security awareness programme", "active")],
        control_evidences=[
            Doc(
                "Awareness training completion register — 2026",
                "Per-employee completion export, 98% of staff, generated from the LMS.",
            )
        ],
        score=4,
    ),
    Case(
        ref_id="A.8.8",
        result="partially_compliant",
        expected="backed",
        why="a partial claim backed by a real report is still backed",
        observation="Monthly scanning in place; remediation SLA not yet met for medium findings.",
        controls=[("Monthly authenticated vulnerability scanning", "active")],
        evidences=[
            Doc(
                "Vulnerability scan report — August 2026",
                "Authenticated scan across production, with per-host findings and severities.",
            )
        ],
        score=3,
        documentation_score=3,
    ),
    Case(
        ref_id="A.5.10",
        result="compliant",
        expected="backed",
        why="two evidences, one empty and one attached — one good one is enough",
        observation="Acceptable use policy acknowledged at onboarding and annually.",
        controls=[("Acceptable use policy with annual acknowledgement", "active")],
        evidences=[
            Doc(
                "Acceptable use policy v2.1",
                "Current signed-off version of the acceptable use policy.",
            ),
            Doc(
                "Acknowledgement export — 2026",
                "Placeholder for the annual acknowledgement extract; never uploaded.",
                state="empty",
                status="draft",
            ),
        ],
    ),
    Case(
        ref_id="A.8.13",
        result="compliant",
        expected="backed",
        why="restore test report attached, with a detailed observation",
        observation=(
            "Backups run nightly to immutable storage. Restore test performed 2026-06-14 "
            "on the billing database; RTO 3h against a 4h objective, signed off by the "
            "service owner."
        ),
        controls=[
            ("Nightly backup to immutable storage", "active"),
            ("Semi-annual restore test", "active"),
        ],
        evidences=[
            Doc(
                "Restore test report — June 2026",
                "Restore rehearsal for the billing database, with timings and sign-off.",
            )
        ],
        score=4,
    ),
    Case(
        ref_id="A.7.4",
        result="compliant",
        expected="backed",
        why="attached and on subject, with everything written in French",
        observation=(
            "Vidéosurveillance en place sur les trois sites, avec conservation de 30 jours. "
            "Registre des accès badge revu chaque trimestre par la sécurité physique."
        ),
        controls=[("Vidéosurveillance et contrôle d'accès par badge", "active")],
        control_evidences=[
            Doc(
                "Registre des accès badge — T3 2026",
                "Export trimestriel des accès badge pour les trois sites.",
            )
        ],
    ),
    # ================= thin: something there, it does not carry =============
    Case(
        ref_id="A.5.15",
        result="compliant",
        expected="concern",
        why="the evidence never left draft: EvidenceAllDraft",
        observation="Access reviews are performed quarterly by system owners.",
        controls=[("Quarterly access review for production systems", "active")],
        evidences=[
            Doc(
                "Quarterly access review — Q3 2026",
                "Placeholder raised by the control owner; the export was never attached.",
                state="empty",
                status="draft",
            )
        ],
    ),
    Case(
        ref_id="A.8.7",
        result="compliant",
        expected="concern",
        why="the only evidence expired: EvidenceExpired",
        observation="EDR deployed fleet-wide.",
        controls=[("Endpoint malware protection with central reporting", "active")],
        evidences=[
            Doc(
                "EDR coverage report — Q1 2025",
                "Coverage export from the EDR console, superseded and past its expiry.",
                state="expired",
                status="expired",
            )
        ],
    ),
    Case(
        ref_id="A.8.24",
        result="compliant",
        expected="needs_look",
        why="attached and current, but about a different requirement — no rule sees subject",
        observation="TLS everywhere; key management handled by the platform team.",
        controls=[("Encrypt data at rest and in transit (AES-256, TLS 1.3)", "active")],
        control_evidences=[
            Doc(
                "Access review extract — Q3 2026",
                "Quarterly access review export. Attached here by mistake; says nothing about keys.",
            )
        ],
    ),
    Case(
        ref_id="A.5.7",
        result="partially_compliant",
        expected="needs_look",
        why="RULE GAP: partially compliant with a control and zero evidence — CompliantNoEvidence only fires on `compliant`",
        observation="Feeds are consumed informally by the SOC; no formal process yet.",
        controls=[("Subscribe to sector threat intelligence feeds", "active")],
    ),
    Case(
        ref_id="A.8.16",
        result="compliant",
        expected="needs_look",
        why="RULE GAP: the empty evidence is `in_review`, not `draft`, so EvidenceAllDraft misses it and evidenceNoFile is an evidence-level rule that does not surface here",
        observation="SIEM in place with 24/7 alerting.",
        controls=[
            ("Centralised log collection into the SIEM", "active"),
            ("Alert triage runbook for the SOC", "active"),
        ],
        control_evidences=[
            Doc(
                "SIEM alerting configuration export",
                "Intended export of detection rules; the file was never uploaded.",
                state="empty",
                status="in_review",
            )
        ],
    ),
    Case(
        ref_id="A.8.2",
        result="compliant",
        expected="concern",
        why="the control is still planned: CompliantNoActiveControl",
        observation="PAM rollout scheduled for Q4.",
        controls=[("Privileged access management for production", "to_do")],
        evidences=[
            Doc(
                "PAM design document",
                "Target design for privileged access management. Describes intent, not operation.",
            )
        ],
    ),
    Case(
        ref_id="A.5.34",
        result="compliant",
        expected="concern",
        why="the document says of itself that it is a draft: EvidenceAllDraft",
        observation="PII handling procedure written with the DPO.",
        controls=[("PII handling procedure", "active")],
        evidences=[
            Doc(
                "PII handling procedure — DRAFT",
                "Working draft, not reviewed or approved. Circulated for comment only.",
                status="draft",
            )
        ],
    ),
    Case(
        ref_id="A.8.15",
        result="compliant",
        expected="concern",
        why="two evidence records, both draft: EvidenceAllDraft",
        observation="Logging enabled across the estate.",
        controls=[("Centralised logging with 12-month retention", "active")],
        evidences=[
            Doc(
                "Log retention configuration",
                "Placeholder for the retention settings export.",
                state="empty",
                status="draft",
            ),
            Doc(
                "Log source inventory",
                "Placeholder for the inventory of log sources.",
                state="empty",
                status="draft",
            ),
        ],
    ),
    Case(
        ref_id="A.5.19",
        result="partially_compliant",
        expected="needs_look",
        why="RULE GAP: one evidence expired and one draft — EvidenceExpired needs all expired, EvidenceAllDraft needs all draft, so mixed states pass both",
        observation=(
            "Supplier register maintained. Annual reviews completed for all critical "
            "suppliers."
        ),
        controls=[("Supplier security review before onboarding", "active")],
        evidences=[
            Doc(
                "Supplier security review — 2024",
                "Review pack from the 2024 cycle, past its expiry.",
                state="expired",
                status="expired",
            ),
            Doc(
                "Supplier register extract — 2026",
                "Placeholder for the current register extract.",
                state="empty",
                status="draft",
            ),
        ],
    ),
    Case(
        ref_id="A.8.9",
        result="compliant",
        expected="needs_look",
        why="attached and never expired, but three years old — no rule sees age",
        observation="Configuration baselines defined for all server roles.",
        controls=[("Hardened configuration baselines", "active")],
        evidences=[
            Doc(
                "Configuration baseline review — March 2023",
                "Baseline review for the server estate, carried out in March 2023. "
                "No review has been recorded since.",
            )
        ],
    ),
    # ================= unsupported: nothing at all ==========================
    Case(
        ref_id="A.5.23",
        result="compliant",
        expected="concern",
        why="no control and no evidence: NoAppliedControl + CompliantNoEvidence",
        observation="Cloud usage is covered by the enterprise agreement.",
    ),
    Case(
        ref_id="A.8.12",
        result="partially_compliant",
        expected="concern",
        why="nothing recorded at all: NoAppliedControl",
    ),
    Case(
        ref_id="A.5.30",
        result="compliant",
        expected="concern",
        why="no control and no evidence, and the observation admits it",
        observation="ICT continuity plan drafted but not yet tested; evidence pending.",
    ),
    Case(
        ref_id="A.8.25",
        result="partially_compliant",
        expected="concern",
        why="nothing recorded at all: NoAppliedControl",
        observation="Secure SDLC being rolled out team by team.",
    ),
    Case(
        ref_id="A.6.6",
        result="compliant",
        expected="concern",
        why="confident observation, nothing recorded: the rules say so",
        observation=(
            "All staff and contractors sign confidentiality agreements as part of "
            "onboarding; HR confirms 100% coverage."
        ),
    ),
    Case(
        ref_id="A.8.31",
        result="compliant",
        expected="concern",
        why="responsibility deflected to a provider, nothing recorded",
        observation="Separation of environments is handled by the cloud provider.",
    ),
    # ============ outside the filter: the sweep must never see these ========
    Case(
        ref_id="A.5.2",
        result="non_compliant",
        expected="",
        why="non-compliant: honest about itself, so the sweep skips it",
        observation="Roles not formally assigned; gap accepted and scheduled.",
        controls=[("Assign and document ISMS roles", "to_do")],
        evidences=[
            Doc(
                "ISMS role matrix — draft",
                "Draft role matrix pending management approval.",
            )
        ],
    ),
    Case(
        ref_id="A.5.3",
        result="not_assessed",
        expected="",
        why="not assessed yet, so there is no claim to challenge",
    ),
    Case(
        ref_id="A.5.4",
        result="not_applicable",
        expected="",
        why="scoped out, so there is no claim to challenge",
        observation="Not applicable: no in-house development in this scope.",
    ),
]


class Command(BaseCommand):
    help = "Seeds a labelled ISO 27001 audit for benchmarking the AI evidence review"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default=f"{PREFIX}ISO27001",
            help=f"Domain to seed into (default: {PREFIX}ISO27001)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete the seeded domain and everything in it, then stop",
        )
        parser.add_argument(
            "--fresh", action="store_true", help="Clean, then seed again"
        )
        parser.add_argument(
            "--out",
            help="Write the expected answers to this path as JSON, for scoring a run",
        )

    def handle(self, *args, **options):
        domain_name = options["domain"]
        if options["clean"] or options["fresh"]:
            self._clean(domain_name)
            if options["clean"]:
                return

        framework = Framework.objects.filter(urn=FRAMEWORK_URN).first()
        if framework is None:
            self.stderr.write(
                self.style.ERROR(
                    f"{FRAMEWORK_URN} is not loaded. Import the ISO 27001:2022 "
                    "library first, from the library catalog."
                )
            )
            return

        audit, domain = self._create_audit(framework, domain_name)
        seeded, missing = self._seed_cases(audit, domain)
        reviewable = [c for c in seeded if c.expected]
        excluded = [c for c in seeded if not c.expected]

        self.stdout.write("")
        self.stdout.write(f"Audit: {audit.name}")
        self.stdout.write(f"  id     {audit.id}")
        self.stdout.write(f"  domain {domain.name}")
        self.stdout.write("")
        self.stdout.write("Expected answers:")
        for case in reviewable:
            self.stdout.write(
                f"  {case.ref_id:<8} {case.result:<22} {case.expected:<12} {case.why}"
            )
        tally = {
            verdict: sum(1 for c in reviewable if c.expected == verdict)
            for verdict in ("concern", "needs_look", "backed")
        }
        self.stdout.write("")
        self.stdout.write(
            f"  {len(reviewable)} reviewable — "
            + ", ".join(f"{n} {verdict}" for verdict, n in tally.items())
        )
        self.stdout.write("")
        self.stdout.write("Outside the filter — a review that mentions these is wrong:")
        for case in excluded:
            self.stdout.write(f"  {case.ref_id:<8} {case.result:<22} {case.why}")
        if missing:
            self.stderr.write(
                self.style.WARNING(
                    f"  not in this framework, skipped: {', '.join(missing)}"
                )
            )

        if options["out"]:
            truth = {
                "audit_id": str(audit.id),
                "framework": FRAMEWORK_URN,
                "expected": {c.ref_id: c.expected for c in reviewable},
                "why": {c.ref_id: c.why for c in reviewable},
                # A run that reports on any of these read past its own filter.
                "excluded": {c.ref_id: c.result for c in excluded},
            }
            with open(options["out"], "w") as handle:
                json.dump(truth, handle, indent=2)
            self.stdout.write(f"\nExpected answers written to {options['out']}")

        self.stdout.write(
            self.style.SUCCESS(f"\nRun the review against it with audit_id={audit.id}")
        )

    def _clean(self, domain_name):
        folders = Folder.objects.filter(name=domain_name)
        if not folders.exists():
            self.stdout.write(f"Nothing to clean: no domain named {domain_name}")
            return
        # Everything seeded here lives in the domain, so the folder takes it all
        # down with it — except a workflow run against the benchmark, which
        # leaves a workflow behind, and `Workflow.folder` is PROTECT. Clearing
        # the condition trees first is what the product's own delete does
        # (WorkflowViewSet.cascade_preclear): conditions PROTECT their variables
        # and both hang off the version, so the trees go or the delete trips.
        from automation.workflows.models import ConditionGroup, Workflow

        for folder in folders:
            self.stdout.write(f"Deleting domain {folder.name} and its contents...")
            workflows = Workflow.objects.filter(folder=folder)
            if workflows.exists():
                ConditionGroup.objects.filter(
                    branch__node__version__workflow__in=workflows
                ).delete()
                self.stdout.write(f"  removing {workflows.count()} workflow(s) first")
                workflows.delete()
            folder.delete()

    def _create_audit(self, framework, domain_name):
        from core.utils import build_initial_field_visibility

        domain = Folder.objects.create(
            name=domain_name,
            description="Seeded ISO 27001 audit with known answers, for benchmarking.",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        perimeter = Perimeter.objects.create(
            name=f"{PREFIX}Corporate IT", folder=domain
        )
        audit = ComplianceAssessment.objects.create(
            name=f"{PREFIX}ISO 27001:2022 — surveillance audit",
            description=(
                "Seeded for benchmarking: each requirement below carries a known "
                "expected answer. Not a real assessment."
            ),
            framework=framework,
            perimeter=perimeter,
            folder=domain,
            field_visibility=build_initial_field_visibility(framework),
        )
        audit.create_requirement_assessments()
        return audit, domain

    def _seed_cases(self, audit, domain):
        seeded, missing = [], []
        for case in CASES:
            assessment = RequirementAssessment.objects.filter(
                compliance_assessment=audit, requirement__ref_id=case.ref_id
            ).first()
            if assessment is None:
                missing.append(case.ref_id)
                continue

            assessment.result = case.result
            assessment.observation = case.observation
            if case.score is not None:
                assessment.is_scored = True
                assessment.score = case.score
            if case.documentation_score is not None:
                assessment.documentation_score = case.documentation_score
            assessment.save()

            control = None
            for name, status in case.controls:
                control = AppliedControl.objects.create(
                    name=name,
                    description=f"Seeded control for {case.ref_id}.",
                    folder=domain,
                    status=status,
                )
                assessment.applied_controls.add(control)

            for doc in case.evidences:
                assessment.evidences.add(self._evidence(doc, domain, case.ref_id))
            for doc in case.control_evidences:
                evidence = self._evidence(doc, domain, case.ref_id)
                if control is not None:
                    control.evidences.add(evidence)
                else:  # pragma: no cover - a case with no control to hang it on
                    assessment.evidences.add(evidence)

            seeded.append(case)
        return seeded, missing

    def _evidence(self, doc, domain, ref_id):
        today = timezone.now().date()
        evidence = Evidence.objects.create(
            name=doc.name,
            description=doc.description,
            folder=domain,
            status=doc.status,
            expiry_date=(
                today - timedelta(days=120) if doc.state == "expired" else None
            ),
        )
        if doc.state != "empty":
            # A link stands in for an uploaded file: both read as "something is
            # behind this title", which is the distinction under test.
            EvidenceRevision.objects.create(
                evidence=evidence,
                version=1,
                link=f"{LINK}{ref_id.lower().replace('.', '-')}",
            )
        return evidence
