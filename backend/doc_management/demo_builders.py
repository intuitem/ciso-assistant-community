"""Document management demo builder: the company's security policy set.

Documents are created the way the editor leaves them: a container per logical
document, one ``ManagedDocument`` per locale, and a revision chain walked
through the editorial workflow (draft, in review, change requested, validated,
published, deprecated). Publication is written directly rather than through
``DocumentRevision.publish()``, which stamps ``now()``; the PDF snapshot the
publish view renders is never produced at seed time.

Revision authors and reviewers stay empty: the demo never creates users.
"""

from datetime import UTC, datetime, time
from typing import ClassVar

from django.core.files.base import ContentFile

from core.demo import COMPANY, PAY_ENTITY, DemoBuilder, register
from core.models import Policy
from doc_management.models import (
    DocumentAttachment,
    DocumentContainer,
    DocumentRevision,
    DocumentTemplate,
    ManagedDocument,
)

DRAFT = DocumentRevision.Status.DRAFT
IN_REVIEW = DocumentRevision.Status.IN_REVIEW
CHANGE_REQUESTED = DocumentRevision.Status.CHANGE_REQUESTED
VALIDATED = DocumentRevision.Status.VALIDATED
PUBLISHED = DocumentRevision.Status.PUBLISHED
DEPRECATED = DocumentRevision.Status.DEPRECATED

MAIL_DOMAIN = f"{COMPANY.split()[0].lower()}.example"

TEMPLATES = [
    (
        "secpol-policy",
        "Security policy skeleton",
        "policy",
        (
            "House structure for every security policy: purpose, scope, "
            "statements, roles, compliance and review."
        ),
        (
            "# {Policy title}\n\n"
            "| Owner | Approver | Classification | Review cycle |\n"
            "|---|---|---|---|\n"
            "| CISO | Executive Committee | Internal | Annual |\n\n"
            "## 1. Purpose\n\nWhy this policy exists and which risk it addresses.\n\n"
            "## 2. Scope\n\nEntities, sites (Lyon, Brno, Eindhoven), products, "
            "systems and people covered.\n\n"
            "## 3. Policy statements\n\nNumbered, testable statements. Use *must* "
            "for mandatory requirements.\n\n"
            "## 4. Roles and responsibilities\n\n## 5. Compliance and exceptions\n\n"
            "Exceptions are requested through the security exception process and "
            "are time-boxed.\n\n## 6. Review\n\nReviewed at least annually.\n"
        ),
    ),
    (
        "secpol-procedure",
        "Security procedure skeleton",
        "procedure",
        "Step-by-step operating procedure with triggers, roles and records.",
        (
            "# {Procedure title}\n\n## Trigger\n\nThe event that starts this "
            "procedure.\n\n## Roles\n\n## Steps\n\n1. ...\n2. ...\n\n"
            "## Regulatory clocks\n\nAny reporting deadline this procedure must "
            "meet.\n\n## Records kept\n\nWhat evidence the procedure leaves behind.\n"
        ),
    ),
    (
        "secpol-minutes",
        "Committee minutes",
        "meeting_minutes",
        "Minutes for governance committees: attendance, decisions, actions.",
        (
            "# {Committee} — {date}\n\n## Attendees\n\n## Agenda\n\n"
            "## Decisions\n\n## Actions\n\n| # | Action | Owner | Due |\n"
            "|---|---|---|---|\n"
        ),
    ),
    (
        "secpol-product-standard",
        "Product security standard skeleton",
        "policy",
        (
            "Structure for product security standards that feed the CRA "
            "technical documentation."
        ),
        (
            "# {Standard title}\n\n## 1. Products in scope\n\n"
            "## 2. Requirements\n\nOne requirement per line, traceable to CRA "
            "Annex I.\n\n## 3. Evidence for the technical file\n\n"
            "## 4. Exceptions\n\nApproved by the Head of Product Security.\n"
        ),
    ),
]

ISSP = [
    (
        "Information Security Policy",
        (
            "| Owner | Approver | Classification | Review cycle |\n"
            "|---|---|---|---|\n"
            "| CISO | Executive Committee | Internal | Annual |"
        ),
    ),
    (
        "1. Purpose",
        (
            f"{COMPANY} designs, builds and sells connected home devices: Kelvin "
            "thermostats, Lookout security cameras and the Keystone home hub, "
            "together with the companion app and the device cloud that keep them "
            "working. Customers let our products into their homes; retail "
            "partners, payment partners and regulators expect us to protect the "
            "data those products generate and to keep them secure for their whole "
            "support period.\n\n"
            "This policy sets the management direction for information and "
            "product security and is the top of the policy framework. "
            "Topic-specific policies, standards and procedures implement it."
        ),
    ),
    (
        "2. Scope",
        (
            f"The policy applies to every {COMPANY} entity, including "
            f"{PAY_ENTITY}, to the Lyon headquarters, the Brno assembly plant and "
            "warehouse and the Eindhoven design office, and to every employee, "
            "contractor and supplier with access to our information, systems or "
            "production equipment. It covers corporate IT, the device cloud, the "
            "online store, the plant operational technology and every product "
            "with digital elements we place on the market, from first design to "
            "end of support."
        ),
    ),
    (
        "3. Security objectives",
        (
            "- Protect customer and device accounts, camera footage and energy "
            "telemetry against unauthorised access.\n"
            "- Ship products without known exploitable vulnerabilities and "
            "deliver security updates for the declared support period.\n"
            "- Keep the store checkout, the device cloud and the assembly line "
            "available within their recovery objectives.\n"
            "- Hold ISO 27001 certification, keep the payments subsidiary PCI "
            "DSS compliant and meet our NIS2, DORA, GDPR and Cyber Resilience "
            "Act obligations.\n"
            "- Detect and contain incidents quickly and report them within "
            "regulatory deadlines."
        ),
    ),
    (
        "4. Principles",
        (
            "1. **Risk-based**: controls are proportionate to assessed risk; "
            "residual risk above appetite is accepted by the Executive Committee "
            "only.\n"
            "2. **Least privilege**: access is granted on business need and "
            "reviewed every quarter.\n"
            "3. **Secure by design and by default**: products ship with unique "
            "credentials, signed firmware and no unnecessary open services; "
            "security requirements are part of every project from initiation.\n"
            "4. **Defence in depth**: no single control is relied upon to protect "
            "a critical asset.\n"
            "5. **IT and OT separation**: plant networks are reachable from "
            "corporate IT only through monitored conduits."
        ),
    ),
    (
        "5. Policy framework",
        (
            "NIST CSF 2.0 is our minimum security baseline and the ISO 27001 "
            "ISMS is the management system that runs it. This policy is "
            "implemented by the access control, acceptable use, supplier "
            "security, backup and recovery, OT security, secure firmware "
            "development and coordinated vulnerability disclosure policies, and "
            "by the incident response and vulnerability management procedures."
        ),
    ),
    (
        "6. Roles and responsibilities",
        (
            "The **Executive Committee** owns information risk and approves this "
            "policy. The **CISO** maintains the policy framework, reports on the "
            "security posture monthly and chairs the Security Committee. The "
            "**Head of Product Security** runs the PSIRT and owns product "
            "security across the lifecycle. The **Plant OT Engineering Manager** "
            "owns the security of the Brno production systems. The **DPO** "
            "advises on personal data and handles breach notifications. The "
            f"**Payments Risk Officer** owns ICT risk at {PAY_ENTITY}. **Asset "
            "owners** classify their assets and approve access. **Every "
            "employee** completes annual security training and reports suspected "
            "incidents immediately."
        ),
    ),
    (
        "7. Compliance",
        (
            "Compliance is verified through internal audits, the annual ISO "
            "27001 audit, the PCI DSS assessment of the payments subsidiary and "
            "the IEC 62443 assessment of the plant. Breaches of this policy may "
            "lead to disciplinary action. Deviations require a documented, "
            "time-limited security exception."
        ),
    ),
]

