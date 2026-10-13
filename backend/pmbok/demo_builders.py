"""PMBOK demo builder: the 2026 security portfolio, collections,
accreditations and responsibility matrices.

Matrix members are teams: ``Actor`` wraps a user, a team or an entity, and the
demo never creates users. Teams are looked up by name anywhere in the demo
domain tree and created in the root domain when missing, so a teams builder
seeding the same names shares them.
"""

from decimal import Decimal
from typing import ClassVar

from dateutil.relativedelta import relativedelta

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.models import Actor, Policy, Team, Terminology
from pmbok.models import (
    Accreditation,
    GenericCollection,
    Project,
    ResponsibilityAssignment,
    ResponsibilityMatrix,
    ResponsibilityMatrixActivity,
    ResponsibilityMatrixActor,
    ResponsibilityRole,
)

CURRENCY = "EUR"

# ref_id, name, kind, parent ref_id, status, health, priority, start, end, progress, budget, actual cost.
PROJECTS = [
    (
        "PF.2026",
        f"{COMPANY} security portfolio 2026",
        "portfolio",
        None,
        "in_progress",
        "amber",
        1,
        -120,
        270,
        38,
        2_350_000,
        760_000,
    ),
    (
        "PRG.01",
        "Certification and assurance programme",
        "program",
        "PF.2026",
        "in_progress",
        "amber",
        1,
        -100,
        240,
        45,
        640_000,
        260_000,
    ),
    (
        "PRJ.001",
        "ISO 27001 recertification",
        "project",
        "PRG.01",
        "in_progress",
        "green",
        1,
        -150,
        45,
        70,
        160_000,
        108_000,
    ),
    (
        "PRJ.002",
        f"PCI DSS 4.0.1 compliance — {PAY_ENTITY}",
        "project",
        "PRG.01",
        "in_progress",
        "red",
        1,
        -90,
        75,
        40,
        280_000,
        131_000,
    ),
    (
        "PRG.02",
        "Cyber Resilience Act readiness programme",
        "program",
        "PF.2026",
        "in_progress",
        "amber",
        1,
        -180,
        420,
        30,
        820_000,
        245_000,
    ),
    (
        "PRJ.009",
        "Keystone hub v3 secure-by-design",
        "project",
        "PRG.02",
        "in_progress",
        "green",
        1,
        -200,
        160,
        45,
        390_000,
        171_000,
    ),
    (
        "PRJ.010",
        "PSIRT and coordinated disclosure set-up",
        "project",
        "PRG.02",
        "closing",
        "green",
        2,
        -170,
        -5,
        95,
        90_000,
        84_500,
    ),
    (
        "PRJ.003",
        "Workforce IAM modernisation",
        "project",
        "PF.2026",
        "planning",
        "green",
        2,
        20,
        230,
        5,
        310_000,
        12_000,
    ),
    (
        "PRJ.004",
        "OT segmentation of the Brno plant",
        "project",
        "PF.2026",
        "on_hold",
        "amber",
        1,
        -60,
        200,
        20,
        260_000,
        58_000,
    ),
    (
        "PRJ.012",
        "Checkout page script integrity",
        "project",
        "PRG.01",
        "in_progress",
        "amber",
        1,
        -30,
        40,
        35,
        60_000,
        19_000,
    ),
    (
        "PRJ.005",
        "SOC platform migration",
        "project",
        "PF.2026",
        "closed",
        "green",
        2,
        -300,
        -40,
        100,
        95_000,
        102_300,
    ),
    (
        "PRJ.007",
        "Supplier security assurance programme",
        "project",
        "PF.2026",
        "draft",
        None,
        3,
        60,
        330,
        0,
        55_000,
        0,
    ),
    (
        "PRJ.013",
        "Device cloud certificate rotation",
        "project",
        "PF.2026",
        "initiated",
        "green",
        3,
        30,
        210,
        0,
        70_000,
        0,
    ),
    (
        "PRJ.008",
        "Plant historian cloud migration",
        "project",
        "PF.2026",
        "cancelled",
        None,
        4,
        -200,
        -20,
        15,
        40_000,
        6_200,
    ),
]

