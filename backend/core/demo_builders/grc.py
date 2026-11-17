"""Core GRC builders: organisation, assets, controls, audits, risk.

Content is a fixed vocabulary; the only randomness comes from ``ctx.rng``.
Builders that need objects from another builder read them from ``ctx.refs``:

- ``core``: ``assets``, ``controls``, ``perimeters``
- ``compliance``: ``framework``, ``audits``
- ``risk``: ``risk_assessment``, ``threats``, ``risk_scenarios``
"""

from typing import ClassVar

from core.demo import PAY_ENTITY, DemoBuilder, register
from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Framework,
    Perimeter,
    Policy,
    ReferenceControl,
    RequirementAssessment,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    Threat,
)
from core.utils import get_global_currency
from iam.models import Folder

ISO27001_LIBRARY = "urn:intuitem:risk:library:iso27001-2022"
MATRIX_LIBRARY = "urn:intuitem:risk:library:risk-matrix-5x5-iso27005"
PCI_DSS_LIBRARY = "urn:intuitem:risk:library:pcidss-4_0"
IEC_62443_LIBRARY = "urn:intuitem:risk:library:iec-62443-3-3-2013"
CRA_LIBRARY = "urn:intuitem:risk:library:cra-resolution-annexes"
NIS2_LIBRARY = "urn:intuitem:risk:library:nis2-directive"
NIST_CSF_LIBRARY = "urn:intuitem:risk:library:nist-csf-2.0"

PERIMETERS = [
    ("PER.001", "Device cloud platform", "in_prod"),
    ("PER.002", "Online store and checkout", "in_prod"),
    ("PER.003", "Brno assembly plant", "in_prod"),
    ("PER.004", "Keystone hub v3 programme", "in_dev"),
]

# name, description, {objective: 0-4}
PRIMARY_ASSETS = [
    (
        "Store checkout and payments",
        (
            "Card and instalment payments taken on the online store, run by the "
            f"{PAY_ENTITY} subsidiary."
        ),
        {"confidentiality": 3, "integrity": 4, "availability": 3},
    ),
    (
        "Customer and device accounts",
        "Store customers, companion-app users and the devices paired to them.",
        {"confidentiality": 3, "integrity": 3, "availability": 2, "privacy": 4},
    ),
    (
        "Order fulfilment",
        "Order capture through to dispatch from the Brno warehouse.",
        {"confidentiality": 1, "integrity": 2, "availability": 3},
    ),
    (
        "Device firmware and signing keys",
        (
            "Firmware images for Kelvin thermostats, Lookout cameras and Keystone "
            "hubs, and the keys that sign every over-the-air update."
        ),
        {"confidentiality": 4, "integrity": 4, "availability": 2, "authenticity": 4},
    ),
    (
        "Production line control",
        "Recipes, test benches and line control for the Brno assembly plant.",
        {"integrity": 3, "availability": 4, "safety": 3},
    ),
    (
        "Product designs and source code",
        "Hardware schematics, firmware and app source, and the patent pipeline.",
        {"confidentiality": 4, "integrity": 3, "availability": 1},
    ),
]

# name, description, parent primary asset
SUPPORTING_ASSETS = [
    (
        "Device cloud Kubernetes cluster",
        "Three-zone managed cluster hosting the device backend and the store.",
        "Customer and device accounts",
    ),
    (
        "PostgreSQL primary",
        "Transactional store, streaming replica in the DR region.",
        "Store checkout and payments",
    ),
    (
        "Corporate VPN gateway",
        "Remote access concentrator for staff and contractors.",
        "Product designs and source code",
    ),
    (
        "S3 evidence bucket",
        "Immutable audit evidence, object-lock enabled.",
        "Order fulfilment",
    ),
    (
        "Firmware CI build farm",
        "Build runners that compile, test and package every firmware release.",
        "Device firmware and signing keys",
    ),
    (
        "Workforce identity provider",
        "Single sign-on and provisioning for every employee and contractor.",
        "Product designs and source code",
    ),
    (
        "Firmware signing HSM",
        "Hardware security module holding the OTA update signing keys.",
        "Device firmware and signing keys",
    ),
    (
        "MQTT device gateway",
        "Broker fleet that every deployed device connects to.",
        "Customer and device accounts",
    ),
    (
        "Online store web front",
        "Storefront, basket and checkout pages.",
        "Store checkout and payments",
    ),
    (
        "Companion mobile app",
        "iOS and Android app used to pair and control devices.",
        "Customer and device accounts",
    ),
    (
        "Plant SCADA server",
        "Supervises the assembly cells and the end-of-line test benches.",
        "Production line control",
    ),
    (
        "Assembly cell PLCs",
        "Programmable controllers driving the pick-and-place and soldering cells.",
        "Production line control",
    ),
]