ISSP_FR = [
    (
        "Politique de sécurité des systèmes d'information",
        (
            "| Propriétaire | Approbateur | Classification | Revue |\n"
            "|---|---|---|---|\n"
            "| RSSI | Comité exécutif | Interne | Annuelle |"
        ),
    ),
    (
        "1. Objet",
        (
            f"{COMPANY} conçoit, fabrique et vend des équipements connectés pour "
            "la maison : les thermostats Kelvin, les caméras de sécurité Lookout "
            "et la passerelle domotique Keystone, ainsi que l'application "
            "compagnon et le cloud qui les font fonctionner. Nos clients font "
            "entrer nos produits chez eux ; nos distributeurs, nos partenaires de "
            "paiement et les autorités attendent de nous que les données "
            "produites soient protégées et que les produits restent sûrs pendant "
            "toute leur période de support.\n\n"
            "Cette politique fixe les orientations de la direction en matière de "
            "sécurité de l'information et des produits. Elle est au sommet du "
            "référentiel documentaire ; les politiques thématiques, les standards "
            "et les procédures la déclinent."
        ),
    ),
    (
        "2. Périmètre",
        (
            f"La politique s'applique à toutes les entités de {COMPANY}, y "
            f"compris {PAY_ENTITY}, au siège de Lyon, à l'usine d'assemblage et à "
            "l'entrepôt de Brno, au bureau d'études d'Eindhoven, ainsi qu'à tous "
            "les salariés, prestataires et fournisseurs ayant accès à nos "
            "informations, à nos systèmes ou à nos équipements de production. "
            "Elle couvre l'informatique de gestion, le cloud des équipements, la "
            "boutique en ligne, l'informatique industrielle de l'usine et chaque "
            "produit comportant des éléments numériques que nous mettons sur le "
            "marché, de la conception à la fin du support."
        ),
    ),
    (
        "3. Objectifs de sécurité",
        (
            "- Protéger les comptes clients et équipements, les vidéos des "
            "caméras et les données de consommation d'énergie contre tout accès "
            "non autorisé.\n"
            "- Livrer des produits sans vulnérabilité exploitable connue et "
            "fournir les mises à jour de sécurité pendant toute la période de "
            "support annoncée.\n"
            "- Maintenir le paiement en ligne, le cloud des équipements et la "
            "ligne d'assemblage disponibles dans le respect de leurs objectifs "
            "de reprise.\n"
            "- Conserver la certification ISO 27001, maintenir la conformité PCI "
            "DSS de la filiale de paiement et respecter nos obligations NIS2, "
            "DORA, RGPD et Cyber Resilience Act.\n"
            "- Détecter et contenir rapidement les incidents et les déclarer "
            "dans les délais réglementaires."
        ),
    ),
    (
        "4. Principes",
        (
            "1. **Approche par les risques** : les mesures sont proportionnées "
            "au risque évalué ; seul le comité exécutif peut accepter un risque "
            "résiduel supérieur à l'appétence.\n"
            "2. **Moindre privilège** : les accès sont accordés selon le besoin "
            "et revus chaque trimestre.\n"
            "3. **Sécurité dès la conception et par défaut** : les produits sont "
            "livrés avec des identifiants uniques, un micrologiciel signé et "
            "aucun service ouvert inutile ; les exigences de sécurité sont "
            "intégrées à chaque projet dès son lancement.\n"
            "4. **Défense en profondeur** : aucune mesure isolée ne suffit à "
            "protéger un actif critique.\n"
            "5. **Séparation IT et OT** : les réseaux de l'usine ne sont "
            "joignables depuis l'informatique de gestion qu'au travers de "
            "conduits surveillés."
        ),
    ),
    (
        "5. Référentiel documentaire",
        (
            "Le NIST CSF 2.0 constitue notre socle minimal de sécurité et le "
            "SMSI ISO 27001 est le système de management qui le met en œuvre. "
            "Cette politique est déclinée par les politiques de contrôle "
            "d'accès, d'usage acceptable, de sécurité des fournisseurs, de "
            "sauvegarde et de restauration, de sécurité OT, de développement "
            "sécurisé du micrologiciel et de divulgation coordonnée des "
            "vulnérabilités, ainsi que par les procédures de réponse aux "
            "incidents et de gestion des vulnérabilités."
        ),
    ),
    (
        "6. Rôles et responsabilités",
        (
            "Le **comité exécutif** porte le risque informationnel et approuve "
            "cette politique. Le **RSSI** tient à jour le référentiel, rend "
            "compte chaque mois du niveau de sécurité et préside le comité "
            "sécurité. Le **responsable de la sécurité des produits** dirige le "
            "PSIRT et porte la sécurité des produits sur tout leur cycle de vie. "
            "Le **responsable de l'ingénierie OT de l'usine** est garant de la "
            "sécurité des systèmes de production de Brno. Le **DPO** conseille "
            "sur les données personnelles et gère les notifications de "
            "violation. Le **responsable des risques de paiement** porte le "
            f"risque informatique de {PAY_ENTITY}. Les **propriétaires "
            "d'actifs** classifient leurs actifs et approuvent les accès. "
            "**Chaque salarié** suit la formation annuelle à la sécurité et "
            "signale sans délai tout incident suspecté."
        ),
    ),
    (
        "7. Conformité",
        (
            "Le respect de la politique est vérifié par les audits internes, "
            "l'audit annuel ISO 27001, l'évaluation PCI DSS de la filiale de "
            "paiement et l'évaluation IEC 62443 de l'usine. Tout manquement "
            "peut entraîner des sanctions disciplinaires. Toute dérogation fait "
            "l'objet d'une exception de sécurité documentée et limitée dans le "
            "temps."
        ),
    ),
]

