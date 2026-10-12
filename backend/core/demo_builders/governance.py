"""Core demo builders: governance.

- ``governance``: ISMS context (issues, objectives), teams, labels, commitments,
  audit campaigns, requirement assignments on the audits, and a CRA maturity
  self-assessment answered through its questionnaire
- ``classification``: the company's own information classification schemes
- ``forms``: published quick forms (derogation, vendor review) with requests
  in every state

Teams are the only actors created: they exist without users, and give
objectives, assignments and requests someone to point at.
"""

from datetime import timedelta
from typing import ClassVar

from django.contrib.contenttypes.models import ContentType

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.demo_builders.grc import ComplianceBuilder
from core.models import (
    Actor,
    Answer,
    AppliedControl,
    Campaign,
    ClassificationLevel,
    Commitment,
    ComplianceAssessment,
    FilteringLabel,
    Framework,
    ObjectClassification,
    OrganisationIssue,
    OrganisationObjective,
    Perimeter,
    Question,
    QuickForm,
    QuickFormPublication,
    QuickFormResponse,
    RequirementAssessment,
    RequirementAssignment,
    Team,
)
from core.utils import (
    apply_answers_dict,
    assign_audit_to,
    build_initial_field_visibility,
)
from iam.models import Folder

CRA_LIBRARY = "urn:intuitem:risk:library:enisa-sme-cra-maturity"
DEROGATION_LIBRARY = "urn:intuitem:risk:library:derogation-request"
VENDOR_REVIEW_LIBRARY = "urn:intuitem:risk:library:vendor-review-request"

MAIL_DOMAIN = f"{COMPANY.lower().replace(' ', '')}.example"

# name, sub-domain (None = root demo domain), mailbox, description.
# Teams that the pmbok builder also uses sit in the root domain under the same
# name, so both builders share one row whichever runs first.
TEAMS = [
    (
        "GRC Office",
        None,
        "grc",
        (
            "Reports to the CISO. Owns the ISMS, the risk register, the ISO 27001 "
            "certification and audit planning."
        ),
    ),
    (
        "Security Operations Centre",
        None,
        "soc",
        (
            "24/7 monitoring of the device cloud, the store and corporate IT; "
            "incident response and NIS2 early warnings."
        ),
    ),
    (
        "IT Operations",
        None,
        "itops",
        (
            "Corporate infrastructure, endpoints, the workforce identity provider "
            "and the service desk for Lyon, Brno and Eindhoven."
        ),
    ),
    (
        "Data Protection Office",
        None,
        "dpo",
        (
            "The DPO and privacy analysts: records of processing, DPIAs, data "
            "subject requests and camera footage questions."
        ),
    ),
    (
        "Procurement",
        None,
        "procurement",
        (
            "Supplier selection, contracts and the supplier security questionnaire, "
            "led by the Head of Procurement."
        ),
    ),
    (
        "People & Culture",
        None,
        "people",
        "HR, onboarding and leavers, security awareness and phishing simulations.",
    ),
    (
        "Facilities & Site Security",
        None,
        "facilities",
        (
            "Badges, CCTV and visitor management at the Lyon HQ, the Brno plant and "
            "the Eindhoven office."
        ),
    ),
    (
        "Cloud Platform",
        "Connected Products",
        "cloud-platform",
        (
            "Runs the device cloud on Kestrava Cloud: Kubernetes, the MQTT device "
            "gateway, telemetry and the OTA update service."
        ),
    ),
    (
        "PSIRT",
        "Connected Products",
        "psirt",
        (
            "Product security incident response team, run by the Head of Product "
            "Security: vulnerability intake, triage, advisories and CRA reporting."
        ),
    ),
    (
        "Firmware Engineering",
        "Connected Products",
        "firmware",
        (
            "Kelvin, Lookout and Keystone firmware, the CI build farm, code signing "
            "and SBOM generation."
        ),
    ),
    (
        "OT Engineering",
        "Manufacturing",
        "ot-eng",
        (
            "PLC, SCADA and plant network engineering at the Brno assembly plant, "
            "led by the Plant OT Engineering Manager."
        ),
    ),
    (
        "Store Engineering",
        "Online Store & Payments",
        "store-eng",
        (
            "Builds the online store web front, checkout and the companion app's "
            "shop screens."
        ),
    ),
    (
        "Payments Risk",
        "Online Store & Payments",
        "payments-risk",
        (
            f"{PAY_ENTITY} second line: the Payments Risk Officer, PCI DSS "
            "compliance, DORA ICT risk and the register of information."
        ),
    ),
]

