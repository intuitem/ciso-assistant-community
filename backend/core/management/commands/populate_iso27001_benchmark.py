"""Seed a labelled ISO 27001 audit for benchmarking the AI evidence review.

The point is the *mix*. A dataset where nothing is evidenced makes any reviewer
look right for saying so, which is exactly what made the first live sweep
uninformative. Here every requirement carries a known answer, so a run can be
scored instead of admired:

    concern      the platform's own quality rules flag it — no control, no
                 evidence, evidence expired or still in draft, a control not yet
                 active, a declared gap with no date. Deterministic: the rule
                 either trips or it does not. Five cases here were seeded as
                 rule gaps and are now caught by rules this benchmark prompted
    needs_look   the rules pass it and a reader would still object: evidence
                 about a different subject, too old to describe the present, a
                 "partial" whose observation describes something else, or an
                 exclusion that gives no reason
    known_gap    a partial claim the rules pass and whose observation names a
                 real gap. Correct, and deliberately not filed with the good
                 news — it is work outstanding
    backed       the rules pass it and the evidence really does show what the
                 requirement asks for, or the exclusion rests on a real fact

A case with no expected bucket is outside the read: non-compliant and unassessed
requirements assert nothing, so the review never fetches them. They are counted
in the audit's own breakdown and a run that writes one up has read past its
filter.

`concern` is settled before any call is made; the other three are the model's.
Which rule fires on which case was measured, not assumed — see the `why` on
each.

    python manage.py populate_iso27001_benchmark --fresh --out /tmp/truth.json
"""

import json
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    Actor,
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
)
from iam.models import Folder, User

# Worst first.
BUCKETS = ("concern", "needs_look", "known_gap", "backed")
#: The buckets only a model can produce. The other two are decided by counting.
MODEL_BUCKETS = ("needs_look", "known_gap", "backed")