ACCESS_CONTROL = [
    (
        "Access Control Policy",
        "Implements principle 2 of the Information Security Policy.",
    ),
    (
        "1. Purpose",
        (
            "Ensure that only authorised people and services can reach "
            f"{COMPANY} systems, device cloud data and production equipment, "
            "with the minimum privileges needed to do their job."
        ),
    ),
    (
        "2. Account lifecycle",
        (
            "- Accounts are provisioned from the HR joiner event in the "
            "workforce identity provider and linked to one named person. Shared "
            "accounts are prohibited, except break-glass accounts held in the "
            "vault and the plant HMI accounts covered by the OT security "
            "policy.\n"
            "- Movers lose the access of their previous role within five "
            "working days.\n"
            "- Leavers are disabled on their last working day; access to the "
            "cardholder data environment, the firmware signing service and the "
            "device cloud production cluster is revoked within four hours."
        ),
    ),
    (
        "3. Authentication",
        (
            "Single sign-on through the workforce identity provider is "
            "mandatory for every application that supports SAML or OIDC. "
            "Phishing-resistant multi-factor authentication (FIDO2 security "
            "keys) is required for administrators, for access to the cardholder "
            "data environment and for the firmware release pipeline; app-based "
            "MFA is the minimum for everyone else. Local account passwords are "
            "at least 14 characters and stored only in the corporate password "
            "manager."
        ),
    ),
    (
        "4. Privileged access",
        (
            "Administrative rights are granted just in time through the "
            "privileged access management tool, for at most eight hours. "
            "Privileged sessions on the device cloud, the store and the plant "
            "SCADA server are recorded and kept for one year. Production "
            "database access goes through the bastion, never from a laptop."
        ),
    ),
    (
        "5. Service accounts and machine identities",
        (
            "Service accounts have a named owner and no interactive login. "
            "Device cloud workloads authenticate with short-lived workload "
            "identities; static API keys are rotated every 90 days and scanned "
            "for in every repository."
        ),
    ),
    (
        "6. Access reviews",
        (
            "Asset owners review all access to their systems every quarter. "
            "Privileged, signing-key and cardholder-data access is reviewed "
            "monthly. Access not confirmed within ten working days is removed."
        ),
    ),
]

ACCEPTABLE_USE = [
    (
        "Acceptable Use Policy",
        f"Applies to every person given a {COMPANY} account or device.",
    ),
    (
        "1. Using company systems",
        (
            "Company laptops, phones, accounts and lab equipment are provided "
            "for business use. Limited personal use is tolerated if it does not "
            "interfere with work, break the law or expose the company to risk."
        ),
    ),
    (
        "2. You must",
        (
            "- Lock your screen whenever you leave your device.\n"
            "- Store company data only in approved locations: the corporate "
            "file share, the document management system and approved SaaS.\n"
            "- Register every pre-release device (for example a Keystone hub v3 "
            "prototype) you take out of a lab, and return it when the test "
            "ends.\n"
            "- Report lost devices and suspicious messages to the SOC "
            "immediately."
        ),
    ),
    (
        "3. You must not",
        (
            "- Paste customer data, source code or unreleased product "
            "information into public AI tools or file-sharing sites.\n"
            "- View customer camera footage or telemetry outside a support "
            "ticket the customer has consented to.\n"
            "- Install unapproved software or browser extensions, or connect "
            "personal devices to plant networks.\n"
            "- Share your credentials or MFA codes with anyone, including IT."
        ),
    ),
    (
        "4. Monitoring",
        (
            "The company monitors the use of its systems for security purposes, "
            "in line with the employee privacy notice, works council agreements "
            "and local law in France, Czechia and the Netherlands."
        ),
    ),
]

ACCEPTABLE_USE_FR = [
    (
        "Charte d'usage des moyens informatiques",
        f"S'applique à toute personne disposant d'un compte ou d'un équipement {COMPANY}.",
    ),
    (
        "1. Utilisation des moyens de l'entreprise",
        (
            "Les ordinateurs, téléphones, comptes et équipements de laboratoire "
            "sont fournis pour un usage professionnel. Un usage personnel limité "
            "est toléré s'il ne gêne pas le travail, respecte la loi et "
            "n'expose pas l'entreprise à un risque."
        ),
    ),
    (
        "2. Vous devez",
        (
            "- Verrouiller votre écran dès que vous vous éloignez de votre "
            "poste.\n"
            "- Stocker les données de l'entreprise uniquement dans les espaces "
            "autorisés : partage de fichiers de l'entreprise, système de gestion "
            "documentaire et SaaS approuvés.\n"
            "- Enregistrer tout équipement de préproduction (par exemple un "
            "prototype de passerelle Keystone v3) que vous sortez d'un "
            "laboratoire, et le restituer à la fin du test.\n"
            "- Signaler immédiatement au SOC tout équipement perdu et tout "
            "message suspect."
        ),
    ),
    (
        "3. Vous ne devez pas",
        (
            "- Copier des données clients, du code source ou des informations "
            "sur des produits non annoncés dans des outils d'IA publics ou des "
            "sites de partage de fichiers.\n"
            "- Consulter les vidéos ou la télémétrie d'un client en dehors d'un "
            "ticket de support auquel il a consenti.\n"
            "- Installer des logiciels ou des extensions de navigateur non "
            "approuvés, ni brancher un équipement personnel sur les réseaux de "
            "l'usine.\n"
            "- Communiquer vos identifiants ou vos codes MFA à quiconque, y "
            "compris au service informatique."
        ),
    ),
    (
        "4. Surveillance",
        (
            "L'entreprise surveille l'usage de ses systèmes à des fins de "
            "sécurité, conformément à la notice d'information des salariés, aux "
            "accords conclus avec les instances représentatives du personnel et "
            "au droit applicable en France, en Tchéquie et aux Pays-Bas."
        ),
    ),
]