PROJECT_TEXT = {
    "PF.2026": {
        "description": f"Every security investment {COMPANY} funds in 2026, "
        "tracked against the board-approved security strategy.",
        "purpose": "Give the Executive Committee one view of security spend, "
        "delivery health and risk reduction across corporate IT, the plant, "
        "the products and the payments subsidiary.",
        "objectives": "- Be ready for CRA vulnerability reporting obligations\n"
        "- Keep ISO 27001 certification and PCI DSS compliance\n"
        "- Cut the top-five enterprise risks by one level\n"
        "- Keep the portfolio within 5% of the approved budget",
    },
    "PRG.01": {
        "description": "Certifications, attestations and regulatory returns "
        "that retail partners, the card acquirer and supervisors ask for.",
        "purpose": "Keep the licence to operate: ISO 27001 for retail partners, "
        f"PCI DSS and DORA for {PAY_ENTITY}.",
        "objectives": "- ISO 27001 certificate renewed with no major finding\n"
        "- PCI DSS 4.0.1 report on compliance signed by the QSA\n"
        "- DORA register of information submitted on time",
    },
    "PRJ.001": {
        "description": "Recertification audit of the ISMS covering the device "
        "cloud, the online store and the Lyon and Eindhoven offices.",
        "purpose": "Two of our three largest retail partners make the "
        "certificate a listing condition for connected products.",
        "objectives": "- Close all non-conformities from the last surveillance "
        "audit\n- Extend the scope to the Brno plant at the next cycle",
        "success_criteria": "Certificate renewed by Vantor Legal & Audit; "
        "fewer than five minor non-conformities.",
        "deliverables": "- Statement of Applicability\n- Risk treatment plan\n"
        "- Internal audit report\n- Management review minutes",
        "assumptions": "The certification body keeps the audit slot booked for "
        "the agreed week.",
        "constraints": "No change freeze exemption during the November sales peak.",
        "exit_criteria": "Certificate received and surveillance audit scheduled.",
    },
    "PRJ.002": {
        "description": "Gap closure for PCI DSS 4.0.1 on the store checkout "
        "and instalment payment chain run by the payments subsidiary.",
        "purpose": "Pellion Payments requires a QSA-signed report on compliance "
        "before the contract renewal.",
        "objectives": "- Reduce cardholder data environment scope through "
        "tokenisation\n- Implement requirements 6.4.3 and 11.6.1 on payment "
        "page scripts",
        "success_criteria": "Signed report on compliance and attestation of "
        "compliance.",
        "deliverables": "- CDE network diagram\n- Targeted risk analyses\n"
        "- Authenticated vulnerability scanning",
        "dependencies_note": "Depends on the checkout page script integrity "
        "project (PRJ.012) and CDE segmentation (AC.016).",
        "observation": "Red: script integrity monitoring slipped and the QSA "
        "fieldwork date cannot move.",
    },
    "PRG.02": {
        "description": "Everything the Cyber Resilience Act asks of our "
        "products: vulnerability handling, SBOM, secure defaults, support "
        "period and technical documentation.",
        "purpose": "Vulnerability reporting applies from September 2026 and "
        "the full essential requirements from December 2027; Keystone hub v3 "
        "is the first product designed against them.",
        "objectives": "- Report actively exploited vulnerabilities within 24 "
        "hours\n- Publish an SBOM with every release\n- Complete the CRA "
        "technical file for Keystone hub v3 before launch",
    },
    "PRJ.009": {
        "description": "Security engineering for the Keystone hub v3: threat "
        "model, secure boot, unique device credentials, Matter certification "
        "and pentest before launch.",
        "purpose": "First product built against the CRA essential "
        "requirements from day one.",
        "success_criteria": "No open high finding from the Redhaven Security "
        "pentest; CRA checklist fully assessed.",
        "deliverables": "- Threat model\n- Secure boot chain\n"
        "- CRA technical documentation",
    },
    "PRJ.010": {
        "description": "Stand up the product security incident response team, "
        "the disclosure policy, security.txt and the advisory process.",
        "purpose": "Receive and handle vulnerability reports from researchers "
        "and meet CRA reporting deadlines.",
        "exit_criteria": "Policy published and first advisory issued through "
        "the new process.",
    },
    "PRJ.003": {
        "description": "Consolidate workforce identities in the Brightline "
        "Identity tenant, enforce FIDO2 keys for admins and automate joiner, "
        "mover and leaver flows from HR.",
        "purpose": "Leavers kept access for up to two weeks in the last access review.",
        "objectives": "- Onboard the 60 most-used applications to SSO\n"
        "- Phishing-resistant MFA for every privileged account",
    },
    "PRJ.004": {
        "description": "Segment the Brno plant into IEC 62443 zones and put "
        "assembly cell PLCs behind monitored conduits, with a DMZ jump host "
        "for Linterra Automation.",
        "purpose": "A ransomware outbreak in corporate IT must not stop the "
        "assembly line.",
        "observation": "On hold until the summer shutdown window; firewall "
        "hardware delivery delayed four weeks.",
    },
    "PRJ.012": {
        "description": "Inventory, authorise and monitor every script loaded "
        "on the checkout pages; alert on unexpected changes.",
        "purpose": "Close the skimming scenario (RS.09) and meet PCI DSS "
        "requirements 6.4.3 and 11.6.1.",
    },
    "PRJ.005": {
        "description": "Move log collection and detection rules from the "
        "on-premises SIEM to the managed SOC platform.",
        "purpose": "End of support of the on-premises appliance.",
        "success_criteria": "All tier-1 log sources onboarded, including the "
        "MQTT device gateway; detection coverage at least equal to the old "
        "platform.",
        "observation": "Closed 8% over budget because of extra ingestion "
        "volume from device telemetry.",
    },
    "PRJ.007": {
        "description": "Tiered assurance of the suppliers that touch customer "
        "data, card data, firmware or production systems.",
        "purpose": "NIS2 supply chain obligations and DORA third-party risk oversight.",
    },
    "PRJ.013": {
        "description": "Rotate the device cloud intermediate CA and move "
        "device certificates to a shorter lifetime with automated renewal.",
        "purpose": "The current intermediate expires within the support "
        "period of the oldest Kelvin thermostats.",
    },
    "PRJ.008": {
        "description": "Replicate the plant historian to the device cloud for "
        "production analytics.",
        "purpose": "Give the Lyon quality team live yield data.",
        "observation": "Cancelled: an inbound path from the cloud conflicts "
        "with the OT security policy zone model; replaced by a one-way export "
        "in PRJ.004.",
    },
}