# ref_id, name, category, origin, status, start offset, expiry offset, assets, description.
ISSUES = [
    (
        "ISS.01",
        "Cyber Resilience Act reporting obligations for every product line",
        "legal",
        "external",
        "active",
        -200,
        900,
        ["Device firmware and signing keys", "Companion mobile app"],
        (
            "Actively exploited vulnerabilities must be notified within 24 hours "
            "from September 2026; SBOM, support period and security updates are "
            "mandatory from December 2027."
        ),
    ),
    (
        "ISS.02",
        f"NIS2 transposition classifies {COMPANY} as an important entity",
        "legal",
        "external",
        "active",
        -300,
        None,
        ["Production line control", "Order fulfilment"],
        (
            "Manufacturing of electronics is in scope: management body "
            "accountability, supply chain security and 24-hour early warning apply."
        ),
    ),
    (
        "ISS.03",
        f"PCI DSS 4.0 future-dated requirements now mandatory for {PAY_ENTITY}",
        "legal",
        "external",
        "active",
        -420,
        None,
        ["Store checkout and payments", "Online store web front"],
        (
            "Payment page script integrity (6.4.3, 11.6.1) and authenticated "
            "internal scans are in scope of the next report on compliance."
        ),
    ),
    (
        "ISS.04",
        f"DORA register of information due for {PAY_ENTITY}",
        "legal",
        "external",
        "active",
        -180,
        None,
        ["Store checkout and payments"],
        (
            "Pellion Payments and Kestrava Cloud support critical functions; the "
            "register and exit plans go to the competent authority each year."
        ),
    ),
    (
        "ISS.05",
        "Wi-Fi and Thread chipset supply shortage",
        "economic",
        "external",
        "active",
        -150,
        300,
        ["Product designs and source code"],
        (
            "Orbisil Semiconductors module lead times reached 38 weeks; a second "
            "source means a new firmware port and a new radio certification cycle."
        ),
    ),
    (
        "ISS.06",
        "Retail partners add security requirements to listing contracts",
        "economic",
        "external",
        "active",
        -120,
        None,
        ["Device firmware and signing keys"],
        (
            "Two large retail partners now require ETSI EN 303 645 conformity and a "
            "published security update period on the shelf label."
        ),
    ),
    (
        "ISS.07",
        "Reputation risk around connected camera privacy",
        "technology",
        "external",
        "active",
        -90,
        None,
        ["Customer and device accounts"],
        (
            "A competitor's leak of indoor camera footage made headlines; Lookout "
            "customers now ask where their video is stored and who can see it."
        ),
    ),
    (
        "ISS.08",
        "Ransomware campaigns targeting European manufacturers",
        "technology",
        "external",
        "active",
        -160,
        None,
        ["Production line control", "Plant SCADA server"],
        (
            "Three electronics manufacturers stopped production this year; initial "
            "access through VPN appliances and integrator remote access."
        ),
    ),
    (
        "ISS.09",
        "Ageing OT estate at the Brno assembly plant",
        "internalProcesses",
        "internal",
        "active",
        -400,
        None,
        ["Plant SCADA server", "Assembly cell PLCs"],
        (
            "Line-1 PLCs and the SCADA server run end-of-life firmware on a flat "
            "network shared with office IT; segmentation waits for a line shutdown."
        ),
    ),
    (
        "ISS.10",
        "Product security team attrition",
        "humanResources",
        "internal",
        "active",
        -120,
        240,
        [],
        (
            "Two of six PSIRT seats are vacant while the CRA reporting deadline "
            "approaches; hiring approved, interviews in progress."
        ),
    ),
    (
        "ISS.11",
        "Low phishing reporting rate on the shop floor",
        "companyCulture",
        "internal",
        "active",
        -60,
        None,
        [],
        (
            "23% of staff reported the last simulated phishing campaign, 9% at the "
            "Brno plant where shared kiosks are the only mailbox access."
        ),
    ),
    (
        "ISS.12",
        "Integration of the Eindhoven hardware design office",
        "organisationStructure",
        "internal",
        "draft",
        30,
        400,
        ["Workforce identity provider", "Product designs and source code"],
        (
            "The acquired office runs its own identity provider and file shares and "
            "sits outside the ISMS scope; integration plan in preparation."
        ),
    ),
    (
        "ISS.13",
        "Energy price volatility at the Brno plant",
        "financialCapacity",
        "external",
        "inactive",
        -700,
        -100,
        [],
        "Mitigated by the multi-year energy contract signed in 2026; kept for history.",
    ),
    (
        "ISS.14",
        "Heat waves threatening the Brno plant server room",
        "environmental",
        "external",
        "active",
        -30,
        None,
        ["Plant SCADA server"],
        (
            "Two cooling alarms last summer; SCADA failover to the standby server "
            "has never been tested under production load."
        ),
    ),
]

# ref_id, name, status, health, start, eta, due, closing, issues, assets, teams, description.
OBJECTIVES = [
    (
        "OBJ.01",
        "Publish an SBOM with every product release",
        "in_progress",
        "on_track",
        -200,
        110,
        120,
        None,
        ["ISS.01", "ISS.06"],
        ["Device firmware and signing keys"],
        ["Firmware Engineering", "PSIRT"],
        (
            "KPI: share of Kelvin, Lookout and Keystone releases shipped with a "
            "CycloneDX SBOM; 71% today."
        ),
    ),
    (
        "OBJ.02",
        "Fix critical product vulnerabilities within 30 days",
        "in_progress",
        "at_risk",
        -150,
        60,
        90,
        None,
        ["ISS.01", "ISS.10"],
        ["Device firmware and signing keys"],
        ["PSIRT"],
        (
            "KPI: median fix time 47 days last quarter, held back by a Lookout v1 "
            "chipset SDK fix from Orbisil Semiconductors."
        ),
    ),
    (
        "OBJ.03",
        f"Pass PCI DSS 4.0.1 for {PAY_ENTITY} with no compensating controls",
        "in_progress",
        "on_track",
        -200,
        110,
        120,
        None,
        ["ISS.03", "ISS.04"],
        ["Store checkout and payments"],
        ["Payments Risk", "Store Engineering"],
        "KPI: open PCI findings at zero by the QSA fieldwork date.",
    ),
    (
        "OBJ.04",
        "Report significant incidents within 24 hours, as NIS2 requires",
        "in_progress",
        "at_risk",
        -150,
        60,
        90,
        None,
        ["ISS.02", "ISS.08"],
        [],
        ["Security Operations Centre"],
        "KPI: median time from detection to early warning below 12 hours.",
    ),
    (
        "OBJ.05",
        "Complete IT/OT segmentation at the Brno plant",
        "draft",
        "--",
        60,
        330,
        365,
        None,
        ["ISS.08", "ISS.09"],
        ["Production line control", "Plant SCADA server", "Assembly cell PLCs"],
        ["OT Engineering"],
        (
            "KPI: zero IT-to-OT flows outside the conduit firewall, per IEC 62443 "
            "zones and conduits."
        ),
    ),
    (
        "OBJ.06",
        "Restart the Brno assembly line within 8 hours of a ransomware event",
        "in_progress",
        "off_track",
        -180,
        150,
        180,
        None,
        ["ISS.08", "ISS.14"],
        ["Production line control", "Plant SCADA server"],
        ["OT Engineering", "IT Operations"],
        "KPI: the last restore rehearsal took 13h 20m against an 8h target.",
    ),
    (
        "OBJ.07",
        "Keep ISO 27001 certification through the 2027 recertification",
        "in_progress",
        "on_track",
        -90,
        250,
        270,
        None,
        ["ISS.02", "ISS.12"],
        [],
        ["GRC Office"],
        (
            "KPI: no major nonconformity at the Vantor Legal & Audit surveillance "
            "and recertification audits."
        ),
    ),
    (
        "OBJ.08",
        "Publish a coordinated vulnerability disclosure policy for products",
        "achieved",
        "on_track",
        -240,
        -40,
        -30,
        -35,
        ["ISS.01", "ISS.06"],
        [],
        ["PSIRT"],
        (
            "KPI: security.txt live on every product domain and reports "
            "acknowledged within 5 working days."
        ),
    ),
    (
        "OBJ.09",
        "Raise phishing reporting above 60% of staff",
        "in_progress",
        "on_track",
        -60,
        120,
        180,
        None,
        ["ISS.11"],
        [],
        ["People & Culture", "GRC Office"],
        "KPI: report rate measured on each quarterly simulation, per site.",
    ),
    (
        "OBJ.10",
        "Enforce phishing-resistant MFA for every workforce account",
        "degraded",
        "at_risk",
        -300,
        -20,
        30,
        None,
        ["ISS.08", "ISS.12"],
        ["Workforce identity provider", "Corporate VPN gateway"],
        ["IT Operations"],
        "KPI: 94% enrolled; shared plant kiosks and the Eindhoven tenant lag behind.",
    ),
    (
        "OBJ.11",
        "Keep IT security spend within 7% of the IT budget",
        "deprecated",
        "--",
        -700,
        -200,
        -180,
        -150,
        ["ISS.13"],
        [],
        [],
        "Replaced by the risk-based budget model adopted in 2026.",
    ),
]