# ref_id, name, category, csf_function, status, priority, effort, eta offset.
# csf_function is spread across all six functions on purpose: the analytics
# summary renders a CSF radar, and controls left unset collapse into a single
# "--" wedge that makes the chart useless as a documentation image.
CONTROLS = [
    (
        "AC.001",
        "Quarterly access review",
        "technical",
        "protect",
        "in_progress",
        1,
        "M",
        30,
    ),
    (
        "AC.002",
        "Privileged session recording",
        "technical",
        "detect",
        "to_do",
        1,
        "L",
        75,
    ),
    ("AC.003", "Backup restore test", "process", "recover", "active", 2, "S", -20),
    (
        "AC.004",
        "Supplier security questionnaire",
        "process",
        "govern",
        "in_progress",
        2,
        "M",
        45,
    ),
    (
        "AC.005",
        "Endpoint disk encryption",
        "technical",
        "protect",
        "active",
        1,
        "M",
        -60,
    ),
    (
        "AC.006",
        "Secure firmware development training",
        "policy",
        "protect",
        "to_do",
        3,
        "S",
        90,
    ),
    (
        "AC.007",
        "IT/OT network segmentation",
        "technical",
        "protect",
        "on_hold",
        2,
        "L",
        120,
    ),
    (
        "AC.008",
        "Incident response tabletop",
        "process",
        "respond",
        "active",
        2,
        "M",
        -10,
    ),
    ("AC.009", "Log retention policy", "policy", "detect", "active", 3, "XS", -120),
    (
        "AC.010",
        "Vulnerability handling and disclosure",
        "process",
        "identify",
        "in_progress",
        1,
        "S",
        15,
    ),
    ("AC.011", "Data retention schedule", "policy", "govern", "to_do", 4, "M", 150),
    (
        "AC.012",
        "Plant physical access badge audit",
        "physical",
        "recover",
        "active",
        3,
        "S",
        -45,
    ),
    ("AC.013", "Firmware code signing", "technical", "protect", "active", 1, "M", -90),
    (
        "AC.014",
        "Staged OTA update rollout",
        "process",
        "recover",
        "in_progress",
        1,
        "M",
        20,
    ),
    (
        "AC.015",
        "SBOM published with every release",
        "process",
        "identify",
        "in_progress",
        2,
        "S",
        40,
    ),
    (
        "AC.016",
        "Cardholder data environment segmentation",
        "technical",
        "protect",
        "active",
        1,
        "L",
        -30,
    ),
    ("AC.017", "PLC change management", "process", "govern", "to_do", 2, "M", 60),
    (
        "AC.018",
        "Unique per-device default credentials",
        "technical",
        "protect",
        "active",
        1,
        "M",
        -150,
    ),
]