CVD = [
    (
        "Coordinated Vulnerability Disclosure Policy",
        (
            "Owner: Head of Product Security. Meets the vulnerability handling "
            "requirements of the Cyber Resilience Act (Annex I, Part II)."
        ),
    ),
    (
        "1. Products in scope",
        (
            "Kelvin thermostats, Lookout cameras, the Keystone hub (including "
            "Keystone hub v3 once released), the companion app for iOS and "
            "Android and the device cloud services they depend on. Each product "
            "is supported with security updates for at least five years after "
            "it is last placed on the market; the end-of-support date is printed "
            "on the packaging and published on the product security page."
        ),
    ),
    (
        "2. Reporting a vulnerability",
        (
            f"Researchers report to security@{MAIL_DOMAIN} (PGP key published "
            "in our security.txt) or through the web form on the product "
            "security page. The PSIRT acknowledges every report within two "
            "business days and gives the reporter a named contact. We do not "
            "take legal action against good-faith research that respects this "
            "policy, avoids customer data and does not degrade the service."
        ),
    ),
    (
        "3. Triage and remediation",
        (
            "The PSIRT reproduces the issue, scores it with CVSS 4.0 and "
            "identifies affected firmware and app versions from the SBOM.\n\n"
            "| Severity | Fix available | Rollout complete |\n|---|---|---|\n"
            "| Critical or actively exploited | 7 days | 14 days |\n"
            "| High | 30 days | 45 days |\n"
            "| Medium | 90 days | next scheduled release |\n"
            "| Low | next scheduled release | next scheduled release |\n\n"
            "Security fixes ship through the staged OTA rollout and are never "
            "bundled behind a feature update the customer has to accept."
        ),
    ),
    (
        "4. Disclosure",
        (
            "We disclose in coordination with the reporter, by default 90 days "
            "after the report or when the fix has reached 95% of the active "
            "fleet, whichever comes first. Every fixed vulnerability gets a "
            "public advisory and a CVE identifier; reporters are credited unless "
            "they ask otherwise. The SBOM of every release is published with "
            "its release notes."
        ),
    ),
    (
        "5. Reporting to authorities",
        (
            "An actively exploited vulnerability in one of our products is "
            "reported through the ENISA single reporting platform: an early "
            "warning within 24 hours of becoming aware, a vulnerability "
            "notification within 72 hours and a final report within 14 days "
            "after a corrective measure is available. Users are informed of the "
            "vulnerability and of the mitigations they can apply. Components "
            "from suppliers such as Orbisil Semiconductors are reported to the "
            "supplier at the same time."
        ),
    ),
]

FIRMWARE_SDL = [
    (
        "Secure Development Lifecycle for Firmware",
        (
            "Standard for every firmware image running on Kelvin, Lookout and "
            "Keystone devices. Owner: Head of Product Security."
        ),
    ),
    (
        "1. Threat modelling",
        (
            "Every new feature that adds an interface, a protocol or a data "
            "flow gets a threat model before implementation starts. The model "
            "is reviewed by product security at the design gate and stored with "
            "the feature specification."
        ),
    ),
    (
        "2. Secure coding",
        (
            "New components are written in a memory-safe language where the "
            "toolchain allows; C code follows the company coding standard, "
            "with banned functions enforced by the compiler. Static analysis "
            "runs on every merge request and blocks on high-severity findings. "
            "Every engineer completes the secure firmware development training "
            "each year."
        ),
    ),
    (
        "3. Build and dependencies",
        (
            "Release images are built only on the firmware CI build farm, from "
            "a tagged commit, with reproducible builds. Third-party and vendor "
            "SDK components are pinned and scanned for known vulnerabilities; a "
            "CycloneDX SBOM is produced for every build and archived with the "
            "release."
        ),
    ),
    (
        "4. Signing and release",
        (
            "Release images are signed by the firmware signing HSM; signing "
            "keys never leave it. A release needs approval from firmware "
            "engineering and product security. Updates go out through the "
            "staged OTA rollout: 1% of the fleet, then 10%, then everyone, with "
            "automatic halt on crash-rate or connectivity regressions."
        ),
    ),
    (
        "5. Secure defaults",
        (
            "Devices ship with secure boot enabled, a unique per-device "
            "credential provisioned at the Brno end-of-line station, debug "
            "interfaces (JTAG, UART console) disabled by fuse, and no listening "
            "service other than those required for Matter, Thread and the cloud "
            "connection."
        ),
    ),
    (
        "6. Security testing",
        (
            "Network interfaces and parsers are fuzzed continuously. Each major "
            "release and each new product is penetration tested by Redhaven "
            "Security before launch; findings rated high or above block the "
            "release."
        ),
    ),
]

OT_POLICY = [
    (
        "OT Security Policy — Brno Assembly Plant",
        (
            "Owner: Plant OT Engineering Manager. Based on IEC 62443-3-3; "
            "applies to every production, test and warehouse automation system "
            "on the Brno site."
        ),
    ),
    (
        "1. Zones and conduits",
        (
            "| Zone | Contents | Target security level |\n|---|---|---|\n"
            "| Enterprise | Corporate IT, MES clients | — |\n"
            "| Plant DMZ | Jump host, historian replica, patch server | SL 2 |\n"
            "| Supervisory | SCADA server, engineering workstations | SL 2 |\n"
            "| Cell | Assembly cell PLCs, test benches, end-of-line "
            "provisioning | SL 3 |\n\n"
            "Traffic between zones only crosses documented conduits through the "
            "plant firewall; nothing in the cell zone talks to the internet."
        ),
    ),
    (
        "2. Remote maintenance",
        (
            "Integrators such as Linterra Automation connect only through the "
            "plant DMZ jump host, with named accounts and MFA. Each session is "
            "requested in advance, approved by the on-duty OT engineer, limited "
            "to the systems in the work order, recorded, and closed "
            "automatically after four hours."
        ),
    ),
    (
        "3. Change management",
        (
            "PLC programmes and SCADA configurations are versioned in the OT "
            "change repository. Every change has a work order, a tested rollback "
            "and the line supervisor's approval; emergency changes are reviewed "
            "within two working days."
        ),
    ),
    (
        "4. Patching and removable media",
        (
            "Patches are applied in the monthly maintenance window after the "
            "vendor confirms compatibility. Systems that cannot be patched are "
            "listed with compensating controls. USB media are scanned at the "
            "plant kiosk before use; autorun is disabled everywhere."
        ),
    ),
    (
        "5. Physical security",
        (
            "Control cabinets are locked and the supervisory room is badge "
            "controlled. Badge access to production areas is audited every "
            "quarter and visitors are escorted at all times."
        ),
    ),
    (
        "6. Shared operator accounts",
        (
            "Shared HMI operator accounts are tolerated on line consoles where "
            "named login would stop production, provided the console is in a "
            "badge-controlled area, cannot reach other zones and logs shift "
            "attendance alongside HMI actions."
        ),
    ),
]

