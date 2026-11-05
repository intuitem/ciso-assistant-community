"""EBIOS RM demo builder: one study of the Keystone hub and its OTA update chain.

Workshops 1 to 4 are filled in end to end (business values, feared events,
RO/TO couples, ecosystem, strategic and operational scenarios); workshop 5 is
under way, so the study reads as a live analysis rather than a finished one.

The study uses the advanced quotation method: every kill chain step carries a
success probability and a technical difficulty, and the operating mode
likelihood is rolled up from them exactly as the graph editor does. Each
elementary action derives from a MITRE ATT&CK technique, and every operational
scenario lists the techniques of the actions its kill chains use.
"""

import copy
from typing import ClassVar

from core.demo import COMPANY, DemoBuilder, register
from core.models import RiskMatrix, Terminology
from ebios_rm.models import (
    INITIAL_META,
    AttackPath,
    EbiosRMStudy,
    ElementaryAction,
    FearedEvent,
    KillChain,
    OperatingMode,
    OperationalScenario,
    RoTo,
    Stakeholder,
    StrategicScenario,
)
from sec_intel.models import Technique, TTPCatalog
from tprm.models import Entity

EBIOS_MATRIX_LIBRARY = "urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
EBIOS_MATRIX = "urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
ATTACK_LIBRARY = "urn:intuitem:risk:library:mitre-attack"
ATTACK_CATALOG = "urn:intuitem:risk:ttp_catalog:mitre-attack"

STUDY = {
    "name": "Keystone hub and OTA update chain — EBIOS RM 2026",
    "ref_id": "EBIOS.2026.01",
    "version": "1.0",
    "description": (
        "Risk analysis of the Keystone home hub and the chain that builds, signs, "
        "provisions and updates its firmware: CI build farm, signing HSM, contract "
        "manufacturing, OTA service and MQTT gateway, and the support desk that can "
        "re-pair devices."
    ),
    "objectives": (
        "Feed the Cyber Resilience Act conformity file and the Keystone hub v3 "
        "security architecture review: identify the ecosystem attack paths that "
        "could compromise the installed base at scale, leak camera footage or "
        "expose product IP, and prioritise the treatment plan."
    ),
    "constraints_hypotheses": (
        "Kelvin thermostats and Lookout cameras are in scope only where they pair "
        "through the Keystone hub or share the OTA service. The online store and "
        f"the {COMPANY} Pay checkout are covered by the PCI DSS and DORA risk "
        "assessments. Kestrava Cloud's internal platform is treated as a black box "
        "covered by its ISO 27001 certificate."
    ),
    "observation": (
        "Workshop 4 rating sessions held with Product Security (PSIRT), firmware "
        "engineering, Brno plant OT engineering and procurement. Treatment plan "
        "drafting started with the anti-rollback and signing quorum measures."
    ),
}

# Workshop -> step statuses. Workshops 1-4 closed, 5 under way.
WORKSHOP_STATUS = [
    ["done", "done", "done", "done"],
    ["done", "done", "done"],
    ["done", "done", "done"],
    ["done", "done", "done"],
    ["done", "in_progress", "in_progress", "to_do", "to_do"],
]

# Asset names come from the core builder. The three primary assets carry the
# business values: firmware integrity, customer accounts (and the camera footage
# they unlock), product IP.
STUDY_ASSETS = [
    "Device firmware and signing keys",
    "Customer and device accounts",
    "Product designs and source code",
    "Production line control",
    "Firmware CI build farm",
    "Firmware signing HSM",
    "MQTT device gateway",
    "Device cloud Kubernetes cluster",
    "Companion mobile app",
    "Workforce identity provider",
    "Corporate VPN gateway",
    "Plant SCADA server",
    "Assembly cell PLCs",
]

FW = "Device firmware and signing keys"
ACCOUNTS = "Customer and device accounts"
DESIGNS = "Product designs and source code"
CI = "Firmware CI build farm"
HSM = "Firmware signing HSM"
MQTT = "MQTT device gateway"
CLUSTER = "Device cloud Kubernetes cluster"
IDP = "Workforce identity provider"

