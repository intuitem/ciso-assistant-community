"""CRQ demo builder: quantitative risk studies with simulated loss exposure.

Hypotheses carry annual probabilities and 90% loss intervals; every one is
simulated once the study is built, then the portfolio is generated. The Monte
Carlo engine runs on fixed seeds, so the curves are identical on every seed.
"""

from typing import ClassVar

from core.demo import PAY_ENTITY, DemoBuilder, register
from core.models import Terminology
from crq.models import (
    QuantitativeRiskHypothesis,
    QuantitativeRiskScenario,
    QuantitativeRiskStudy,
)
from iam.models import Folder

LOGNORMAL = "LOGNORMAL-CI90"

CONNECTED = "Connected Products"
PLANT = "Manufacturing"

# ref_id, name, sub-domain (None = root demo domain), status, eta, due date,
# loss threshold, risk tolerance (probability, acceptable loss) x2, description.
STUDIES = [
    (
        "CRQ.2026.01",
        "FY2026 cyber loss exposure",
        None,
        "in_progress",
        30,
        60,
        1_000_000,
        ((0.4, 250_000), (0.02, 5_000_000)),
        (
            "Board-requested quantification of the top cyber scenarios ahead of the "
            "FY2026 security budget and the cyber insurance renewal. Losses in euros, "
            "annualised over the whole group including the payments subsidiary."
        ),
    ),
    (
        "CRQ.2026.02",
        "Brno plant OT disruption study",
        PLANT,
        "planned",
        90,
        120,
        500_000,
        ((0.3, 150_000), (0.02, 3_000_000)),
        (
            "Loss exposure of the Brno assembly lines, to size the IT/OT "
            "segmentation programme and the IEC 62443 roadmap. One production day "
            "lost costs about €450,000 in margin, overtime and late-delivery "
            "penalties to retail partners."
        ),
    ),
    (
        "CRQ.2026.03",
        "Connected products CRA exposure",
        CONNECTED,
        "in_progress",
        45,
        75,
        2_000_000,
        ((0.3, 500_000), (0.01, 15_000_000)),
        (
            "Quantifies product security scenarios for the Kelvin, Lookout and "
            "Keystone fleets ahead of the Cyber Resilience Act obligations: recall "
            "and support costs, CRA fines (up to €15M or 2.5% of turnover) and "
            "churn on the companion app."
        ),
    ),
]