SUPPLIER = [
    (
        "Supplier Security Policy",
        "Owner: Head of Procurement, with the CISO.",
    ),
    (
        "1. Purpose",
        (
            "Our products, store and plant depend on suppliers: cloud hosting, "
            "chipsets, contract manufacturing, logistics, customer support and "
            "OT integration. This policy makes sure each supplier is held to "
            "security requirements proportionate to what it can affect."
        ),
    ),
    (
        "2. Supplier tiers",
        (
            "| Tier | Criteria | Examples |\n|---|---|---|\n"
            "| 1 | Hosts or processes customer data, card data or firmware, or "
            "has remote access to production | Kestrava Cloud, Pellion Payments, "
            "Mireo Support, Linterra Automation |\n"
            "| 2 | Supplies a component of our products or a critical business "
            "service | Orbisil Semiconductors, Shenwa Contract Manufacturing, "
            "Brightline Identity |\n"
            "| 3 | No access to data or systems | Office supplies, facilities |"
        ),
    ),
    (
        "3. Due diligence",
        (
            "Tier 1 and tier 2 suppliers complete the supplier security "
            "questionnaire before contract signature and every year after. We "
            "accept a current ISO 27001 certificate or an independent assurance "
            "report as evidence for most sections. Tier 1 suppliers are "
            "reassessed on-site or remotely at least every two years."
        ),
    ),
    (
        "4. Contract clauses",
        (
            "Contracts with tier 1 and tier 2 suppliers include: security "
            "incident notification within 24 hours, approval of "
            "sub-processors, right to audit, data return and deletion at exit. "
            "Component and manufacturing suppliers also commit to provide an "
            "SBOM, to notify vulnerabilities in their components and to support "
            "them for our declared product support period. ICT services used by "
            f"{PAY_ENTITY} carry the contractual provisions required by DORA "
            "article 30 and are recorded in its register of information."
        ),
    ),
    (
        "5. Monitoring and exit",
        (
            "Supplier owners review performance and security findings every "
            "quarter. Access granted to a supplier is reviewed with the same "
            "cadence as employee access and removed on the day the contract "
            "ends. Each tier 1 supplier has a documented exit plan."
        ),
    ),
]

BACKUP = [
    (
        "Backup and Recovery Policy",
        "Supports the availability objectives of the Information Security Policy.",
    ),
    (
        "1. Scope",
        (
            "Device cloud databases, store and order databases, Kubernetes "
            "persistent volumes, corporate file shares, SaaS data exports and "
            "the plant SCADA and MES configurations listed in the asset "
            "inventory."
        ),
    ),
    (
        "2. Backup requirements",
        (
            "| Tier | Examples | Frequency | Retention | RPO |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Store checkout and payments, customer and device accounts, "
            "device cloud | Continuous + daily | 35 days, 12 monthly | 15 min |\n"
            "| 2 | Order fulfilment, plant SCADA and PLC programmes | Daily | 35 "
            "days | 24 h |\n"
            "| 3 | Internal tools | Weekly | 8 weeks | 7 days |"
        ),
    ),
    (
        "3. Protection of backups",
        (
            "Backups are encrypted with keys held outside the production "
            "account. At least one copy is immutable (object lock) and stored "
            "in a separate Kestrava Cloud region. Backup administrators cannot "
            "delete immutable copies before their retention expires. PLC "
            "programme backups are also kept offline at the plant."
        ),
    ),
    (
        "4. Restore testing",
        (
            "Each tier-1 system is restored in the isolated recovery "
            "environment every quarter, and tier-2 systems twice a year. The "
            "test record states the measured restore time against the recovery "
            "time objective and is filed as evidence."
        ),
    ),
]

INCIDENT_RESPONSE = [
    (
        "Incident Response Procedure",
        (
            "Trigger: any suspected security incident reported to the SOC, "
            "raised by monitoring, reported by a customer or researcher, or "
            "notified by a supplier."
        ),
    ),
    (
        "1. Report",
        (
            "Anyone who suspects an incident calls the SOC hotline or uses the "
            "*Report a security incident* form. Do not investigate on your own "
            "and do not power off affected machines or plant equipment."
        ),
    ),
    (
        "2. Triage and classify",
        (
            "The SOC analyst opens an incident ticket within 15 minutes and "
            "assigns a severity using the matrix attached to this procedure:\n\n"
            "| Severity | Examples | Response lead | Executive notice |\n"
            "|---|---|---|---|\n"
            "| SEV-1 | Ransomware on the plant, malicious OTA update, cardholder "
            "data breach | CISO | Immediate |\n"
            "| SEV-2 | Compromised admin account, exposed telemetry bucket | SOC "
            "lead | Within 4 h |\n"
            "| SEV-3 | Malware on a single endpoint | SOC analyst | Weekly report |"
        ),
    ),
    (
        "3. Contain, eradicate, recover",
        (
            "1. Isolate affected hosts through EDR network containment; for the "
            "plant, close the IT/OT conduits and run the line in island mode.\n"
            "2. For a product incident, halt OTA rollouts and revoke affected "
            "device certificates.\n"
            "3. Revoke and rotate exposed credentials and keys.\n"
            "4. Preserve evidence: memory capture before reimaging.\n"
            "5. Rebuild from known-good images, restore data from immutable "
            "backups and monitor closely for 14 days."
        ),
    ),
    (
        "4. Regulatory reporting clocks",
        (
            "The incident manager starts the clocks as soon as the incident is "
            "qualified; Legal and Compliance confirms each notification.\n\n"
            "| Regime | Trigger | Owner | Deadlines |\n|---|---|---|---|\n"
            "| NIS2 | Significant incident affecting our services | CISO | Early "
            "warning 24 h, notification 72 h, final report 1 month |\n"
            f"| DORA | Major ICT-related incident at {PAY_ENTITY} | Payments "
            "Risk Officer | Initial 4 h after classification (max 24 h after "
            "detection), intermediate 72 h, final 1 month |\n"
            "| CRA | Actively exploited product vulnerability or severe incident "
            "affecting product security | Head of Product Security | Early "
            "warning 24 h, notification 72 h, final report 14 days after the "
            "fix (vulnerability) or 1 month (incident) |\n"
            "| GDPR | Personal data breach | DPO | Supervisory authority 72 h; "
            "data subjects without undue delay if high risk |\n"
            "| PCI DSS | Suspected card data compromise | Payments Risk Officer | "
            "Pellion Payments within 24 h |"
        ),
    ),
    (
        "5. Post-incident review",
        (
            "SEV-1 and SEV-2 incidents get a blameless review within ten "
            "working days. Improvement actions are tracked as applied controls "
            "with an owner and an ETA."
        ),
    ),
]

