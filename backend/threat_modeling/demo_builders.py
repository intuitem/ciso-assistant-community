"""Threat modeling demo builder: ATT&CK attack graphs for the top risk scenarios.

Nodes keep position (0, 0), which the graph editor lays out automatically by
tactic lane, exactly as after picking techniques in the matrix.
"""

from typing import ClassVar

from core.demo import DemoBuilder, register
from sec_intel.models import Technique, TTPCatalog
from threat_modeling.models import ThreatModel, ThreatModelEdge, ThreatModelNode

ATTACK_LIBRARY = "urn:intuitem:risk:library:mitre-attack"
ATTACK_CATALOG = "urn:intuitem:risk:ttp_catalog:mitre-attack"

# Asset names come from the core builder.
VPN = "Corporate VPN gateway"
SCADA = "Plant SCADA server"
PLCS = "Assembly cell PLCs"
LINE = "Production line control"
MQTT = "MQTT device gateway"
ACCOUNTS = "Customer and device accounts"
APP = "Companion mobile app"
STORE = "Online store web front"
CHECKOUT = "Store checkout and payments"

# ref_id, name, linked risk scenario ref_ids,
# description, nodes, edges.
# Node: (technique ref_id, tactic ref_id, highlighted, asset names,
# control ref_ids, note). Edges index into the node list.
MODELS = [
    (
        "TM.01",
        "Ransomware kill chain on the Brno assembly plant",
        ["RS.01"],
        (
            "Most likely path to RS.01, from the 2025 tabletop and the CERT "
            "advisories on ransomware crews targeting electronics manufacturers."
        ),
        [
            (
                "T1566.001",
                "TA0001",
                False,
                [],
                ["AC.006"],
                "Purchase-order lure sent to plant production planners.",
            ),
            ("T1078", "TA0001", False, ["Workforce identity provider"], ["AC.001"], ""),
            ("T1059.001", "TA0002", False, [], [], ""),
            ("T1003", "TA0006", False, [], ["AC.002"], ""),
            (
                "T1021.001",
                "TA0008",
                False,
                [VPN],
                ["AC.007"],
                "Engineering workstations still reachable from the office VLAN.",
            ),
            ("T1490", "TA0040", False, ["S3 evidence bucket"], ["AC.003"], ""),
            (
                "T1486",
                "TA0040",
                True,
                [SCADA, "PostgreSQL primary"],
                ["AC.003", "AC.008"],
                "Encrypting the SCADA historian and the MES database stops the line.",
            ),
        ],
        [(0, 2), (1, 4), (2, 3), (3, 4), (4, 5), (4, 6), (5, 6)],
    ),
    (
        "TM.02",
        "Plant remote maintenance path",
        ["RS.08"],
        (
            "Linterra Automation's remote maintenance access, from the vendor VPN "
            "to the assembly cell PLCs."
        ),
        [
            (
                "T1133",
                "TA0001",
                True,
                [VPN],
                ["AC.007"],
                "Shared integrator VPN account without per-technician MFA.",
            ),
            ("T1078", "TA0001", False, [], ["AC.001"], ""),
            (
                "T1219",
                "TA0011",
                False,
                [SCADA],
                ["AC.002"],
                "Remote access tool left installed after a 2025 intervention.",
            ),
            ("T1021.004", "TA0008", False, [SCADA], ["AC.007"], ""),
            (
                "T1565.001",
                "TA0040",
                True,
                [PLCS, LINE],
                ["AC.017"],
                "Altered PLC recipes produce defective hubs that pass end-of-line tests.",
            ),
            ("T1489", "TA0040", False, [LINE], ["AC.008"], ""),
        ],
        [(0, 2), (1, 2), (2, 3), (3, 4), (3, 5)],
    ),
    (
        "TM.03",
        "Device cloud: MQTT gateway and OTA service",
        ["RS.04", "RS.07", "RS.05"],
        (
            "Paths to the installed base through the firmware supply chain, the "
            "signing keys and the cloud accounts running the OTA service."
        ),
        [
            (
                "T1195.002",
                "TA0001",
                False,
                ["Firmware CI build farm"],
                ["AC.015"],
                "Poisoned open-source dependency in the hub firmware build.",
            ),
            (
                "T1552.004",
                "TA0006",
                True,
                ["Firmware signing HSM", "Device firmware and signing keys"],
                ["AC.013"],
                "Signing key extracted or misused through the HSM client.",
            ),
            (
                "T1078.004",
                "TA0001",
                False,
                ["Device cloud Kubernetes cluster"],
                ["AC.001"],
                "",
            ),
            (
                "T1072",
                "TA0002",
                True,
                [MQTT],
                ["AC.014"],
                "Malicious image distributed by the OTA service.",
            ),
            (
                "T1530",
                "TA0009",
                False,
                [ACCOUNTS],
                ["AC.011"],
                "Telemetry exports left in a publicly readable bucket.",
            ),
            ("T1495", "TA0040", False, [MQTT], ["AC.014"], ""),
            (
                "T1498",
                "TA0040",
                False,
                [MQTT],
                [],
                "Reconnect storm after a forced rollout saturates the broker.",
            ),
        ],
        [(0, 1), (1, 3), (2, 3), (2, 4), (3, 5), (3, 6)],
    ),
    (
        "TM.04",
        "Companion app and device pairing",
        ["RS.02"],
        (
            "Account takeover and pairing abuse leading to control of devices and "
            "access to Lookout camera clips."
        ),
        [
            ("T1110.004", "TA0006", True, [ACCOUNTS], ["AC.010"], ""),
            (
                "T1621",
                "TA0006",
                False,
                [APP],
                [],
                "Push-approval fatigue on the companion app login prompt.",
            ),
            ("T1078", "TA0001", False, [ACCOUNTS], [], ""),
            (
                "T1528",
                "TA0006",
                False,
                [APP],
                [],
                "Pairing token recovered from the app's verbose debug logs.",
            ),
            (
                "T1098",
                "TA0003",
                False,
                [ACCOUNTS],
                ["AC.018"],
                "Attacker added as a second owner of the household.",
            ),
            (
                "T1530",
                "TA0009",
                True,
                [ACCOUNTS],
                [],
                "Camera clips downloaded from the cloud archive.",
            ),
        ],
        [(0, 2), (1, 2), (2, 4), (3, 4), (4, 5)],
    ),
    (
        "TM.05",
        "Online store checkout",
        ["RS.09", "RS.06"],
        (
            "Payment page skimming through a third-party script, and launch-day "
            "floods against the store."
        ),
        [
            (
                "T1195.002",
                "TA0001",
                False,
                [STORE],
                ["AC.016"],
                "Compromised third-party tag script loaded by the checkout page.",
            ),
            (
                "T1059.007",
                "TA0002",
                True,
                [STORE],
                ["AC.016"],
                "Skimmer injected in the payment page.",
            ),
            ("T1185", "TA0009", False, [CHECKOUT], ["AC.016"], ""),
            ("T1048", "TA0010", False, [], ["AC.009"], ""),
            ("T1657", "TA0040", True, [CHECKOUT], [], ""),
            (
                "T1498",
                "TA0040",
                False,
                [STORE],
                [],
                "Flood timed with the Keystone hub v3 launch.",
            ),
        ],
        [(0, 1), (1, 2), (2, 3), (3, 4)],
    ),
    (
        "TM.06",
        "Insider exfiltration of product designs",
        ["RS.03"],
        "Departing engineer with legitimate access to the firmware and CAD repositories.",
        [
            (
                "T1213.003",
                "TA0009",
                False,
                ["Product designs and source code"],
                ["AC.001"],
                "",
            ),
            (
                "T1560.001",
                "TA0009",
                False,
                [],
                [],
                "Repositories archived before upload.",
            ),
            ("T1567.002", "TA0010", True, [], ["AC.009"], ""),
            ("T1048", "TA0010", False, [], ["AC.007"], ""),
        ],
        [(0, 1), (1, 2), (1, 3)],
    ),
]


