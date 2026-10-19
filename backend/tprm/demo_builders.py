"""Third-party risk demo: the device maker's supplier and partner portfolio.

Cloud hosting, the card acquirer of the payments subsidiary, the contract
manufacturer and its sub-tier suppliers, the plant OT integrator, the analytics
SDK in the companion app and the rest of the vendor base, with their contacts,
solutions, subcontracting chains, contracts, external ratings, tier history and
assurance rounds. Seven rounds carry a Vendor Due Diligence questionnaire in the
vendor's enclave, built the way the API does.

The tier scale itself is not seeded: ``Tier.save`` pins every tier to the root
folder and startup creates the default four-level scale, which this builder
reads by key.
"""

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import ClassVar

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    Terminology,
)
from tprm.models import (
    Contract,
    Entity,
    EntityAssessment,
    EntityScore,
    EntityTierChange,
    Representative,
    Solution,
    SolutionSubcontractor,
    SolutionTierChange,
    Tier,
)
from tprm.services import create_enclave_audit
from tprm.tiers import set_entity_tier, set_solution_tier

VDD_LIBRARY = "urn:intuitem:risk:library:vendor-due-diligence"
VDD_FRAMEWORK = "urn:intuitem:risk:framework:vendor-due-diligence"

# Tier keys of the default scale, most critical first.
CRITICAL, IMPORTANT, STANDARD, LOW = "critical", "important", "standard", "low-impact"

# Contracts provided by (or to) the company itself use this pseudo-key.
MAIN = "main"

# key, ref_id, name, country, currency,
# relationship, description, mission, (dependency, penetration, maturity,
# trust), optional parent, DORA fields, legal identifiers, active flag.
ENTITIES = [
    {
        "key": "kestrava",
        "ref_id": "TP-001",
        "name": "Kestrava Cloud B.V.",
        "country": "NL",
        "currency": "EUR",
        "relationship": "supplier",
        "description": (
            "European IaaS and managed Kubernetes provider, three availability "
            "zones in Amsterdam."
        ),
        "mission": (
            "Hosts the device cloud (MQTT gateway, telemetry, OTA update service) "
            "and the online store; no tolerable outage beyond 4 hours."
        ),
        "levels": (4, 4, 3, 3),
        "dora_entity_hierarchy": "eba_RP:x210",
        "reference_link": "https://trust.kestrava.example",
        "legal_identifiers": {"LEI": "724500KESTRAVA0CLD01", "VAT": "NL859210374B01"},
    },
    {
        "key": "kestrava-de",
        "ref_id": "TP-001b",
        "name": "Kestrava Cloud Deutschland GmbH",
        "parent": "kestrava",
        "country": "DE",
        "currency": "EUR",
        "relationship": "supplier",
        "description": "German affiliate of Kestrava operating the Frankfurt region.",
        "mission": (
            "Runs the disaster-recovery region and the replicated PostgreSQL "
            "standby of the device cloud."
        ),
        "levels": (3, 2, 3, 3),
        "dora_entity_hierarchy": "eba_RP:x210",
    },
    {
        "key": "pellion",
        "ref_id": "TP-002",
        "name": "Pellion Payments SA",
        "country": "BE",
        "currency": "EUR",
        "relationship": "supplier",
        "description": (
            "Licensed card acquirer and processor: hosted payment fields, network "
            "tokens, settlement and instalment plans."
        ),
        "mission": (
            f"Authorises, tokenises and settles every card payment taken by "
            f"{PAY_ENTITY}. Supports a critical or important function under DORA."
        ),
        "levels": (4, 3, 4, 3),
        "dora_entity_type": "eba_CT:x300",
        "dora_entity_hierarchy": "eba_RP:x210",
        "dora_competent_authority": "National Bank of Belgium",
        "reference_link": "https://www.pellion.example/security",
        "legal_identifiers": {"LEI": "549300PELLIONPAY0021", "VAT": "BE0712345678"},
    },
    {
        "key": "shenwa",
        "ref_id": "TP-003",
        "name": "Shenwa Contract Manufacturing Co., Ltd.",
        "country": "CN",
        "currency": "USD",
        "relationship": "contractor",
        "description": (
            "Electronics contract manufacturer in Shenzhen building the Lookout "
            "camera range end to end."
        ),
        "mission": (
            "Holds camera board designs, runs the factory provisioning station that "
            "injects per-device credentials, and ships 40,000 cameras a month."
        ),
        "levels": (4, 3, 2, 2),
        "reference_link": "https://www.shenwa-cm.example",
    },
    {
        "key": "orbisil",
        "ref_id": "TP-004",
        "name": "Orbisil Semiconductors Ltd.",
        "country": "TW",
        "currency": "USD",
        "relationship": "supplier",
        "description": (
            "Fabless designer of the Wi-Fi 6 and Thread radio modules used in "
            "Kelvin, Lookout and Keystone devices, with their firmware SDK."
        ),
        "mission": (
            "Single source for the Thread radio module of the Keystone hub; the "
            "SDK is compiled into every firmware image."
        ),
        "levels": (4, 2, 4, 3),
    },
    {
        "key": "tallbridge",
        "ref_id": "TP-005",
        "name": "Tallbridge Logistics s.r.o.",
        "country": "CZ",
        "currency": "EUR",
        "relationship": "contractor",
        "description": "Parcel carrier and overflow warehousing next to the Brno plant.",
        "mission": (
            "Collects store orders from the Brno warehouse and receives delivery "
            "addresses and phone numbers through its shipping API."
        ),
        "levels": (3, 2, 3, 3),
    },
    {
        "key": "mireo",
        "ref_id": "TP-006",
        "name": "Mireo Support Lda.",
        "country": "PT",
        "currency": "EUR",
        "relationship": "contractor",
        "description": (
            "Outsourced customer support centre in Lisbon, tier-1 support in eight "
            "languages."
        ),
        "mission": (
            "Handles device support tickets; agents may view Lookout camera clips "
            "when a customer grants temporary access."
        ),
        "levels": (3, 3, 2, 3),
    },
    {
        "key": "brightline",
        "ref_id": "TP-007",
        "name": "Brightline Identity Oy",
        "country": "FI",
        "currency": "EUR",
        "relationship": "supplier",
        "description": "Workforce identity SaaS: single sign-on, MFA and lifecycle.",
        "mission": (
            "Behind the workforce identity provider: every staff login, including "
            "plant engineers and the firmware build farm, goes through it."
        ),
        "levels": (4, 3, 4, 3),
        "reference_link": "https://status.brightline-id.example",
    },
    {
        "key": "linterra",
        "ref_id": "TP-008",
        "name": "Linterra Automation GmbH",
        "country": "AT",
        "currency": "EUR",
        "relationship": "contractor",
        "description": (
            "Industrial automation integrator that built the Brno assembly lines; "
            "PLC/SCADA maintenance and on-call support."
        ),
        "mission": (
            "Has remote maintenance access to the plant SCADA server and the "
            "assembly cell PLCs; a compromise stops production."
        ),
        "levels": (4, 4, 2, 2),
    },
    {
        "key": "fennick",
        "ref_id": "TP-009",
        "name": "Fennick Analytics Ltd",
        "country": "IE",
        "currency": "EUR",
        "relationship": "supplier",
        "description": (
            "Product analytics SDK embedded in the companion app: funnels, crash "
            "reports and feature usage."
        ),
        "mission": (
            "Receives app events tied to device identifiers; the 2026 DPIA found "
            "location data collected before consent."
        ),
        "levels": (2, 3, 2, 1),
    },
    {
        "key": "quorra",
        "ref_id": "TP-010",
        "name": "Quorra Mail SAS",
        "country": "FR",
        "currency": "EUR",
        "relationship": "supplier",
        "description": "Transactional and marketing email platform.",
        "mission": (
            "Sends order confirmations, password resets, camera motion alerts and "
            "the newsletter; holds customer email addresses."
        ),
        "levels": (2, 2, 3, 3),
    },
    {
        "key": "redhaven",
        "ref_id": "TP-011",
        "name": "Redhaven Security BV",
        "country": "BE",
        "currency": "EUR",
        "relationship": "contractor",
        "description": "CREST-accredited penetration testing, hardware and red team.",
        "mission": (
            "Tests the online store, the device cloud APIs and device hardware "
            "before each product launch."
        ),
        "levels": (1, 3, 4, 4),
    },
    {
        "key": "vantor",
        "ref_id": "TP-012",
        "name": "Vantor Legal & Audit SAS",
        "country": "FR",
        "currency": "EUR",
        "relationship": "accreditation_authority",
        "description": "Accredited ISO 27001 certification body and PCI QSA firm.",
        "mission": (
            f"Runs the annual ISO 27001 surveillance audit and the PCI DSS "
            f"assessment of {PAY_ENTITY}; read-only access to evidence."
        ),
        "levels": (1, 2, 4, 4),
    },
    {
        "key": "huaxin",
        "ref_id": "TP-013",
        "name": "Huaxin PCB Assembly (Dongguan) Co., Ltd.",
        "country": "CN",
        "currency": "CNY",
        "relationship": "contractor",
        "description": "SMT board assembly subcontracted by Shenwa for camera mainboards.",
        "mission": (
            "Receives Lookout board Gerber files and bills of materials from Shenwa; "
            "no direct contract with the company."
        ),
        "levels": (3, 2, 2, 1),
    },
    {
        "key": "sentai",
        "ref_id": "TP-014",
        "name": "Sentai Wafer Foundry Corp.",
        "country": "TW",
        "currency": "USD",
        "relationship": "supplier",
        "description": "Foundry fabricating Orbisil's radio chipsets on a 22 nm process.",
        "mission": "Fourth-party supplier: a fab outage stops radio module supply.",
        "levels": (3, 1, 4, 3),
    },
    {
        "key": "portavia",
        "ref_id": "TP-015",
        "name": "Portavia Remote Access GmbH",
        "country": "DE",
        "currency": "EUR",
        "relationship": "supplier",
        "description": "Industrial remote access gateway used by Linterra's engineers.",
        "mission": (
            "Its cloud broker relays every Linterra maintenance session into the "
            "plant OT network."
        ),
        "levels": (3, 3, 3, 2),
    },
    {
        "key": "domora",
        "ref_id": "CL-001",
        "name": "Domora Retail SA",
        "country": "FR",
        "currency": "EUR",
        "relationship": "client",
        "description": "Consumer electronics retail chain, 210 stores in France and Belgium.",
        "mission": (
            "Largest retail partner: drop-ship orders flow from its web shop into "
            "order fulfilment through a partner API."
        ),
        "levels": (2, 2, 3, 3),
    },
    {
        "key": "huisplein",
        "ref_id": "CL-002",
        "name": "Huisplein Elektronica B.V.",
        "country": "NL",
        "currency": "EUR",
        "relationship": "partner",
        "description": "Dutch smart-home retailer and installer of Keystone hubs.",
        "mission": (
            "Installers pair devices for customers using a partner account in the "
            "companion app."
        ),
        "levels": (2, 2, 2, 3),
    },
    {
        "key": "pay",
        "ref_id": "GRP-001",
        "name": PAY_ENTITY,
        "parent": MAIN,
        "country": "FR",
        "currency": "EUR",
        "relationship": "other",
        "description": (
            f"Licensed payment institution and subsidiary of {COMPANY}: store "
            "checkout and instalment payments."
        ),
        "mission": (
            "Financial entity in DORA scope; keeps the register of information for "
            "its ICT third-party providers."
        ),
        "levels": (4, 4, 3, 4),
        "dora_entity_type": "eba_CT:x300",
        "dora_entity_hierarchy": "eba_RP:x56",
        "dora_competent_authority": "ACPR",
        "dora_assets_value": 48_500_000,
        "legal_identifiers": {"LEI": "969500HALVPAY0000042"},
    },
    {
        "key": "corvel",
        "ref_id": "TP-016",
        "name": "Corvel Fulfilment a.s.",
        "country": "CZ",
        "currency": "CZK",
        "relationship": "contractor",
        "description": "Former third-party fulfilment warehouse in Brno.",
        "mission": "Offboarded: fulfilment moved in-house and to Tallbridge.",
        "levels": (1, 1, 2, 2),
        "is_active": False,
    },
]