# ref_id, name, assets, gravity (0..3 on G1..G4), qualifications, selected, justification
FEARED_EVENTS = [
    (
        "FE.01",
        "Malicious firmware hijacks Keystone hubs across the installed base",
        [FW, MQTT],
        3,
        ["integrity", "safety", "trust", "reputation"],
        True,
        (
            "Around 600,000 hubs control locks, heating and cameras; a hijacked "
            "fleet is a safety issue and a CRA reportable incident."
        ),
    ),
    (
        "FE.02",
        "Hubs bricked at scale by a corrupted or rolled-back update",
        [FW, MQTT],
        3,
        ["availability", "safety", "financial", "trust"],
        True,
        (
            "Homes lose heating schedules and alarm arming; field replacement "
            "costs exceed one year of hub margin."
        ),
    ),
    (
        "FE.03",
        "Lookout camera footage disclosed",
        [ACCOUNTS],
        3,
        ["confidentiality", "privacy", "legal", "image"],
        True,
        (
            "Footage from inside homes is sensitive personal data: GDPR notification "
            "to every affected customer and lasting brand damage."
        ),
    ),
    (
        "FE.04",
        "Firmware signing keys disclosed or misused",
        [FW, HSM],
        3,
        ["integrity", "authenticity", "confidentiality"],
        True,
        (
            "Key rotation requires a field update of the boot ROM trust anchor, "
            "impossible on hubs v1 and v2."
        ),
    ),
    (
        "FE.05",
        "Keystone hub v3 designs and firmware source stolen",
        [DESIGNS],
        2,
        ["confidentiality", "financial", "governance"],
        True,
        (
            "A competitor clone could reach the market before the v3 launch; "
            "estimated at two years of R&D investment."
        ),
    ),
    (
        "FE.06",
        "OTA service unavailable during a critical security patch window",
        [MQTT, CLUSTER],
        1,
        ["availability", "operational"],
        True,
        (
            "The CRA reporting clock keeps running while devices stay unpatched; "
            "retry logic recovers within a day."
        ),
    ),
    (
        "FE.07",
        "Customer accounts and paired devices taken over",
        [ACCOUNTS],
        2,
        ["privacy", "trust", "human"],
        True,
        "Targeted harm to households: unlocked doors, disabled cameras, stalking.",
    ),
    (
        "FE.08",
        "Cloned hubs provisioned with genuine device identities",
        [FW, "Production line control"],
        1,
        ["authenticity", "financial"],
        False,
        "Already tracked in the enterprise risk register; kept for context only.",
    ),
]

# risk origin, target objective, category, motivation, resources, activity,
# feared events, selected, justification
ROTOS = [
    (
        "organized_crime",
        "Enrol the hub fleet in a botnet or extort by threatening mass bricking",
        "lucrative",
        4,
        3,
        3,
        ["FE.01", "FE.02", "FE.04"],
        True,
        (
            "IoT botnet crews now target update channels rather than default "
            "passwords; two consumer IoT makers extorted in 2025."
        ),
    ),
    (
        "competitor",
        "Obtain the Keystone hub v3 designs and firmware source",
        "espionage",
        3,
        3,
        2,
        ["FE.05", "FE.04"],
        True,
        (
            "Low-cost hub makers are entering the Matter market; design files "
            "circulate among contract manufacturers."
        ),
    ),
    (
        "state",
        "Pre-position persistent access in European smart homes",
        "strategic_prepositioning",
        2,
        4,
        2,
        ["FE.01", "FE.03", "FE.08"],
        True,
        (
            "National CERT advisories describe state actors implanting consumer "
            "IoT at the factory; the hub fleet sits in homes of officials."
        ),
    ),
    (
        "activist",
        "Leak camera footage to denounce home surveillance",
        "influence",
        3,
        1,
        2,
        ["FE.03", "FE.07"],
        True,
        (
            "Privacy campaigners publicly targeted smart camera brands after the "
            "2025 doorbell footage scandal."
        ),
    ),
    (
        "avenger",
        "Former firmware contractor sabotages a release",
        "operational_disruption",
        3,
        2,
        1,
        ["FE.02", "FE.06"],
        False,
        (
            "Contractor accounts are revoked at the end of each statement of work; "
            "reassessed at next review."
        ),
    ),
    (
        "amateur",
        "Resell remote access to hijacked cameras",
        "lucrative",
        2,
        1,
        2,
        ["FE.03", "FE.07"],
        False,
        (
            "Covered by the account takeover scenarios of the enterprise register "
            "(credential stuffing)."
        ),
    ),
]

# entity, description, relationship, current (dependency, penetration, maturity,
# trust), residual (same order), control ref_ids, selected
STAKEHOLDERS = [
    (
        "Kestrava Cloud B.V.",
        "IaaS provider hosting the device cloud, the OTA service and the MQTT gateway.",
        "supplier",
        (4, 4, 3, 2),
        (4, 3, 3, 3),
        ["AC.003", "AC.014"],
        True,
    ),
    (
        "Orbisil Semiconductors Ltd.",
        (
            "Supplies the Wi-Fi/Thread modules and the radio firmware blobs bundled in "
            "every hub image."
        ),
        "supplier",
        (4, 2, 2, 2),
        (4, 2, 3, 2),
        ["AC.015"],
        True,
    ),
    (
        "Shenwa Contract Manufacturing Co., Ltd.",
        (
            "Builds Lookout cameras and a second source of Keystone hubs in Shenzhen; "
            "runs end-of-line provisioning of device identities."
        ),
        "contractor",
        (3, 4, 2, 2),
        (3, 3, 3, 2),
        ["AC.004", "AC.018"],
        True,
    ),
    (
        "Linterra Automation GmbH",
        (
            "PLC/SCADA integrator with remote maintenance access to the Brno assembly "
            "and provisioning lines."
        ),
        "contractor",
        (3, 4, 2, 2),
        (3, 2, 3, 3),
        ["AC.007", "AC.017", "AC.002"],
        True,
    ),
    (
        "Mireo Support Lda.",
        (
            "Outsourced customer support; agents can unpair devices and re-pair "
            "cameras after identity checks."
        ),
        "contractor",
        (2, 3, 1, 2),
        (2, 2, 2, 2),
        ["AC.001", "AC.002"],
        True,
    ),
    (
        "Varnholt Embedded",
        (
            "Firmware contractor maintaining the hub's Thread stack, with commit rights "
            "and CI access on the firmware monorepo."
        ),
        "contractor",
        (2, 4, 2, 2),
        (2, 3, 3, 2),
        ["AC.006", "AC.013"],
        True,
    ),
    (
        "Fennick Analytics Ltd",
        "Product analytics SDK embedded in the companion app.",
        "supplier",
        (2, 2, 2, 2),
        None,
        [],
        False,
    ),
    (
        "Domora Retail SA",
        "Largest retail partner; in-store demo hubs run on the shops' guest Wi-Fi.",
        "client",
        (1, 1, 2, 3),
        None,
        [],
        False,
    ),
]