# ref_id, name, description, audit ref_ids, policies (None = all, n = first n),
# include the enterprise risk assessment, dependency collection ref_ids.
COLLECTIONS = [
    (
        "COL.01",
        "ISO 27001 recertification dossier",
        "Audits, risk assessment and policies the auditor reviews at recertification.",
        ("AUD.2026.01", "AUD.2025.04"),
        None,
        True,
        (),
    ),
    (
        "COL.02",
        "PCI DSS evidence pack",
        (
            "Everything the QSA samples on the payments subsidiary's cardholder "
            "data environment."
        ),
        ("AUD.2026.03",),
        2,
        False,
        (),
    ),
    (
        "COL.03",
        "Keystone hub v3 CRA technical file",
        (
            "Conformity evidence for Keystone hub v3: CRA checklist, risk "
            "assessment, SBOM and test reports."
        ),
        ("AUD.2026.05",),
        0,
        True,
        (),
    ),
    (
        "COL.04",
        "Brno OT zone accreditation file",
        (
            "IEC 62443 assessment, plant readiness review and zone diagrams "
            "supporting the OT zone accreditation."
        ),
        ("AUD.2026.04", "AUD.2025.04"),
        0,
        True,
        ("COL.01",),
    ),
]

# ref_id, name, category, status, commission offset, duration (months),
# checklist audit ref_id, collection ref_id, observation.
ACCREDITATIONS = [
    (
        "ACC.2026.01",
        "Keystone hub v3 product security approval",
        "accreditation_advanced",
        "in_progress",
        None,
        24,
        "AUD.2026.05",
        "COL.03",
        (
            "Approval decision planned after the Redhaven Security pentest and "
            "closure of CRA checklist gaps."
        ),
    ),
    (
        "ACC.2026.02",
        "Payments checkout accreditation",
        "accreditation_elaborated",
        "accredited",
        -45,
        12,
        "AUD.2026.03",
        "COL.02",
        (
            "Accredited with reservations: payment page script monitoring must be "
            "live before the November sales peak."
        ),
    ),
    (
        "ACC.2026.03",
        "Brno OT zone accreditation",
        "accreditation_elaborated",
        "draft",
        None,
        None,
        "AUD.2026.04",
        "COL.04",
        "",
    ),
    (
        "ACC.2025.01",
        "Device cloud platform accreditation",
        "accreditation_elaborated",
        "accredited",
        -260,
        24,
        "AUD.2026.01",
        "COL.01",
        (
            "Renewal review brought forward if the certificate rotation project "
            "changes the device trust chain."
        ),
    ),
    (
        "ACC.2023.01",
        "Lookout v1 cloud recording service accreditation",
        "accreditation_simplified",
        "obsolete",
        -1000,
        24,
        None,
        None,
        (
            "Service replaced by the device cloud recording service; accreditation "
            "kept for the record."
        ),
    ),
]