LABELS = [
    "pci-dss",
    "dora",
    "nis2",
    "gdpr",
    "cra",
    "iec-62443",
    "crown-jewel",
    "ot",
    "cloud",
    "retail-partner",
    "board-reporting",
    "quick-win",
]

# Which labels go on which core objects (assets by name, controls by ref_id,
# risk scenarios by ref_id).
ASSET_LABELS = {
    "Store checkout and payments": ["pci-dss", "dora", "crown-jewel"],
    "Customer and device accounts": ["gdpr", "crown-jewel"],
    "Device firmware and signing keys": ["cra", "crown-jewel"],
    "Production line control": ["ot", "iec-62443", "nis2"],
    "Product designs and source code": ["crown-jewel"],
    "Device cloud Kubernetes cluster": ["cloud", "nis2"],
    "PostgreSQL primary": ["gdpr", "cloud"],
    "S3 evidence bucket": ["cloud"],
    "Workforce identity provider": ["cloud", "nis2"],
    "Firmware signing HSM": ["cra", "crown-jewel"],
    "MQTT device gateway": ["cloud", "cra"],
    "Online store web front": ["pci-dss"],
    "Companion mobile app": ["gdpr", "cra"],
    "Plant SCADA server": ["ot", "iec-62443"],
    "Assembly cell PLCs": ["ot", "iec-62443"],
}
CONTROL_LABELS = {
    "AC.001": ["pci-dss", "nis2"],
    "AC.002": ["pci-dss"],
    "AC.004": ["nis2", "dora"],
    "AC.005": ["quick-win"],
    "AC.007": ["ot", "iec-62443"],
    "AC.008": ["nis2", "board-reporting"],
    "AC.010": ["cra", "retail-partner"],
    "AC.011": ["gdpr"],
    "AC.013": ["cra"],
    "AC.014": ["cra"],
    "AC.015": ["cra", "retail-partner"],
    "AC.016": ["pci-dss"],
    "AC.017": ["ot", "iec-62443"],
    "AC.018": ["cra", "retail-partner", "quick-win"],
}
SCENARIO_LABELS = {
    "RS.01": ["board-reporting", "ot"],
    "RS.02": ["gdpr"],
    "RS.03": ["crown-jewel"],
    "RS.04": ["cra"],
    "RS.05": ["gdpr", "cloud"],
    "RS.07": ["cra", "board-reporting", "crown-jewel"],
    "RS.08": ["ot", "iec-62443"],
    "RS.09": ["pci-dss"],
}

# Commitment cycles per control ref_id, oldest first:
# (state, committed eta offset, note, committed-at offset in days before the stamp base).
# Every note is unique: it is the stamp order.
COMMITMENTS = {
    "AC.001": [
        (
            "committed",
            30,
            "Committed to the NIS2 supervisor for the Q2 access review window.",
            12,
        )
    ],
    "AC.002": [
        (
            "in_negotiation",
            None,
            (
                "Waiting for the privileged access licence quote from Brightline "
                "Identity before committing to a date."
            ),
            None,
        )
    ],
    "AC.003": [
        (
            "fulfilled",
            -25,
            "Device cloud restore test passed; evidence filed for the ISO auditor.",
            60,
        )
    ],
    "AC.004": [
        (
            "committed",
            15,
            (
                "Questionnaire promised to the DORA register owner for Pellion "
                "Payments and Kestrava Cloud first."
            ),
            70,
        ),
        (
            "in_negotiation",
            15,
            (
                "Procurement asked to fold the questionnaire into contract renewals: "
                "renegotiating."
            ),
            None,
        ),
    ],
    "AC.007": [
        (
            "declined",
            None,
            "Cannot commit before the Brno line-1 shutdown is scheduled.",
            None,
        )
    ],
    "AC.010": [
        (
            "committed",
            -10,
            (
                "Promised two retail partners to acknowledge vulnerability reports "
                "within 5 working days."
            ),
            90,
        ),
        (
            "fulfilled",
            -10,
            (
                "Acknowledgement target met on every report for two quarters; retail "
                "partners informed."
            ),
            5,
        ),
    ],
    "AC.013": [
        (
            "in_negotiation",
            None,
            (
                "Signing key rotation date under negotiation with Shenwa Contract "
                "Manufacturing, who inject device keys at the factory."
            ),
            None,
        )
    ],
    "AC.014": [
        (
            "committed",
            45,
            "Staged OTA rollout committed in the Keystone hub v3 launch plan.",
            20,
        )
    ],
    "AC.015": [
        (
            "committed",
            120,
            (
                "SBOM with every release promised to retail partners ahead of the CRA "
                "deadline."
            ),
            30,
        )
    ],
    "AC.016": [
        (
            "committed",
            60,
            (
                "Cardholder data environment segmentation retest promised to the QSA "
                "before fieldwork."
            ),
            25,
        )
    ],
    "AC.018": [
        (
            "fulfilled",
            -60,
            (
                "Unique per-device credentials shipped on every Lookout and Kelvin "
                "line; retail partner checklist closed."
            ),
            100,
        )
    ],
}