# Tier history per entity, oldest first: (days ago, tier key, note).
TIER_HISTORY = {
    "kestrava": [
        (-540, IMPORTANT, "Initial qualification: online store hosting only."),
        (
            -210,
            CRITICAL,
            "Device cloud migrated to Kestrava: every connected device depends on it.",
        ),
    ],
    "kestrava-de": [
        (-200, IMPORTANT, "DR region only; inherits the parent's controls.")
    ],
    "pellion": [
        (-720, CRITICAL, f"Sole acquirer of {PAY_ENTITY}; PCI DSS and DORA scope."),
    ],
    "shenwa": [
        (-800, IMPORTANT, "Second-source manufacturer for Lookout accessories."),
        (
            -400,
            CRITICAL,
            "Took over full Lookout production and per-device credential provisioning.",
        ),
    ],
    "orbisil": [
        (-650, STANDARD, "Radio modules dual-sourced at qualification."),
        (
            -120,
            IMPORTANT,
            "Thread module for Keystone hub v3 is single-sourced; 26-week lead time.",
        ),
    ],
    "tallbridge": [
        (-400, IMPORTANT, "Main carrier after Corvel's exit."),
        (-60, STANDARD, "Second carrier contracted; no longer single-sourced."),
    ],
    "mireo": [
        (-480, STANDARD, "Ticket handling only at onboarding."),
        (-150, IMPORTANT, "Agents granted consent-based access to camera clips."),
    ],
    "brightline": [
        (-600, IMPORTANT, "All workforce logins; break-glass accounts kept.")
    ],
    "linterra": [
        (-700, IMPORTANT, "Line integrator during commissioning."),
        (
            -95,
            CRITICAL,
            "Remote access review: vendor path reaches the assembly PLCs directly.",
        ),
    ],
    "fennick": [
        (-300, STANDARD, "Pseudonymised app events only."),
        (-75, IMPORTANT, "DPIA: device identifiers and location data in scope."),
    ],
    "quorra": [(-420, STANDARD, "Customer email addresses and alert content.")],
    "redhaven": [
        (-500, STANDARD, "Access to pre-production during engagements."),
        (-90, LOW, "Engagements now run on dedicated test tenants only."),
    ],
    "vantor": [(-380, LOW, "Read-only access to audit evidence.")],
    "huaxin": [(-390, IMPORTANT, "Holds camera board designs through Shenwa.")],
    "sentai": [(-120, STANDARD, "Fourth party; monitored through Orbisil.")],
    "portavia": [(-95, IMPORTANT, "Relays vendor sessions into the OT network.")],
    "domora": [(-300, STANDARD, "Partner API access to order fulfilment.")],
    "huisplein": [(-260, LOW, "Installer accounts with scoped permissions.")],
    "corvel": [
        (-1100, IMPORTANT, "Ran all store fulfilment from Brno."),
        (-200, None, "Contract terminated; tier cleared at offboarding."),
    ],
}

