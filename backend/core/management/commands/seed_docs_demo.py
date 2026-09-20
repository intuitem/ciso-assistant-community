"""Deterministic demo dataset used to shoot the product documentation screenshots.

Unlike the ``populate_*`` commands this one seeds the RNG and uses a fixed
vocabulary, so two runs on the same checkout produce identical content and the
screenshots only change when the UI does.
"""

import random
from datetime import date, datetime, time, timedelta, timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Framework,
    Perimeter,
    ReferenceControl,
    RequirementAssessment,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    StoredLibrary,
    Threat,
)
from global_settings.models import GlobalSettings
from iam.models import Folder

SEED = 1337
TODAY = date(2026, 3, 2)  # frozen so ETAs and due dates never drift

LIBRARIES = [
    "urn:intuitem:risk:library:iso27001-2022",
    "urn:intuitem:risk:library:risk-matrix-5x5-iso27005",
    "urn:intuitem:risk:library:doc-pol",
]

DOMAIN = "Northwind Trading"
SUBDOMAINS = ["Corporate IT", "Manufacturing", "Retail Operations"]

PERIMETERS = [
    ("PER.001", "Core banking platform", "in_prod"),
    ("PER.002", "Customer web portal", "in_prod"),
    ("PER.003", "Warehouse management", "in_dev"),
]

PRIMARY_ASSETS = [
    ("Payment processing", "Card authorisation and settlement chain."),
    ("Customer records", "Master customer database and CRM replicas."),
    ("Order fulfilment", "Order capture through to dispatch."),
]

SUPPORTING_ASSETS = [
    (
        "Production Kubernetes cluster",
        "Three-zone managed cluster hosting the platform.",
    ),
    ("PostgreSQL primary", "Transactional store, streaming replica in the DR region."),
    ("Corporate VPN gateway", "Remote access concentrator for staff and contractors."),
    ("S3 evidence bucket", "Immutable audit evidence, object-lock enabled."),
    ("Jenkins build farm", "CI runners with production deployment credentials."),
    ("Okta tenant", "Workforce identity provider, SAML and SCIM."),
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
    ("AC.006", "Secure development training", "policy", "protect", "to_do", 3, "S", 90),
    (
        "AC.007",
        "Network segmentation review",
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
        "Vulnerability scanning cadence",
        "technical",
        "identify",
        "in_progress",
        1,
        "S",
        15,
    ),
    ("AC.011", "Data retention schedule", "policy", "govern", "to_do", 4, "M", 150),
    (
        "AC.012",
        "Physical access badge audit",
        "physical",
        "recover",
        "active",
        3,
        "S",
        -45,
    ),
]

AUDITS = [
    ("AUD.2026.01", "ISO 27001:2022 — annual certification audit", "in_progress", 45),
    ("AUD.2026.02", "ISO 27001:2022 — customer portal scope", "planned", 120),
    ("AUD.2025.04", "ISO 27001:2022 — warehouse readiness review", "done", -30),
]

THREATS = [
    ("T-001", "Ransomware deployment"),
    ("T-002", "Credential stuffing"),
    ("T-003", "Insider data exfiltration"),
    ("T-004", "Supply chain compromise"),
    ("T-005", "Cloud misconfiguration"),
    ("T-006", "Denial of service"),
]

# Probability and impact are 0-based indices into the matrix grid (0..4 on a 5x5).
SCENARIOS = [
    ("RS.01", "Ransomware encrypts the production cluster", 3, 4, 1, 3, "mitigate"),
    (
        "RS.02",
        "Customer credentials replayed against the portal",
        3,
        2,
        1,
        2,
        "mitigate",
    ),
    (
        "RS.03",
        "Departing employee exports the customer database",
        1,
        4,
        1,
        2,
        "mitigate",
    ),
    (
        "RS.04",
        "Compromised build dependency reaches production",
        1,
        4,
        0,
        3,
        "mitigate",
    ),
    ("RS.05", "Public object storage exposes audit evidence", 2, 2, 0, 1, "mitigate"),
    ("RS.06", "Volumetric attack saturates the portal edge", 2, 1, 2, 1, "accept"),
]