TEAMS = [
    ("Security Operations Centre", "24/7 monitoring, triage and first response."),
    (
        "PSIRT",
        "PSIRT, secure development and product vulnerability handling.",
    ),
    ("Firmware Engineering", "Firmware for Kelvin, Lookout and Keystone devices."),
    ("Cloud Platform", "Device cloud, MQTT gateway and OTA service."),
    ("IT Operations", "Infrastructure, endpoints and the service desk."),
    ("OT Engineering", "PLC, SCADA and plant network engineering in Brno."),
    ("Legal and Compliance", "Contracts, regulatory notifications and audits."),
    ("Data Protection Office", "DPO and privacy analysts."),
    ("Corporate Communications", "Press, customer and staff communications."),
    ("Customer Support", "Support desk run with Mireo Support."),
    ("Payments Risk", f"ICT and operational risk at {PAY_ENTITY}."),
    ("Executive Committee", "CEO, CFO, COO and the CISO."),
]

# name, ref_id, preset, project ref_ids, description,
# links: (control ref_ids, asset names, audit ref_ids, risk assessment),
# activities: (name, description, {team name: role code}).
MATRICES = [
    (
        "Incident response RACI",
        "RACI.IR",
        "raci",
        ("PRJ.001",),
        (
            "Who does what when a security incident is declared, from triage to "
            "the post-incident review, including every regulatory clock."
        ),
        (
            ("AC.008", "AC.009", "AC.002"),
            (
                "Device cloud Kubernetes cluster",
                "Store checkout and payments",
                "Production line control",
            ),
            ("AUD.2026.06",),
            False,
        ),
        [
            (
                "Detect and triage alerts",
                (
                    "Qualify the alert, open the incident ticket and page the on-call "
                    "lead."
                ),
                {
                    "Security Operations Centre": "R",
                    "IT Operations": "C",
                    "Executive Committee": "A",
                },
            ),
            (
                "Classify severity",
                "Apply the severity matrix of the incident response procedure.",
                {
                    "Security Operations Centre": "A",
                    "IT Operations": "R",
                    "PSIRT": "C",
                    "Data Protection Office": "C",
                },
            ),
            (
                "Contain the threat",
                (
                    "Isolate hosts, close IT/OT conduits, halt OTA rollouts, revoke "
                    "credentials."
                ),
                {
                    "IT Operations": "R",
                    "OT Engineering": "R",
                    "Security Operations Centre": "A",
                    "Cloud Platform": "C",
                },
            ),
            (
                "Eradicate and recover",
                "Rebuild from known-good images and restore from backups.",
                {
                    "IT Operations": "R",
                    "Security Operations Centre": "A",
                    "Cloud Platform": "R",
                    "Executive Committee": "I",
                },
            ),
            (
                "Send the NIS2 early warning",
                "Early warning to the CSIRT within 24 hours of a significant incident.",
                {
                    "Legal and Compliance": "R",
                    "Executive Committee": "A",
                    "Security Operations Centre": "C",
                },
            ),
            (
                "Notify DORA major incidents",
                (
                    f"Initial notification for {PAY_ENTITY} within 4 hours of "
                    "classification."
                ),
                {
                    "Payments Risk": "R",
                    "Executive Committee": "A",
                    "Legal and Compliance": "C",
                    "Security Operations Centre": "C",
                },
            ),
            (
                "Notify the supervisory authority",
                (
                    "GDPR article 33 notification within 72 hours when personal data "
                    "is at risk."
                ),
                {
                    "Data Protection Office": "R",
                    "Legal and Compliance": "A",
                    "Executive Committee": "I",
                },
            ),
            (
                "Communicate with customers and press",
                "Holding statement, customer notice in the companion app and FAQ.",
                {
                    "Corporate Communications": "R",
                    "Executive Committee": "A",
                    "Customer Support": "C",
                    "Legal and Compliance": "C",
                },
            ),
            (
                "Run the post-incident review",
                (
                    "Blameless review within ten working days; actions tracked as "
                    "applied controls."
                ),
                {
                    "Security Operations Centre": "R",
                    "Executive Committee": "A",
                    "IT Operations": "C",
                    "PSIRT": "C",
                },
            ),
        ],
    ),
    (
        "Vulnerability management RASCI",
        "RASCI.VM",
        "rasci",
        ("PRJ.001", "PRJ.002"),
        (
            "Scanning, triage and patching responsibilities for the corporate "
            "IT, device cloud and store platforms in certification scope."
        ),
        (
            ("AC.010", "AC.016"),
            (
                "Online store web front",
                "Device cloud Kubernetes cluster",
                "Corporate VPN gateway",
            ),
            ("AUD.2026.01",),
            False,
        ),
        [
            (
                "Run authenticated scans",
                "Weekly on internet-facing assets, monthly internally.",
                {
                    "Security Operations Centre": "R",
                    "IT Operations": "S",
                    "Executive Committee": "I",
                },
            ),
            (
                "Triage and assign findings",
                "Confirm exploitability, set the due date from the SLA table.",
                {
                    "Security Operations Centre": "A",
                    "IT Operations": "R",
                    "Cloud Platform": "C",
                },
            ),
            (
                "Patch infrastructure",
                "Operating systems, middleware and network devices.",
                {"IT Operations": "R", "Security Operations Centre": "A"},
            ),
            (
                "Fix cloud and store vulnerabilities",
                "Code and dependency fixes shipped through the normal pipeline.",
                {
                    "Cloud Platform": "R",
                    "Security Operations Centre": "A",
                    "IT Operations": "S",
                },
            ),
            (
                "Approve risk exceptions",
                "Findings that cannot meet the SLA go to a time-boxed exception.",
                {
                    "Executive Committee": "A",
                    "Legal and Compliance": "C",
                    "Security Operations Centre": "R",
                },
            ),
        ],
    ),
    (
        "Risk acceptance decisions",
        "RAPID.RA",
        "rapid",
        ("PF.2026",),
        "Decision rights for accepting residual risk above appetite.",
        ((), (), (), True),
        [
            (
                "Accept a high residual risk",
                "Residual risk above appetite on a primary asset.",
                {
                    "Security Operations Centre": "R",
                    "Legal and Compliance": "A",
                    "IT Operations": "I",
                    "Executive Committee": "D",
                },
            ),
            (
                "Grant a security exception",
                "Deviation from policy for up to six months.",
                {
                    "Security Operations Centre": "R",
                    "Data Protection Office": "I",
                    "OT Engineering": "P",
                    "Executive Committee": "D",
                },
            ),
            (
                "Ship a product with a known vulnerability",
                "Release despite an open medium finding with a planned fix.",
                {
                    "PSIRT": "R",
                    "Firmware Engineering": "P",
                    "Legal and Compliance": "A",
                    "Executive Committee": "D",
                },
            ),
        ],
    ),
]