# Campaign: name, status, start, due, {perimeter ref_id: share of requirements
# answered}, ref prefix, framework library URN (None = the core ISO 27001
# framework), description.
CAMPAIGNS = [
    (
        "2026 internal ISMS audit programme",
        "in_progress",
        -45,
        75,
        {"PER.001": 0.5, "PER.002": 0.15},
        "CMP26",
        None,
        (
            "Annual internal audit of the device cloud and the online store "
            "against ISO 27001, ahead of the surveillance audit."
        ),
    ),
]
CAMPAIGN_TEAMS = {
    "PER.001": "Cloud Platform",
    "PER.002": "Store Engineering",
    "PER.003": "OT Engineering",
    "PER.004": "Firmware Engineering",
}

# Assignments on the audits the compliance builder seeds, keyed by audit ref_id:
# (team, status, parent requirement ref_ids or None for the whole audit).
# Statuses are distinct per audit: (audit name, status) is the stamp order.
ISO_CLAUSES = ["4", "5", "6", "6.1", "7", "7.5", "8", "9", "9.2", "9.3", "10"]
AUDIT_ASSIGNMENTS = {
    "AUD.2026.01": [
        ("GRC Office", "submitted", [*ISO_CLAUSES, "A.5"]),
        ("People & Culture", "closed", ["A.6"]),
        ("Facilities & Site Security", "changes_requested", ["A.7"]),
        ("Cloud Platform", "in_progress", ["A.8"]),
    ],
    "AUD.2026.03": [("Payments Risk", "in_progress", None)],
    "AUD.2026.04": [("OT Engineering", "submitted", None)],
    "AUD.2026.05": [("PSIRT", "in_progress", None)],
    "AUD.2026.06": [("GRC Office", "closed", None)],
    "AUD.2026.07": [("IT Operations", "draft", None)],
}

CRA_AUDIT = (
    "AUD.2026.CRA",
    "CRA maturity self-assessment — Lookout camera range",
)
# Per top-level CRA domain: team answering it, assignment status, maturity
# levels given (one per requirement, None = left unanswered).
CRA_SECTIONS = {
    "1": ("GRC Office", "closed", [3, 4, 2, 3, 3]),
    "2": ("Firmware Engineering", "submitted", [2, 3, 2, 3, 2]),
    "3": ("PSIRT", "in_progress", [3, 2, None, None, None]),
    "4": ("Cloud Platform", "changes_requested", [2, 1, 2, 2, 1]),
    "5": ("People & Culture", "draft", [None, None, None, None, None]),
}

# ref_id, name, description, levels: (name, abbreviation, rank, colour, description).
CLASSIFICATIONS = [
    (
        "HIC",
        f"{COMPANY} information classification",
        (
            "Corporate scheme from the information handling policy, applied to "
            "documents, repositories and assets."
        ),
        [
            ("Public", "PUB", 0, "#2E7D32", "Approved for publication."),
            (
                "Internal",
                "INT",
                1,
                "#1565C0",
                "Staff and contractors under NDA.",
            ),
            (
                "Confidential",
                "CONF",
                2,
                "#EF6C00",
                (
                    "Named teams only; encrypted at rest. Unreleased roadmaps, "
                    "supplier contracts, audit reports."
                ),
            ),
            (
                "Restricted",
                "RESTR",
                3,
                "#C62828",
                (
                    "Named individuals; logged access. Firmware signing keys, "
                    "unreleased product designs, embargoed vulnerabilities."
                ),
            ),
        ],
    ),
    (
        "PDS",
        "Personal data sensitivity",
        "Used by the Data Protection Office to scope DPIAs and transfer assessments.",
        [
            ("No personal data", "NONE", 0, "#9E9E9E", "Aggregated or anonymised."),
            (
                "Personal data",
                "PD",
                1,
                "#F9A825",
                "GDPR article 4 personal data: accounts, orders, support tickets.",
            ),
            (
                "Home activity data",
                "HOME",
                2,
                "#AD1457",
                (
                    "Lookout video and audio, Kelvin occupancy and energy usage: "
                    "reveals life inside the home."
                ),
            ),
            (
                "Special category",
                "SPECIAL",
                3,
                "#6A1B9A",
                "GDPR article 9 data: health, biometrics, union membership.",
            ),
        ],
    ),
    (
        "PCI",
        f"{PAY_ENTITY} payment data classification",
        (
            "PCI DSS scoping of systems and data for the store checkout and "
            "instalment payments."
        ),
        [
            (
                "Out of scope",
                "OOS",
                0,
                "#9E9E9E",
                "No connection to the cardholder data environment.",
            ),
            (
                "Connected to the CDE",
                "CONN",
                1,
                "#1565C0",
                (
                    "Security-impacting or connected systems: identity, logging, "
                    "jump hosts."
                ),
            ),
            (
                "Cardholder data",
                "CHD",
                2,
                "#EF6C00",
                "Primary account numbers, tokenised or truncated outside the CDE.",
            ),
            (
                "Sensitive authentication data",
                "SAD",
                3,
                "#C62828",
                "Never stored after authorisation.",
            ),
        ],
    ),
]