# Build and run cost per control (fixed EUR, people-days), amortised over three
# years. Without them the CRQ studies can't compute a return on investment.
# ref_id: (build fixed, build days, run fixed, run days)
# Control ref_id -> (ISO 27001 Annex A reference control, assets it protects).
CONTROL_LINKS = {
    "AC.001": (
        "A.5.18",
        ("Workforce identity provider", "Customer and device accounts"),
    ),
    "AC.002": ("A.8.2", ("Device cloud Kubernetes cluster", "PostgreSQL primary")),
    "AC.003": ("A.8.13", ("PostgreSQL primary", "Plant SCADA server")),
    "AC.004": (
        "A.5.19",
        ("Device cloud Kubernetes cluster", "Store checkout and payments"),
    ),
    "AC.005": ("A.8.1", ("Product designs and source code",)),
    "AC.006": ("A.6.3", ("Device firmware and signing keys", "Firmware CI build farm")),
    "AC.007": ("A.8.22", ("Production line control", "Plant SCADA server")),
    "AC.008": ("A.5.24", ("Store checkout and payments", "Production line control")),
    "AC.009": ("A.8.15", ("S3 evidence bucket", "Device cloud Kubernetes cluster")),
    "AC.010": ("A.8.8", ("Companion mobile app", "Device firmware and signing keys")),
    "AC.011": ("A.8.10", ("Customer and device accounts", "PostgreSQL primary")),
    "AC.012": ("A.7.2", ("Production line control",)),
    "AC.013": ("A.8.24", ("Firmware signing HSM", "Device firmware and signing keys")),
    "AC.014": ("A.8.32", ("MQTT device gateway", "Device firmware and signing keys")),
    "AC.015": ("A.8.8", ("Firmware CI build farm", "Companion mobile app")),
    "AC.016": ("A.8.22", ("Store checkout and payments", "Online store web front")),
    "AC.017": ("A.8.32", ("Assembly cell PLCs", "Production line control")),
    "AC.018": ("A.8.5", ("Device firmware and signing keys", "MQTT device gateway")),
}

CONTROL_COSTS = {
    "AC.001": (0, 10, 0, 24),
    "AC.002": (45000, 30, 12000, 10),
    "AC.003": (0, 5, 0, 12),
    "AC.004": (8000, 15, 0, 20),
    "AC.005": (15000, 10, 4000, 4),
    "AC.006": (12000, 5, 6000, 5),
    "AC.007": (180000, 90, 25000, 20),
    "AC.008": (6000, 4, 6000, 4),
    "AC.009": (0, 3, 18000, 2),
    "AC.010": (20000, 25, 0, 60),
    "AC.011": (0, 12, 0, 6),
    "AC.012": (4000, 3, 0, 6),
    "AC.013": (60000, 20, 8000, 12),
    "AC.014": (35000, 40, 0, 15),
    "AC.015": (25000, 30, 10000, 10),
    "AC.016": (90000, 45, 15000, 10),
    "AC.017": (10000, 20, 0, 30),
    "AC.018": (40000, 35, 0, 5),
}

# ref_id, name, framework URN, perimeter ref_id, status, due offset,
# share of requirements given a result (the lead ISO audit is filled in fully).
AUDITS = [
    (
        "AUD.2026.01",
        "ISO 27001:2022 — annual certification audit",
        ISO27001_LIBRARY,
        "PER.001",
        "in_progress",
        45,
        1.0,
    ),
    (
        "AUD.2025.04",
        "ISO 27001:2022 — Brno plant readiness review",
        ISO27001_LIBRARY,
        "PER.003",
        "done",
        -30,
        1.0,
    ),
    (
        "AUD.2026.03",
        f"PCI DSS 4.0.1 — {PAY_ENTITY} self-assessment",
        PCI_DSS_LIBRARY,
        "PER.002",
        "in_progress",
        75,
        0.6,
    ),
    (
        "AUD.2026.04",
        "IEC 62443-3-3 — assembly line zones",
        IEC_62443_LIBRARY,
        "PER.003",
        "in_progress",
        100,
        0.4,
    ),
    (
        "AUD.2026.05",
        "CRA essential requirements — Keystone hub v3",
        CRA_LIBRARY,
        "PER.004",
        "in_progress",
        160,
        0.3,
    ),
    (
        "AUD.2026.06",
        "NIS2 — important entity gap analysis",
        NIS2_LIBRARY,
        None,
        "done",
        -15,
        1.0,
    ),
    (
        "AUD.2026.07",
        "NIST CSF 2.0 — minimum security baseline",
        NIST_CSF_LIBRARY,
        None,
        "in_progress",
        90,
        0.7,
    ),
]