VULNERABILITY = [
    (
        "Vulnerability Management Procedure",
        (
            "Trigger: a scanner finding, a vendor advisory or a pentest report "
            "on corporate IT, the device cloud or the online store. Product "
            "vulnerabilities follow the coordinated vulnerability disclosure "
            "policy."
        ),
    ),
    (
        "1. Scan",
        (
            "Internet-facing assets (online store web front, MQTT device "
            "gateway, VPN gateway) are scanned weekly with authenticated scans; "
            "internal networks monthly. Container images are scanned at build "
            "time and daily in the registry."
        ),
    ),
    (
        "2. Remediation deadlines",
        (
            "| Severity | Internet-facing | Internal |\n|---|---|---|\n"
            "| Critical | 7 days | 14 days |\n| High | 14 days | 30 days |\n"
            "| Medium | 60 days | 90 days |"
        ),
    ),
    (
        "3. Exceptions",
        (
            "Findings that cannot be fixed in time need a compensating control "
            "and a security exception approved by the CISO, valid for at most "
            "six months."
        ),
    ),
]

CHARTER = [
    (
        "Security Committee Charter",
        "Approved by the Executive Committee.",
    ),
    (
        "1. Mandate",
        (
            "The committee steers the security programme, arbitrates priorities "
            "and budget across projects, and reviews the risk register, product "
            "security posture and audit results before they go to the Executive "
            "Committee."
        ),
    ),
    (
        "2. Membership",
        (
            "Chair: CISO. Members: CIO, COO, Head of Product Security, Plant OT "
            "Engineering Manager, DPO, Payments Risk Officer, Head of "
            "Procurement, Head of Legal. The internal auditor attends as an "
            "observer."
        ),
    ),
    (
        "3. Cadence and quorum",
        (
            "The committee meets every quarter, and within 48 hours of any "
            "SEV-1 incident. Decisions require the chair and at least half of "
            "the members. Minutes are published within five working days."
        ),
    ),
]

MINUTES_Q2 = [
    (
        "Security Committee — Q2 2026",
        (
            "Attendees: CISO (chair), CIO, COO, Head of Product Security, Plant "
            "OT Engineering Manager, DPO, Payments Risk Officer. Apologies: Head "
            "of Procurement."
        ),
    ),
    (
        "Decisions",
        (
            "1. Funding for the Brno OT segmentation project is approved; work "
            "starts after the summer shutdown.\n"
            f"2. The {PAY_ENTITY} register of information is approved for "
            "submission to the competent authority.\n"
            "3. The committee confirms a five-year minimum support period for "
            "every product launched from 2027."
        ),
    ),
    (
        "Actions",
        (
            "| # | Action | Owner | Due |\n|---|---|---|---|\n"
            "| 1 | Publish the coordinated vulnerability disclosure policy | Head "
            "of Product Security | Next meeting |\n"
            "| 2 | Add SBOM and vulnerability notification clauses to the Shenwa "
            "and Orbisil contracts | Head of Procurement | Next meeting |\n"
            "| 3 | Book the Redhaven Security pentest of Keystone hub v3 | Head of "
            "Product Security | Six weeks |"
        ),
    ),
]

MINUTES_Q3 = [
    (
        "Security Committee — Q3 2026",
        (
            "Attendees: CISO (chair), CIO, COO, Head of Product Security, Plant "
            "OT Engineering Manager, DPO, Payments Risk Officer, Head of "
            "Procurement, Head of Legal."
        ),
    ),
    (
        "Decisions",
        (
            "1. CRA readiness is rated amber: the SBOM pipeline covers Keystone "
            "and Kelvin firmware, Lookout is blocked on SBOM delivery from "
            "Shenwa Contract Manufacturing.\n"
            "2. The residual risk of shared HMI accounts on assembly line 2 is "
            "accepted for six months with the compensating controls of the OT "
            "security policy.\n"
            "3. Checkout page script monitoring must be live before the "
            "November sales peak; PCI DSS fieldwork stays on its current date."
        ),
    ),
    (
        "Actions",
        (
            "| # | Action | Owner | Due |\n|---|---|---|---|\n"
            "| 1 | Escalate the Lookout SBOM delivery with Shenwa | Head of "
            "Procurement | Two weeks |\n"
            "| 2 | Run the incident tabletop on a malicious OTA update | CISO | "
            "Next meeting |\n"
            "| 3 | Confirm restore test results for the PostgreSQL primary | CIO | "
            "Two weeks |\n"
            "| 4 | Present the Keystone hub v3 pentest findings | Head of Product "
            "Security | Next meeting |"
        ),
    ),
]

NO_LINKS = {"policies": False, "controls": (), "assets": ()}