# entity key, first name, last name, role, phone.
REPRESENTATIVES = [
    ("kestrava", "Lotte", "van Dijk", "Customer success manager", "+31 20 555 0112"),
    ("kestrava", "Ruben", "Smit", "Head of security & compliance", "+31 20 555 0188"),
    (
        "kestrava-de",
        "Jana",
        "Koch",
        "Frankfurt region operations lead",
        "+49 69 5550 1142",
    ),
    ("pellion", "Sophie", "Lambert", "Account director", "+32 2 555 01 67"),
    (
        "pellion",
        "Thomas",
        "Claes",
        "PCI and DORA compliance officer",
        "+32 2 555 01 90",
    ),
    ("shenwa", "Wei", "Zhang", "Key account manager (Europe)", "+86 755 5550 1234"),
    ("shenwa", "Lina", "Chen", "Factory IT security manager", "+86 755 5550 1288"),
    ("orbisil", "Kevin", "Lin", "Field application engineer", "+886 3 555 0145"),
    ("orbisil", "Grace", "Huang", "Product security (PSIRT) lead", "+886 3 555 0177"),
    ("tallbridge", "Petr", "Novák", "Key account manager", "+420 5 5550 1210"),
    ("mireo", "Inês", "Ferreira", "Service delivery manager", "+351 21 555 0140"),
    ("mireo", "Tiago", "Costa", "Data protection officer", "+351 21 555 0177"),
    ("brightline", "Aino", "Virtanen", "Customer success manager", "+358 9 5550 1462"),
    ("brightline", "Mikko", "Laine", "Trust & security analyst", "+358 9 5550 1499"),
    ("linterra", "Stefan", "Gruber", "Service manager, Brno lines", "+43 1 555 0133"),
    ("linterra", "Martina", "Huber", "OT security engineer", "+43 1 555 0158"),
    ("fennick", "Ciara", "Walsh", "Customer success", "+353 1 555 0188"),
    ("fennick", "Declan", "Murphy", "Privacy counsel", "+353 1 555 0121"),
    ("quorra", "Julien", "Moreau", "Account manager", "+33 4 55 50 33 10"),
    ("redhaven", "Elise", "Peeters", "Engagement manager", "+32 9 555 01 33"),
    ("vantor", "Claire", "Dubois", "Lead auditor, ISO 27001", "+33 1 55 50 21 40"),
    ("vantor", "Hugo", "Lefebvre", "PCI QSA", "+33 1 55 50 21 77"),
    ("huaxin", "Jun", "Liu", "Quality manager", "+86 769 5550 1180"),
    ("portavia", "Lukas", "Becker", "Partner support engineer", "+49 89 5550 1290"),
    ("domora", "Nadia", "Benali", "Category manager, smart home", "+33 1 55 50 44 12"),
    ("huisplein", "Sanne", "Visser", "Installer network lead", "+31 30 555 0167"),
    ("pay", "Camille", "Rousseau", "Payments risk officer", "+33 4 55 50 10 20"),
]

EMAIL_DOMAINS = {
    "kestrava": "kestrava.example",
    "kestrava-de": "kestrava.example",
    "pellion": "pellion.example",
    "shenwa": "shenwa-cm.example",
    "orbisil": "orbisil.example",
    "tallbridge": "tallbridge.example",
    "mireo": "mireo-support.example",
    "brightline": "brightline-id.example",
    "linterra": "linterra.example",
    "fennick": "fennick.example",
    "quorra": "quorra-mail.example",
    "redhaven": "redhaven.example",
    "vantor": "vantor-audit.example",
    "huaxin": "huaxin-pcb.example",
    "portavia": "portavia.example",
    "domora": "domora.example",
    "huisplein": "huisplein.example",
    "pay": "example.com",
}