# Requests per form. Answers are keyed by the URN tail after the form's page prefix.
# status, resolution, started / submitted offsets (days before the stamp base),
# due offset, observation, answers.
DEROGATION_REQUESTS = [
    (
        "closed",
        "accepted",
        40,
        38,
        -10,
        (
            "Accepted until Kelvin gen-1 end of support; the PSIRT reviews it each "
            "quarter."
        ),
        {
            "request:question:subject": "Kelvin gen-1 thermostats stay on the "
            "legacy firmware signing key",
            "request:question:control": "AC.013 Firmware code signing",
            "request:question:scope": "Kelvin gen-1, about 62,000 devices in the field",
            "request:question:justification": "The gen-1 bootloader cannot verify "
            "the new ECDSA key, and re-flashing it needs a technician visit.",
            "risk:question:severity": "high",
            "risk:question:expires_on": 240,
            "mitigation:question:has_compensating": True,
            "mitigation:question:compensating_control": "Legacy key moved into the "
            "firmware signing HSM under dual control; gen-1 builds signed for "
            "security fixes only.",
        },
    ),
    (
        "closed",
        "rejected",
        30,
        29,
        -5,
        (
            "Rejected: IEC 62443 SR 1.1 requires individual accounts; badge-tap "
            "login offered instead."
        ),
        {
            "request:question:subject": "Shared operator account on the Brno "
            "line-2 HMI",
            "request:question:control": "AC.017 PLC change management",
            "request:question:scope": "Line-2 HMI panels, three shifts",
            "request:question:justification": "Operators change every shift and "
            "individual logins slow down the line restart.",
            "risk:question:severity": "critical",
            "risk:question:expires_on": 365,
            "mitigation:question:has_compensating": False,
            "mitigation:question:compensating_plan": "None proposed.",
        },
    ),
    (
        "closed",
        "accepted",
        25,
        24,
        -15,
        "Accepted through the seasonal change freeze only; WAF rule reviewed weekly.",
        {
            "request:question:subject": "Delay a CMS plugin patch on the store "
            "web front during the peak season freeze",
            "request:question:control": "AC.010 Vulnerability handling and disclosure",
            "request:question:scope": "Online store web front, product pages only",
            "request:question:justification": "The patch changes the page "
            "templates and cannot be regression-tested before the freeze ends.",
            "risk:question:severity": "medium",
            "risk:question:expires_on": 30,
            "mitigation:question:has_compensating": True,
            "mitigation:question:compensating_control": "Virtual patch on the WAF "
            "and the plugin endpoint blocked outside the admin network.",
        },
    ),
    (
        "in_review",
        "",
        12,
        10,
        8,
        None,
        {
            "request:question:subject": "No EDR agent on the Brno line-3 HMI stations",
            "request:question:control": "ISO 27001 A.8.7 Protection against malware",
            "request:question:scope": "Six Windows 10 IoT HMI stations on line 3",
            "request:question:justification": "Linterra Automation voids support "
            "if third-party agents are installed.",
            "risk:question:severity": "medium",
            "risk:question:expires_on": 300,
            "mitigation:question:has_compensating": False,
            "mitigation:question:compensating_plan": "Application allow-listing "
            "and USB lockdown by the end of the quarter.",
        },
    ),
    (
        "in_review",
        "",
        9,
        7,
        5,
        None,
        {
            "request:question:subject": "Lookout v1 cameras miss the 30-day "
            "critical fix target",
            "request:question:control": "AC.010 Vulnerability handling and disclosure",
            "request:question:scope": "Lookout v1 indoor cameras built by Shenwa "
            "Contract Manufacturing, about 41,000 units",
            "request:question:justification": "The fix depends on a chipset SDK "
            "release from Orbisil Semiconductors expected in ten weeks.",
            "risk:question:severity": "high",
            "risk:question:expires_on": 75,
            "mitigation:question:has_compensating": False,
            "mitigation:question:compensating_plan": "Disable UPnP port mapping "
            "by configuration push and publish a security advisory.",
        },
    ),
    (
        "submitted",
        "",
        4,
        3,
        12,
        None,
        {
            "request:question:subject": "Static API key for the Tallbridge "
            "Logistics label integration",
            "request:question:scope": "Order fulfilment to the carrier label API",
            "request:question:justification": "The carrier API has no OAuth "
            "support until their next major release.",
            "risk:question:severity": "low",
            "risk:question:expires_on": 150,
            "mitigation:question:has_compensating": True,
            "mitigation:question:compensating_control": "Key scoped to label "
            "creation, kept in the secrets vault, rotated quarterly; egress "
            "limited to the carrier's address range.",
        },
    ),
    (
        "draft",
        "",
        1,
        None,
        None,
        None,
        {
            "request:question:subject": "Extend the log retention exemption for "
            "the Keystone v1 telemetry cluster",
            "request:question:justification": "The cluster is decommissioned once "
            "the last v1 hubs migrate to the device cloud.",
        },
    ),
]

VENDOR_REQUESTS = [
    (
        "closed",
        "accepted",
        50,
        48,
        -20,
        "Full assessment launched in TPRM; added to the DORA register.",
        {
            "vendor:question:vendor_name": "Ostrel Tokenisation",
            "vendor:question:service": "Network tokens for instalment payments "
            f"at {PAY_ENTITY}",
            "vendor:question:already_used": False,
            "vendor:question:website": "ostrel.example",
            "exposure:question:hosting_model": "saas",
            "exposure:question:data_location": "eu",
            "exposure:question:data_types": ["financial", "personal"],
            "exposure:question:access": ["production"],
            "dependency:question:business_impact": "cannot_operate",
            "dependency:question:alternatives": False,
            "dependency:question:needed_by": -15,
        },
    ),
    (
        "closed",
        "rejected",
        35,
        33,
        -10,
        (
            "Rejected: source code access is not justified; the Redhaven Security "
            "contract already covers product testing."
        ),
        {
            "vendor:question:vendor_name": "Brisk Crowdtest",
            "vendor:question:service": "Crowdsourced beta testing of the companion app",
            "vendor:question:already_used": False,
            "vendor:question:website": "briskcrowdtest.example",
            "exposure:question:hosting_model": "saas",
            "exposure:question:data_location": "elsewhere",
            "exposure:question:data_types": ["personal", "credentials"],
            "exposure:question:access": ["source_code", "production"],
            "dependency:question:business_impact": "negligible",
            "dependency:question:alternatives": True,
            "dependency:question:needed_by": -5,
        },
    ),
    (
        "in_review",
        "",
        14,
        12,
        6,
        None,
        {
            "vendor:question:vendor_name": "Lumetric Vision",
            "vendor:question:service": "Cloud person detection on Lookout video clips",
            "vendor:question:already_used": False,
            "vendor:question:website": "lumetric.example",
            "exposure:question:hosting_model": "paas_iaas",
            "exposure:question:data_location": "unknown",
            "exposure:question:data_types": ["personal", "sensitive"],
            "exposure:question:access": ["production"],
            "dependency:question:business_impact": "major",
            "dependency:question:alternatives": True,
            "dependency:question:needed_by": 45,
        },
    ),
    (
        "submitted",
        "",
        6,
        5,
        10,
        None,
        {
            "vendor:question:vendor_name": "Talvi Translations",
            "vendor:question:service": "Translation of product manuals and the "
            "companion app",
            "vendor:question:already_used": True,
            "exposure:question:hosting_model": "saas",
            "exposure:question:data_location": "adequacy",
            "exposure:question:data_types": ["internal"],
            "exposure:question:access": ["none"],
            "dependency:question:business_impact": "negligible",
            "dependency:question:alternatives": True,
            "dependency:question:needed_by": 20,
        },
    ),
    (
        "draft",
        "",
        2,
        None,
        None,
        None,
        {
            "vendor:question:vendor_name": "Morava Robotics",
            "vendor:question:service": "Remote maintenance of the Brno "
            "palletising robots",
            "vendor:question:already_used": False,
            "exposure:question:hosting_model": "on_premises",
            "exposure:question:access": ["network"],
        },
    ),
]