# Scenario ref_id -> (assets, existing controls, additional controls).
SCENARIO_LINKS = {
    "RS.01": (
        ("Production line control", "Plant SCADA server"),
        ("AC.003",),
        ("AC.007", "AC.017"),
    ),
    "RS.02": (
        ("Customer and device accounts", "Online store web front"),
        ("AC.009",),
        ("AC.008",),
    ),
    "RS.03": (
        ("Product designs and source code", "Workforce identity provider"),
        ("AC.005",),
        ("AC.001", "AC.002"),
    ),
    "RS.04": (
        ("Device firmware and signing keys", "Firmware CI build farm"),
        ("AC.006",),
        ("AC.015", "AC.010"),
    ),
    "RS.05": (
        ("Customer and device accounts", "S3 evidence bucket"),
        ("AC.011",),
        ("AC.009",),
    ),
    "RS.06": (
        ("Online store web front", "Store checkout and payments"),
        (),
        ("AC.008",),
    ),
    "RS.07": (
        ("Device firmware and signing keys", "Firmware signing HSM"),
        ("AC.013",),
        ("AC.014", "AC.002"),
    ),
    "RS.08": (
        ("Assembly cell PLCs", "Corporate VPN gateway"),
        ("AC.004",),
        ("AC.007", "AC.002"),
    ),
    "RS.09": (
        ("Online store web front", "Store checkout and payments"),
        ("AC.016",),
        ("AC.004",),
    ),
    "PAY.01": (("Store checkout and payments",), ("AC.004",), ("AC.008",)),
    "PAY.02": (
        ("Customer and device accounts", "Store checkout and payments"),
        ("AC.009",),
        ("AC.008",),
    ),
    "PAY.03": (
        ("Store checkout and payments", "PostgreSQL primary"),
        ("AC.016",),
        ("AC.001", "AC.002"),
    ),
    "PAY.04": (
        ("Device cloud Kubernetes cluster", "Store checkout and payments"),
        ("AC.003",),
        ("AC.004",),
    ),
}

THREATS = [
    ("T-001", "Ransomware deployment"),
    ("T-002", "Credential stuffing"),
    ("T-003", "Insider data exfiltration"),
    ("T-004", "Supply chain compromise"),
    ("T-005", "Cloud misconfiguration"),
    ("T-006", "Denial of service"),
    ("T-007", "Malicious firmware update"),
    ("T-008", "OT intrusion through remote maintenance"),
    ("T-009", "Payment page skimming"),
]

# Probability and impact are 0-based indices into the matrix grid (0..4 on a 5x5).
# ref_id, name, current p/i, residual p/i, treatment, threat ref_id
SCENARIOS = [
    (
        "RS.01",
        "Ransomware halts the Brno assembly line",
        3,
        4,
        1,
        3,
        "mitigate",
        "T-001",
    ),
    (
        "RS.02",
        "Customer credentials replayed against the online store",
        3,
        2,
        1,
        2,
        "mitigate",
        "T-002",
    ),
    (
        "RS.03",
        "Departing engineer exports product designs",
        1,
        4,
        1,
        2,
        "mitigate",
        "T-003",
    ),
    (
        "RS.04",
        "Compromised build dependency ships in hub firmware",
        1,
        4,
        0,
        3,
        "mitigate",
        "T-004",
    ),
    (
        "RS.05",
        "Public object storage exposes device telemetry",
        2,
        2,
        0,
        1,
        "mitigate",
        "T-005",
    ),
    (
        "RS.06",
        "Volumetric attack saturates the store during a launch",
        2,
        1,
        2,
        1,
        "accept",
        "T-006",
    ),
    (
        "RS.07",
        "Stolen signing key pushes a malicious OTA update",
        1,
        4,
        0,
        4,
        "mitigate",
        "T-007",
    ),
    (
        "RS.08",
        "Vendor remote access used to reach assembly PLCs",
        2,
        3,
        1,
        2,
        "mitigate",
        "T-008",
    ),
    (
        "RS.09",
        "Skimming script injected into the checkout page",
        2,
        3,
        1,
        1,
        "mitigate",
        "T-009",
    ),
]