# ref_id, entity key, name, tier key, asset names, service type, data stored
# (storage country, processing country, sensitiveness), reliance,
# substitutability, exit plan, optional register-of-information fields.
SOLUTIONS = [
    {
        "ref_id": "SOL-001",
        "entity": "kestrava",
        "name": "Managed Kubernetes and PostgreSQL (Amsterdam)",
        "tier": CRITICAL,
        "assets": [
            "Device cloud Kubernetes cluster",
            "PostgreSQL primary",
            "MQTT device gateway",
        ],
        "service": "eba_TA:S18",
        "data": ("NL", "NL", "eba_ZZ:x793"),
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x960",
        "exit_plan": "eba_BT:x28",
        "non_substitutability_reason": "eba_ZZ:x964",
        "reintegration": "eba_ZZ:x967",
        "discontinuing_impact": "eba_ZZ:x793",
        "alternatives_identified": "eba_BT:x28",
        "alternatives": "Two EU IaaS providers shortlisted in the 2025 exit plan.",
        "description": (
            "Three-zone managed cluster running the device cloud, the MQTT gateway "
            "and managed PostgreSQL."
        ),
    },
    {
        "ref_id": "SOL-002",
        "entity": "kestrava",
        "name": "Object storage with object lock",
        "tier": IMPORTANT,
        "assets": ["S3 evidence bucket"],
        "service": "eba_TA:S17",
        "data": ("NL", "NL", "eba_ZZ:x792"),
        "reliance": "eba_ZZ:x796",
        "substitutability": "eba_ZZ:x961",
        "exit_plan": "eba_BT:x28",
        "description": "S3-compatible buckets for audit evidence and firmware artefacts.",
    },
    {
        "ref_id": "SOL-003",
        "entity": "kestrava",
        "name": "Online store hosting and CDN",
        "tier": CRITICAL,
        "assets": ["Online store web front"],
        "service": "eba_TA:S17",
        "data": ("NL", "NL", "eba_ZZ:x792"),
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x961",
        "exit_plan": "eba_BT:x28",
        "description": "Store web front, CDN and DDoS scrubbing for launch-day peaks.",
    },
    {
        "ref_id": "SOL-004",
        "entity": "kestrava-de",
        "name": "Disaster recovery region (Frankfurt)",
        "tier": IMPORTANT,
        "assets": ["PostgreSQL primary"],
        "service": "eba_TA:S17",
        "data": ("DE", "DE", "eba_ZZ:x793"),
        "reliance": "eba_ZZ:x796",
        "substitutability": "eba_ZZ:x961",
        "exit_plan": "eba_BT:x28",
        "description": "Warm standby cluster and streaming PostgreSQL replica.",
    },
    {
        "ref_id": "SOL-005",
        "entity": "pellion",
        "name": "Card acquiring, tokenisation and hosted payment fields",
        "tier": CRITICAL,
        "assets": ["Store checkout and payments"],
        "service": "eba_TA:S19",
        "data": ("BE", "BE", "eba_ZZ:x793"),
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x960",
        "exit_plan": "eba_BT:x28",
        "non_substitutability_reason": "eba_ZZ:x965",
        "reintegration": "eba_ZZ:x0",
        "discontinuing_impact": "eba_ZZ:x793",
        "alternatives_identified": "eba_BT:x28",
        "alternatives": "One alternative acquirer pre-qualified; 9-month migration.",
        "description": (
            "Hosted payment fields keep card data out of the store; network tokens "
            "and daily settlement files."
        ),
    },
    {
        "ref_id": "SOL-006",
        "entity": "pellion",
        "name": "Instalment payment processing",
        "tier": IMPORTANT,
        "assets": ["Store checkout and payments"],
        "service": "eba_TA:S19",
        "data": ("BE", "BE", "eba_ZZ:x793"),
        "reliance": "eba_ZZ:x796",
        "substitutability": "eba_ZZ:x961",
        "exit_plan": "eba_BT:x28",
        "discontinuing_impact": "eba_ZZ:x792",
        "alternatives_identified": "eba_BT:x21",
        "description": "Three- and ten-instalment plans with credit checks at checkout.",
    },
    {
        "ref_id": "SOL-007",
        "entity": "shenwa",
        "name": "Lookout camera contract manufacturing",
        "tier": CRITICAL,
        "assets": [
            "Product designs and source code",
            "Device firmware and signing keys",
        ],
        "service": "eba_TA:S12",
        "data": ("CN", "CN", "eba_ZZ:x793"),
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x960",
        "exit_plan": "eba_BT:x29",
        "description": (
            "Board assembly, final assembly and test, firmware flashing and "
            "per-device credential provisioning (AC.018)."
        ),
    },
    {
        "ref_id": "SOL-008",
        "entity": "orbisil",
        "name": "Wi-Fi and Thread radio modules with SDK",
        "tier": IMPORTANT,
        "assets": ["Device firmware and signing keys"],
        "service": "eba_TA:S12",
        "data": None,
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x959",
        "exit_plan": "eba_BT:x29",
        "description": (
            "Certified radio modules and the binary SDK compiled into Kelvin, "
            "Lookout and Keystone firmware; SBOM delivered per release."
        ),
    },
    {
        "ref_id": "SOL-009",
        "entity": "tallbridge",
        "name": "Parcel delivery and overflow warehousing",
        "tier": STANDARD,
        "assets": ["Order fulfilment"],
        "service": "",
        "data": None,
        "reliance": "eba_ZZ:x796",
        "substitutability": "eba_ZZ:x962",
        "description": "Next-day delivery in the EU, launch-peak storage, tracking API.",
    },
    {
        "ref_id": "SOL-010",
        "entity": "mireo",
        "name": "Tier-1 customer support desk",
        "tier": IMPORTANT,
        "assets": ["Customer and device accounts"],
        "service": "eba_TA:S03",
        "data": ("PT", "PT", "eba_ZZ:x793"),
        "reliance": "eba_ZZ:x796",
        "substitutability": "eba_ZZ:x961",
        "exit_plan": "eba_BT:x28",
        "description": (
            "Phone, chat and email support; consent-based camera clip viewing "
            "for troubleshooting."
        ),
    },
    {
        "ref_id": "SOL-011",
        "entity": "brightline",
        "name": "Workforce SSO and MFA",
        "tier": IMPORTANT,
        "assets": ["Workforce identity provider"],
        "service": "eba_TA:S19",
        "data": ("FI", "FI", "eba_ZZ:x792"),
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x961",
        "exit_plan": "eba_BT:x28",
        "description": "SAML/OIDC single sign-on, phishing-resistant MFA, joiner-leaver flows.",
    },
    {
        "ref_id": "SOL-012",
        "entity": "linterra",
        "name": "PLC and SCADA maintenance with remote support",
        "tier": CRITICAL,
        "assets": [
            "Production line control",
            "Plant SCADA server",
            "Assembly cell PLCs",
        ],
        "service": "eba_TA:S14",
        "data": None,
        "reliance": "eba_ZZ:x797",
        "substitutability": "eba_ZZ:x960",
        "exit_plan": "eba_BT:x29",
        "description": (
            "PLC program changes (AC.017), SCADA patching and 24/7 on-call through "
            "a brokered remote session."
        ),
    },
    {
        "ref_id": "SOL-013",
        "entity": "fennick",
        "name": "Companion app analytics SDK",
        "tier": IMPORTANT,
        "assets": ["Companion mobile app", "Customer and device accounts"],
        "service": "eba_TA:S06",
        "data": ("IE", "US", "eba_ZZ:x792"),
        "reliance": "eba_ZZ:x795",
        "substitutability": "eba_ZZ:x962",
        "description": "Event analytics and crash reporting in the iOS and Android apps.",
    },
    {
        "ref_id": "SOL-014",
        "entity": "quorra",
        "name": "Transactional and marketing email",
        "tier": STANDARD,
        "assets": ["Customer and device accounts"],
        "service": "eba_TA:S19",
        "data": ("FR", "FR", "eba_ZZ:x792"),
        "reliance": "eba_ZZ:x796",
        "substitutability": "eba_ZZ:x962",
        "description": "Order mails, password resets, camera alerts and newsletters.",
    },
    {
        "ref_id": "SOL-015",
        "entity": "redhaven",
        "name": "Penetration testing and red team",
        "tier": LOW,
        "assets": ["Online store web front", "Device cloud Kubernetes cluster"],
        "service": "eba_TA:S04",
        "data": None,
        "reliance": "eba_ZZ:x794",
        "substitutability": "eba_ZZ:x962",
        "description": "Pre-launch device and API tests, yearly red-team exercise.",
    },
    {
        "ref_id": "SOL-016",
        "entity": "vantor",
        "name": "ISO 27001 certification and PCI DSS assessment",
        "tier": LOW,
        "assets": [],
        "service": "",
        "data": None,
        "reliance": "eba_ZZ:x794",
        "substitutability": "eba_ZZ:x962",
        "description": "Surveillance and recertification audits, annual PCI QSA report.",
    },
    {
        "ref_id": "SOL-017",
        "entity": "corvel",
        "name": "Brno fulfilment warehouse",
        "tier": None,
        "active": False,
        "assets": ["Order fulfilment"],
        "service": "",
        "data": None,
        "reliance": "eba_ZZ:x794",
        "substitutability": "eba_ZZ:x962",
        "description": "Pick, pack and ship for the online store until the 2025 exit.",
    },
]