def terminology(field_path, name):
    return Terminology.objects.get(field_path=field_path, name=name)


@register
class PmbokBuilder(DemoBuilder):
    """Security portfolio, collections, accreditations and RACI matrices."""

    name = "pmbok"
    feature_flags = ("project_management",)
    # After governance, so RACI actors reuse its teams instead of duplicating them.
    depends = ("core", "compliance", "risk", "governance")
    covers: ClassVar[dict] = {
        Project: "folder",
        GenericCollection: "folder",
        Accreditation: "folder",
        ResponsibilityMatrix: "folder",
        ResponsibilityMatrixActivity: "folder",
        ResponsibilityMatrixActor: "folder",
        ResponsibilityAssignment: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (Project, {"folder__in": folders}, ("ref_id",)),
            (GenericCollection, {"folder__in": folders}, ("name",)),
            (Accreditation, {"folder__in": folders}, ("ref_id",)),
            (ResponsibilityMatrix, {"folder__in": folders}, ("ref_id",)),
            (
                ResponsibilityMatrixActivity,
                {"folder__in": folders},
                ("matrix__ref_id", "order"),
            ),
            (
                ResponsibilityMatrixActor,
                {"folder__in": folders},
                ("matrix__ref_id", "order"),
            ),
            (
                ResponsibilityAssignment,
                {"folder__in": folders},
                ("activity__matrix__ref_id", "activity__order", "actor__team__name"),
            ),
        ]

    def build(self, ctx):
        collections = self.build_collections(ctx)
        projects = self.build_projects(ctx)
        self.build_accreditations(ctx, collections)
        self.build_matrices(ctx, projects)

    @staticmethod
    def audits(ctx, ref_ids):
        wanted = set(ref_ids)
        return [a for a in ctx.refs.get("audits", []) if a.ref_id in wanted]

    def build_collections(self, ctx):
        policies = list(Policy.objects.filter(folder=ctx.domain).order_by("ref_id"))
        risk_assessment = ctx.refs.get("risk_assessment")
        collections = {}
        for (
            ref_id,
            name,
            description,
            audit_refs,
            policy_count,
            with_risk,
            dependencies,
        ) in COLLECTIONS:
            collection, created = GenericCollection.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={"ref_id": ref_id, "description": description},
            )
            collections[ref_id] = collection
            if not created:
                continue
            collection.compliance_assessments.set(self.audits(ctx, audit_refs))
            if policy_count is None:
                collection.policies.set(policies)
            elif policy_count:
                collection.policies.set(policies[:policy_count])
            if with_risk and risk_assessment:
                collection.risk_assessments.set([risk_assessment])
            if dependencies:
                collection.dependencies.set([collections[d] for d in dependencies])
        return collections

    def build_projects(self, ctx):
        projects = {}
        for (
            ref_id,
            name,
            kind,
            parent,
            status,
            health,
            priority,
            start,
            end,
            progress,
            budget,
            cost,
        ) in PROJECTS:
            text = PROJECT_TEXT.get(ref_id, {})
            folder = ctx.domain
            existing = Project.objects.filter(name=name, folder=folder).first()
            if existing:
                projects[ref_id] = existing
                continue
            defaults = {
                key: value for key, value in text.items() if key != "description"
            }
            # closed_at is passed explicitly: save() would stamp today's date.
            project = Project.objects.create(
                name=name,
                folder=folder,
                ref_id=ref_id,
                kind=kind,
                description=text.get("description", ""),
                parent_project=projects.get(parent),
                status=terminology(Terminology.FieldPath.PROJECT_STATUS, status),
                health=terminology(Terminology.FieldPath.PROJECT_HEALTH, health)
                if health
                else None,
                priority=priority,
                start_date=ctx.day(start),
                end_date=ctx.day(end),
                eta=ctx.day(end + (20 if health == "red" else 0)),
                closed_at=ctx.day(end) if status == "closed" else None,
                progress=progress,
                budget=Decimal(budget),
                actual_cost=Decimal(cost),
                currency=CURRENCY,
                tolerances={
                    "time": {"plus_days": 30, "minus_days": 0},
                    "cost": {"plus_pct": 10, "minus_pct": 5},
                },
                **defaults,
            )
            projects[ref_id] = project
        # Projects auto-create a collection named after them; give the
        # certification and product ones the matching audits so their tabs are
        # not empty.
        for ref_id, audit_refs in (
            ("PRJ.001", ("AUD.2026.01", "AUD.2025.04")),
            ("PRJ.002", ("AUD.2026.03",)),
            ("PRJ.009", ("AUD.2026.05",)),
            ("PRJ.004", ("AUD.2026.04",)),
        ):
            collection = projects[ref_id].linked_collection
            if collection is not None:
                collection.compliance_assessments.set(self.audits(ctx, audit_refs))
        return projects

    def build_accreditations(self, ctx, collections):
        for (
            ref_id,
            name,
            category,
            status,
            commission,
            duration,
            audit_ref,
            collection_ref,
            observation,
        ) in ACCREDITATIONS:
            commission_date = ctx.day(commission) if commission is not None else None
            # Same rule as the write serializer: commission + duration.
            expiry = (
                commission_date + relativedelta(months=duration)
                if commission_date and duration
                else None
            )
            checklist = self.audits(ctx, (audit_ref,)) if audit_ref else []
            Accreditation.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "category": terminology(
                        Terminology.FieldPath.ACCREDITATION_CATEGORY, category
                    ),
                    "status": terminology(
                        Terminology.FieldPath.ACCREDITATION_STATUS, status
                    ),
                    "authority_name": "Security Accreditation Board "
                    "(CISO, CIO, Head of Product Security)",
                    "commission_date": commission_date,
                    "duration_months": duration,
                    "expiry_date": expiry,
                    "checklist": checklist[0] if checklist else None,
                    "linked_collection": collections.get(collection_ref),
                    "observation": observation,
                },
            )

    def build_matrices(self, ctx, projects):
        actors = self.team_actors(ctx)
        assets = ctx.refs.get("assets", [])
        controls = ctx.refs.get("controls", [])
        risk_assessment = ctx.refs.get("risk_assessment")
        for (
            name,
            ref_id,
            preset,
            project_refs,
            description,
            links,
            activities,
        ) in MATRICES:
            control_refs, asset_names, audit_refs, with_risk = links
            matrix, created = ResponsibilityMatrix.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "preset": preset,
                    "description": description,
                },
            )
            if not created:
                continue
            # As the write serializer does: a preset matrix gets its builtin roles.
            roles = {
                role.code: role
                for role in ResponsibilityRole.objects.filter(
                    taxonomy=preset, builtin=True, is_visible=True
                )
            }
            matrix.roles.set(roles.values())
            matrix.projects.set([projects[r] for r in project_refs if r in projects])
            members = []
            for _, _, cells in activities:
                members += [team for team in cells if team not in members]
            for order, team in enumerate(members, start=1):
                ResponsibilityMatrixActor.objects.create(
                    matrix=matrix, actor=actors[team], order=order
                )
            # Each activity draws from the matrix's own pool, so links stay on topic.
            control_pool = [c for c in controls if c.ref_id in control_refs] or controls
            asset_pool = [a for a in assets if a.name in asset_names] or assets
            matrix_audits = self.audits(ctx, audit_refs)
            for order, (activity_name, activity_description, cells) in enumerate(
                activities, start=1
            ):
                activity = ResponsibilityMatrixActivity.objects.create(
                    matrix=matrix,
                    name=activity_name,
                    description=activity_description,
                    order=order,
                )
                if control_pool:
                    activity.applied_controls.set(
                        ctx.rng.sample(control_pool, min(2, len(control_pool)))
                    )
                if asset_pool:
                    activity.assets.set(ctx.rng.sample(asset_pool, 1))
                if matrix_audits:
                    activity.compliance_assessments.set(matrix_audits)
                if with_risk and risk_assessment:
                    activity.risk_assessments.set([risk_assessment])
                for team, code in cells.items():
                    if code not in roles:
                        ctx.err(f"role {code} missing from {preset} preset")
                        continue
                    ResponsibilityAssignment.objects.create(
                        activity=activity, actor=actors[team], role=roles[code]
                    )

    def team_actors(self, ctx):
        folders = ctx.folders()
        actors = {}
        for name, description in TEAMS:
            team = (
                Team.objects.filter(name=name, folder__in=folders)
                .order_by("created_at")
                .first()
            )
            if team is None:
                team = Team.objects.create(
                    name=name, folder=ctx.domain, description=description
                )
            actors[name], _ = Actor.objects.get_or_create(team=team)
        return actors