# ref_id, name, type, template ref_id,
# description, links,
# locales: {locale: (sections, [(status, day offset, change summary, comments)])}
DOCUMENTS = [
    (
        "POL-001",
        "Information Security Policy",
        "policy",
        "secpol-policy",
        "Top-level security policy approved by the Executive Committee.",
        {"policies": True, "controls": (), "assets": ()},
        {
            "en": (
                ISSP,
                [
                    (DEPRECATED, -400, "Initial issue.", ""),
                    (
                        PUBLISHED,
                        -35,
                        (
                            "Annual review: product security objectives and the "
                            "Cyber Resilience Act added, NIST CSF 2.0 named as "
                            "the baseline."
                        ),
                        "",
                    ),
                    (DRAFT, -3, "Add a principle on generative AI in engineering.", ""),
                ],
            ),
            "fr": (
                ISSP_FR,
                [(PUBLISHED, -30, "Traduction de la version 2.", "")],
            ),
        },
    ),
    (
        "POL-002",
        "Access Control Policy",
        "policy",
        "secpol-policy",
        "Account lifecycle, authentication, privileged access and reviews.",
        {
            "policies": False,
            "controls": ("AC.001", "AC.002"),
            "assets": ("Workforce identity provider",),
        },
        {
            "en": (
                ACCESS_CONTROL,
                [
                    (PUBLISHED, -210, "Initial issue.", ""),
                    (
                        IN_REVIEW,
                        -6,
                        (
                            "Just-in-time privileged access replaces standing "
                            "admin rights; FIDO2 keys for the release pipeline."
                        ),
                        "",
                    ),
                ],
            ),
        },
    ),
    (
        "POL-003",
        "Backup and Recovery Policy",
        "policy",
        "secpol-policy",
        "Backup tiers, protection of copies and restore testing.",
        {
            "policies": False,
            "controls": ("AC.003",),
            "assets": ("PostgreSQL primary", "S3 evidence bucket"),
        },
        {
            "en": (
                BACKUP,
                [
                    (DEPRECATED, -500, "Initial issue.", ""),
                    (DEPRECATED, -260, "Immutable copies made mandatory.", ""),
                    (PUBLISHED, -90, "Plant configurations added to tier 2.", ""),
                ],
            ),
        },
    ),
    (
        "PRO-001",
        "Incident Response Procedure",
        "procedure",
        "secpol-procedure",
        "From first report to post-incident review, with every reporting clock.",
        {"policies": False, "controls": ("AC.008",), "assets": ()},
        {
            "en": (
                INCIDENT_RESPONSE,
                [
                    (PUBLISHED, -150, "Initial issue.", ""),
                    (
                        CHANGE_REQUESTED,
                        -10,
                        "Add NIS2, DORA and CRA reporting clocks.",
                        (
                            "Please add the DORA major incident classification "
                            "criteria and state who decides that a product "
                            "vulnerability is actively exploited before "
                            "resubmitting."
                        ),
                    ),
                ],
            ),
        },
    ),
    (
        "POL-004",
        "Acceptable Use Policy",
        "policy",
        "secpol-policy",
        "Rules every account and device holder signs at onboarding.",
        NO_LINKS,
        {
            "en": (
                ACCEPTABLE_USE,
                [
                    (PUBLISHED, -300, "Initial issue.", ""),
                    (
                        VALIDATED,
                        -4,
                        "Public AI tools, prototypes and customer footage rules.",
                        "",
                    ),
                ],
            ),
            "fr": (
                ACCEPTABLE_USE_FR,
                [(PUBLISHED, -290, "Traduction de la version 1.", "")],
            ),
        },
    ),
    (
        "PRO-002",
        "Vulnerability Management Procedure",
        "procedure",
        "secpol-procedure",
        "Scanning cadence, remediation deadlines and exceptions for IT systems.",
        {
            "policies": False,
            "controls": ("AC.010",),
            "assets": ("Device cloud Kubernetes cluster", "Online store web front"),
        },
        {"en": (VULNERABILITY, [(DRAFT, -2, "First draft.", "")])},
    ),
    (
        "POL-005",
        "Coordinated Vulnerability Disclosure Policy",
        "policy",
        "secpol-product-standard",
        (
            "How researchers report product vulnerabilities and how the PSIRT "
            "handles, fixes, discloses and reports them under the CRA."
        ),
        {
            "policies": False,
            "controls": ("AC.010", "AC.015"),
            "assets": ("Device firmware and signing keys", "Companion mobile app"),
        },
        {
            "en": (
                CVD,
                [
                    (PUBLISHED, -120, "Initial issue.", ""),
                    (
                        IN_REVIEW,
                        -8,
                        (
                            "Reporting clocks aligned with the ENISA single "
                            "reporting platform; support period stated."
                        ),
                        "",
                    ),
                ],
            ),
        },
    ),
    (
        "POL-006",
        "Secure Development Lifecycle for Firmware",
        "policy",
        "secpol-product-standard",
        (
            "Threat modelling, secure coding, SBOM, signing and secure defaults for "
            "device firmware."
        ),
        {
            "policies": False,
            "controls": ("AC.006", "AC.013", "AC.014", "AC.015", "AC.018"),
            "assets": (
                "Firmware CI build farm",
                "Firmware signing HSM",
                "Device firmware and signing keys",
            ),
        },
        {
            "en": (
                FIRMWARE_SDL,
                [
                    (DEPRECATED, -380, "Initial issue.", ""),
                    (PUBLISHED, -140, "SBOM and reproducible builds required.", ""),
                    (
                        CHANGE_REQUESTED,
                        -12,
                        "Memory-safe languages for new components.",
                        (
                            "Exempt the vendor Thread stack from the "
                            "memory-safety rule explicitly, and reference the "
                            "Keystone hub v3 threat model as the worked example."
                        ),
                    ),
                ],
            ),
        },
    ),
    (
        "POL-007",
        "OT Security Policy — Brno Assembly Plant",
        "policy",
        "secpol-policy",
        "Zones and conduits, remote maintenance and change control for the plant OT.",
        {
            "policies": False,
            "controls": ("AC.007", "AC.012", "AC.017"),
            "assets": (
                "Production line control",
                "Plant SCADA server",
                "Assembly cell PLCs",
            ),
        },
        {
            "en": (
                OT_POLICY,
                [
                    (PUBLISHED, -180, "Initial issue.", ""),
                    (
                        VALIDATED,
                        -5,
                        "Remote maintenance through the new plant DMZ jump host.",
                        "",
                    ),
                ],
            ),
        },
    ),
    (
        "POL-008",
        "Supplier Security Policy",
        "policy",
        "secpol-policy",
        "Supplier tiers, due diligence, contract clauses and exit.",
        {"policies": False, "controls": ("AC.004",), "assets": ()},
        {
            "en": (
                SUPPLIER,
                [
                    (PUBLISHED, -240, "Initial issue.", ""),
                    (
                        DRAFT,
                        -2,
                        "DORA register of information and component supplier clauses.",
                        "",
                    ),
                ],
            ),
        },
    ),
    (
        "CHR-001",
        "Security Committee Charter",
        "charter",
        None,
        "Mandate, membership and cadence of the Security Committee.",
        NO_LINKS,
        {"en": (CHARTER, [(PUBLISHED, -330, "Initial issue.", "")])},
    ),
    (
        "REC-001",
        "Security Committee minutes — Q2 2026",
        "meeting_minutes",
        "secpol-minutes",
        "Decisions and actions of the quarterly Security Committee.",
        NO_LINKS,
        {"en": (MINUTES_Q2, [(PUBLISHED, -110, "Minutes approved.", "")])},
    ),
    (
        "REC-002",
        "Security Committee minutes — Q3 2026",
        "meeting_minutes",
        "secpol-minutes",
        "Decisions and actions of the quarterly Security Committee.",
        NO_LINKS,
        {"en": (MINUTES_Q3, [(PUBLISHED, -20, "Minutes approved.", "")])},
    ),
]