# ref_id, name, description, RO/TO target objective, focused feared event
STRATEGIC_SCENARIOS = [
    (
        "SS.01",
        "Botnet enrolment through a poisoned firmware release",
        (
            "A crime group gets malicious code into a signed hub release through a "
            "less mature link of the build chain, then lets the OTA service "
            "distribute it."
        ),
        "Enrol the hub fleet in a botnet or extort by threatening mass bricking",
        "FE.01",
    ),
    (
        "SS.02",
        "Extortion by bricking the installed base",
        (
            "The attacker proves it can push a bricking update to a sample of hubs, "
            "then demands a ransom before a fleet-wide rollout."
        ),
        "Enrol the hub fleet in a botnet or extort by threatening mass bricking",
        "FE.02",
    ),
    (
        "SS.03",
        "Theft of the Keystone hub v3 designs",
        (
            "A competitor obtains schematics, layouts and firmware source through a "
            "contractor or the contract manufacturer."
        ),
        "Obtain the Keystone hub v3 designs and firmware source",
        "FE.05",
    ),
    (
        "SS.04",
        "Persistent implant in hubs at provisioning",
        (
            "A state actor implants firmware when device identities are provisioned, "
            "giving dormant access to homes that survives normal updates."
        ),
        "Pre-position persistent access in European smart homes",
        "FE.01",
    ),
    (
        "SS.05",
        "Camera footage leak through the support desk",
        (
            "Activists re-pair cameras of targeted customers to accounts they "
            "control and publish the footage."
        ),
        "Leak camera footage to denounce home surveillance",
        "FE.03",
    ),
]

# strategic scenario, ref_id, name, stakeholders, selected, justification
ATTACK_PATHS = [
    (
        "SS.01",
        "AP.01",
        "Hijack a contractor's session and inject code in the build farm before signing",
        ["Varnholt Embedded"],
        True,
        "Contractor CI accounts can modify pipeline definitions on feature branches.",
    ),
    (
        "SS.01",
        "AP.02",
        "Ship a backdoored radio firmware blob with an Orbisil module delivery",
        ["Orbisil Semiconductors Ltd."],
        True,
        "Radio blobs are vendored as binaries and never rebuilt from source.",
    ),
    (
        "SS.02",
        "AP.01",
        "Take over the OTA console at the hoster and push a signed downgrade",
        ["Kestrava Cloud B.V."],
        True,
        "Hubs v1 and v2 have no anti-rollback counter; old signed images still install.",
    ),
    (
        "SS.02",
        "AP.02",
        "Have the signing HSM sign a bricking image with a hijacked release session",
        [],
        True,
        "Per-signature quorum is not enforced; only key ceremonies need two officers.",
    ),
    (
        "SS.03",
        "AP.01",
        "Recruit or phish a firmware contractor engineer and clone the v3 repositories",
        ["Varnholt Embedded"],
        True,
        "Contractor engineers clone the full monorepo; DLP covers staff laptops only.",
    ),
    (
        "SS.03",
        "AP.02",
        "Harvest design files from the contract manufacturer's factory test servers",
        ["Shenwa Contract Manufacturing Co., Ltd."],
        True,
        "Gerber files and test firmware sit on factory servers outside our access reviews.",
    ),
    (
        "SS.03",
        "AP.03",
        "Phish a hardware designer at the Eindhoven design office",
        [],
        False,
        "Covered by enterprise scenario RS.03 and the design office DLP rollout.",
    ),
    (
        "SS.04",
        "AP.01",
        "Implant firmware at the contract manufacturer's provisioning station",
        ["Shenwa Contract Manufacturing Co., Ltd."],
        True,
        "The provisioning station loads images from a local share we do not monitor.",
    ),
    (
        "SS.04",
        "AP.02",
        "Reach the Brno provisioning line through the integrator's remote maintenance",
        ["Linterra Automation GmbH"],
        True,
        "Linterra's VPN account lands on the line network until segmentation (AC.007) completes.",
    ),
    (
        "SS.05",
        "AP.01",
        "Socially engineer support agents into re-pairing cameras",
        ["Mireo Support Lda."],
        True,
        "Re-pairing is approved after identity checks done by phone.",
    ),
    (
        "SS.05",
        "AP.02",
        "Plant a malicious update of the analytics SDK in the companion app",
        ["Fennick Analytics Ltd"],
        False,
        "The SDK has no access to video streams (verified in the 2025 app review).",
    ),
]