PUBLICATIONS = [
    (
        "urn:intuitem:risk:quick_form:derogation-request",
        "Request a security derogation",
        (
            "Ask for a time-boxed exemption from a control or policy, on corporate "
            "IT, the plant or a product line."
        ),
        "fa-solid fa-scale-unbalanced",
        0,
        DEROGATION_REQUESTS,
    ),
    (
        "urn:intuitem:risk:quick_form:vendor-review-request",
        "Request a vendor review",
        (
            "Before signing with a new supplier, tell Procurement and the GRC Office "
            "what they will touch."
        ),
        "fa-solid fa-handshake",
        1,
        VENDOR_REQUESTS,
    ),
]


def _subdomain(ctx, name):
    if name is None:
        return ctx.domain
    return (
        Folder.objects.filter(name=name, parent_folder=ctx.domain).first() or ctx.domain
    )


def _team_actors(ctx):
    return {
        actor.team.name: actor
        for actor in Actor.objects.filter(
            team__folder__in=ctx.folders(), team__name__in=[t[0] for t in TEAMS]
        ).select_related("team")
    }


@register
class GovernanceBuilder(DemoBuilder):
    """ISMS context, teams, labels, commitments, campaigns and assignments."""

    name = "governance"
    feature_flags = ("commitment_management",)
    depends = ("core", "compliance", "risk")
    libraries = (CRA_LIBRARY,)
    covers: ClassVar[dict] = {
        Team: "folder",
        OrganisationIssue: "folder",
        OrganisationObjective: "folder",
        FilteringLabel: "folder",
        Commitment: "folder",
        Campaign: "folder",
        RequirementAssignment: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (Team, {"folder__in": folders}, ("name",)),
            (OrganisationIssue, {"folder__in": folders}, ("ref_id",)),
            (OrganisationObjective, {"folder__in": folders}, ("ref_id",)),
            (FilteringLabel, {"folder": ctx.domain}, ("label",)),
            (Commitment, {"folder__in": folders}, ("notes",)),
            (Campaign, {"folder": ctx.domain}, ("name",)),
            (
                RequirementAssignment,
                {"folder__in": folders},
                ("compliance_assessment__name", "status"),
            ),
            (
                Answer,
                {"requirement_assessment__compliance_assessment__ref_id": CRA_AUDIT[0]},
                ("question__urn",),
            ),
        ]

    def build(self, ctx):
        self.build_teams(ctx)
        actors = _team_actors(ctx)
        issues = self.build_issues(ctx)
        self.build_objectives(ctx, issues, actors)
        self.build_labels(ctx)
        self.build_commitments(ctx)
        self.build_campaigns(ctx, actors)
        self.build_audit_assignments(ctx, actors)
        self.build_cra_audit(ctx, actors)

    def build_teams(self, ctx):
        for name, subdomain, mailbox, description in TEAMS:
            Team.objects.get_or_create(
                name=name,
                folder=_subdomain(ctx, subdomain),
                defaults={
                    "description": description,
                    "team_email": f"{mailbox}@{MAIL_DOMAIN}",
                },
            )

    def build_issues(self, ctx):
        assets = {a.name: a for a in ctx.refs["assets"]}
        issues = {}
        for (
            ref_id,
            name,
            category,
            origin,
            status,
            start,
            expiry,
            asset_names,
            description,
        ) in ISSUES:
            issue, created = OrganisationIssue.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "category": category,
                    "origin": origin,
                    "status": status,
                    "description": description,
                    "start_date": ctx.day(start),
                    "expiration_date": ctx.day(expiry) if expiry is not None else None,
                },
            )
            if created:
                issue.assets.set([assets[n] for n in asset_names if n in assets])
            issues[ref_id] = issue
        return issues

    def build_objectives(self, ctx, issues, actors):
        assets = {a.name: a for a in ctx.refs["assets"]}
        for (
            ref_id,
            name,
            status,
            health,
            start,
            eta,
            due,
            closing,
            issue_refs,
            asset_names,
            team_names,
            description,
        ) in OBJECTIVES:
            objective, created = OrganisationObjective.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "ref_id": ref_id,
                    "status": status,
                    "health": health,
                    "description": description,
                    "is_active": status != "deprecated",
                    "start_date": ctx.day(start),
                    "eta": ctx.day(eta),
                    "due_date": ctx.day(due),
                    "closing_date": ctx.day(closing) if closing is not None else None,
                },
            )
            if created:
                objective.issues.set([issues[r] for r in issue_refs])
                objective.assets.set([assets[n] for n in asset_names if n in assets])
                objective.assigned_to.set([actors[t] for t in team_names])

    def build_labels(self, ctx):
        labels = {}
        for label in LABELS:
            labels[label], _ = FilteringLabel.objects.get_or_create(
                label=label, folder=ctx.domain
            )
        # add() is a no-op for a label already there, so reseeding is idempotent
        # and a label a user removed is not resurrected unless reseeded.
        targets = (
            ({a.name: a for a in ctx.refs["assets"]}, ASSET_LABELS),
            ({c.ref_id: c for c in ctx.refs["controls"]}, CONTROL_LABELS),
            (
                {s.ref_id: s for s in ctx.refs.get("risk_scenarios", [])},
                SCENARIO_LABELS,
            ),
        )
        for objects, mapping in targets:
            for key, names in mapping.items():
                if key in objects:
                    objects[key].filtering_labels.add(*(labels[n] for n in names))

    def build_commitments(self, ctx):
        """Cycles written as `core.commitment.apply_transition` leaves them.

        Written directly rather than replayed: `committed_at` is the wall clock
        there, and the demo needs it pinned.
        """
        content_type = ContentType.objects.get_for_model(AppliedControl)
        controls = {c.ref_id: c for c in ctx.refs["controls"]}
        for ref_id, cycles in COMMITMENTS.items():
            control = controls.get(ref_id)
            if (
                control is None
                or Commitment.objects.filter(
                    content_type=content_type, object_id=control.pk
                ).exists()
            ):
                continue
            for index, (state, eta, notes, committed_days) in enumerate(cycles):
                Commitment.objects.create(
                    target=control,
                    state=state,
                    committed_eta=ctx.day(eta) if eta is not None else None,
                    committed_at=ctx.timestamp_base - timedelta(days=committed_days)
                    if committed_days is not None
                    else None,
                    notes=notes,
                    is_current=index == len(cycles) - 1,
                )

    def build_campaigns(self, ctx, actors):
        from core.views import CampaignViewSet

        perimeters = {p.ref_id: p for p in Perimeter.objects.filter(folder=ctx.domain)}
        for (
            name,
            status,
            start,
            due,
            shares,
            prefix,
            library_urn,
            description,
        ) in CAMPAIGNS:
            if library_urn is None:
                framework = ctx.refs.get("framework")
            else:
                framework = Framework.objects.filter(library__urn=library_urn).first()
            if framework is None:
                ctx.err(f"framework for campaign {name!r} not loaded, skipping")
                continue
            campaign, created = Campaign.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "kind": Campaign.Kind.INTERNAL,
                    "status": Campaign.Status.DRAFT,
                    "description": description,
                    "start_date": ctx.day(start),
                    "due_date": ctx.day(due),
                },
            )
            if not created:
                continue
            campaign.frameworks.set([framework])
            campaign.perimeters.set([perimeters[r] for r in shares])
            # The app launches a campaign on create: one audit per perimeter and
            # framework, wired to the perimeter's assignees (none in the demo).
            CampaignViewSet()._launch_internal(campaign, campaign.frameworks.all())
            for audit in ComplianceAssessment.objects.filter(
                campaign=campaign
            ).select_related("perimeter"):
                audit.ref_id = f"{prefix}.{audit.perimeter.ref_id}"
                audit.save(update_fields=["ref_id"])
                team = actors[CAMPAIGN_TEAMS[audit.perimeter.ref_id]]
                audit.authors.set([team])
                assignment = assign_audit_to(audit, [team])
                if status == Campaign.Status.IN_PROGRESS:
                    # What "Start the campaign" does.
                    assignment.status = RequirementAssignment.Status.IN_PROGRESS
                    assignment.save(update_fields=["status"])
                    audit.status = ComplianceAssessment.Status.IN_PROGRESS
                    audit.save(update_fields=["status"])
                    ComplianceBuilder.fill(audit, shares[audit.perimeter.ref_id])
            if status != Campaign.Status.DRAFT:
                campaign.status = status
                campaign.save(update_fields=["status"])

    def build_audit_assignments(self, ctx, actors):
        """Hand the compliance builder's audits to the teams answering them."""
        audits = {a.ref_id: a for a in ctx.refs.get("audits", [])}
        for ref_id, rows in AUDIT_ASSIGNMENTS.items():
            audit = audits.get(ref_id)
            if audit is None or audit.requirement_assignments.exists():
                continue
            assessments = list(
                RequirementAssessment.objects.filter(
                    compliance_assessment=audit, requirement__assessable=True
                ).select_related("requirement")
            )
            parents = dict(
                RequirementAssessment.objects.filter(
                    compliance_assessment=audit, requirement__assessable=False
                ).values_list("requirement__urn", "requirement__ref_id")
            )
            for team, status, sections in rows:
                members = [
                    ra
                    for ra in assessments
                    if sections is None
                    or parents.get(ra.requirement.parent_urn) in sections
                ]
                if not members:
                    continue
                assignment = RequirementAssignment.objects.create(
                    compliance_assessment=audit, folder=audit.folder, status=status
                )
                assignment.actor.set([actors[team]])
                assignment.requirement_assessments.set(members)

    def build_cra_audit(self, ctx, actors):
        framework = Framework.objects.filter(
            urn="urn:intuitem:risk:framework:enisa-sme-cra-maturity"
        ).first()
        if framework is None:
            ctx.err("ENISA CRA maturity framework not loaded, skipping")
            return
        ref_id, name = CRA_AUDIT
        audit, created = ComplianceAssessment.objects.get_or_create(
            name=name,
            folder=ctx.domain,
            defaults={
                "framework": framework,
                "ref_id": ref_id,
                "status": ComplianceAssessment.Status.IN_PROGRESS,
                "due_date": ctx.day(70),
                "field_visibility": build_initial_field_visibility(framework),
                "description": "Self-check of the Lookout camera range against "
                "the ENISA SME CRA maturity model before the December 2027 "
                "deadline.",
            },
        )
        if not created:
            return
        audit.create_requirement_assessments()
        assessments = list(
            RequirementAssessment.objects.filter(compliance_assessment=audit)
            .select_related("requirement")
            .order_by("requirement__order_id")
        )
        sections = {
            ra.requirement.urn: ra.requirement.ref_id
            for ra in assessments
            if not ra.requirement.assessable
        }
        for section, (team, status, levels) in CRA_SECTIONS.items():
            members = [
                ra
                for ra in assessments
                if ra.requirement.assessable
                and sections.get(ra.requirement.parent_urn) == section
            ]
            if not members:
                continue
            assignment = RequirementAssignment.objects.create(
                compliance_assessment=audit, folder=audit.folder, status=status
            )
            assignment.actor.set([actors[team]])
            assignment.requirement_assessments.set(members)
            for ra, level in zip(members, levels):
                if level is not None:
                    self.answer_maturity(ra, level)
        audit.authors.set([actors["PSIRT"]])

    def answer_maturity(self, ra, level):
        """Pick maturity ``level`` on the requirement's question, as the audit
        form does: write the answer, then recompute score and result."""
        questions = {
            q.urn: q
            for q in Question.objects.filter(
                requirement_node=ra.requirement
            ).prefetch_related("choices")
        }
        answers = {}
        for urn, question in questions.items():
            choice = next(
                (c for c in question.choices.all() if c.urn.endswith(f":{level}")),
                None,
            )
            if choice is not None:
                answers[urn] = choice.urn
        apply_answers_dict("requirement_assessment", ra, questions, answers)
        ra.compute_score_and_result()
        ra.status = "done"
        ra.save(update_fields=["status"])