@register
class ThreatModelingBuilder(DemoBuilder):
    """ATT&CK threat models for the headline risk scenarios."""

    name = "threat_modeling"
    feature_flags = ("threat_modeling",)
    depends = ("core", "risk")
    libraries = (ATTACK_LIBRARY,)
    covers: ClassVar[dict] = {
        ThreatModel: "folder",
        ThreatModelNode: "folder",
        ThreatModelEdge: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (ThreatModel, {"folder__in": folders}, ("ref_id",)),
            (
                ThreatModelNode,
                {"folder__in": folders},
                ("threat_model__ref_id", "technique__ref_id", "tactic__ref_id"),
            ),
            (
                ThreatModelEdge,
                {"folder__in": folders},
                (
                    "threat_model__ref_id",
                    "source__technique__ref_id",
                    "source__tactic__ref_id",
                    "target__technique__ref_id",
                    "target__tactic__ref_id",
                ),
            ),
        ]

    def build(self, ctx):
        catalog = TTPCatalog.objects.filter(urn=ATTACK_CATALOG).first()
        if catalog is None:
            ctx.err("MITRE ATT&CK catalog not loaded, skipping threat models")
            return
        assets = {asset.name: asset for asset in ctx.refs["assets"]}
        controls = {control.ref_id: control for control in ctx.refs["controls"]}
        scenarios = {s.ref_id: s for s in ctx.refs.get("risk_scenarios", [])}
        for ref_id, name, scenario_refs, description, nodes, edges in MODELS:
            model, created = ThreatModel.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "catalog": catalog,
                    "description": description,
                },
            )
            if not created:
                continue
            model.risk_scenarios.set(
                [scenarios[r] for r in scenario_refs if r in scenarios]
            )
            placed = []
            for technique_ref, tactic_ref, highlighted, names, refs, note in nodes:
                technique = Technique.objects.filter(
                    catalog=catalog, ref_id=technique_ref
                ).first()
                tactic = (
                    technique.tactics.filter(ref_id=tactic_ref).first()
                    if technique
                    else None
                )
                if tactic is None:
                    ctx.err(f"{technique_ref} not under {tactic_ref} in ATT&CK")
                    placed.append(None)
                    continue
                node = ThreatModelNode.objects.create(
                    threat_model=model,
                    kind=ThreatModelNode.Kind.TECHNIQUE,
                    technique=technique,
                    tactic=tactic,
                    is_highlighted=highlighted,
                    description=note,
                )
                node.assets.set([assets[n] for n in names if n in assets])
                node.applied_controls.set([controls[r] for r in refs if r in controls])
                placed.append(node)
            for source, target in edges:
                if placed[source] and placed[target]:
                    ThreatModelEdge.objects.create(
                        threat_model=model,
                        source=placed[source],
                        target=placed[target],
                    )
        ctx.out(f"{len(MODELS)} threat models seeded")