# ref_id, name, attack stage, icon, threat ref_id, ATT&CK technique ref_id
KNOW = ElementaryAction.AttackStage.KNOW
ENTER = ElementaryAction.AttackStage.ENTER
DISCOVER = ElementaryAction.AttackStage.DISCOVER
EXPLOIT = ElementaryAction.AttackStage.EXPLOIT
ELEMENTARY_ACTIONS = [
    (
        "EA.01",
        "Open-source reconnaissance on the firmware team and contractors",
        KNOW,
        "search",
        None,
        "T1593",
    ),
    (
        "EA.02",
        "Scan the device cloud, MQTT gateway and OTA endpoints",
        KNOW,
        "globe",
        None,
        "T1595",
    ),
    (
        "EA.03",
        "Tear down a retail hub to dump firmware and debug interfaces",
        KNOW,
        "usb",
        None,
        "T1592.001",
    ),
    (
        "EA.04",
        "Open fake researcher and press accounts to stage the campaign",
        KNOW,
        "phone",
        None,
        "T1585.001",
    ),
    (
        "EA.05",
        "Spear-phishing of a contractor developer",
        ENTER,
        "carrot",
        None,
        "T1566.002",
    ),
    (
        "EA.06",
        "Sign in to the build farm with a hijacked contractor SSO session",
        ENTER,
        "key",
        "T-004",
        "T1078",
    ),
    (
        "EA.07",
        "Recruit an insider at a supplier",
        ENTER,
        "money",
        "T-003",
        "T1199",
    ),
    (
        "EA.08",
        "Ship a backdoored radio firmware blob with a module delivery",
        ENTER,
        "cube",
        "T-004",
        "T1195.002",
    ),
    (
        "EA.09",
        "Enter through the vendor remote maintenance VPN",
        ENTER,
        "computer",
        "T-008",
        "T1133",
    ),
    (
        "EA.10",
        "Call a support agent posing as the customer to re-pair a camera",
        ENTER,
        "phone",
        None,
        "T1566.004",
    ),
    (
        "EA.11",
        "Log in to the OTA console with credentials leaked in a hoster ticket",
        ENTER,
        "key",
        "T-005",
        "T1078.004",
    ),
    (
        "EA.12",
        "Steal a release manager's session to reach the signing service",
        ENTER,
        "key",
        "T-007",
        "T1539",
    ),
    (
        "EA.13",
        "Harvest signing service tokens from CI runner variables",
        DISCOVER,
        "key",
        "T-004",
        "T1552.001",
    ),
    (
        "EA.14",
        "Map the release pipeline and the HSM signing client",
        DISCOVER,
        "network",
        None,
        "T1046",
    ),
    (
        "EA.15",
        "Locate the provisioning station and the device identity database",
        DISCOVER,
        "database",
        None,
        "T1083",
    ),
    (
        "EA.16",
        "Identify the v3 repositories and CAD vaults",
        DISCOVER,
        "search",
        "T-003",
        "T1213.003",
    ),
    (
        "EA.17",
        "Inject a backdoor into the hub firmware build",
        EXPLOIT,
        "skull",
        "T-007",
        "T1195.002",
    ),
    (
        "EA.18",
        "Get a malicious image signed by the HSM",
        EXPLOIT,
        "key",
        "T-007",
        "T1553.002",
    ),
    (
        "EA.19",
        "Stage a fleet-wide rollout that skips the canary ring",
        EXPLOIT,
        "cloud",
        "T-007",
        "T1072",
    ),
    (
        "EA.20",
        "Push a signed downgrade to a vulnerable firmware",
        EXPLOIT,
        "cloud",
        "T-007",
        "T1601.002",
    ),
    (
        "EA.21",
        "Corrupt hub firmware and post a ransom demand",
        EXPLOIT,
        "skull",
        "T-001",
        "T1495",
    ),
    (
        "EA.22",
        "Implant persistent firmware in hubs at provisioning",
        EXPLOIT,
        "usb",
        "T-004",
        "T1542.001",
    ),
    (
        "EA.23",
        "Exfiltrate repositories and CAD files to cloud storage",
        EXPLOIT,
        "file",
        "T-003",
        "T1567.002",
    ),
    (
        "EA.24",
        "Download footage from re-paired cameras and publish it",
        EXPLOIT,
        "globe",
        None,
        "T1530",
    ),
]