# Subcontracting chains (DORA b_05.02): solution ref_id, subcontractor key,
# recipient key (None = the solution's direct provider).
SUBCONTRACTORS = [
    # Pellion's processing platform runs on Kestrava: a concentration risk.
    ("SOL-005", "kestrava", None),
    ("SOL-005", "kestrava-de", "kestrava"),
    # Lookout supply chain: Shenwa -> Huaxin boards -> Orbisil modules -> foundry.
    ("SOL-007", "huaxin", None),
    ("SOL-007", "orbisil", "huaxin"),
    ("SOL-007", "sentai", "orbisil"),
    ("SOL-008", "sentai", None),
    ("SOL-012", "portavia", None),
]

# ref_id, name, provider key, status, (start, end) offsets, annual expense,
# notice periods (entity, provider), solution ref_ids, overarching ref_id,
# termination reason, description; optional beneficiary key and intragroup flag.
CONTRACTS = [
    {
        "ref_id": "CTR-2024-011",
        "name": "Kestrava master services agreement",
        "provider": "kestrava",
        "status": "active",
        "dates": (-620, 475),
        "expense": None,
        "notice": (180, 365),
        "description": (
            "Framework agreement with SLA schedule (99.95%), audit rights, exit "
            "assistance and 24h incident notification."
        ),
    },
    {
        "ref_id": "CTR-2024-012",
        "name": "Kestrava data processing agreement",
        "provider": "kestrava",
        "status": "active",
        "dates": (-620, 475),
        "notice": (180, 365),
        "overarching": "CTR-2024-011",
        "description": (
            "GDPR Article 28 terms for device telemetry and customer accounts; EU "
            "processing only, sub-processor list annexed."
        ),
    },
    {
        "ref_id": "CTR-2025-004",
        "name": "Kestrava order form: device cloud and store hosting",
        "provider": "kestrava",
        "status": "active",
        "dates": (-210, 520),
        "expense": 486000,
        "notice": (90, 180),
        "solutions": ["SOL-001", "SOL-002", "SOL-003"],
        "overarching": "CTR-2024-011",
        "description": "Compute, managed PostgreSQL, object storage and CDN under the MSA.",
    },
    {
        "ref_id": "CTR-2025-005",
        "name": "Kestrava order form: Frankfurt DR region",
        "provider": "kestrava-de",
        "status": "active",
        "dates": (-200, 530),
        "expense": 94000,
        "notice": (90, 180),
        "solutions": ["SOL-004"],
        "overarching": "CTR-2024-011",
        "description": "Warm standby, 4h RTO and 15 min RPO commitments.",
    },
    {
        "ref_id": "CTR-2023-007",
        "name": f"Pellion acquiring and processing agreement ({PAY_ENTITY})",
        "provider": "pellion",
        "beneficiary": "pay",
        "status": "active",
        "dates": (-1050, 45),
        "expense": 268000,
        "notice": (90, 90),
        "solutions": ["SOL-005"],
        "description": (
            "Register of information: supports the critical function 'card "
            "payments'. DORA Article 30 clauses, PCI DSS responsibility matrix; "
            "auto-renews unless notice is served."
        ),
    },
    {
        "ref_id": "CTR-2025-020",
        "name": f"Pellion instalment processing addendum ({PAY_ENTITY})",
        "provider": "pellion",
        "beneficiary": "pay",
        "status": "active",
        "dates": (-300, 45),
        "expense": 61000,
        "notice": (90, 90),
        "solutions": ["SOL-006"],
        "overarching": "CTR-2023-007",
        "description": "Instalment plans at checkout under the acquiring agreement.",
    },
    {
        "ref_id": "CTR-2026-002",
        "name": f"Pellion acquiring agreement: 2026 renewal ({PAY_ENTITY})",
        "provider": "pellion",
        "beneficiary": "pay",
        "status": "draft",
        "dates": (46, 776),
        "expense": 255000,
        "notice": (90, 90),
        "solutions": ["SOL-005", "SOL-006"],
        "description": (
            "Draft renewal: 4h major incident notification, tested exit plan and "
            "disclosure of Pellion's own hosting subcontractor."
        ),
    },
    {
        "ref_id": "CTR-2024-030",
        "name": f"Group ICT shared services agreement ({PAY_ENTITY})",
        "provider": MAIN,
        "beneficiary": "pay",
        "intragroup": True,
        "status": "active",
        "dates": (-640, 455),
        "expense": 640000,
        "notice": (180, 180),
        "description": (
            "Group IT runs the store platform, identity and SOC for the payments "
            "subsidiary; intragroup arrangement declared in the register."
        ),
    },
    {
        "ref_id": "CTR-2022-018",
        "name": "Shenwa manufacturing services agreement",
        "provider": "shenwa",
        "status": "active",
        "dates": (-820, 640),
        "expense": None,
        "notice": (180, 180),
        "description": (
            "Quality, IP protection and security schedule: segregated design "
            "storage, credential provisioning controls, right to audit on site."
        ),
    },
    {
        "ref_id": "CTR-2025-031",
        "name": "Shenwa production order: Lookout gen 3",
        "provider": "shenwa",
        "status": "active",
        "dates": (-120, 245),
        "expense": 14200000,
        "notice": (90, 90),
        "solutions": ["SOL-007"],
        "overarching": "CTR-2022-018",
        "description": "480,000 indoor and outdoor cameras over twelve months.",
    },
    {
        "ref_id": "CTR-2025-007",
        "name": "Orbisil module supply agreement",
        "provider": "orbisil",
        "status": "active",
        "dates": (-400, 330),
        "expense": 6800000,
        "notice": (180, 180),
        "solutions": ["SOL-008"],
        "description": (
            "Wi-Fi and Thread modules with 26-week lead time, last-time-buy notice "
            "and SDK vulnerability notification within 72h."
        ),
    },
    {
        "ref_id": "CTR-2023-014",
        "name": "Tallbridge carriage contract 2023",
        "provider": "tallbridge",
        "status": "expired",
        "dates": (-1100, -365),
        "notice": (60, 60),
        "description": "Previous carriage terms, superseded by the 2025 agreement.",
    },
    {
        "ref_id": "CTR-2025-012",
        "name": "Tallbridge carriage and warehousing 2025",
        "provider": "tallbridge",
        "status": "active",
        "dates": (-364, 366),
        "expense": 410000,
        "notice": (60, 60),
        "solutions": ["SOL-009"],
        "description": "EU parcel delivery, launch-peak storage and shipping API access.",
    },
    {
        "ref_id": "CTR-2024-019",
        "name": "Mireo support outsourcing agreement",
        "provider": "mireo",
        "status": "active",
        "dates": (-480, 250),
        "expense": 720000,
        "notice": (90, 90),
        "solutions": ["SOL-010"],
        "description": (
            "Eight-language support desk with DPA: camera clips viewable only with "
            "customer consent, access logged."
        ),
    },
    {
        "ref_id": "CTR-2024-008",
        "name": "Brightline Identity subscription",
        "provider": "brightline",
        "status": "active",
        "dates": (-600, 130),
        "expense": 118000,
        "notice": (30, 90),
        "solutions": ["SOL-011"],
        "description": "1,500 workforce licences, 99.99% SLA, EU data residency.",
    },
    {
        "ref_id": "CTR-2025-001",
        "name": "Linterra maintenance and remote support contract",
        "provider": "linterra",
        "status": "active",
        "dates": (-380, 715),
        "expense": 265000,
        "notice": (90, 180),
        "solutions": ["SOL-012"],
        "description": (
            "IEC 62443-2-4 requirements, named engineer accounts, session "
            "recording and change approval by the Plant OT Engineering Manager."
        ),
    },
    {
        "ref_id": "CTR-2025-015",
        "name": "Fennick analytics subscription",
        "provider": "fennick",
        "status": "active",
        "dates": (-260, 105),
        "expense": 54000,
        "notice": (30, 30),
        "solutions": ["SOL-013"],
        "description": "Annual subscription; renewal conditional on the EU-only endpoint.",
    },
    {
        "ref_id": "CTR-2025-016",
        "name": "Fennick data processing agreement",
        "provider": "fennick",
        "status": "active",
        "dates": (-260, 105),
        "notice": (30, 30),
        "overarching": "CTR-2025-015",
        "description": (
            "Article 28 DPA with SCCs for US processing; amendment pending to ban "
            "location collection."
        ),
    },
    {
        "ref_id": "CTR-2025-009",
        "name": "Quorra email services",
        "provider": "quorra",
        "status": "active",
        "dates": (-420, 310),
        "expense": 46000,
        "notice": (30, 60),
        "solutions": ["SOL-014"],
        "description": "Transactional and marketing volume tiers, DPA and DKIM set-up.",
    },
    {
        "ref_id": "CTR-2026-001",
        "name": "Redhaven penetration testing framework",
        "provider": "redhaven",
        "status": "active",
        "dates": (-90, 275),
        "expense": 88000,
        "notice": (30, 30),
        "solutions": ["SOL-015"],
        "description": "Call-off contract: launch tests per product and one red team a year.",
    },
    {
        "ref_id": "CTR-2026-003",
        "name": "Vantor certification and QSA engagement",
        "provider": "vantor",
        "status": "active",
        "dates": (-380, 715),
        "expense": 72000,
        "notice": (90, 90),
        "solutions": ["SOL-016"],
        "description": "Three-year ISO 27001 cycle and annual PCI DSS assessment.",
    },
    {
        "ref_id": "CTR-2025-040",
        "name": "Domora Retail distribution agreement",
        "provider": MAIN,
        "beneficiary": "domora",
        "status": "active",
        "dates": (-300, 430),
        "notice": (90, 90),
        "description": (
            "Sell-in terms, drop-ship partner API and a security annex on API "
            "credentials and order data."
        ),
    },
    {
        "ref_id": "CTR-2021-002",
        "name": "Corvel fulfilment services",
        "provider": "corvel",
        "status": "terminated",
        "dates": (-1800, -200),
        "expense": 5200000,
        "notice": (90, 90),
        "solutions": ["SOL-017"],
        "termination_reason": "eba_CO:x6",
        "description": "Terminated after repeated launch-day backlogs at the warehouse.",
    },
]