@register
class ClassificationBuilder(DemoBuilder):
    """The company's own classification schemes next to the built-in TLP."""

    name = "classification"
    depends = ("core",)
    covers: ClassVar[dict] = {
        ObjectClassification: "folder",
        ClassificationLevel: "folder",
    }

    def stamps(self, ctx):
        return [
            (ObjectClassification, {"folder": ctx.domain}, ("name",)),
            (
                ClassificationLevel,
                {"folder": ctx.domain},
                ("object_classification__name", "rank"),
            ),
        ]

    def build(self, ctx):
        for ref_id, name, description, levels in CLASSIFICATIONS:
            scheme, _ = ObjectClassification.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={"ref_id": ref_id, "description": description},
            )
            for level_name, abbreviation, rank, colour, level_desc in levels:
                # The level's folder follows its scheme on save.
                ClassificationLevel.objects.get_or_create(
                    object_classification=scheme,
                    abbreviation=abbreviation,
                    defaults={
                        "name": level_name,
                        "rank": rank,
                        "hexcolor": colour,
                        "description": level_desc,
                    },
                )


@register
class FormsBuilder(DemoBuilder):
    """Published quick forms and the requests filed through them."""

    name = "forms"
    feature_flags = ("quick_forms",)
    depends = ("core",)
    libraries = (DEROGATION_LIBRARY, VENDOR_REVIEW_LIBRARY)
    covers: ClassVar[dict] = {
        QuickFormPublication: "folder",
        QuickFormResponse: "folder",
        Answer: "folder",
    }

    def stamps(self, ctx):
        return [
            (QuickFormPublication, {"folder": ctx.domain}, ("name",)),
            (QuickFormResponse, {"folder": ctx.domain}, ("ref_id",)),
            (
                Answer,
                {"response__folder": ctx.domain},
                ("response__ref_id", "question__urn"),
            ),
        ]

    def build(self, ctx):
        # Teams come from the governance builder when it runs; requests are
        # simply left without respondents otherwise.
        actors = _team_actors(ctx)
        reviewers = [a for name, a in actors.items() if name == "GRC Office"]
        for urn, name, description, icon, order, requests in PUBLICATIONS:
            form = QuickForm.objects.filter(urn=urn).first()
            if form is None:
                ctx.err(f"quick form {urn} not loaded, skipping")
                continue
            publication, created = QuickFormPublication.objects.get_or_create(
                name=name,
                folder=ctx.domain,
                defaults={
                    "quick_form": form,
                    "description": description,
                    "icon": icon,
                    "order": order,
                },
            )
            if created:
                publication.default_reviewers.set(reviewers)
            self.build_requests(ctx, publication, requests, reviewers)

    def build_requests(self, ctx, publication, requests, reviewers):
        form = publication.quick_form
        questions = {
            q.urn: q
            for q in Question.objects.filter(page__quick_form=form).prefetch_related(
                "choices"
            )
        }
        title_urn = form.title_question_urn
        # Answers are keyed by the URN tail after "urn:intuitem:risk:qf_page:<form>".
        prefix = ":".join(title_urn.split(":")[:5])
        for (
            status,
            resolution,
            started,
            submitted,
            due,
            observation,
            answers,
        ) in requests:
            full = {}
            for tail, value in answers.items():
                urn = f"{prefix}:{tail}"
                question = questions.get(urn)
                if question is None:
                    continue
                if question.type in (
                    Question.Type.UNIQUE_CHOICE,
                    Question.Type.MULTIPLE_CHOICE,
                ):
                    values = value if isinstance(value, list) else [value]
                    urns = [f"{urn}:choice:{v}" for v in values]
                    value = urns if isinstance(value, list) else urns[0]
                elif question.type == Question.Type.DATE:
                    value = ctx.day(value).isoformat()
                full[urn] = value
            title = full[title_urn]
            response, created = QuickFormResponse.objects.get_or_create(
                name=title,
                quick_form=form,
                folder=publication.target_folder,
                defaults={
                    "publication": publication,
                    "started_at": ctx.timestamp_base - timedelta(days=started),
                    "due_date": ctx.day(due) if due is not None else None,
                },
            )
            if not created:
                continue
            response.reviewers.set(reviewers)
            # Filled while still a draft, as a requester would, so the title and
            # the score are computed by the form itself.
            response.seed_answers()
            apply_answers_dict("response", response, questions, full)
            response.refresh_title_from_answers()
            if status != QuickFormResponse.Status.DRAFT:
                response.status = status
                response.resolution = resolution
                response.observation = observation
                response.submitted_at = ctx.timestamp_base - timedelta(days=submitted)
                response.save(
                    update_fields=[
                        "status",
                        "resolution",
                        "observation",
                        "submitted_at",
                    ]
                )