# Hypothesis: (probability, lb, ub, existing control ref_ids, added control ref_ids).
# Scenario: study ref_id, ref_id, name, description, status, priority, asset
# names, threat ref_ids, qualifications, inherent, current, residual list of
# (name, selected, hypothesis, observation).
SCENARIOS = [
    (
        "CRQ.2026.01",
        "QR.01",
        "Ransomware stops the Brno assembly plant",
        (
            "Encryption of plant IT spreads to the line control network. Loss model: "
            "2 to 15 production days at about €450,000 per day, plus recovery "
            "services and late-delivery penalties."
        ),
        "mitigate",
        1,
        ["Production line control", "Plant SCADA server", "Order fulfilment"],
        ["T-001"],
        ["operational", "financial"],
        (0.3, 900_000, 9_000_000, [], []),
        (0.15, 600_000, 6_500_000, ["AC.003", "AC.008"], []),
        [
            (
                "IT/OT segmentation and PLC change control",
                True,
                (0.06, 300_000, 3_000_000, ["AC.003", "AC.008"], ["AC.007", "AC.017"]),
                (
                    "Segmentation keeps an IT infection off the assembly cells; lines "
                    "restart from tested backups in two days."
                ),
            ),
            (
                "PLC change management only",
                False,
                (0.11, 500_000, 5_000_000, ["AC.003", "AC.008"], ["AC.017"]),
                "Cheaper option, rejected: lateral movement from IT stays possible.",
            ),
        ],
    ),
    (
        "CRQ.2026.01",
        "QR.02",
        "Malicious OTA update pushed to the device fleet",
        (
            "A stolen signing key or poisoned build ships firmware that bricks or "
            "backdoors Kelvin and Keystone devices. Loss model: device replacement "
            "and support surge, CRA fine, retail partner chargebacks."
        ),
        "mitigate",
        1,
        [
            "Device firmware and signing keys",
            "Firmware signing HSM",
            "Firmware CI build farm",
        ],
        ["T-007", "T-004"],
        ["integrity", "reputation", "legal", "financial"],
        (0.08, 2_000_000, 40_000_000, [], []),
        (0.05, 1_500_000, 30_000_000, ["AC.013"], []),
        [
            (
                "Staged OTA rollout and SBOM per release",
                True,
                (0.02, 500_000, 12_000_000, ["AC.013"], ["AC.014", "AC.015"]),
                "A canary ring of 1% caps the blast radius before the fleet-wide push.",
            ),
            (
                "Secure firmware development training only",
                False,
                (0.04, 1_200_000, 25_000_000, ["AC.013"], ["AC.006"]),
                "Reduces defects, not key theft: rejected as the primary response.",
            ),
        ],
    ),
    (
        "CRQ.2026.01",
        "QR.03",
        "Lookout camera footage breach",
        (
            "Misconfigured storage or a support-tool compromise exposes customer "
            "video clips. Loss model: GDPR fine, notification and legal costs, "
            "subscription churn on the camera plan."
        ),
        "mitigate",
        2,
        ["Customer and device accounts", "Device cloud Kubernetes cluster"],
        ["T-005", "T-003"],
        ["confidentiality", "privacy", "legal", "reputation"],
        (0.15, 1_000_000, 25_000_000, [], []),
        (0.1, 800_000, 18_000_000, ["AC.001", "AC.009"], []),
        [
            (
                "Retention schedule and privileged session recording",
                True,
                (0.05, 400_000, 9_000_000, ["AC.001", "AC.009"], ["AC.011", "AC.002"]),
                (
                    "Clips deleted after 30 days halve the footage exposed; Mireo Support "
                    "sessions are recorded."
                ),
            ),
        ],
    ),
    (
        "CRQ.2026.01",
        "QR.04",
        "Checkout outage during a product launch",
        (
            "A volumetric attack or a cloud incident takes the store checkout down "
            "on a launch day. Loss model: lost orders at about €120,000 per hour of "
            "peak traffic, partly recovered later."
        ),
        "transfer",
        3,
        ["Store checkout and payments", "Online store web front"],
        ["T-006"],
        ["availability", "financial"],
        (0.4, 100_000, 2_500_000, [], []),
        (0.3, 80_000, 1_800_000, ["AC.003"], []),
        [
            (
                "Kestrava Cloud SLA credits and cyber insurance",
                True,
                (0.3, 30_000, 500_000, ["AC.003"], []),
                (
                    "Residual loss transferred under the 2026 hosting contract and the "
                    "business interruption cover."
                ),
            ),
        ],
    ),
    (
        "CRQ.2026.01",
        "QR.05",
        "Camera hijacking through default credentials",
        (
            "Attackers take over cameras still using shared factory credentials and "
            "publish live feeds. Loss model: incident handling, regulator inquiry, "
            "returns and brand damage."
        ),
        "mitigate",
        2,
        ["Customer and device accounts", "Companion mobile app"],
        ["T-002"],
        ["privacy", "reputation"],
        (0.25, 200_000, 6_000_000, [], []),
        (0.2, 150_000, 5_000_000, ["AC.010"], []),
        [
            (
                "Unique per-device credentials at manufacturing",
                True,
                (0.04, 80_000, 1_500_000, ["AC.010"], ["AC.018"]),
                (
                    "Shenwa Contract Manufacturing injects a unique credential per "
                    "camera on the line from batch 2026-14."
                ),
            ),
        ],
    ),
    (
        "CRQ.2026.01",
        "QR.06",
        f"Skimming script on the {PAY_ENTITY} checkout",
        (
            "An injected script on the payment page harvests card data. Loss model: "
            "PCI DSS forensic investigation, card brand penalties, reissuance costs."
        ),
        "accept",
        4,
        ["Store checkout and payments"],
        ["T-009"],
        ["financial", "legal"],
        (0.12, 150_000, 3_000_000, [], []),
        (0.06, 100_000, 2_000_000, ["AC.016"], []),
        [],
    ),
    (
        "CRQ.2026.02",
        "QR.01",
        "Ransomware spreads to the assembly cell network",
        (
            "Malware crosses from plant IT to the cell network and stops every line. "
            "Assumes 3 to 12 days to rebuild and revalidate the cells."
        ),
        "open",
        1,
        ["Production line control", "Assembly cell PLCs"],
        ["T-001"],
        ["operational", "safety"],
        (0.25, 1_300_000, 6_000_000, [], []),
        (0.15, 1_000_000, 5_000_000, ["AC.012"], []),
        [],
    ),
    (
        "CRQ.2026.02",
        "QR.02",
        "Integrator remote access abused to tamper with PLCs",
        (
            "Linterra Automation's remote maintenance account is used to alter PLC "
            "logic. Loss model: scrapped batches, line stoppage, safety review."
        ),
        "draft",
        2,
        ["Assembly cell PLCs", "Plant SCADA server", "Corporate VPN gateway"],
        ["T-008"],
        ["safety", "integrity"],
        (0.08, 150_000, 4_000_000, [], []),
        (0.05, 120_000, 3_000_000, ["AC.004", "AC.017"], []),
        [],
    ),
    (
        "CRQ.2026.02",
        "QR.03",
        "USB-borne malware on packing-line HMIs",
        (
            "A contractor laptop or USB key infects HMI workstations; one packing "
            "line stops for a shift while the HMIs are reimaged."
        ),
        "draft",
        3,
        ["Plant SCADA server"],
        ["T-001"],
        ["operational"],
        (0.5, 20_000, 400_000, [], []),
        (0.35, 15_000, 300_000, ["AC.012"], []),
        [],
    ),
    (
        "CRQ.2026.03",
        "QR.01",
        "Critical firmware flaw exploited across the Kelvin fleet",
        (
            "A remotely exploitable flaw reported to the disclosure programme is "
            "weaponised before the fix ships. Loss model: emergency OTA campaign, "
            "support surge, CRA penalties for late handling."
        ),
        "mitigate",
        1,
        ["Device firmware and signing keys", "MQTT device gateway"],
        ["T-004"],
        ["integrity", "legal", "reputation"],
        (0.2, 500_000, 12_000_000, [], []),
        (0.12, 400_000, 9_000_000, ["AC.010"], []),
        [
            (
                "Staged OTA rollout and SBOM-driven triage",
                True,
                (0.05, 200_000, 4_000_000, ["AC.010"], ["AC.014", "AC.015"]),
                (
                    "SBOM lookups cut triage from days to hours; fixes reach 95% of the "
                    "fleet within 10 days."
                ),
            ),
        ],
    ),
    (
        "CRQ.2026.03",
        "QR.02",
        "MQTT gateway outage strands devices offline",
        (
            "The device gateway on Kestrava Cloud fails for a day: thermostats fall "
            "back to local schedules, cameras stop uploading clips. Loss model: "
            "support calls, service credits, app-store ratings."
        ),
        "accept",
        3,
        ["MQTT device gateway", "Device cloud Kubernetes cluster"],
        ["T-006"],
        ["availability", "reputation"],
        (0.3, 50_000, 1_200_000, [], []),
        (0.2, 40_000, 900_000, ["AC.003"], []),
        [],
    ),
]