# entity key, name, status, conclusion, criticality, eta / due / expiry offsets
# (None = unset), questionnaire fill ratio (None = no questionnaire),
# solution ref_ids, observation; optional perimeter ref_id (root entities only).
ASSESSMENTS = [
    (
        "kestrava",
        "Kestrava: annual assurance 2026",
        "in_progress",
        None,
        4,
        (10, 30, None),
        0.6,
        ["SOL-001", "SOL-002", "SOL-003"],
        "Questionnaire returned in part; SOC 2 Type II bridge letter requested.",
        "PER.001",
    ),
    (
        "kestrava",
        "Kestrava: annual assurance 2025",
        "done",
        "warning",
        4,
        (-350, -340, 15),
        None,
        ["SOL-001", "SOL-004"],
        "Accepted with a warning: Frankfurt failover not tested within the 4h RTO.",
        "PER.001",
    ),
    (
        "pellion",
        "Pellion: PCI DSS and DORA third-party review",
        "in_review",
        None,
        4,
        (-5, 12, None),
        1.0,
        ["SOL-005", "SOL-006"],
        (
            "AOC received. Pellion's platform runs on Kestrava, our own cloud "
            "provider: concentration risk raised with the Payments Risk Officer."
        ),
    ),
    (
        "shenwa",
        "Shenwa: factory security audit 2026",
        "in_progress",
        None,
        4,
        (5, 35, None),
        0.5,
        ["SOL-007"],
        (
            "On-site audit in Shenzhen: provisioning station isolated; design files "
            "still reachable through a shared engineering account."
        ),
    ),
    (
        "orbisil",
        "Orbisil: supply continuity and SDK security",
        "done",
        "warning",
        3,
        (-100, -90, 275),
        None,
        ["SOL-008"],
        (
            "Single source for the Thread module; second-source qualification "
            "started for Keystone hub v3. SDK SBOM provided with each release."
        ),
    ),
    (
        "linterra",
        "Linterra: remote access and IEC 62443-2-4 review",
        "done",
        "blocker",
        4,
        (-110, -95, None),
        None,
        ["SOL-012"],
        (
            "Blocker: shared vendor account on the plant jump host, sessions not "
            "recorded. Remote access suspended until fixed."
        ),
    ),
    (
        "fennick",
        "Fennick: companion app SDK privacy review",
        "done",
        "blocker",
        3,
        (-80, -75, None),
        None,
        ["SOL-013"],
        (
            "Blocker: the SDK collected precise location and Wi-Fi network names "
            "before consent. Collection disabled in app 4.12; EU endpoint required."
        ),
    ),
    (
        "fennick",
        "Fennick: re-assessment after EU endpoint",
        "planned",
        None,
        3,
        (40, 60, None),
        None,
        ["SOL-013"],
        None,
    ),
    (
        "mireo",
        "Mireo: GDPR processor assessment",
        "in_progress",
        None,
        3,
        (20, 45, None),
        None,
        ["SOL-010"],
        "Camera clip access logging and agent screening evidence still outstanding.",
    ),
    (
        "corvel",
        "Corvel: offboarding check",
        "deprecated",
        "ok",
        1,
        (-205, -200, None),
        None,
        ["SOL-017"],
        "Badges returned, WMS accounts disabled, customer data deletion certified.",
    ),
]