# A second, smaller register for the payments subsidiary (DORA ICT risk).
PAY_SCENARIOS = [
    ("PAY.01", "Card processor outage stops checkout", 2, 3, 2, 2, "transfer", "T-006"),
    (
        "PAY.02",
        "Fraudulent instalment applications with stolen identities",
        3,
        2,
        1,
        2,
        "mitigate",
        "T-002",
    ),
    (
        "PAY.03",
        "Misconfigured tokenisation vault exposes card data",
        1,
        4,
        0,
        3,
        "mitigate",
        "T-005",
    ),
    (
        "PAY.04",
        "ICT provider concentration on a single cloud region",
        2,
        3,
        1,
        3,
        "mitigate",
        "T-004",
    ),
]

# Result distribution walked in order, so the compliance donut is stable.
# Two of every ten are left unassessed on purpose: an audit whose every
# requirement carries a verdict shows 100% progress, which contradicts its
# "In progress" status in the list view.
RESULT_CYCLE = [
    "compliant",
    "compliant",
    "partially_compliant",
    "compliant",
    "non_compliant",
    "not_assessed",
    "partially_compliant",
    "not_applicable",
    "compliant",
    "not_assessed",
]


@register
class CoreBuilder(DemoBuilder):
    """Perimeters, assets and applied controls."""

    name = "core"
    libraries = (ISO27001_LIBRARY,)
    covers: ClassVar[dict] = {
        Folder: "parent_folder",
        Perimeter: "folder",
        Asset: "folder",
        AppliedControl: "folder",
        # Proxy over AppliedControl: the policy-category controls above.
        Policy: "folder",
    }

    def build(self, ctx):
        self.build_org(ctx)
        ctx.refs["assets"] = self.build_assets(ctx)
        ctx.refs["controls"] = self.build_controls(ctx, ctx.refs["assets"])
        ctx.refs["perimeters"] = list(
            Perimeter.objects.filter(folder=ctx.domain).order_by("ref_id")
        )

    def stamps(self, ctx):
        return [
            (Asset, {"folder": ctx.domain}, ("name",)),
            (AppliedControl, {"folder": ctx.domain}, ("name",)),
            (Perimeter, {"folder": ctx.domain}, ("name",)),
        ]

    def build_org(self, ctx):
        for ref_id, name, lc_status in PERIMETERS:
            Perimeter.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={"ref_id": ref_id, "lc_status": lc_status},
            )

    def build_assets(self, ctx):
        assets = []
        for name, description, objectives in PRIMARY_ASSETS:
            asset, _ = Asset.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "description": description,
                    "type": Asset.Type.PRIMARY,
                    "security_objectives": {
                        "objectives": {
                            key: {"value": value, "is_enabled": True}
                            for key, value in objectives.items()
                        }
                    },
                },
            )
            assets.append(asset)
        primaries = {asset.name: asset for asset in assets}
        for name, description, parent in SUPPORTING_ASSETS:
            asset, created = Asset.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={"description": description, "type": Asset.Type.SUPPORT},
            )
            if created:
                asset.parent_assets.set([primaries[parent]])
            assets.append(asset)
        return assets

    @staticmethod
    def cost(ref_id):
        build_fixed, build_days, run_fixed, run_days = CONTROL_COSTS[ref_id]
        return {
            "currency": get_global_currency(),
            "amortization_period": 3,
            "build": {"fixed_cost": build_fixed, "people_days": build_days},
            "run": {"fixed_cost": run_fixed, "people_days": run_days},
        }

    def build_controls(self, ctx, assets):
        # Scoped to the libraries the demo loads: on a populated instance an
        # unscoped query would link the demo to the customer's own referentials.
        references = {
            r.ref_id: r
            for r in ReferenceControl.objects.filter(library__urn=ISO27001_LIBRARY)
        }
        assets = {a.name: a for a in assets}
        controls = []
        for (
            ref_id,
            name,
            category,
            csf_function,
            status,
            priority,
            effort,
            eta_offset,
        ) in CONTROLS:
            reference, protected = CONTROL_LINKS[ref_id]
            control, created = AppliedControl.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "category": category,
                    "csf_function": csf_function,
                    "status": status,
                    "priority": priority,
                    "effort": effort,
                    "eta": ctx.day(eta_offset),
                    "cost": self.cost(ref_id),
                    "reference_control": references.get(reference),
                },
            )
            if created:
                control.assets.set([assets[name] for name in protected])
            controls.append(control)
        return controls