PREFIX = "BENCH-"
#: The audit needs one, or the review has nobody to hand its write-up to.
REVIEWER_EMAIL = "bench-reviewer@test.example"
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
    #: A target date on the first control. Without one anywhere, a partial
    #: claim trips requirementAssessmentPartialNoPlan and is settled by rule.
    gap_dated: bool = False
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
        expected="known_gap",
        gap_dated=True,
        why="an honest partial: a real report behind it, and an observation that names what is still missing",
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
        why="an empty record among usable ones does not sink the claim",
        observation="Acceptable use policy acknowledged at onboarding and annually.",
        controls=[("Acceptable use policy with annual acknowledgement", "active")],
        # A.5.10 asks for rules documented AND implemented, so both halves are
        # attached and the empty record is the supplementary one.
        evidences=[
            Doc(
                "Acceptable use policy v2.1",
                "Current signed-off version of the acceptable use policy.",
            ),
            Doc(
                "Acknowledgement export — 2026",
                "Per-employee acknowledgement extract from the HR system, 100% of "
                "staff for the current year.",
            ),
            Doc(
                "Acceptable use briefing deck",
                "Placeholder for the induction slides; never uploaded.",
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
        why="on subject and carried by what is attached, with everything written in French",
        observation=(
            "Vidéosurveillance en place sur les trois sites, avec conservation de 30 jours. "
            "Registre des accès badge revu chaque trimestre par la sécurité physique."
        ),
        controls=[("Vidéosurveillance et contrôle d'accès par badge", "active")],
        # The surveillance record carries the requirement; a badge export alone
        # does not. This case is about reading French — A.8.24 is the one about
        # evidence on the wrong subject.
        control_evidences=[
            Doc(
                "Relevé de vidéosurveillance — T3 2026",
                "Relevé trimestriel des caméras des trois sites : couverture, disponibilité "
                "et conservation des enregistrements sur 30 jours.",
            ),
            Doc(
                "Registre des accès badge — T3 2026",
                "Export trimestriel des accès badge pour les trois sites.",
            ),
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
        expected="concern",
        why="partially compliant with a control and zero evidence — a rule gap this benchmark found, now requirementAssessmentPartialNoEvidence",
        observation="Feeds are consumed informally by the SOC; no formal process yet.",
        controls=[("Subscribe to sector threat intelligence feeds", "active")],
    ),
    Case(
        ref_id="A.8.16",
        result="compliant",
        expected="concern",
        why="an evidence record with nothing uploaded and not in draft — a rule gap this benchmark found, now requirementAssessmentNoUsableEvidence",
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
        expected="concern",
        why="one evidence expired and one empty — a rule gap this benchmark found, now requirementAssessmentNoUsableEvidence",
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
    # ============ outside the read: no claim, so never fetched ==============
    Case(
        ref_id="A.5.2",
        result="non_compliant",
        expected="",
        why="non-compliant is already an admission, so there is nothing to challenge",
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
        why="not answered yet, so there is no claim to challenge",
    ),
    # ============ exclusions: the one answer with no evidence behind it =====
    Case(
        ref_id="A.6.7",
        result="not_applicable",
        expected="backed",
        why="the justification names a fact about the organisation that puts the requirement out of reach",
        observation=(
            "Not applicable: all staff work on site and no role is provisioned for remote "
            "access to production systems."
        ),
    ),
    Case(
        ref_id="A.8.30",
        result="not_applicable",
        expected="needs_look",
        why="the justification restates the exclusion instead of giving a reason for it",
        observation="Out of scope for this audit cycle.",
    ),
    # ============ a partial whose observation does not match the label ======
    Case(
        ref_id="A.8.32",
        result="partially_compliant",
        expected="needs_look",
        gap_dated=True,
        why="the observation describes a complete implementation, so partially compliant is not what it says",
        observation=(
            "All production changes go through the change advisory board and are recorded in "
            "the change register; emergency changes are reviewed retrospectively within 48 hours."
        ),
        controls=[("Change advisory board and change register", "active")],
        evidences=[
            Doc(
                "Change register export — Q3 2026",
                "Every production change for the quarter, with approver, date and rollback plan.",
            )
        ],
        score=3,
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
        reviewed = [c for c in seeded if c.expected]
        outside = [c for c in seeded if not c.expected]

        self.stdout.write("")
        self.stdout.write(f"Audit: {audit.name}")
        self.stdout.write(f"  id     {audit.id}")
        self.stdout.write(f"  domain {domain.name}")
        self.stdout.write("")
        self.stdout.write("Expected answers:")
        for case in reviewed:
            self.stdout.write(
                f"  {case.ref_id:<8} {case.result:<22} {case.expected:<12} {case.why}"
            )
        tally = {
            verdict: sum(1 for c in reviewed if c.expected == verdict)
            for verdict in BUCKETS
        }
        self.stdout.write("")
        self.stdout.write(
            f"  {len(reviewed)} reviewed — "
            + ", ".join(f"{n} {verdict}" for verdict, n in tally.items())
        )
        judged = sum(1 for c in reviewed if c.expected in MODEL_BUCKETS)
        self.stdout.write(
            f"  {judged} of them reach the model; the rest are settled by rule"
        )
        self.stdout.write("")
        self.stdout.write("Outside the read — a review that writes these up is wrong:")
        for case in outside:
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
                "expected": {c.ref_id: c.expected for c in reviewed},
                "why": {c.ref_id: c.why for c in reviewed},
                # A run that reports on any of these read past its own filter.
                "outside": {c.ref_id: c.result for c in outside},
            }
            with open(options["out"], "w") as handle:
                json.dump(truth, handle, indent=2)
            self.stdout.write(f"\nExpected answers written to {options['out']}")

        self.stdout.write(
            self.style.SUCCESS(f"\nRun the review against it with audit_id={audit.id}")
        )

    def _clean(self, domain_name):
        # Only ever a domain this command made. Matching on the name alone would
        # let `--domain` name a real one and take it, and everything in it, down
        # with the seed.
        if not domain_name.startswith(PREFIX):
            raise CommandError(
                f"refusing to clean '{domain_name}': this command only deletes "
                f"domains it seeded, whose names start with {PREFIX}"
            )
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
        user, _created = User.objects.get_or_create(email=REVIEWER_EMAIL)
        audit.reviewers.add(Actor.objects.get(user=user))
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
                    eta=(
                        timezone.now().date() + timedelta(days=90)
                        if case.gap_dated and control is None
                        else None
                    ),
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