# Ratings: (entity key, provider, scale max, [(days ago, score, grade)]).
SCORES = [
    (
        "kestrava",
        "SecurityScorecard",
        100,
        [(-270, 84, "B"), (-90, 88, "B"), (-5, 91, "A")],
    ),
    ("kestrava", "Bitsight", 900, [(-180, 740, ""), (-20, 760, "")]),
    ("pellion", "SecurityScorecard", 100, [(-200, 93, "A"), (-15, 95, "A")]),
    ("pellion", "CyberVadis", 1000, [(-160, 812, "")]),
    (
        "shenwa",
        "SecurityScorecard",
        100,
        [(-300, 61, "D"), (-120, 66, "D"), (-10, 71, "C")],
    ),
    ("shenwa", "EcoVadis", 100, [(-200, 48, "")]),
    ("orbisil", "Bitsight", 900, [(-150, 710, ""), (-30, 725, "")]),
    ("mireo", "SecurityScorecard", 100, [(-210, 72, "C"), (-30, 79, "C")]),
    ("brightline", "SecurityScorecard", 100, [(-90, 94, "A")]),
    ("brightline", "CyberVadis", 1000, [(-300, 780, ""), (-60, 805, "")]),
    (
        "linterra",
        "SecurityScorecard",
        100,
        [(-240, 58, "F"), (-100, 63, "D"), (-12, 74, "C")],
    ),
    ("fennick", "SecurityScorecard", 100, [(-150, 68, "D"), (-10, 74, "C")]),
    ("quorra", "Bitsight", 900, [(-40, 690, "")]),
    ("tallbridge", "SecurityScorecard", 100, [(-40, 81, "B")]),
    ("tallbridge", "EcoVadis", 100, [(-120, 62, "")]),
]

# Questionnaire results walked in order, so each round shows a stable spread.
RESULT_CYCLE = [
    "compliant",
    "compliant",
    "partially_compliant",
    "compliant",
    "non_compliant",
    "compliant",
    "partially_compliant",
    "not_applicable",
]


def moment(ctx, offset, hour=10):
    return datetime.combine(ctx.day(offset), time(hour, 0), tzinfo=UTC)