# A linked document lives on the intranet; the revision only carries its URL.
LINKED = (
    "STD-001",
    "Cryptography and Key Management Standard",
    "policy",
    (
        "Approved algorithms, key lengths and key custody, including device "
        "identity certificates and firmware signing keys. Maintained by the "
        "architecture team on the intranet."
    ),
    f"https://intranet.{MAIL_DOMAIN}/standards/cryptography",
    -60,
)

# Distinctive, fixed blob name: a domain flush cascades rows without deleting
# files, so a reseed reuses the blob instead of piling up suffixed copies.
ATTACHMENT_NAME = "demo-docs-incident-severity-matrix.png"


def at(ctx, offset):
    return datetime.combine(ctx.day(offset), time(10, 0), tzinfo=UTC)


def render(sections, keep):
    title, intro = sections[0]
    body = "\n\n".join(f"## {heading}\n\n{text}" for heading, text in sections[1:keep])
    return f"# {title}\n\n{intro}\n\n{body}\n"


def severity_matrix_png():
    """A small three-band severity legend (red / amber / green) as a PNG."""
    import struct
    import zlib

    width, height = 240, 90
    bands = [(220, 38, 38), (245, 158, 11), (16, 185, 129)]
    rows = b""
    for y in range(height):
        color = bands[min(y * len(bands) // height, len(bands) - 1)]
        rows += b"\x00" + bytes(color) * width

    def chunk(kind, data):
        payload = kind + data
        return (
            struct.pack(">I", len(data))
            + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


@register
class DocumentsBuilder(DemoBuilder):
    """Policy set with revisions across the editorial workflow."""

    name = "documents"
    depends = ("core",)
    covers: ClassVar[dict] = {
        DocumentContainer: "folder",
        ManagedDocument: "folder",
        DocumentRevision: "folder",
        DocumentAttachment: "folder",
        DocumentTemplate: "folder",
    }

    def stamps(self, ctx):
        folders = ctx.folders()
        return [
            (DocumentTemplate, {"folder": ctx.domain}, ("ref_id", "locale")),
            (DocumentContainer, {"folder__in": folders}, ("ref_id",)),
            (
                ManagedDocument,
                {"folder__in": folders},
                ("container__ref_id", "locale"),
            ),
            (
                DocumentRevision,
                {"folder__in": folders},
                ("document__container__ref_id", "document__locale", "version_number"),
            ),
            (
                DocumentAttachment,
                {"folder__in": folders},
                ("document__container__ref_id",),
            ),
        ]

    def build(self, ctx):
        self.build_templates(ctx)
        for spec in DOCUMENTS:
            self.build_document(ctx, *spec)
        self.build_linked(ctx)

    def build_templates(self, ctx):
        for ref_id, name, document_type, description, content in TEMPLATES:
            # (ref_id, locale) is unique instance-wide, not per folder.
            DocumentTemplate.objects.get_or_create(
                ref_id=ref_id,
                locale="en",
                defaults={
                    "name": name,
                    "folder": ctx.domain,
                    "document_type": document_type,
                    "description": description,
                    "provider": COMPANY,
                    "content": content,
                },
            )

    def build_document(
        self,
        ctx,
        ref_id,
        name,
        document_type,
        template,
        description,
        links,
        locales,
    ):
        folder = ctx.domain
        container, created = DocumentContainer.objects.get_or_create(
            name=name,
            folder=folder,
            defaults={
                "ref_id": ref_id,
                "document_type": document_type,
                "description": description,
            },
        )
        if not created:
            return
        if links["policies"]:
            container.policies.set(Policy.objects.filter(folder=ctx.domain))
        if links["controls"]:
            container.applied_controls.set(
                [c for c in ctx.refs["controls"] if c.ref_id in links["controls"]]
            )
        if links["assets"]:
            container.assets.set(
                [a for a in ctx.refs["assets"] if a.name in links["assets"]]
            )
        for index, (locale, (sections, revisions)) in enumerate(locales.items()):
            document = ManagedDocument.objects.create(
                container=container,
                folder=folder,
                name=sections[0][0],
                locale=locale,
                default_locale=index == 0,
                template_used=template,
            )
            self.build_revisions(ctx, document, sections, revisions)
            if ref_id == "PRO-001" and locale == "en":
                self.attach(document)

    def attach(self, document):
        attachment = DocumentAttachment(document=document)
        storage = attachment.file.storage
        if storage.exists(ATTACHMENT_NAME):
            attachment.file.name = ATTACHMENT_NAME
        else:
            attachment.file.save(
                ATTACHMENT_NAME, ContentFile(severity_matrix_png()), save=False
            )
        attachment.save()

    def build_revisions(self, ctx, document, sections, revisions):
        total = len(revisions)
        current = None
        for number, (status, offset, summary, comments) in enumerate(
            revisions, start=1
        ):
            # Earlier versions carry fewer sections, so diffs show real change.
            keep = max(3, len(sections) - (total - number))
            published = status in (PUBLISHED, DEPRECATED)
            revision = DocumentRevision.objects.create(
                document=document,
                version_number=number,
                content=render(sections, keep),
                status=status,
                change_summary=summary,
                reviewer_comments=comments or None,
                published_at=at(ctx, offset) if published else None,
            )
            # The serializer points a new document at v1; publishing moves it.
            if number == 1 or status == PUBLISHED:
                current = revision
        document.current_revision = current
        document.save()

    def build_linked(self, ctx):
        ref_id, name, document_type, description, url, offset = LINKED
        container, created = DocumentContainer.objects.get_or_create(
            name=name,
            folder=ctx.domain,
            defaults={
                "ref_id": ref_id,
                "document_type": document_type,
                "description": description,
            },
        )
        if not created:
            return
        document = ManagedDocument.objects.create(
            container=container, folder=ctx.domain, name=name, locale="en"
        )
        revision = DocumentRevision.objects.create(
            document=document,
            version_number=1,
            source=DocumentRevision.Source.LINK,
            url=url,
            status=PUBLISHED,
            change_summary="Linked to the intranet standard.",
            published_at=at(ctx, offset),
        )
        document.current_revision = revision
        document.save()