def parameters(probability, lower, upper):
    return {
        "probability": probability,
        "impact": {"distribution": LOGNORMAL, "lb": lower, "ub": upper},
    }


def tolerance(points):
    (p1, loss1), (p2, loss2) = points
    return {
        "points": {
            "point1": {"probability": p1, "acceptable_loss": loss1},
            "point2": {"probability": p2, "acceptable_loss": loss2},
        }
    }


@register
class CrqBuilder(DemoBuilder):
    """Three quantitative studies, simulated, linked to the core assets and controls."""

    name = "crq"
    depends = ("core", "risk")
    covers: ClassVar[dict] = {
        QuantitativeRiskStudy: "folder",
        QuantitativeRiskScenario: "folder",
        QuantitativeRiskHypothesis: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (QuantitativeRiskStudy, {"folder__in": folders}, ("ref_id",)),
            (
                QuantitativeRiskScenario,
                {"folder__in": folders},
                ("quantitative_risk_study__ref_id", "ref_id"),
            ),
            (
                QuantitativeRiskHypothesis,
                {"folder__in": folders},
                (
                    "quantitative_risk_scenario__quantitative_risk_study__ref_id",
                    "quantitative_risk_scenario__ref_id",
                    "ref_id",
                ),
            ),
        ]

    def build(self, ctx):
        self.assets = {asset.name: asset for asset in ctx.refs["assets"]}
        self.controls = {control.ref_id: control for control in ctx.refs["controls"]}
        self.threats = {threat.ref_id: threat for threat in ctx.refs.get("threats", [])}
        self.qualifications = {
            term.name: term
            for term in Terminology.objects.filter(
                field_path=Terminology.FieldPath.QUALIFICATIONS, builtin=True
            )
        }
        for (
            ref_id,
            name,
            subdomain,
            status,
            eta,
            due,
            threshold,
            points,
            description,
        ) in STUDIES:
            folder = (
                Folder.objects.get(name=subdomain, parent_folder=ctx.domain)
                if subdomain
                else ctx.domain
            )
            study, created = QuantitativeRiskStudy.objects.get_or_create(
                name=name,
                folder=folder,
                defaults={
                    "ref_id": ref_id,
                    "description": description,
                    "status": status,
                    "eta": ctx.day(eta),
                    "due_date": ctx.day(due),
                    "loss_threshold": threshold,
                },
            )
            if not created:
                continue
            # Set as an update, like the study page does: save() only fits the
            # tolerance curve when the points change. Fitting it later, inside
            # the first simulation, would flag that hypothesis as stale.
            study.risk_tolerance = tolerance(points)
            study.save()
            for row in SCENARIOS:
                if row[0] == ref_id:
                    self.build_scenario(study, row[1:])
            self.simulate(study)
            ctx.out(f"quantitative study {ref_id} simulated")

    def build_scenario(self, study, row):
        (
            ref_id,
            name,
            description,
            status,
            priority,
            asset_names,
            threat_refs,
            qualifications,
            inherent,
            current,
            residuals,
        ) = row
        scenario = QuantitativeRiskScenario.objects.create(
            quantitative_risk_study=study,
            folder=study.folder,
            ref_id=ref_id,
            name=name,
            description=description,
            status=status,
            priority=priority,
        )
        scenario.assets.set([self.assets[n] for n in asset_names if n in self.assets])
        scenario.threats.set(
            [self.threats[r] for r in threat_refs if r in self.threats]
        )
        scenario.qualifications.set(
            [self.qualifications[q] for q in qualifications if q in self.qualifications]
        )
        # The API creates the current hypothesis with every new scenario.
        self.hypothesis(scenario, "H.01", "baseline", "current", True, current)
        self.hypothesis(
            scenario, "H.02", "Inherent exposure", "inherent", False, inherent
        )
        for index, (label, selected, values, observation) in enumerate(residuals):
            self.hypothesis(
                scenario,
                f"H.{index + 3:02d}",
                label,
                "residual",
                selected,
                values,
                observation,
            )

    def hypothesis(self, scenario, ref_id, name, stage, selected, values, note=""):
        probability, lower, upper, existing, added = values
        hypothesis = QuantitativeRiskHypothesis.objects.create(
            quantitative_risk_scenario=scenario,
            folder=scenario.folder,
            ref_id=ref_id,
            name=name,
            risk_stage=stage,
            is_selected=selected,
            parameters=parameters(probability, lower, upper),
            observation=note or None,
        )
        hypothesis.existing_applied_controls.set(
            [self.controls[r] for r in existing if r in self.controls]
        )
        hypothesis.added_applied_controls.set(
            [self.controls[r] for r in added if r in self.controls]
        )
        return hypothesis

    def simulate(self, study):
        # Same sequence as the study's "retrigger all simulations" action.
        for hypothesis in QuantitativeRiskHypothesis.objects.filter(
            quantitative_risk_scenario__quantitative_risk_study=study
        ).order_by("quantitative_risk_scenario__ref_id", "ref_id"):
            hypothesis.run_simulation()
        study.refresh_from_db()
        study.get_or_generate_portfolio_simulation(force_refresh=True)