@register
class ComplianceBuilder(DemoBuilder):
    """Audits across the frameworks the company answers to, with results."""

    name = "compliance"
    depends = ("core",)
    libraries = (
        ISO27001_LIBRARY,
        PCI_DSS_LIBRARY,
        IEC_62443_LIBRARY,
        CRA_LIBRARY,
        NIS2_LIBRARY,
        NIST_CSF_LIBRARY,
    )
    covers: ClassVar[dict] = {
        ComplianceAssessment: "folder",
        RequirementAssessment: "compliance_assessment__folder",
    }

    def stamps(self, ctx):
        # `requirement__order_id` alone is NOT unique as a sort key: every audit
        # on the same framework repeats the whole requirement tree, so each
        # order_id is shared by one row per audit and the sort would fall back
        # to the UUID again. The (audit, requirement) pair identifies a row.
        stamps = [
            (ComplianceAssessment, {"folder__in": ctx.folders()}, ("name",)),
            (
                RequirementAssessment,
                {"compliance_assessment__folder__in": ctx.folders()},
                ("compliance_assessment__ref_id", "requirement__order_id"),
            ),
        ]
        # Library-loaded referentials are stamped at import time, so they
        # drift whenever the database is rebuilt. They live in the root folder
        # and are shared with user data, so only screenshot runs touch them.
        if ctx.frozen:
            stamps.append((Framework, {"library__urn__in": self.libraries}, ("name",)))
        return stamps

    def build(self, ctx):
        perimeters = {p.ref_id: p for p in ctx.refs["perimeters"]}
        audits = []
        for (
            ref_id,
            name,
            library,
            perimeter,
            status,
            offset,
            share,
        ) in AUDITS:
            framework = Framework.objects.filter(library__urn=library).first()
            if framework is None:
                ctx.err(f"{library} not loaded, skipping {ref_id}")
                continue
            audit, created = ComplianceAssessment.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "framework": framework,
                    "perimeter": perimeters.get(perimeter),
                    "status": status,
                    "ref_id": ref_id,
                    "due_date": ctx.day(offset),
                },
            )
            if created:
                audit.create_requirement_assessments()
                self.fill(audit, share)
            audits.append(audit)
        if not audits:
            return
        ctx.refs["framework"] = audits[0].framework
        ctx.refs["audits"] = audits

        # Each control answers its Annex A requirement on the lead audit.
        lead = {
            ra.requirement.ref_id: ra
            for ra in RequirementAssessment.objects.filter(
                compliance_assessment=audits[0], requirement__assessable=True
            ).select_related("requirement")
        }
        for control in ctx.refs["controls"]:
            assessment = lead.get(CONTROL_LINKS[control.ref_id][0])
            if assessment is not None:
                assessment.applied_controls.add(control)
        ctx.out(f"{len(audits)} audits seeded")

    @staticmethod
    def fill(audit, share):
        """Walk RESULT_CYCLE over the first ``share`` of the requirements, so
        each audit's progress matches its status in the list view."""
        assessments = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=audit, requirement__assessable=True
            ).order_by("requirement__order_id")
        )
        filled = round(len(assessments) * share)
        for index, assessment in enumerate(assessments[:filled]):
            assessment.result = RESULT_CYCLE[index % len(RESULT_CYCLE)]
            assessment.status = (
                "done" if assessment.result != "not_assessed" else "to_do"
            )
            assessment.save(update_fields=["result", "status"])