@register
class TprmBuilder(DemoBuilder):
    """Vendors, solutions, contracts, contacts, ratings, tiers and assurance."""

    name = "tprm"
    feature_flags = ("contracts",)
    depends = ("core",)
    libraries = (VDD_LIBRARY,)
    covers: ClassVar[dict] = {
        Entity: "folder",
        Representative: "entity__folder",
        Solution: "provider_entity__folder",
        SolutionSubcontractor: "solution__provider_entity__folder",
        Contract: "folder",
        EntityAssessment: "folder",
        EntityScore: "folder",
        EntityTierChange: "folder",
        SolutionTierChange: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (Entity, {"folder__in": folders}, ("ref_id",)),
            (Representative, {"entity__folder__in": folders}, ("email",)),
            (Solution, {"provider_entity__folder__in": folders}, ("ref_id",)),
            (
                SolutionSubcontractor,
                {"solution__provider_entity__folder__in": folders},
                ("solution__ref_id", "subcontractor__ref_id"),
            ),
            (Contract, {"folder__in": folders}, ("ref_id",)),
            (EntityAssessment, {"folder__in": folders}, ("name",)),
            (
                EntityScore,
                {"folder__in": folders},
                ("entity__ref_id", "provider__name", "as_of"),
            ),
            # Tier changes and enclave questionnaires are dated in build():
            # their created_at is the history the UI shows.
        ]

    def build(self, ctx):
        tiers = {tier.key: tier for tier in Tier.objects.all()}
        missing = {CRITICAL, IMPORTANT, STANDARD, LOW} - set(tiers)
        if missing:
            ctx.err(f"default tier scale incomplete, missing {sorted(missing)}")
        # The API sets every solution's recipient to the built-in main entity.
        main = Entity.objects.filter(builtin=True).order_by("created_at").first()
        entities = self.build_entities(ctx, tiers, main)
        self.build_representatives(ctx, entities)
        solutions = self.build_solutions(ctx, entities, tiers, main)
        self.build_subcontractors(ctx, entities, solutions)
        self.build_contracts(ctx, entities, solutions, main)
        self.build_scores(ctx, entities)
        self.build_assessments(ctx, entities, solutions)
        ctx.out(f"tprm seeded with {len(entities)} third parties")

    def build_entities(self, ctx, tiers, main):
        relationships = {
            term.name: term
            for term in Terminology.objects.filter(
                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP
            )
        }
        entities = {MAIN: main}
        for spec in ENTITIES:
            dependency, penetration, maturity, trust = spec["levels"]
            entity, created = Entity.objects.get_or_create(
                name=spec["name"],
                folder=ctx.domain,
                defaults={
                    "ref_id": spec["ref_id"],
                    "description": spec["description"],
                    "mission": spec["mission"],
                    "country": spec["country"],
                    "currency": spec["currency"],
                    "is_active": spec.get("is_active", True),
                    "parent_entity": entities.get(spec.get("parent")),
                    "default_dependency": dependency,
                    "default_penetration": penetration,
                    "default_maturity": maturity,
                    "default_trust": trust,
                    "reference_link": spec.get("reference_link"),
                    "legal_identifiers": spec.get("legal_identifiers", {}),
                    "dora_entity_type": spec.get("dora_entity_type", ""),
                    "dora_entity_hierarchy": spec.get("dora_entity_hierarchy", ""),
                    "dora_competent_authority": spec.get(
                        "dora_competent_authority", ""
                    ),
                    "dora_assets_value": spec.get("dora_assets_value"),
                    "dora_provider_person_type": "eba_CT:x212",
                },
            )
            entities[spec["key"]] = entity
            if not created:
                continue
            relationship = relationships.get(spec["relationship"])
            if relationship:
                entity.relationship.set([relationship])
            self.build_tier_history(
                ctx, entity, TIER_HISTORY.get(spec["key"], ()), tiers
            )
        return entities

    def build_tier_history(self, ctx, entity, history, tiers):
        """Replay the history through set_entity_tier, then date each step."""
        for offset, key, note in history:
            change = set_entity_tier(entity, tiers.get(key) if key else None, note=note)
            if change is None:
                continue
            EntityTierChange.objects.filter(pk=change.pk).update(
                created_at=moment(ctx, offset), updated_at=moment(ctx, offset)
            )
            if entity.tier_id:
                Entity.objects.filter(pk=entity.pk).update(
                    tier_set_at=moment(ctx, offset)
                )

    def build_representatives(self, ctx, entities):
        for key, first, last, role, phone in REPRESENTATIVES:
            email = f"{first[0]}.{last.replace(' ', '')}@{EMAIL_DOMAINS[key]}".lower()
            # Contacts only: no account is minted (the UI's create_user stays off).
            # Representative has no name, so it reads as its id: derive the id from
            # the email, or a rebuilt demo shows every contact under a new label.
            Representative.objects.get_or_create(
                email=email,
                defaults={
                    "id": uuid.uuid5(uuid.NAMESPACE_URL, f"mailto:{email}"),
                    "entity": entities[key],
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "phone": phone,
                },
            )

    def build_solutions(self, ctx, entities, tiers, main):
        assets = {asset.name: asset for asset in ctx.refs["assets"]}
        solutions = {}
        for spec in SOLUTIONS:
            data = spec.get("data")
            solution, created = Solution.objects.get_or_create(
                name=spec["name"],
                provider_entity=entities[spec["entity"]],
                defaults={
                    "ref_id": spec["ref_id"],
                    "description": spec["description"],
                    "recipient_entity": main,
                    "is_active": spec.get("active", True),
                    "dora_ict_service_type": spec["service"],
                    "storage_of_data": data is not None,
                    "data_location_storage": data[0] if data else "",
                    "data_location_processing": data[1] if data else "",
                    "dora_data_sensitiveness": data[2] if data else "",
                    "dora_reliance_level": spec["reliance"],
                    "dora_substitutability": spec["substitutability"],
                    "dora_non_substitutability_reason": spec.get(
                        "non_substitutability_reason", ""
                    ),
                    "dora_has_exit_plan": spec.get("exit_plan", ""),
                    "dora_reintegration_possibility": spec.get("reintegration", ""),
                    "dora_discontinuing_impact": spec.get("discontinuing_impact", ""),
                    "dora_alternative_providers_identified": spec.get(
                        "alternatives_identified", ""
                    ),
                    "dora_alternative_providers": spec.get("alternatives", ""),
                },
            )
            solutions[spec["ref_id"]] = solution
            if created:
                solution.assets.set([assets[name] for name in spec["assets"]])
                if spec["tier"]:
                    set_solution_tier(
                        solution, tiers.get(spec["tier"]), propagate=False
                    )
        return solutions

    def build_subcontractors(self, ctx, entities, solutions):
        for solution_ref, key, recipient in SUBCONTRACTORS:
            SolutionSubcontractor.objects.get_or_create(
                solution=solutions[solution_ref],
                subcontractor=entities[key],
                defaults={"recipient": entities.get(recipient)},
            )

    def build_contracts(self, ctx, entities, solutions, main):
        overarching_refs = {spec.get("overarching") for spec in CONTRACTS}
        contracts = {}
        for spec in CONTRACTS:
            provider = entities[spec["provider"]]
            beneficiary = entities.get(spec.get("beneficiary"))
            if provider is None:
                ctx.err(f"no main entity, contract {spec['ref_id']} skipped")
                continue
            # A contract lives with the third party, never in the root folder.
            party = beneficiary if spec["provider"] == MAIN else provider
            start, end = spec["dates"]
            notice_entity, notice_provider = spec["notice"]
            overarching = spec.get("overarching")
            if overarching:
                arrangement = "eba_CO:x3"
            elif spec["ref_id"] in overarching_refs:
                arrangement = "eba_CO:x2"
            else:
                arrangement = "eba_CO:x1"
            contract, created = Contract.objects.get_or_create(
                name=spec["name"],
                folder=party.folder,
                defaults={
                    "ref_id": spec["ref_id"],
                    "description": spec["description"],
                    "provider_entity": provider,
                    "beneficiary_entity": beneficiary,
                    "is_intragroup": spec.get("intragroup", False),
                    "status": spec["status"],
                    "start_date": ctx.day(start),
                    "end_date": ctx.day(end),
                    "annual_expense": spec.get("expense"),
                    "currency": party.currency,
                    "notice_period_entity": notice_entity,
                    "notice_period_provider": notice_provider,
                    "governing_law_country": party.country,
                    "termination_reason": spec.get("termination_reason", ""),
                    "overarching_contract": contracts.get(overarching),
                    "dora_contractual_arrangement": arrangement,
                },
            )
            contracts[spec["ref_id"]] = contract
            if created:
                contract.solutions.set(
                    [solutions[ref] for ref in spec.get("solutions", [])]
                )

    def build_scores(self, ctx, entities):
        providers = {
            term.name: term
            for term in Terminology.objects.filter(
                field_path=Terminology.FieldPath.ENTITY_SCORE_PROVIDER
            )
        }
        for key, provider_name, scale_max, readings in SCORES:
            provider = providers.get(provider_name)
            if provider is None:
                ctx.err(f"rating provider {provider_name} not found")
                continue
            for offset, score, grade in readings:
                EntityScore.objects.get_or_create(
                    entity=entities[key],
                    provider=provider,
                    as_of=ctx.day(offset),
                    defaults={"score": score, "scale_max": scale_max, "grade": grade},
                )

    def build_assessments(self, ctx, entities, solutions):
        framework = Framework.objects.filter(urn=VDD_FRAMEWORK).first()
        if framework is None:
            ctx.err("Vendor Due Diligence framework not loaded, no questionnaires")
        perimeters = {p.ref_id: p for p in ctx.refs.get("perimeters", [])}
        levels = {spec["key"]: spec["levels"] for spec in ENTITIES}
        for (
            key,
            name,
            status,
            conclusion,
            criticality,
            (eta, due, expiry),
            fill,
            solution_refs,
            observation,
            *perimeter_ref,
        ) in ASSESSMENTS:
            entity = entities[key]
            dependency, penetration, maturity, trust = levels[key]
            perimeter = perimeters.get(perimeter_ref[0]) if perimeter_ref else None
            assessment, created = EntityAssessment.objects.get_or_create(
                name=name,
                entity=entity,
                folder=entity.folder,
                defaults={
                    "status": status,
                    "conclusion": conclusion,
                    "criticality": criticality,
                    "dependency": dependency,
                    "penetration": penetration,
                    "maturity": maturity,
                    "trust": trust,
                    "eta": ctx.day(eta),
                    "due_date": ctx.day(due),
                    "expiry_date": ctx.day(expiry) if expiry is not None else None,
                    "observation": observation,
                    # Perimeters live in the root demo domain only.
                    "perimeter": perimeter if entity.folder == ctx.domain else None,
                },
            )
            if not created:
                continue
            assessment.solutions.set([solutions[ref] for ref in solution_refs])
            if fill is not None and framework is not None:
                self.build_questionnaire(ctx, assessment, framework, fill, eta - 21)

    def build_questionnaire(self, ctx, assessment, framework, fill, sent_offset):
        """The audit the API's create_audit builds, minus the respondent group:
        the demo grants no access, and the contacts have no accounts."""
        audit = create_enclave_audit(assessment, framework)
        # The questionnaire follows the round: answered, under review or closed.
        audit.status = {
            "done": ComplianceAssessment.Status.DONE,
            "in_review": ComplianceAssessment.Status.IN_REVIEW,
        }.get(assessment.status, ComplianceAssessment.Status.IN_PROGRESS)
        audit.save(update_fields=["status"])
        ComplianceAssessment.objects.filter(pk=audit.pk).update(
            created_at=moment(ctx, sent_offset), updated_at=moment(ctx, sent_offset)
        )
        requirements = list(
            RequirementAssessment.objects.filter(compliance_assessment=audit).order_by(
                "requirement__order_id", "requirement__urn"
            )
        )
        assessable = [ra for ra in requirements if ra.requirement.assessable]
        answered = round(len(assessable) * fill)
        start = ctx.rng.randrange(len(RESULT_CYCLE))
        for index, ra in enumerate(assessable[:answered]):
            ra.result = RESULT_CYCLE[(start + index) % len(RESULT_CYCLE)]
            ra.status = "done"
            ra.save(update_fields=["result", "status"])
        for index, ra in enumerate(requirements):
            stamp = moment(ctx, sent_offset) + timedelta(seconds=index)
            RequirementAssessment.objects.filter(pk=ra.pk).update(
                created_at=stamp, updated_at=stamp
            )