# Kill chain step: (action ref_id, antecedent indexes, logic operator,
# success probability, technical difficulty, highlighted, supporting assets).
# Levels are 0..3 on the 4x4 EBIOS RM scales.
#
# (strategic scenario, attack path) -> threats, forced likelihood,
# justification, [(operating mode name, description, steps)]
OPERATIONAL_SCENARIOS = {
    ("SS.01", "AP.01"): (
        ["T-004", "T-007"],
        None,
        "Two firmware contractors hold commit and CI rights; SSO sessions last 12 hours.",
        [
            (
                "Phished contractor session used to inject code before signing",
                (
                    "A Varnholt developer is phished; the session reaches the build "
                    "farm, where a pipeline change slips a backdoor into the hub "
                    "image before it is signed."
                ),
                [
                    ("EA.01", [], None, 3, 0, False, []),
                    ("EA.05", [0], None, 2, 1, False, [IDP]),
                    ("EA.06", [1], None, 2, 1, False, [CI]),
                    ("EA.14", [2], None, 3, 1, False, [CI]),
                    ("EA.17", [2, 3], "AND", 2, 2, False, [CI, FW]),
                    ("EA.19", [4], None, 1, 2, True, [MQTT, CLUSTER]),
                ],
            ),
            (
                "Leaked CI tokens replayed against the build farm",
                (
                    "Runner tokens found in a public fork of a contractor's tooling "
                    "repository are replayed against the build farm."
                ),
                [
                    ("EA.02", [], None, 3, 0, False, []),
                    ("EA.13", [0], None, 1, 2, False, [CI]),
                    ("EA.17", [1], None, 2, 2, False, [CI]),
                    ("EA.19", [2], None, 1, 2, True, [MQTT]),
                ],
            ),
        ],
    ),
    ("SS.01", "AP.02"): (
        ["T-004", "T-007"],
        None,
        "Orbisil blobs are checked against a vendor hash, but the hash ships with the blob.",
        [
            (
                "Backdoored Thread radio blob carried into a signed release",
                (
                    "An insider at the module supplier swaps the radio firmware "
                    "blob; our pipeline signs it with the rest of the image."
                ),
                [
                    ("EA.03", [], None, 3, 0, False, []),
                    ("EA.07", [], None, 1, 2, False, []),
                    ("EA.08", [0, 1], "AND", 1, 3, False, [FW]),
                    ("EA.19", [2], None, 2, 1, True, [MQTT]),
                ],
            ),
        ],
    ),
    ("SS.02", "AP.01"): (
        ["T-005", "T-007"],
        None,
        "OTA console MFA is enforced, but the hoster's support desk can reset it.",
        [
            (
                "Hoster console takeover and signed downgrade to firmware 2.4",
                (
                    "Credentials pasted in a hoster support ticket open the OTA "
                    "console; the attacker schedules firmware 2.4, signed but "
                    "vulnerable, then bricks the hubs through its flaw."
                ),
                [
                    ("EA.02", [], None, 3, 0, False, []),
                    ("EA.11", [0], None, 1, 2, False, [CLUSTER]),
                    ("EA.20", [1], None, 2, 1, False, [MQTT, FW]),
                    ("EA.21", [2], None, 2, 1, True, [MQTT]),
                ],
            ),
        ],
    ),
    ("SS.02", "AP.02"): (
        ["T-007"],
        None,
        "Signing is triggered from the release pipeline without per-signature approval.",
        [
            (
                "Release manager session hijack and HSM signing",
                (
                    "A stolen release manager session drives the HSM signing client; "
                    "both the session and knowledge of the signing workflow are needed."
                ),
                [
                    ("EA.01", [], None, 3, 0, False, []),
                    ("EA.12", [0], None, 1, 2, False, [IDP]),
                    ("EA.14", [1], None, 2, 1, False, [HSM]),
                    ("EA.18", [1, 2], "AND", 1, 3, False, [HSM]),
                    ("EA.21", [3], None, 2, 1, True, [MQTT]),
                ],
            ),
        ],
    ),
    ("SS.03", "AP.01"): (
        ["T-003"],
        None,
        "v3 work is split between Lyon and Varnholt; contractor clones are not watermarked.",
        [
            (
                "Recruited contractor engineer clones the v3 repositories",
                (
                    "A competitor recruits a Varnholt engineer who copies the v3 "
                    "firmware and hardware repositories before leaving."
                ),
                [
                    ("EA.07", [], None, 2, 1, False, []),
                    ("EA.16", [0], None, 3, 0, False, [DESIGNS]),
                    ("EA.23", [1], None, 2, 1, True, [DESIGNS]),
                ],
            ),
            (
                "Phished contractor laptop used to pull the CAD vaults",
                (
                    "A phished contractor session is used to browse and export the "
                    "CAD vaults shared for the v3 enclosure."
                ),
                [
                    ("EA.05", [], None, 2, 1, False, []),
                    ("EA.06", [0], None, 2, 1, False, [IDP]),
                    ("EA.16", [1], None, 2, 1, False, [DESIGNS]),
                    ("EA.23", [2], None, 2, 1, True, []),
                ],
            ),
        ],
    ),
    ("SS.03", "AP.02"): (
        ["T-004", "T-003"],
        None,
        "Factory test servers hold Lookout and hub v2 board files for in-circuit testing.",
        [
            (
                "Factory test server compromise at the contract manufacturer",
                (
                    "Either an exposed factory service or a bribed operator gives "
                    "access to the test servers holding board files."
                ),
                [
                    ("EA.02", [], None, 2, 1, False, []),
                    ("EA.07", [], None, 2, 1, False, []),
                    ("EA.15", [0, 1], "OR", 2, 1, False, []),
                    ("EA.23", [2], None, 2, 1, True, [DESIGNS]),
                ],
            ),
        ],
    ),
    ("SS.04", "AP.01"): (
        ["T-004"],
        2,
        (
            "Raised to level 2 after the national CERT advisory on implants in "
            "consumer IoT factories, beyond what the step ratings capture."
        ),
        [
            (
                "Implant loaded at the end-of-line provisioning station",
                (
                    "An operator is coerced into replacing the provisioning image on "
                    "the station's local share; implanted hubs pass functional tests."
                ),
                [
                    ("EA.01", [], None, 3, 0, False, []),
                    ("EA.07", [0], None, 1, 2, False, []),
                    ("EA.15", [1], None, 2, 1, False, []),
                    ("EA.22", [2], None, 1, 3, True, [FW, ACCOUNTS]),
                ],
            ),
        ],
    ),
    ("SS.04", "AP.02"): (
        ["T-008", "T-004"],
        None,
        "Linterra uses a shared VPN account without per-technician MFA.",
        [
            (
                "Integrator VPN pivot into the Brno provisioning line",
                (
                    "The integrator's VPN account reaches the SCADA server, then "
                    "the provisioning PCs on the same line network."
                ),
                [
                    ("EA.01", [], None, 3, 0, False, []),
                    (
                        "EA.09",
                        [0],
                        None,
                        2,
                        1,
                        False,
                        ["Corporate VPN gateway", "Plant SCADA server"],
                    ),
                    ("EA.15", [1], None, 2, 1, False, ["Assembly cell PLCs"]),
                    ("EA.22", [2], None, 1, 2, True, [FW]),
                ],
            ),
        ],
    ),
    ("SS.05", "AP.01"): (
        ["T-003"],
        None,
        "Mireo handles 9,000 camera tickets a month; re-pairing needs no in-app approval.",
        [
            (
                "Vishing the support desk to re-pair cameras",
                (
                    "Activists gather personal details of targeted customers, call "
                    "the support desk and get cameras re-paired to their accounts."
                ),
                [
                    ("EA.04", [], None, 3, 0, False, []),
                    ("EA.10", [0], None, 2, 1, False, [ACCOUNTS]),
                    (
                        "EA.24",
                        [1],
                        None,
                        2,
                        1,
                        True,
                        [ACCOUNTS, "Companion mobile app"],
                    ),
                ],
            ),
            (
                "Insider support agent sells re-pairings",
                "A Mireo agent is paid to re-pair cameras without any call.",
                [
                    ("EA.07", [], None, 2, 1, False, []),
                    ("EA.24", [0], None, 2, 1, True, [ACCOUNTS]),
                ],
            ),
        ],
    ),
}