@register
class RiskBuilder(DemoBuilder):
    """The enterprise risk register, plus the payments subsidiary's ICT risks."""

    name = "risk"
    depends = ("core",)
    libraries = (MATRIX_LIBRARY,)
    covers: ClassVar[dict] = {
        RiskAssessment: "folder",
        RiskScenario: "risk_assessment__folder",
        Threat: "folder",
    }

    def stamps(self, ctx):
        stamps = [
            (RiskAssessment, {"folder__in": ctx.folders()}, ("name",)),
            (
                RiskScenario,
                {"risk_assessment__folder__in": ctx.folders()},
                ("risk_assessment__ref_id", "ref_id"),
            ),
            (Threat, {"folder": ctx.domain}, ("name",)),
        ]
        # Shared root-folder library content: screenshot runs only.
        if ctx.frozen:
            stamps.append((RiskMatrix, {"library__urn__in": self.libraries}, ("name",)))
        return stamps

    def build(self, ctx):
        matrix = RiskMatrix.objects.filter(urn__icontains="5x5-iso27005").first()
        if matrix is None:
            ctx.err("risk matrix not loaded, skipping risk assessment")
            return
        perimeter = (
            Perimeter.objects.filter(folder=ctx.domain).order_by("ref_id").first()
        )
        assessment, created = RiskAssessment.objects.get_or_create(
            name="2026 enterprise risk review",
            folder=ctx.domain,
            defaults={
                "risk_matrix": matrix,
                "perimeter": perimeter,
                "status": "in_progress",
                "ref_id": "RA.2026.01",
                "due_date": ctx.day(60),
            },
        )
        ctx.refs["risk_assessment"] = assessment
        if not created:
            self.collect_refs(ctx, assessment)
            return
        threats = {}
        for ref_id, name in THREATS:
            threat, _ = Threat.objects.get_or_create(
                name=name, folder=ctx.domain, defaults={"ref_id": ref_id}
            )
            threats[ref_id] = threat
        self.add_scenarios(ctx, assessment, SCENARIOS, threats)

        pay_assessment, created = RiskAssessment.objects.get_or_create(
            name=f"{PAY_ENTITY} ICT risk assessment",
            folder=ctx.domain,
            defaults={
                "risk_matrix": matrix,
                "perimeter": next(
                    p for p in ctx.refs["perimeters"] if p.ref_id == "PER.002"
                ),
                "status": "in_review",
                "ref_id": "RA.2026.02",
                "due_date": ctx.day(25),
            },
        )
        if created:
            self.add_scenarios(ctx, pay_assessment, PAY_SCENARIOS, threats)
        self.collect_refs(ctx, assessment)
        ctx.out(
            f"risk assessments seeded with {len(SCENARIOS) + len(PAY_SCENARIOS)} "
            "scenarios"
        )

    def add_scenarios(self, ctx, assessment, rows, threats):
        assets = {a.name: a for a in ctx.refs["assets"]}
        controls = {c.ref_id: c for c in ctx.refs["controls"]}
        for (
            ref_id,
            name,
            c_proba,
            c_impact,
            r_proba,
            r_impact,
            treatment,
            threat,
        ) in rows:
            scenario = RiskScenario.objects.create(
                name=name,
                ref_id=ref_id,
                risk_assessment=assessment,
                current_proba=c_proba,
                current_impact=c_impact,
                residual_proba=r_proba,
                residual_impact=r_impact,
                treatment=treatment,
            )
            scenario.threats.add(threats[threat])
            impacted, existing, additional = SCENARIO_LINKS[ref_id]
            scenario.assets.set([assets[name] for name in impacted])
            scenario.existing_applied_controls.set([controls[r] for r in existing])
            scenario.applied_controls.set([controls[r] for r in additional])

    def collect_refs(self, ctx, assessment):
        ctx.refs["threats"] = list(
            Threat.objects.filter(folder=ctx.domain).order_by("ref_id")
        )
        ctx.refs["risk_scenarios"] = list(
            RiskScenario.objects.filter(risk_assessment=assessment).order_by("ref_id")
        )