# Result distribution walked in order, so the compliance donut is stable.
RESULT_CYCLE = [
    "compliant",
    "compliant",
    "partially_compliant",
    "compliant",
    "non_compliant",
    "compliant",
    "partially_compliant",
    "not_applicable",
    "compliant",
    "partially_compliant",
]


class Command(BaseCommand):
    help = "Seed the deterministic demo dataset used for documentation screenshots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete the demo domain and everything under it before seeding.",
        )

    def handle(self, *args, **options):
        random.seed(SEED)

        if options["flush"]:
            deleted, _ = Folder.objects.filter(name=DOMAIN).delete()
            self.stdout.write(f"flushed {deleted} objects under {DOMAIN}")

        self.load_libraries()
        with transaction.atomic():
            self.tune_global_settings()
            domain = self.build_org()
            assets = self.build_assets(domain)
            controls = self.build_controls(domain, assets)
            self.build_audit(domain, controls)
            self.build_risk_assessment(domain, assets, controls)
            self.freeze_timestamps()
        self.stdout.write(self.style.SUCCESS("demo dataset ready"))

    def freeze_timestamps(self):
        """Pin created_at / updated_at to fixed, *distinct* values.

        Both are auto_now_add / auto_now, so without this every run stamps the
        current time and every "Created at" column drifts. A bulk ``update()``
        bypasses ``save()`` and therefore the auto fields.

        The stamps must also be unique per row. ``BaseModelViewSet`` orders by
        ``created_at`` and ``SmartOrderingFilter`` appends ``pk`` as the
        pagination tiebreaker — and ``pk`` is a random UUID. Giving every row
        the same timestamp therefore hands row order to the UUIDs, and lists
        come back shuffled after each database rebuild.
        """
        base = datetime.combine(TODAY, time(9, 0), tzinfo=timezone.utc)
        # Library-loaded referentials are stamped at import time, so they drift
        # too whenever the database is rebuilt — and their detail pages show
        # Created at / Updated at.
        models = (
            Asset,
            AppliedControl,
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RiskAssessment,
            RiskMatrix,
            RiskScenario,
            Threat,
        )
        for model in models:
            fields = {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}
            stamped = {"created_at", "updated_at"} & fields
            if not stamped:
                continue
            order = "name" if "name" in fields else "id"
            for offset, pk in enumerate(
                model.objects.order_by(order).values_list("pk", flat=True)
            ):
                stamp = base + timedelta(minutes=offset)
                model.objects.filter(pk=pk).update(**{n: stamp for n in stamped})
        self.stdout.write(
            f"timestamps pinned from {base:%Y-%m-%d %H:%M} UTC, staggered"
        )

    # ------------------------------------------------------------------ setup

    def tune_global_settings(self):
        """Drop chrome that is meaningful in a live instance but noise in a doc."""
        setting, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.GENERAL,
            defaults={"value": dict(GlobalSettings.GENERAL_DEFAULT_VALUE)},
        )
        value = dict(setting.value or {})
        value["show_get_started"] = False
        setting.value = value
        setting.save(update_fields=["value"])

    def load_libraries(self):
        for urn in LIBRARIES:
            stored = StoredLibrary.objects.filter(urn=urn).order_by("-version").first()
            if stored is None:
                self.stderr.write(f"missing stored library {urn}")
                continue
            error = stored.load()
            self.stdout.write(f"library {urn.split(':')[-1]}: {error or 'loaded'}")

    def build_org(self):
        root = Folder.get_root_folder()
        domain, _ = Folder.objects.get_or_create(
            name=DOMAIN,
            defaults={
                "description": "Demo organisation used across the documentation.",
                "parent_folder": root,
                "content_type": Folder.ContentType.DOMAIN,
            },
        )
        for name in SUBDOMAINS:
            Folder.objects.get_or_create(
                name=name,
                parent_folder=domain,
                defaults={"content_type": Folder.ContentType.DOMAIN},
            )
        for ref_id, name, lc_status in PERIMETERS:
            Perimeter.objects.get_or_create(
                name=name,
                folder=domain,
                defaults={"ref_id": ref_id, "lc_status": lc_status},
            )
        return domain

    def build_assets(self, domain):
        assets = []
        for name, description in PRIMARY_ASSETS:
            asset, _ = Asset.objects.get_or_create(
                name=name,
                folder=domain,
                defaults={"description": description, "type": Asset.Type.PRIMARY},
            )
            assets.append(asset)
        primaries = list(assets)
        for index, (name, description) in enumerate(SUPPORTING_ASSETS):
            asset, created = Asset.objects.get_or_create(
                name=name,
                folder=domain,
                defaults={"description": description, "type": Asset.Type.SUPPORT},
            )
            if created:
                asset.parent_assets.set([primaries[index % len(primaries)]])
            assets.append(asset)
        return assets

    def build_controls(self, domain, assets):
        references = list(ReferenceControl.objects.order_by("urn")[:12])
        controls = []
        for index, (
            ref_id,
            name,
            category,
            csf_function,
            status,
            priority,
            effort,
            eta_offset,
        ) in enumerate(CONTROLS):
            control, created = AppliedControl.objects.get_or_create(
                name=name,
                folder=domain,
                defaults={
                    "ref_id": ref_id,
                    "category": category,
                    "csf_function": csf_function,
                    "status": status,
                    "priority": priority,
                    "effort": effort,
                    "eta": TODAY + timedelta(days=eta_offset),
                    "reference_control": references[index]
                    if index < len(references)
                    else None,
                },
            )
            if created:
                control.assets.set(random.sample(assets, 2))
            controls.append(control)
        return controls

    def build_audit(self, domain, controls):
        framework = Framework.objects.filter(urn__icontains="iso27001-2022").first()
        if framework is None:
            self.stderr.write("ISO 27001 framework not loaded, skipping audit")
            return
        perimeters = list(Perimeter.objects.filter(folder=domain).order_by("ref_id"))
        audits = []
        for index, (ref_id, name, status, offset) in enumerate(AUDITS):
            audit, created = ComplianceAssessment.objects.get_or_create(
                name=name,
                folder=domain,
                defaults={
                    "framework": framework,
                    "perimeter": perimeters[index % len(perimeters)],
                    "status": status,
                    "ref_id": ref_id,
                    "due_date": TODAY + timedelta(days=offset),
                },
            )
            if created:
                audit.create_requirement_assessments()
            audits.append(audit)

        # Only the lead audit gets a filled-in result spread; the others stay
        # untouched so the list view shows a range of progress values.
        audit = audits[0]
        assessments = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=audit, requirement__assessable=True
            ).order_by("requirement__order_id")
        )
        for index, assessment in enumerate(assessments):
            assessment.result = RESULT_CYCLE[index % len(RESULT_CYCLE)]
            assessment.status = (
                "done" if assessment.result != "not_assessed" else "to_do"
            )
            assessment.save(update_fields=["result", "status"])
        # Attach a few controls so the requirement detail pages are not empty.
        for assessment, control in zip(assessments[:12], controls):
            assessment.applied_controls.add(control)
        self.stdout.write(f"audit seeded with {len(assessments)} requirements")

    def build_risk_assessment(self, domain, assets, controls):
        matrix = RiskMatrix.objects.filter(urn__icontains="5x5-iso27005").first()
        if matrix is None:
            self.stderr.write("risk matrix not loaded, skipping risk assessment")
            return
        perimeter = Perimeter.objects.filter(folder=domain).order_by("ref_id").first()
        assessment, created = RiskAssessment.objects.get_or_create(
            name="2026 enterprise risk review",
            folder=domain,
            defaults={
                "risk_matrix": matrix,
                "perimeter": perimeter,
                "status": "in_progress",
                "ref_id": "RA.2026.01",
                "due_date": TODAY + timedelta(days=60),
            },
        )
        if not created:
            return
        threats = []
        for ref_id, name in THREATS:
            threat, _ = Threat.objects.get_or_create(
                name=name, folder=domain, defaults={"ref_id": ref_id}
            )
            threats.append(threat)
        for index, (
            ref_id,
            name,
            c_proba,
            c_impact,
            r_proba,
            r_impact,
            treatment,
        ) in enumerate(SCENARIOS):
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
            scenario.threats.add(threats[index % len(threats)])
            scenario.assets.set(random.sample(assets, 2))
            scenario.applied_controls.set(random.sample(controls, 2))
        self.stdout.write(f"risk assessment seeded with {len(SCENARIOS)} scenarios")