def terminology(field_path, name):
    return (
        Terminology.objects.filter(field_path=field_path, name=name)
        .order_by("-builtin", "created_at")
        .first()
    )


@register
class EbiosRMBuilder(DemoBuilder):
    """One EBIOS RM study of the Keystone hub OTA chain, workshops 1 to 5."""

    name = "ebios_rm"
    feature_flags = ("ttps",)
    depends = ("core", "compliance", "risk", "tprm")
    libraries = (EBIOS_MATRIX_LIBRARY, ATTACK_LIBRARY)
    covers: ClassVar[dict] = {
        EbiosRMStudy: "folder",
        FearedEvent: "ebios_rm_study__folder",
        RoTo: "ebios_rm_study__folder",
        Stakeholder: "ebios_rm_study__folder",
        StrategicScenario: "ebios_rm_study__folder",
        AttackPath: "ebios_rm_study__folder",
        OperationalScenario: "ebios_rm_study__folder",
        OperatingMode: "operational_scenario__ebios_rm_study__folder",
        ElementaryAction: "folder",
        KillChain: "operating_mode__operational_scenario__ebios_rm_study__folder",
    }

    def stamps(self, ctx):
        study = "ebios_rm_study__name"
        scenario = "operational_scenario__attack_path"
        step = "operating_mode__operational_scenario__attack_path"
        return [
            (EbiosRMStudy, {"folder": ctx.domain}, ("name",)),
            (FearedEvent, {"folder": ctx.domain}, (study, "ref_id")),
            (RoTo, {"folder": ctx.domain}, (study, "target_objective")),
            (Stakeholder, {"folder": ctx.domain}, (study, "entity__name")),
            (StrategicScenario, {"folder": ctx.domain}, (study, "ref_id")),
            (
                AttackPath,
                {"folder": ctx.domain},
                (study, "strategic_scenario__ref_id", "ref_id"),
            ),
            (
                OperationalScenario,
                {"folder": ctx.domain},
                (
                    study,
                    "attack_path__strategic_scenario__ref_id",
                    "attack_path__ref_id",
                ),
            ),
            (
                OperatingMode,
                {"folder": ctx.domain},
                (
                    "operational_scenario__ebios_rm_study__name",
                    f"{scenario}__strategic_scenario__ref_id",
                    f"{scenario}__ref_id",
                    "ref_id",
                ),
            ),
            (ElementaryAction, {"folder": ctx.domain}, ("name",)),
            (
                KillChain,
                {"folder": ctx.domain},
                (
                    "operating_mode__operational_scenario__ebios_rm_study__name",
                    f"{step}__strategic_scenario__ref_id",
                    f"{step}__ref_id",
                    "operating_mode__ref_id",
                    "elementary_action__name",
                ),
            ),
        ]

    def build(self, ctx):
        matrix = RiskMatrix.objects.filter(urn=EBIOS_MATRIX).first()
        if matrix is None:
            ctx.err("EBIOS RM risk matrix not loaded, skipping study")
            return
        if Entity.get_main_entity() is None:
            ctx.err("no main entity on this instance, skipping study")
            return
        threats = {t.ref_id: t for t in ctx.refs.get("threats", [])}
        actions = self.build_elementary_actions(ctx, threats)
        entities = self.build_entities(ctx)

        meta = copy.deepcopy(INITIAL_META)
        for workshop, statuses in zip(meta["workshops"], WORKSHOP_STATUS):
            for step, status in zip(workshop["steps"], statuses):
                step["status"] = status
        study, created = EbiosRMStudy.objects.get_or_create(
            name=STUDY["name"],
            folder=ctx.domain,
            defaults={
                **{k: v for k, v in STUDY.items() if k != "name"},
                "risk_matrix": matrix,
                "status": EbiosRMStudy.Status.IN_PROGRESS,
                "quotation_method": EbiosRMStudy.QuotationMethod.ADVANCED,
                "eta": ctx.day(30),
                "due_date": ctx.day(45),
                "meta": meta,
            },
        )
        ctx.refs["ebios_rm_study"] = study
        if not created:
            return

        assets = {a.name: a for a in ctx.refs["assets"]}
        controls = {c.ref_id: c for c in ctx.refs["controls"]}
        study.assets.set([assets[name] for name in STUDY_ASSETS if name in assets])
        # The lead ISO 27001 audit and the CRA essential requirements audit.
        study.compliance_assessments.set(
            a
            for a in ctx.refs.get("audits") or []
            if a.ref_id in ("AUD.2026.01", "AUD.2026.05")
        )

        feared_events = self.build_feared_events(ctx, study, assets)
        rotos = self.build_rotos(study, feared_events)
        stakeholders = self.build_stakeholders(study, entities, controls)
        attack_paths = self.build_strategic_scenarios(
            study, rotos, feared_events, stakeholders
        )
        self.build_operational_scenarios(study, attack_paths, actions, threats, assets)
        ctx.out(
            f"EBIOS RM study seeded: {len(feared_events)} feared events, "
            f"{len(rotos)} RO/TO, {len(attack_paths)} attack paths"
        )

    def build_elementary_actions(self, ctx, threats):
        actions = {}
        catalog = TTPCatalog.objects.filter(urn=ATTACK_CATALOG).first()
        if catalog is None:
            ctx.err("MITRE ATT&CK catalog not loaded, actions left unmapped")
        for ref_id, name, stage, icon, threat, technique_ref in ELEMENTARY_ACTIONS:
            technique = None
            if catalog is not None:
                technique = Technique.objects.filter(
                    catalog=catalog, ref_id=technique_ref
                ).first()
                if technique is None:
                    ctx.err(f"{technique_ref} not found in ATT&CK")
            action, _ = ElementaryAction.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "attack_stage": stage,
                    "icon": icon,
                    "threat": threats.get(threat),
                    "technique": technique,
                },
            )
            actions[ref_id] = action
        return actions

    def build_entities(self, ctx):
        # Vendors come from the tprm builder; reuse them rather than duplicating.
        # Only parties tprm does not know are created here, in the root domain.
        entities = {}
        for (
            name,
            description,
            relationship,
            (dependency, penetration, maturity, trust),
            *_,
        ) in STAKEHOLDERS:
            entity = Entity.objects.filter(name=name, folder__in=ctx.folders()).first()
            if entity is not None:
                entities[name] = entity
                continue
            entity, created = Entity.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "description": description,
                    "default_dependency": dependency,
                    "default_penetration": penetration,
                    "default_maturity": maturity,
                    "default_trust": trust,
                },
            )
            if created:
                category = terminology(
                    Terminology.FieldPath.ENTITY_RELATIONSHIP, relationship
                )
                if category is not None:
                    entity.relationship.set([category])
            entities[name] = entity
        return entities

    def build_feared_events(self, ctx, study, assets):
        feared_events = {}
        for (
            ref_id,
            name,
            asset_names,
            gravity,
            qualifications,
            selected,
            justification,
        ) in FEARED_EVENTS:
            feared_event = FearedEvent.objects.create(
                ebios_rm_study=study,
                ref_id=ref_id,
                name=name,
                gravity=gravity,
                is_selected=selected,
                justification=justification,
            )
            feared_event.assets.set([assets[n] for n in asset_names if n in assets])
            feared_event.qualifications.set(
                filter(
                    None,
                    (
                        terminology(Terminology.FieldPath.QUALIFICATIONS, q)
                        for q in qualifications
                    ),
                )
            )
            feared_events[ref_id] = feared_event
        return feared_events

    def build_rotos(self, study, feared_events):
        rotos = {}
        for (
            origin,
            objective,
            category,
            motivation,
            resources,
            activity,
            feared_event_refs,
            selected,
            justification,
        ) in ROTOS:
            roto = RoTo.objects.create(
                ebios_rm_study=study,
                risk_origin=terminology(Terminology.FieldPath.ROTO_RISK_ORIGIN, origin),
                target_objective=objective,
                target_objective_category=terminology(
                    Terminology.FieldPath.ROTO_TARGET_OBJECTIVE_CATEGORY, category
                ),
                motivation=motivation,
                resources=resources,
                activity=activity,
                is_selected=selected,
                justification=justification,
            )
            roto.feared_events.set([feared_events[r] for r in feared_event_refs])
            rotos[objective] = roto
        return rotos

    def build_stakeholders(self, study, entities, controls):
        stakeholders = {}
        for (
            name,
            _,
            relationship,
            current,
            residual,
            control_refs,
            selected,
        ) in STAKEHOLDERS:
            # As the API does: residual starts as a copy of current, and only
            # drops once controls are applied to the stakeholder.
            residual = residual or current
            stakeholder = Stakeholder.objects.create(
                ebios_rm_study=study,
                entity=entities[name],
                category=terminology(
                    Terminology.FieldPath.ENTITY_RELATIONSHIP, relationship
                ),
                current_dependency=current[0],
                current_penetration=current[1],
                current_maturity=current[2],
                current_trust=current[3],
                residual_dependency=residual[0],
                residual_penetration=residual[1],
                residual_maturity=residual[2],
                residual_trust=residual[3],
                is_selected=selected,
            )
            stakeholder.applied_controls.set(
                [controls[r] for r in control_refs if r in controls]
            )
            stakeholders[name] = stakeholder
        return stakeholders

    def build_strategic_scenarios(self, study, rotos, feared_events, stakeholders):
        scenarios = {}
        for ref_id, name, description, objective, focused in STRATEGIC_SCENARIOS:
            scenarios[ref_id] = StrategicScenario.objects.create(
                ebios_rm_study=study,
                ro_to_couple=rotos[objective],
                ref_id=ref_id,
                name=name,
                description=description,
                focused_feared_event=feared_events[focused] if focused else None,
            )
        attack_paths = {}
        for (
            scenario_ref,
            ref_id,
            name,
            stakeholder_names,
            selected,
            justification,
        ) in ATTACK_PATHS:
            attack_path = AttackPath.objects.create(
                ebios_rm_study=study,
                strategic_scenario=scenarios[scenario_ref],
                ref_id=ref_id,
                name=name,
                is_selected=selected,
                justification=justification,
            )
            attack_path.stakeholders.set([stakeholders[n] for n in stakeholder_names])
            attack_paths[(scenario_ref, ref_id)] = attack_path
        return attack_paths

    def build_operational_scenarios(
        self, study, attack_paths, actions, threats, assets
    ):
        for key, (
            threat_refs,
            forced,
            justification,
            modes,
        ) in OPERATIONAL_SCENARIOS.items():
            scenario = OperationalScenario.objects.create(
                ebios_rm_study=study,
                attack_path=attack_paths[key],
                operating_modes_description="\n".join(m[0] for m in modes),
                likelihood_forced=forced,
                is_selected=True,
                justification=justification,
            )
            scenario.threats.set([threats[r] for r in threat_refs if r in threats])
            # Techniques of the scenario: those its kill chain actions derive from.
            techniques = {
                actions[step[0]].technique
                for _, _, steps in modes
                for step in steps
                if actions[step[0]].technique
            }
            scenario.techniques.set(techniques)
            for index, (name, description, steps) in enumerate(modes, start=1):
                mode = OperatingMode.objects.create(
                    operational_scenario=scenario,
                    ref_id=f"MO.{index:02d}",
                    name=name,
                    description=description,
                )
                created = []
                for (
                    action_ref,
                    antecedents,
                    operator,
                    probability,
                    difficulty,
                    highlighted,
                    asset_names,
                ) in steps:
                    step = KillChain.objects.create(
                        operating_mode=mode,
                        elementary_action=actions[action_ref],
                        logic_operator=operator,
                        success_probability=probability,
                        technical_difficulty=difficulty,
                        is_highlighted=highlighted,
                    )
                    step.antecedents.set([created[i] for i in antecedents])
                    step.assets.set([assets[n] for n in asset_names if n in assets])
                    created.append(step)
                # The graph editor recomputes the roll-up after each save; the
                # operating mode save then refreshes the scenario likelihood.
                mode.refresh_likelihood()
