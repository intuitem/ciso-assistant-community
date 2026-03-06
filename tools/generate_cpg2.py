#!/usr/bin/env python3
"""Generate CISA CPG 2.0 framework YAML for CISO Assistant."""

import yaml
import sys

# --- Data ---

LIBRARY_URN = "urn:intuitem:risk:library:cisa-cpg-2.0"
FRAMEWORK_URN = "urn:intuitem:risk:framework:cisa-cpg-2.0"
REQ_URN_PREFIX = "urn:intuitem:risk:req_node:cisa-cpg-2.0"
RC_URN_PREFIX = "urn:intuitem:risk:function:cisa-cpg-2.0"
THREAT_URN_PREFIX = "urn:intuitem:risk:threat:cisa-cpg-2.0"

FUNCTIONS = [
    (
        "GV",
        "GOVERN",
        "The organization's cybersecurity risk management strategy, expectations, and policy are established, communicated, and monitored.",
    ),
    (
        "ID",
        "IDENTIFY",
        "The organization's current cybersecurity risks are understood.",
    ),
    (
        "PR",
        "PROTECT",
        "Safeguards to manage the organization's cybersecurity risks are used.",
    ),
    (
        "DE",
        "DETECT",
        "Possible cybersecurity attacks and compromises are found and analyzed.",
    ),
    ("RS", "RESPOND", "Actions regarding a detected cybersecurity incident are taken."),
    (
        "RC",
        "RECOVER",
        "Assets and operations affected by a cybersecurity incident are restored.",
    ),
]

FUNCTIONS_FR = {
    "GV": (
        "GOUVERNER",
        "La stratégie, les attentes et la politique de gestion des risques de cybersécurité de l'organisation sont établies, communiquées et surveillées.",
    ),
    "ID": (
        "IDENTIFIER",
        "Les risques de cybersécurité actuels de l'organisation sont compris.",
    ),
    "PR": (
        "PROTÉGER",
        "Des mesures de protection sont utilisées pour gérer les risques de cybersécurité de l'organisation.",
    ),
    "DE": (
        "DÉTECTER",
        "Les attaques et compromissions potentielles en matière de cybersécurité sont détectées et analysées.",
    ),
    "RS": (
        "RÉPONDRE",
        "Des actions sont prises concernant un incident de cybersécurité détecté.",
    ),
    "RC": (
        "RÉTABLIR",
        "Les actifs et les opérations affectés par un incident de cybersécurité sont restaurés.",
    ),
}

SCORES_FR = {
    1: (
        "Non mis en œuvre",
        "L'objectif n'est pas traité. L'organisation n'a pris aucune mesure concernant les pratiques recommandées, ou les actions sont entièrement ponctuelles sans approche documentée.",
    ),
    2: (
        "Partiellement mis en œuvre",
        "Certaines actions recommandées sont en place mais la mise en œuvre est incomplète ou incohérente. Les pratiques peuvent être ponctuelles ou limitées à des domaines spécifiques de l'organisation.",
    ),
    3: (
        "Largement mis en œuvre",
        "La plupart des actions recommandées sont systématiquement appliquées dans l'ensemble de l'organisation. Les pratiques sont documentées, reproductibles et couvrent la majorité des actifs et processus concernés.",
    ),
    4: (
        "Entièrement mis en œuvre",
        "Toutes les actions recommandées sont en place, testées et continuellement améliorées. Les pratiques sont appliquées à l'échelle de l'organisation, régulièrement revues et adaptées en fonction des retours d'expérience et de l'évolution des menaces.",
    ),
}

# Threats distilled from TTP/Risk Addressed sections
# (ref_id, name, description)
THREATS = [
    (
        "T.01",
        "Insufficient Cybersecurity Governance",
        "Lack of sufficient cybersecurity accountability, investment, or effectiveness due to absent or inadequate policies, roles, and procedures for managing cybersecurity risk.",
    ),
    (
        "T.02",
        "Ineffective Incident Response",
        "Inability to quickly and effectively isolate, contain, eradicate, remediate, and communicate about cybersecurity incidents. Communication failures slow resolution, increase downtime, and amplify damage.",
    ),
    (
        "T.03",
        "Supply Chain Compromise",
        "Adversaries exploit vulnerabilities by abusing trusted third-party relationships, manipulating products or delivery mechanisms before they reach final users, or compromising vendor environments.",
    ),
    (
        "T.04",
        "Exploitation of Known Vulnerabilities",
        "Adversaries target unpatched and misconfigured systems, particularly those exposed to the internet, leveraging software vulnerabilities, temporary malfunctions, or configuration errors to gain initial access.",
    ),
    (
        "T.05",
        "Unvalidated Security Controls",
        "Gaps in cyber defenses or overconfidence in existing protections due to lack of independent validation that implemented controls are properly configured and working as intended.",
    ),
    (
        "T.06",
        "Insufficient Asset and Network Visibility",
        "Incomplete or inaccurate understanding of organizational assets, network topology, and security logs inhibits effective detection, incident response, and recovery.",
    ),
    (
        "T.07",
        "Default Credential Exploitation",
        "Adversaries acquire and exploit default manufacturer account credentials to gain initial access, maintain persistence, escalate privileges, or evade defenses.",
    ),
    (
        "T.08",
        "Brute Force and Password Attacks",
        "Adversaries use brute force techniques to crack passwords, systematically guessing credentials using repetitive or iterative methods against unknown passwords or obtained hashes.",
    ),
    (
        "T.09",
        "Credential Theft and Misuse",
        "Adversaries obtain and exploit account credentials through theft, reuse, or abuse of inactive accounts to gain access, maintain persistence, escalate privileges, or bypass network access controls.",
    ),
    (
        "T.10",
        "Unauthorized Access and Lateral Movement",
        "Unauthorized access to network resources enabling adversaries to move across systems undetected, escalate privileges, and compromise sensitive data and critical systems.",
    ),
    (
        "T.11",
        "Social Engineering and Phishing",
        "Adversaries use deceptive emails, malicious attachments or links, and social engineering tactics to trick users into revealing sensitive information, executing malicious code, or granting unauthorized access.",
    ),
    (
        "T.12",
        "Network Interception and Data Manipulation",
        "Adversaries position themselves between networked devices to enable network sniffing and data manipulation, or steal operational data for personal gain or future operations.",
    ),
    (
        "T.13",
        "Uncontained Network Compromise",
        "If a network is compromised by an unauthorized user, lack of segmentation allows malicious activity to spread uncontrolled across networks and critical infrastructure.",
    ),
    (
        "T.14",
        "Malware and Malicious Code",
        "Adversaries deploy malware including payloads, droppers, and backdoors to control remote machines, evade defenses, and execute post-compromise actions. Malware can spread via removable media to air-gapped networks.",
    ),
    (
        "T.15",
        "Unmanaged System Changes",
        "Delayed, insufficient, or incomplete ability to maintain or restore functionality of critical devices and service operations due to unauthorized or untested changes.",
    ),
    (
        "T.16",
        "Data Destruction and Service Disruption",
        "Adversaries disrupt critical systems, delete data, and disable recovery services to prevent system recovery, causing disruption to asset, service, or system availability.",
    ),
]

# Mapping of goal ref_id -> list of threat ref_ids
GOAL_THREATS = {
    "1.A": ["T.01"],
    "1.B": ["T.01"],
    "1.C": ["T.02"],
    "1.D": ["T.03"],
    "1.E": ["T.03"],
    "2.A": ["T.06"],
    "2.B": ["T.04"],
    "2.C": ["T.05"],
    "2.D": ["T.04"],
    "2.E": ["T.06"],
    "3.A": ["T.07", "T.10"],
    "3.B": ["T.08"],
    "3.C": ["T.09", "T.10"],
    "3.D": ["T.09"],
    "3.E": ["T.07"],
    "3.F": ["T.08", "T.10"],
    "3.G": ["T.09", "T.10"],
    "3.H": ["T.10"],
    "3.I": ["T.13", "T.10"],
    "3.J": ["T.11"],
    "3.K": ["T.12"],
    "3.L": ["T.11"],
    "3.M": ["T.11", "T.14"],
    "3.N": ["T.15"],
    "3.O": ["T.16"],
    "3.P": ["T.03"],
    "3.Q": ["T.06"],
    "3.R": ["T.14"],
    "3.S": ["T.04", "T.10"],
    "4.A": ["T.14"],
    "4.B": ["T.10"],
    "5.A": ["T.02"],
    "5.B": ["T.02"],
    "6.A": ["T.16", "T.02"],
}

THREATS_FR = {
    "T.01": (
        "Gouvernance insuffisante de la cybersécurité",
        "Manque de responsabilité, d'investissement ou d'efficacité en matière de cybersécurité en raison de l'absence ou de l'inadéquation des politiques, des rôles et des procédures de gestion des risques cyber.",
    ),
    "T.02": (
        "Réponse aux incidents inefficace",
        "Incapacité à isoler, contenir, éradiquer, remédier et communiquer rapidement et efficacement lors d'incidents de cybersécurité. Les défaillances de communication ralentissent la résolution, augmentent les temps d'arrêt et amplifient les dommages.",
    ),
    "T.03": (
        "Compromission de la chaîne d'approvisionnement",
        "Les adversaires exploitent les vulnérabilités en abusant des relations de confiance avec des tiers, en manipulant les produits ou les mécanismes de livraison avant qu'ils n'atteignent les utilisateurs finaux, ou en compromettant les environnements des fournisseurs.",
    ),
    "T.04": (
        "Exploitation de vulnérabilités connues",
        "Les adversaires ciblent les systèmes non corrigés et mal configurés, en particulier ceux exposés à Internet, en exploitant les vulnérabilités logicielles, les dysfonctionnements temporaires ou les erreurs de configuration pour obtenir un accès initial.",
    ),
    "T.05": (
        "Contrôles de sécurité non validés",
        "Lacunes dans les défenses cyber ou excès de confiance dans les protections existantes en raison d'un manque de validation indépendante du bon fonctionnement et de la configuration des contrôles mis en place.",
    ),
    "T.06": (
        "Visibilité insuffisante des actifs et du réseau",
        "Compréhension incomplète ou inexacte des actifs organisationnels, de la topologie réseau et des journaux de sécurité, entravant la détection efficace, la réponse aux incidents et la reprise d'activité.",
    ),
    "T.07": (
        "Exploitation des identifiants par défaut",
        "Les adversaires acquièrent et exploitent les identifiants de comptes par défaut du fabricant pour obtenir un accès initial, maintenir la persistance, élever les privilèges ou contourner les défenses.",
    ),
    "T.08": (
        "Attaques par force brute et sur les mots de passe",
        "Les adversaires utilisent des techniques de force brute pour craquer les mots de passe, en devinant systématiquement les identifiants par des méthodes répétitives ou itératives sur des mots de passe inconnus ou des condensats obtenus.",
    ),
    "T.09": (
        "Vol et utilisation abusive d'identifiants",
        "Les adversaires obtiennent et exploitent des identifiants de comptes par vol, réutilisation ou abus de comptes inactifs pour obtenir un accès, maintenir la persistance, élever les privilèges ou contourner les contrôles d'accès réseau.",
    ),
    "T.10": (
        "Accès non autorisé et mouvement latéral",
        "Accès non autorisé aux ressources réseau permettant aux adversaires de se déplacer entre les systèmes sans être détectés, d'élever les privilèges et de compromettre les données sensibles et les systèmes critiques.",
    ),
    "T.11": (
        "Ingénierie sociale et hameçonnage",
        "Les adversaires utilisent des courriels trompeurs, des pièces jointes ou liens malveillants et des tactiques d'ingénierie sociale pour inciter les utilisateurs à divulguer des informations sensibles, exécuter du code malveillant ou accorder un accès non autorisé.",
    ),
    "T.12": (
        "Interception réseau et manipulation de données",
        "Les adversaires se positionnent entre les équipements réseau pour permettre l'écoute et la manipulation de données, ou voler des données opérationnelles à des fins personnelles ou pour de futures opérations.",
    ),
    "T.13": (
        "Compromission réseau non contenue",
        "Si un réseau est compromis par un utilisateur non autorisé, l'absence de segmentation permet à l'activité malveillante de se propager de manière incontrôlée à travers les réseaux et les infrastructures critiques.",
    ),
    "T.14": (
        "Logiciels malveillants et code malveillant",
        "Les adversaires déploient des logiciels malveillants incluant des charges utiles, des téléchargeurs et des portes dérobées pour contrôler des machines à distance, contourner les défenses et exécuter des actions post-compromission. Les logiciels malveillants peuvent se propager via des supports amovibles vers des réseaux isolés.",
    ),
    "T.15": (
        "Changements système non maîtrisés",
        "Capacité retardée, insuffisante ou incomplète à maintenir ou restaurer le fonctionnement des dispositifs critiques et des opérations de service en raison de changements non autorisés ou non testés.",
    ),
    "T.16": (
        "Destruction de données et interruption de service",
        "Les adversaires perturbent les systèmes critiques, suppriment des données et désactivent les services de récupération pour empêcher la restauration des systèmes, causant une interruption de la disponibilité des actifs, services ou systèmes.",
    ),
}

# Reference controls distilled from recommended actions
# (ref_id, name, category, csf_function, description)
REFERENCE_CONTROLS = [
    (
        "RC.01",
        "Cybersecurity Roles and Responsibilities Policy",
        "policy",
        "govern",
        "Document all cybersecurity roles, responsibilities, and authorities in organizational policy. Distribute responsibilities across the organization, including third parties. Ensure legal and regulatory compliance.",
    ),
    (
        "RC.02",
        "Cybersecurity Policy Lifecycle Management",
        "policy",
        "govern",
        "Review cybersecurity policies annually and update when requirements, risks, threats, or technology changes. Communicate and enforce policies reflecting organizational strategy and priorities.",
    ),
    (
        "RC.03",
        "OT-Specific Security Policy",
        "policy",
        "govern",
        "Develop OT-specific cybersecurity policies acknowledging IT program limitations and critical function priorities. Establish governance encompassing regulatory, legal, risk, environmental, and operational obligations.",
    ),
    (
        "RC.04",
        "Incident Response Plan Management",
        "process",
        "govern",
        "Develop, maintain, update, and regularly exercise incident response plans for common and organizationally specific scenarios. Ensure realistic drills including all relevant stakeholders. Review and drill IR plans minimum annually. Account for OT-specific safety and containment considerations.",
    ),
    (
        "RC.05",
        "Supply Chain Incident Notification SLAs",
        "process",
        "govern",
        "Require vendors and service providers to notify customers of security incidents and vulnerabilities within risk-informed timeframes via SLAs and contracts.",
    ),
    (
        "RC.06",
        "OT Supply Chain Authenticity Verification",
        "process",
        "govern",
        "Document and track OT asset serial numbers, checksums, digital certificates/signatures to verify authenticity of hardware, software, and firmware.",
    ),
    (
        "RC.07",
        "Managed Service Provider Risk Management",
        "process",
        "govern",
        "Develop understanding of MSP services and security products. Understand contractual agreements and proactively address security gaps. Ensure contracts detail how and when MSPs notify customers of incidents.",
    ),
    (
        "RC.08",
        "Asset Inventory Management",
        "process",
        "identify",
        "Maintain regularly updated inventory of all organizational assets including data, hardware, software, systems, facilities, and personnel. Update critical IT/OT assets more frequently.",
    ),
    (
        "RC.09",
        "Vulnerability Management Program",
        "process",
        "identify",
        "Implement vulnerability management program to patch and mitigate misconfigured software timely. Monitor risk response progress via POA&M, risk registers, and risk detail reports. Assign responsibilities for processing cybersecurity threat, vulnerability, or incident disclosures.",
    ),
    (
        "RC.10",
        "Legacy System Compensating Controls",
        "technical",
        "identify",
        "Incorporate compensating security controls for legacy systems where patching is infeasible. For OT assets, apply compensating controls such as segmentation and monitoring, making assets inaccessible from public internet.",
    ),
    (
        "RC.11",
        "Independent Security Validation",
        "process",
        "identify",
        "Regularly engage third-party cybersecurity experts for penetration tests, bug bounties, incident simulations, and table-top exercises. Assess ability of adversaries to infiltrate and move laterally within networks. Ensure findings are addressed.",
    ),
    (
        "RC.12",
        "Vulnerability Disclosure Program",
        "process",
        "identify",
        "Maintain public, easily discoverable method for notifying security teams of vulnerable, misconfigured, or exploitable assets. Acknowledge valid submissions and respond timely. Protect good-faith reporters under safe harbor provisions. Apply security.txt files conforming to RFC 9116 on all public-facing web domains.",
    ),
    (
        "RC.13",
        "Network Topology Documentation",
        "process",
        "identify",
        "Maintain accurate documentation describing current network topology across all IT and OT networks. Perform network reviews and track annually; update when topology changes.",
    ),
    (
        "RC.14",
        "Default Password Elimination",
        "technical",
        "protect",
        "Require changing default manufacturer passwords for all hardware, software, and firmware before network connection. If infeasible (hard-coded passwords), document and implement compensating controls; monitor logs for network traffic and login attempts.",
    ),
    (
        "RC.15",
        "Password Strength Policy",
        "technical",
        "protect",
        "Enforce system policy establishing minimum password strength including 16+ character length for all password-protected IT and OT assets. Leverage passphrases and password managers. Prioritize upgrade/replacement of assets unable to support sufficient strength passwords.",
    ),
    (
        "RC.16",
        "Unique Credential Management",
        "process",
        "protect",
        "Create distinct, separate credentials for similar services and asset access across IT/OT networks. Ensure no password reuse across accounts. Unique passwords for admin/machine accounts. No universal NPE account passwords. Utilize role-based accounts.",
    ),
    (
        "RC.17",
        "Credential Revocation and Offboarding",
        "process",
        "protect",
        "Establish defined, enforced administrative offboarding process for staff, contractors, and vendors including return of physical tokens/badges and revocation of all system/facility access. Disable inactive accounts after specified period (e.g., 30 days) via automated process.",
    ),
    (
        "RC.18",
        "Failed Login Monitoring and Alerting",
        "technical",
        "protect",
        "Capture and log all unsuccessful logins per security policy. Alert security personnel after consecutive unsuccessful attempts and deviations from normal user behavior. Store alerts in security or ticketing system for retroactive analysis.",
    ),
    (
        "RC.19",
        "Multi-Factor Authentication Deployment",
        "technical",
        "protect",
        "Require MFA using strongest available method for assets with remote access. Prioritize phishing-resistant MFA (FIDO/WebAuthn or PKI-based), then mobile app-based soft tokens, then SMS/voice as last resort. Enable MFA on all remotely accessible OT accounts/systems.",
    ),
    (
        "RC.20",
        "Privileged Account Separation",
        "process",
        "protect",
        "Ensure user accounts lack administrator privileges. Administrators maintain separate user accounts for non-admin activities. Re-evaluate privileges on recurring basis. Maintain separation of duties across multiple individuals/roles.",
    ),
    (
        "RC.21",
        "Least Privilege Implementation",
        "process",
        "protect",
        "All user accounts, system roles, and processes operate with minimum privileges necessary for their tasks. Perform quarterly reviews of access permissions and role assignments validating policy compliance.",
    ),
    (
        "RC.22",
        "Network Segmentation",
        "technical",
        "protect",
        "Place routers between networks creating boundaries, increasing broadcast domains, and filtering broadcast traffic. Use boundaries to contain security breaches by restricting traffic to separate segments. Physically segment OT enclaves (e.g., data diodes) when applicable.",
    ),
    (
        "RC.23",
        "Cybersecurity Awareness and Training Program",
        "process",
        "protect",
        "Provide initial cybersecurity training before new employees access systems. Provide at least annual training covering social engineering, attack reporting, acceptable use, and basic cyber hygiene. Identify specialized roles requiring additional training. Provide OT personnel security awareness training.",
    ),
    (
        "RC.24",
        "Encryption and Cryptographic Controls",
        "technical",
        "protect",
        "Use encryption, digital signatures, and cryptographic hashes protecting network communication confidentiality and integrity. Identify critical data for protection in transit and at rest. Prevent plaintext storage of sensitive data and passwords. Use encryption for OT external connections where latency permits.",
    ),
    (
        "RC.25",
        "Email Security Configuration",
        "technical",
        "protect",
        "Enable STARTTLS, SPF, DKIM, and DMARC (set to reject) on all corporate email infrastructure to reduce risk from spoofing, phishing, and interception.",
    ),
    (
        "RC.26",
        "Macro and Autorun Restriction",
        "technical",
        "protect",
        "Enforce system-wide policy disabling macros or similar embedded code by default. Establish policy for authorized macro enablement on specific assets. Disable Autorun/AutoPlay by default preventing unintentional code execution.",
    ),
    (
        "RC.27",
        "Secure Change Management Process",
        "process",
        "protect",
        "Implement policies and processes for secure change management. Enforce configuration restrictions preventing unauthorized changes. Test and document proposed changes in non-production environments. Implement OT limited functionality permitting only necessary functions, protocols, and services.",
    ),
    (
        "RC.28",
        "Backup and Recovery Program",
        "process",
        "protect",
        "Develop list of all maintained backups including installation media, license keys, configuration information, and retention periods. Back up critical operations in near-real-time. Securely store backups offsite and offline. Test backups and recovery minimum annually. Validate integrity before restoration. Include OT device configurations and engineering drawings.",
    ),
    (
        "RC.29",
        "Hardware and Software Approval Process",
        "process",
        "protect",
        "Implement administrative policy requiring review, testing, and approval before new hardware, firmware, or software installation. Maintain approved list including versions. Consider OT environment additional requirements for patches/updates ensuring no operational or safety impact.",
    ),
    (
        "RC.30",
        "Security Log Collection and Management",
        "technical",
        "protect",
        "Collect and store administrative/security-focused logs (OS, applications, IDS/IPS, firewalls, DLP, VPNs). Store logs centrally in SIEM or database with restricted access. Store logs per risk-informed duration or regulatory guidelines. For OT assets with non-standard logs, collect network traffic.",
    ),
    (
        "RC.31",
        "Removable Media and Unauthorized Device Controls",
        "technical",
        "protect",
        "Maintain policies ensuring unauthorized media and hardware don't connect to IT/OT assets. Establish procedures removing, disabling, or securing physical ports preventing unauthorized device connection.",
    ),
    (
        "RC.32",
        "Internet-Facing Device Hardening",
        "technical",
        "protect",
        "Minimize internet-facing assets. Prioritize timely patches/updates. Disable unnecessary OS applications and network protocols. Never expose network management interfaces to public internet. Logically segment networks per trust boundaries and platform types.",
    ),
    (
        "RC.33",
        "Malicious Code Detection and Prevention",
        "technical",
        "detect",
        "Implement signature-based and non-signature-based mechanisms (behavior, heuristics, anomalies) detecting/eradicating malicious code at endpoints. Ensure antivirus software is updated, active, and configured for auto-scanning. Use OT-compatible antivirus with special change management practices.",
    ),
    (
        "RC.34",
        "Adverse Event Identification and Analysis",
        "process",
        "detect",
        "Define clear adverse event criteria and processes. Escalate suspected events per incident response plan. Automate event information analysis. Conduct analyst role-specific training. Account for OT-specific events and anomalies.",
    ),
    (
        "RC.35",
        "Incident Communication Procedures",
        "process",
        "respond",
        "Design communications plan identifying stakeholders and coordination mechanisms during incidents. Securely share information per response plans. Regularly update senior leadership. Notify HR on insider threats. Establish media communications procedures.",
    ),
    (
        "RC.36",
        "Incident Reporting Procedures",
        "process",
        "respond",
        "Maintain policy and procedures on reporting confirmed incidents to external entities (regulators, SRMAs, ISACs, ISAOs, CISA). Report within regulatory timeframes or as soon as safely feasible.",
    ),
    (
        "RC.37",
        "Incident Recovery and Lessons Learned",
        "process",
        "recover",
        "Execute plans recovering/restoring service to critical assets impacted by incidents. Enable degraded operations (paper, radio). Complete post-incident analysis identifying improvement areas. Incorporate lessons learned. Update policies, procedures, and training.",
    ),
]

RC_FR = {
    "RC.01": (
        "Politique de rôles et responsabilités en cybersécurité",
        "Documenter tous les rôles, responsabilités et autorités en matière de cybersécurité dans la politique organisationnelle. Répartir les responsabilités au sein de l'organisation, y compris avec les tiers. Assurer la conformité légale et réglementaire.",
    ),
    "RC.02": (
        "Gestion du cycle de vie des politiques de cybersécurité",
        "Réviser les politiques de cybersécurité annuellement et les mettre à jour en cas de changement des exigences, des risques, des menaces ou des technologies. Communiquer et appliquer les politiques reflétant la stratégie et les priorités organisationnelles.",
    ),
    "RC.03": (
        "Politique de sécurité spécifique aux OT",
        "Développer des politiques de cybersécurité spécifiques aux technologies opérationnelles (OT), tenant compte des limitations des programmes informatiques et des priorités des fonctions critiques. Établir une gouvernance englobant les obligations réglementaires, juridiques, environnementales et opérationnelles.",
    ),
    "RC.04": (
        "Gestion du plan de réponse aux incidents",
        "Développer, maintenir, mettre à jour et exercer régulièrement les plans de réponse aux incidents pour des scénarios courants et spécifiques à l'organisation. Garantir des exercices réalistes incluant toutes les parties prenantes. Réviser et tester les plans au minimum annuellement. Prendre en compte les considérations de sûreté et de confinement spécifiques aux OT.",
    ),
    "RC.05": (
        "SLA de notification d'incidents de la chaîne d'approvisionnement",
        "Exiger des fournisseurs et prestataires de services qu'ils notifient les clients des incidents de sécurité et des vulnérabilités dans des délais adaptés au risque, via des SLA et des contrats.",
    ),
    "RC.06": (
        "Vérification de l'authenticité de la chaîne d'approvisionnement OT",
        "Documenter et suivre les numéros de série, les sommes de contrôle, les certificats numériques et signatures des actifs OT pour vérifier l'authenticité du matériel, des logiciels et des micrologiciels.",
    ),
    "RC.07": (
        "Gestion des risques liés aux prestataires de services managés",
        "Développer la compréhension des services et produits de sécurité des MSP. Comprendre les accords contractuels et combler proactivement les lacunes de sécurité. S'assurer que les contrats précisent comment et quand les MSP notifient les clients des incidents.",
    ),
    "RC.08": (
        "Gestion de l'inventaire des actifs",
        "Maintenir un inventaire régulièrement mis à jour de tous les actifs organisationnels, incluant les données, le matériel, les logiciels, les systèmes, les installations et le personnel. Mettre à jour plus fréquemment les actifs IT/OT critiques.",
    ),
    "RC.09": (
        "Programme de gestion des vulnérabilités",
        "Mettre en œuvre un programme de gestion des vulnérabilités pour corriger et atténuer les logiciels mal configurés en temps voulu. Suivre l'avancement de la réponse aux risques via les POA&M, les registres de risques et les rapports détaillés. Attribuer les responsabilités pour le traitement des divulgations de menaces, vulnérabilités ou incidents.",
    ),
    "RC.10": (
        "Contrôles compensatoires pour les systèmes existants",
        "Incorporer des contrôles de sécurité compensatoires pour les systèmes existants lorsque la correction est impossible. Pour les actifs OT, appliquer des contrôles compensatoires tels que la segmentation et la surveillance, rendant les actifs inaccessibles depuis l'internet public.",
    ),
    "RC.11": (
        "Validation indépendante de la sécurité",
        "Engager régulièrement des experts tiers en cybersécurité pour des tests d'intrusion, des programmes de bug bounty, des simulations d'incidents et des exercices sur table. Évaluer la capacité des adversaires à infiltrer et se déplacer latéralement dans les réseaux. S'assurer que les conclusions sont traitées.",
    ),
    "RC.12": (
        "Programme de divulgation des vulnérabilités",
        "Maintenir une méthode publique et facilement accessible pour signaler aux équipes de sécurité les actifs vulnérables, mal configurés ou exploitables. Accuser réception des soumissions valides et y répondre dans des délais raisonnables. Protéger les personnes signalant les vulnérabilités de bonne foi. Appliquer les fichiers security.txt conformes à la RFC 9116 sur tous les domaines web publics.",
    ),
    "RC.13": (
        "Documentation de la topologie réseau",
        "Maintenir une documentation précise décrivant la topologie réseau actuelle pour tous les réseaux IT et OT. Effectuer des revues réseau et les suivre annuellement ; mettre à jour en cas de changement de topologie.",
    ),
    "RC.14": (
        "Élimination des mots de passe par défaut",
        "Exiger le changement des mots de passe par défaut du fabricant pour tout matériel, logiciel et micrologiciel avant la connexion au réseau. Si impossible (mots de passe codés en dur), documenter et mettre en œuvre des contrôles compensatoires ; surveiller les journaux de trafic réseau et de tentatives de connexion.",
    ),
    "RC.15": (
        "Politique de robustesse des mots de passe",
        "Appliquer une politique système établissant une robustesse minimale des mots de passe incluant une longueur de 16 caractères ou plus pour tous les actifs IT et OT protégés par mot de passe. Utiliser des phrases de passe et des gestionnaires de mots de passe. Prioriser la mise à niveau ou le remplacement des actifs ne pouvant pas supporter une robustesse suffisante.",
    ),
    "RC.16": (
        "Gestion des identifiants uniques",
        "Créer des identifiants distincts et séparés pour des services similaires et l'accès aux actifs entre les réseaux IT/OT. Garantir l'absence de réutilisation de mots de passe entre les comptes. Mots de passe uniques pour les comptes d'administration et de machines. Pas de mot de passe universel pour les comptes non personnels. Utiliser des comptes basés sur les rôles.",
    ),
    "RC.17": (
        "Révocation des identifiants et départ du personnel",
        "Établir un processus administratif défini et appliqué de départ pour le personnel, les prestataires et les fournisseurs, incluant la restitution des jetons physiques et badges, et la révocation de tous les accès aux systèmes et aux locaux. Désactiver les comptes inactifs après une période définie (par ex. 30 jours) via un processus automatisé.",
    ),
    "RC.18": (
        "Surveillance et alerte des tentatives de connexion échouées",
        "Capturer et journaliser toutes les tentatives de connexion infructueuses conformément à la politique de sécurité. Alerter le personnel de sécurité après des tentatives consécutives infructueuses et des écarts par rapport au comportement normal de l'utilisateur. Stocker les alertes dans un système de sécurité ou de tickets pour analyse rétrospective.",
    ),
    "RC.19": (
        "Déploiement de l'authentification multifacteur",
        "Exiger l'AMF en utilisant la méthode la plus forte disponible pour les actifs avec accès à distance. Prioriser l'AMF résistante à l'hameçonnage (FIDO/WebAuthn ou basée sur PKI), puis les jetons logiciels d'application mobile, puis SMS/voix en dernier recours. Activer l'AMF sur tous les comptes et systèmes OT accessibles à distance.",
    ),
    "RC.20": (
        "Séparation des comptes à privilèges",
        "S'assurer que les comptes utilisateurs ne disposent pas de privilèges d'administrateur. Les administrateurs maintiennent des comptes utilisateurs séparés pour les activités non administratives. Réévaluer les privilèges périodiquement. Maintenir la séparation des tâches entre plusieurs individus et rôles.",
    ),
    "RC.21": (
        "Mise en œuvre du moindre privilège",
        "Tous les comptes utilisateurs, rôles système et processus fonctionnent avec les privilèges minimaux nécessaires à leurs tâches. Effectuer des revues trimestrielles des permissions d'accès et des attributions de rôles pour valider la conformité à la politique.",
    ),
    "RC.22": (
        "Segmentation réseau",
        "Placer des routeurs entre les réseaux créant des limites, augmentant les domaines de diffusion et filtrant le trafic. Utiliser les limites pour contenir les violations de sécurité en restreignant le trafic à des segments séparés. Segmenter physiquement les enclaves OT (par ex. diodes de données) le cas échéant.",
    ),
    "RC.23": (
        "Programme de sensibilisation et de formation à la cybersécurité",
        "Fournir une formation initiale à la cybersécurité avant que les nouveaux employés n'accèdent aux systèmes. Fournir au moins une formation annuelle couvrant l'ingénierie sociale, le signalement des attaques, l'utilisation acceptable et l'hygiène cyber de base. Identifier les rôles spécialisés nécessitant une formation complémentaire. Former le personnel OT à la sensibilisation à la sécurité.",
    ),
    "RC.24": (
        "Chiffrement et contrôles cryptographiques",
        "Utiliser le chiffrement, les signatures numériques et les condensats cryptographiques pour protéger la confidentialité et l'intégrité des communications réseau. Identifier les données critiques à protéger en transit et au repos. Empêcher le stockage en clair des données sensibles et des mots de passe. Utiliser le chiffrement pour les connexions OT externes lorsque la latence le permet.",
    ),
    "RC.25": (
        "Configuration de la sécurité des courriels",
        "Activer STARTTLS, SPF, DKIM et DMARC (configuré sur « reject ») sur toute l'infrastructure de messagerie d'entreprise pour réduire les risques d'usurpation d'identité, d'hameçonnage et d'interception.",
    ),
    "RC.26": (
        "Restriction des macros et de l'exécution automatique",
        "Appliquer une politique système désactivant par défaut les macros ou le code embarqué similaire. Établir une politique pour l'activation autorisée des macros sur des actifs spécifiques. Désactiver l'exécution automatique (Autorun/AutoPlay) par défaut pour prévenir l'exécution involontaire de code.",
    ),
    "RC.27": (
        "Processus de gestion sécurisée des changements",
        "Mettre en œuvre des politiques et processus de gestion sécurisée des changements. Appliquer des restrictions de configuration empêchant les modifications non autorisées. Tester et documenter les changements proposés dans des environnements hors production. Mettre en œuvre une fonctionnalité limitée pour les OT ne permettant que les fonctions, protocoles et services nécessaires.",
    ),
    "RC.28": (
        "Programme de sauvegarde et de récupération",
        "Développer la liste de toutes les sauvegardes maintenues incluant les supports d'installation, les clés de licence, les informations de configuration et les durées de rétention. Sauvegarder les opérations critiques en quasi-temps réel. Stocker les sauvegardes hors site et hors ligne de manière sécurisée. Tester les sauvegardes et la récupération au minimum annuellement. Valider l'intégrité avant la restauration. Inclure les configurations des équipements OT et les schémas techniques.",
    ),
    "RC.29": (
        "Processus d'approbation du matériel et des logiciels",
        "Mettre en œuvre une politique administrative exigeant la revue, les tests et l'approbation avant l'installation de tout nouveau matériel, micrologiciel ou logiciel. Maintenir une liste approuvée incluant les versions. Prendre en compte les exigences supplémentaires de l'environnement OT pour les correctifs et mises à jour afin de ne pas impacter les opérations ou la sûreté.",
    ),
    "RC.30": (
        "Collecte et gestion des journaux de sécurité",
        "Collecter et stocker les journaux d'administration et de sécurité (systèmes d'exploitation, applications, IDS/IPS, pare-feux, DLP, VPN). Stocker les journaux de manière centralisée dans un SIEM ou une base de données avec accès restreint. Conserver les journaux selon des durées adaptées au risque ou aux exigences réglementaires. Pour les actifs OT avec des journaux non standards, collecter le trafic réseau.",
    ),
    "RC.31": (
        "Contrôles des supports amovibles et des dispositifs non autorisés",
        "Maintenir des politiques garantissant que les supports et matériels non autorisés ne se connectent pas aux actifs IT/OT. Établir des procédures pour retirer, désactiver ou sécuriser les ports physiques afin d'empêcher la connexion de dispositifs non autorisés.",
    ),
    "RC.32": (
        "Durcissement des dispositifs exposés à Internet",
        "Minimiser les actifs exposés à Internet. Prioriser les correctifs et mises à jour en temps voulu. Désactiver les applications et protocoles réseau inutiles du système d'exploitation. Ne jamais exposer les interfaces de gestion réseau sur l'Internet public. Segmenter logiquement les réseaux selon les périmètres de confiance et les types de plateformes.",
    ),
    "RC.33": (
        "Détection et prévention du code malveillant",
        "Mettre en œuvre des mécanismes basés sur les signatures et non basés sur les signatures (comportement, heuristique, anomalies) pour détecter et éradiquer le code malveillant sur les terminaux. S'assurer que l'antivirus est à jour, actif et configuré pour l'analyse automatique. Utiliser un antivirus compatible OT avec des pratiques spéciales de gestion des changements.",
    ),
    "RC.34": (
        "Identification et analyse des événements indésirables",
        "Définir des critères et des processus clairs pour les événements indésirables. Escalader les événements suspects selon le plan de réponse aux incidents. Automatiser l'analyse des informations sur les événements. Former les analystes aux protocoles spécifiques. Prendre en compte les événements et anomalies spécifiques aux OT.",
    ),
    "RC.35": (
        "Procédures de communication en cas d'incident",
        "Concevoir un plan de communication identifiant les parties prenantes et les mécanismes de coordination lors des incidents. Partager l'information de manière sécurisée selon les plans de réponse. Informer régulièrement la direction. Notifier les RH en cas de menace interne. Établir des procédures de communication médiatique.",
    ),
    "RC.36": (
        "Procédures de signalement des incidents",
        "Maintenir une politique et des procédures de signalement des incidents confirmés aux entités externes (régulateurs, autorités sectorielles, ISAC, ISAO, CISA). Signaler dans les délais réglementaires ou dès que possible en toute sécurité.",
    ),
    "RC.37": (
        "Récupération après incident et retour d'expérience",
        "Exécuter les plans de récupération et de restauration des services pour les actifs critiques impactés par les incidents. Permettre les opérations en mode dégradé (papier, radio). Réaliser une analyse post-incident identifiant les axes d'amélioration. Intégrer les retours d'expérience. Mettre à jour les politiques, procédures et formations.",
    ),
}

# Goals: (ref_id, name, function_ref, outcome, risk, recommended_actions_text, cost, impact, ease, control_refs)
GOALS = [
    (
        "1.A",
        "Establish Cybersecurity Responsibilities",
        "GV",
        "Roles, responsibilities, and authorities related to the organization's cybersecurity program are established, communicated, enforced, and aligned within the organization and external partners.",
        "Lack of sufficient cybersecurity accountability, investment, or effectiveness.",
        "- Document all cybersecurity roles and responsibilities in organizational policy\n- Distribute cybersecurity responsibilities across the organization; third parties may assist\n- Implement legal and regulatory cybersecurity requirements, including privacy\n- Establish continuous IT/OT team collaboration for security and operational effectiveness",
        "Low",
        "High",
        "Moderate",
        ["RC.01", "RC.03"],
    ),
    (
        "1.B",
        "Manage Cybersecurity Oversight",
        "GV",
        "The organization's cybersecurity risk management strategy, expectations, and policies are established.",
        "Insufficient cybersecurity policies and procedures/practices that can manage cybersecurity risk for the organization's technologies and processes.",
        "- Review cybersecurity policies annually; update when requirements, risks, threats, or technology changes\n- Communicate and enforce policies reflecting organizational strategy and priorities\n- Establish governance encompassing regulatory, legal, risk, environmental, and operational obligations\n- Develop OT-specific policies acknowledging IT program limitations and critical function priorities",
        "Low",
        "High",
        "Moderate",
        ["RC.02", "RC.03"],
    ),
    (
        "1.C",
        "Manage Incident Response Plans",
        "GV",
        "Identify improvements by practicing cybersecurity and incident response plans to maintain and update the organization's cybersecurity program.",
        "Inability to quickly and effectively isolate, contain, eradicate, remediate, and communicate about cybersecurity incidents.",
        "- Develop, maintain, update, and regularly exercise IR plans for common and organizationally specific scenarios\n- Ensure realistic drills including all relevant stakeholders\n- Review and drill IR plans minimum annually\n- Account for OT-specific safety and containment considerations",
        "Low",
        "High",
        "Moderate",
        ["RC.04"],
    ),
    (
        "1.D",
        "Supply Chain Incident Reporting & Vulnerability Disclosure",
        "GV",
        "Organizations more rapidly learn about and respond to known incidents or breaches across vendors and service providers.",
        "Insufficient cybersecurity supply chain risk management (C-SCRM) practices that cannot securely support the organization's technologies and processes.",
        "- Require vendors/service providers to notify customers of security incidents and vulnerabilities within risk-informed timeframes via SLAs and contracts\n- Document and track OT asset serial numbers, checksums, digital certificates/signatures to verify authenticity of hardware, software, and firmware",
        "Moderate",
        "Moderate",
        "Complex",
        ["RC.05", "RC.06"],
    ),
    (
        "1.E",
        "Manage Risks from Managed Service Providers",
        "GV",
        "The risks posed by a managed service provider (MSP) are identified, recorded, assessed, prioritized, monitored, and updated over the course of the relationship.",
        "Adversaries can exploit vulnerabilities by abusing trusted third-party relationships.",
        "- Develop understanding of MSP services and security products\n- Understand contractual agreements and proactively address security gaps outside contract scope\n- Ensure contracts detail how and when MSPs notify customers of incidents affecting their environment",
        "Moderate",
        "Moderate",
        "Complex",
        ["RC.07"],
    ),
    (
        "2.A",
        "Manage Organizational Assets",
        "ID",
        "A maintained asset inventory to improve cybersecurity resilience by reducing downtime, aiding recovery, bolstering defenses, and improving preparedness.",
        "Adversaries might use computer accessories, networking hardware, or other devices as entry points to infiltrate systems or networks.",
        "- Maintain regularly updated inventory of all organizational assets including data, hardware, software, systems, facilities, and personnel\n- Update critical IT/OT assets more frequently",
        "Low",
        "High",
        "Moderate",
        ["RC.08"],
    ),
    (
        "2.B",
        "Mitigate Known Vulnerabilities",
        "ID",
        "Reduced likelihood of threat actors exploiting known vulnerabilities to breach organizational networks.",
        "Adversaries frequently target unpatched and misconfigured systems, particularly those exposed to the internet. Adversaries often leverage software vulnerabilities, temporary malfunctions, or configuration errors to gain initial access to a network.",
        "- Implement vulnerability management program to patch and mitigate misconfigured software timely\n- Monitor risk response progress via POA&M, risk registers, and risk detail reports\n- Document potential risks of proposed changes; provide rollback guidance\n- Assign responsibilities for processing cybersecurity threat, vulnerability, or incident disclosures\n- Incorporate compensating security controls for legacy systems where possible\n- For OT assets where patching is infeasible, apply compensating controls (segmentation, monitoring)",
        "High",
        "High",
        "Complex",
        ["RC.09", "RC.10", "RC.27"],
    ),
    (
        "2.C",
        "Obtain Independent Validation of Cybersecurity Controls",
        "ID",
        "Validate that implemented security controls are properly configured and working as intended.",
        "Gaps in cyber defenses or overconfidence in existing protections.",
        "- Regularly engage third-party cybersecurity experts for penetration tests, bug bounties, incident simulations, and table-top exercises\n- Assess ability of adversaries to infiltrate and move laterally within networks targeting critical systems\n- Ensure findings from tests are addressed",
        "High",
        "High",
        "Complex",
        ["RC.11"],
    ),
    (
        "2.D",
        "Maintain Vulnerability Disclosure/Reporting Process",
        "ID",
        "Organizations more rapidly learn about vulnerabilities or weaknesses.",
        "Unreported security vulnerabilities in software, networks, devices, and systems can be exploited by adversaries before they are mitigated.",
        "- Maintain public, easily discoverable method for notifying security teams of vulnerable, misconfigured, or exploitable assets via email or web form\n- Acknowledge valid submissions and respond timely considering completeness and complexity\n- Mitigate validated, exploitable weaknesses consistently with severity\n- Protect individuals identifying/reporting vulnerabilities in good faith under safe harbor provisions\n- Apply security.txt files conforming to RFC 9116 on all public-facing web domains",
        "Low",
        "Low",
        "Moderate",
        ["RC.12"],
    ),
    (
        "2.E",
        "Document Network Topology",
        "ID",
        "More efficiently and effectively respond to incidents and maintain service continuity.",
        "Incomplete or inaccurate understanding of network topology inhibits effective incident response and recovery.",
        "- Maintain accurate documentation describing current network topology and relevant information across all IT and OT networks\n- Perform network reviews and track annually; update when topology changes",
        "Low",
        "High",
        "Moderate",
        ["RC.13"],
    ),
    (
        "3.A",
        "Changing Default Passwords",
        "PR",
        "Prevent threat actors from using default passwords to achieve initial access and move laterally in a network.",
        "Adversaries might acquire and exploit default account credentials to gain initial access, maintain persistence, escalate privileges, or evade defenses.",
        "- Require changing default manufacturer passwords for all hardware, software, and firmware before network connection\n- If infeasible (hard-coded passwords), document and implement compensating controls; monitor logs for network traffic and login attempts\n- Change default passwords on existing OT systems; establish policy for all new/future devices",
        "Low",
        "High",
        "Simple",
        ["RC.14", "RC.18"],
    ),
    (
        "3.B",
        "Establish Minimum Password Strength",
        "PR",
        "Organizational passwords are harder for threat actors to guess or crack.",
        "Adversaries use brute force techniques to crack passwords when unknown or hashes are obtained. They systematically guess passwords using repetitive or iterative methods.",
        "- Enforce system policy establishing minimum password strength including 16+ character length for all password-protected IT and OT assets\n- Leverage passphrases and password managers for longer passwords\n- When minimum lengths are infeasible, apply compensating controls and record them; log all login attempts\n- Prioritize upgrade/replacement of assets unable to support sufficient strength passwords",
        "Low",
        "High",
        "Simple",
        ["RC.15", "RC.18"],
    ),
    (
        "3.C",
        "Create Unique Credentials",
        "PR",
        "Adversaries are unable to reuse compromised credentials to move laterally across the organization, particularly between IT and OT networks.",
        "Adversaries can obtain and exploit account credentials to gain access, maintain persistence, escalate privileges, or evade defenses. Compromised credentials can bypass network access controls.",
        "- Create distinct, separate credentials for similar services and asset access across IT/OT networks\n- Users refrain from reusing passwords across accounts, applications, and services\n- System administrators and service/machine accounts have unique passwords\n- No universal non-person entity (NPE) account passwords\n- Utilize role-based accounts for IT/OT systems when possible",
        "Low",
        "High",
        "Simple",
        ["RC.16"],
    ),
    (
        "3.D",
        "Revoking Credentials for Departing Staff",
        "PR",
        "Prevent unauthorized access to organizational accounts or resources by former staff.",
        "Adversaries can exploit inactive accounts of former staff to evade detection.",
        "- Establish defined, enforced administrative offboarding process for staff, contractors, vendors including return of physical tokens/badges and revocation of all system/facility access\n- Review user access and disable inactive accounts after specified period (e.g., 30 days), ideally via automated process",
        "Low",
        "High",
        "Moderate",
        ["RC.17"],
    ),
    (
        "3.E",
        "Monitor Unsuccessful (Automated) Login Attempts",
        "PR",
        "Protect organizations from automated, credential-based attacks.",
        "Adversaries might acquire and exploit default account credentials to gain access, maintain persistence, escalate privileges, or evade defenses.",
        "- Capture and log all unsuccessful logins per organization's security policy\n- Notify security personnel after consecutive unsuccessful attempts and deviations from normal behavior\n- Log and store alerts in relevant security or ticketing system for retroactive analysis",
        "Moderate",
        "High",
        "Moderate",
        ["RC.18", "RC.30"],
    ),
    (
        "3.F",
        "Implement Multi-factor Authentication",
        "PR",
        "Add a critical, additional layer of security to protect asset accounts.",
        "Adversaries without prior knowledge of legitimate credentials might try commonly used passwords across various accounts. They might also systematically guess passwords using repetitive or iterative methods.",
        "- Require MFA using strongest available method for assets with remote access\n- MFA options ranked by strength: (1) Phishing-resistant MFA (FIDO/WebAuthn or PKI-based), (2) Mobile app-based soft tokens, (3) SMS/voice only when no other options available\n- All IT accounts leverage MFA; prioritize highest-risk accounts\n- OT: Enable MFA on all remotely accessible accounts/systems; if unavailable, remove remote access, add segmentation",
        "Moderate",
        "High",
        "Moderate",
        ["RC.19", "RC.22"],
    ),
    (
        "3.G",
        "Administrators Maintain Separate User and Privileged Accounts",
        "PR",
        "Make it harder for threat actors to gain access to administrator or privileged accounts, even if common user accounts are compromised.",
        "Adversaries might obtain and exploit credentials from existing accounts for initial access, persistence, privilege escalation, or defense evasion.",
        "- User accounts lack administrator privileges\n- Administrators maintain separate user accounts for non-admin activities\n- Re-evaluate privileges on recurring basis validating continued need\n- Maintain separation of duties distributing responsibilities across multiple individuals/roles",
        "Low",
        "High",
        "Simple",
        ["RC.20"],
    ),
    (
        "3.H",
        "Implement the Principles of Least Privilege",
        "PR",
        "Minimizes unauthorized access to systems, data, and processes, reduces human error, and prevents malicious actions.",
        "Unauthorized access to network resources and the potential for adversaries to move across systems undetected, compromising sensitive data and critical systems.",
        "- All user accounts, system roles, and processes operate with minimum privileges necessary\n- Perform quarterly reviews of access permissions and role assignments validating policy compliance",
        "Low",
        "High",
        "Simple",
        ["RC.21"],
    ),
    (
        "3.I",
        "Implement Logical/Physical Network Segmentation",
        "PR",
        "Limiting the impact of a potential breach and preventing adversaries from accessing sensitive data, spaces, and/or critical infrastructure.",
        "If a network is compromised by an unauthorized user, a securely segregated network can contain malicious occurrences.",
        "- Place routers between networks creating boundaries, increasing broadcast domains, and filtering broadcast traffic\n- Use boundaries to contain security breaches by restricting traffic to separate segments and shutting down segments during intrusion\n- Physically segment OT enclaves (e.g., data diodes) when applicable",
        "High",
        "High",
        "Complex",
        ["RC.22"],
    ),
    (
        "3.J",
        "Implement Cybersecurity Training",
        "PR",
        "Organizational users learn and perform more secure behaviors.",
        "Users vulnerable to spear phishing, social engineering, and other techniques that involve user interaction.",
        "- Provide initial cybersecurity training before new employees access computer systems\n- Provide at least annual training covering social engineering recognition, attack reporting, acceptable use, and basic cyber hygiene\n- Identify specialized roles requiring additional training\n- Provide role-based training to specialized roles including contractors, partners, suppliers\n- Provide OT personnel security awareness training",
        "Low",
        "High",
        "Moderate",
        ["RC.23"],
    ),
    (
        "3.K",
        "Utilize Strong Encryption",
        "PR",
        "Encryption is deployed to maintain confidentiality and integrity of sensitive data across the organization's network.",
        "Adversaries can position themselves between networked devices to enable network sniffing and data manipulation, or steal operational data for personal gain or future operations.",
        "- Use encryption, digital signatures, and cryptographic hashes protecting network communication confidentiality and integrity\n- Identify critical data for protection in transit and at rest (PII, proprietary information, PLC programs, CAD/CAM files)\n- Prevent plaintext electronic storage of sensitive data and passwords\n- Store credentials securely via credential/password managers\n- Use encryption for OT external connections where latency permits",
        "Moderate",
        "High",
        "Complex",
        ["RC.24"],
    ),
    (
        "3.L",
        "Enable Email Security",
        "PR",
        "Reduce risk from common email-based threats, such as spoofing, phishing, and interception.",
        "Adversaries might send victims emails with malicious attachments or links, aiming to run harmful code on their systems. They can also conduct phishing through third-party services.",
        "- Enable STARTTLS on all corporate email infrastructure\n- Enable Sender Policy Framework (SPF)\n- Enable DomainKeys Identified Mail (DKIM)\n- Enable DMARC and set to 'reject'",
        "Low",
        "High",
        "Moderate",
        ["RC.25"],
    ),
    (
        "3.M",
        "Disable Autorun & Macros By Default",
        "PR",
        "Reduce the risk from embedded macros and similar executable code.",
        "Adversaries rely on users to open malicious files to execute code. Social engineering tactics could be used to convince users to open such files.",
        "- Enforce system-wide policy disabling macros or similar embedded code by default\n- Establish policy for authorized users requesting macro enablement on specific assets\n- Disable Autorun/AutoPlay by default",
        "Low",
        "Moderate",
        "Simple",
        ["RC.26"],
    ),
    (
        "3.N",
        "Establish Change Management Processes",
        "PR",
        "Policies and procedures exist to manage system changes and configurations.",
        "Delayed, insufficient, or incomplete ability to maintain or restore functionality of critical devices and service operations.",
        "- Implement policies and processes for secure change management\n- Enforce configuration restrictions preventing unauthorized changes\n- Test and document proposed changes in non-production environments; analyze security impacts\n- Implement OT limited functionality permitting only necessary functions, protocols, and services",
        "Moderate",
        "High",
        "Complex",
        ["RC.27"],
    ),
    (
        "3.O",
        "Maintain System Backups & Restoration Ability",
        "PR",
        "Organizations reduce data loss and service disruption risks while efficiently managing, responding to, and recovering from incidents.",
        "Adversaries can disrupt critical systems, delete data, and disable recovery services to prevent system recovery.",
        "- Develop list of all maintained backups including installation media, license keys, configuration information, and retention periods\n- Back up critical operations systems in near-real-time; frequently back up all operational systems\n- Securely store backups offsite and offline\n- Test backups and recovery minimum annually\n- Validate backup integrity before initiating restoration\n- Check restoration assets for indicators of compromise\n- OT: Include device configurations, roles, engineering drawings, and tools",
        "High",
        "High",
        "Moderate",
        ["RC.28"],
    ),
    (
        "3.P",
        "Maintain Hardware & Software Approval Process",
        "PR",
        "Increase visibility into deployed technology assets and reduce the likelihood of breach by users installing unapproved hardware, firmware, or software.",
        "Adversaries can manipulate products or delivery mechanisms before they reach final users and attempt data or system compromise.",
        "- Implement administrative policy requiring review, testing, and approval before new hardware, firmware, or software installation\n- Maintain approved hardware, firmware, and software list including approved versions\n- Consider OT environment additional requirements for patches/updates ensuring no operational or safety impact",
        "Moderate",
        "High",
        "Moderate",
        ["RC.29"],
    ),
    (
        "3.Q",
        "Maintain Log Collection & Storage",
        "PR",
        "Enhance visibility to detect and respond to cyber incidents while ensuring security logs are protected from unauthorized access and tampering.",
        "Delayed, insufficient, or incomplete ability to detect and respond to potential cyber incidents.",
        "- Collect and store administrative/security-focused logs (OS, applications, IDS/IPS, firewalls, DLP, VPNs)\n- Store logs centrally (SIEM tool or database); only authorized, authenticated users access/modify\n- Store logs per risk-informed duration or regulatory guidelines\n- Notify security teams when critical log functions are disabled\n- For OT assets with non-standard logs, collect network traffic between those assets",
        "Moderate",
        "High",
        "Moderate",
        ["RC.30"],
    ),
    (
        "3.R",
        "Prohibit Connection of Unauthorized Devices",
        "PR",
        "Prevent malicious actors from achieving initial access or data exfiltration via unauthorized portable media devices.",
        "Adversaries might infiltrate systems, including disconnected or air-gapped networks, by copying malware to removable media.",
        "- Maintain policies ensuring unauthorized media and hardware don't connect to IT/OT assets\n- Establish procedures removing, disabling, or securing physical ports preventing unauthorized device connection",
        "Moderate",
        "High",
        "Complex",
        ["RC.31"],
    ),
    (
        "3.S",
        "Secure Internet Facing Devices",
        "PR",
        "Unauthorized users cannot gain an initial system foothold by exploiting known weaknesses in internet-facing assets.",
        "Adversaries might exploit weaknesses in internet-facing hosts or systems targeting software bugs, temporary glitches, or misconfigurations.",
        "- Minimize internet-facing assets whenever possible\n- Prioritize keeping software current via timely patches/updates\n- Disable all unnecessary OS applications, software, and network protocols on internet-facing assets\n- Never expose network management interfaces to public internet\n- Logically segment enterprise and production networks per trust boundaries and platform types",
        "Moderate",
        "High",
        "Complex",
        ["RC.32", "RC.22", "RC.09"],
    ),
    (
        "4.A",
        "Establish Malicious Code Detection",
        "DE",
        "Enables early threat identification, strengthens system integrity, provides insights for faster remediation, and minimizes downtime.",
        "Malicious software can involve payloads, droppers, backdoors, etc. Adversaries use malware to control remote machines, evade defenses, and execute post-compromise actions.",
        "- Implement signature-based and non-signature-based mechanisms detecting/eradicating malicious code at endpoints\n- Ensure antivirus software is updated, active, and configured for auto-scanning emails and removable media\n- Use OT-compatible antivirus with special practices including compatibility checks and performance testing",
        "Moderate",
        "High",
        "Moderate",
        ["RC.33"],
    ),
    (
        "4.B",
        "Identify Adverse Events",
        "DE",
        "Organizations can identify adverse security events.",
        "Initial access, privilege escalation, and lateral movement.",
        "- Define clear adverse event criteria and processes; escalate suspected events per incident response plan\n- Automate event information analysis accelerating investigative timelines\n- Conduct analyst role-specific training on proper protocols for suspected cyber incidents\n- Account for OT-specific events and anomalies",
        "Moderate",
        "High",
        "Complex",
        ["RC.34", "RC.04"],
    ),
    (
        "5.A",
        "Establish Incident Communication Procedures",
        "RS",
        "Coordinate crisis communication methods between internal and external organization partners and critical suppliers.",
        "Without established communication procedures, incidents can disrupt coordination among response teams, slowing incident resolution, increasing downtime, and amplifying overall damage.",
        "- Design communications plan identifying stakeholders and coordination mechanisms during incidents\n- Collaborate with stakeholders; securely share information per response plans\n- Regularly update senior leadership on major incident status\n- Notify human resources when malicious insider activity occurs\n- Establish and follow media communications procedures",
        "Low",
        "High",
        "Moderate",
        ["RC.35"],
    ),
    (
        "5.B",
        "Establish Incident Reporting Procedures",
        "RS",
        "CISA and other organizations are better able to provide assistance or understand the broader scope of a cyber incident.",
        "Without timely incident reporting, CISA and other groups are less able to assist affected organizations and lack critical insight into the broader threat landscape.",
        "- Maintain policy and procedures on reporting confirmed incidents to external entities (regulators, SRMAs, ISACs, ISAOs, CISA)\n- Report known incidents within regulatory timeframes or as soon as safely feasible",
        "Moderate",
        "High",
        "Moderate",
        ["RC.36"],
    ),
    (
        "6.A",
        "Incident Planning and Preparedness",
        "RC",
        "Organizations are capable of safely and effectively recovering from a cybersecurity incident.",
        "Disruption to the availability of an asset, service, or system.",
        "- Execute plans recovering/restoring service to critical assets impacted by incidents\n- Enable degraded operations (paper-based, radio communications) without critical assets or internet\n- Complete post-incident analysis identifying improvement areas\n- Incorporate lessons learned; enhance detection/response capabilities\n- Update policies, procedures, and training; ensure stakeholder awareness of changes",
        "Moderate",
        "High",
        "Complex",
        ["RC.37", "RC.02", "RC.23"],
    ),
]

# French translations for goals: ref_id -> (name_fr, description_fr, actions_fr)
GOALS_FR = {
    "1.A": (
        "Établir les responsabilités en cybersécurité",
        "Les rôles, responsabilités et autorités liés au programme de cybersécurité de l'organisation sont établis, communiqués, appliqués et alignés au sein de l'organisation et avec les partenaires externes.",
        "- Documenter tous les rôles et responsabilités en cybersécurité dans la politique organisationnelle\n- Répartir les responsabilités en cybersécurité au sein de l'organisation ; des tiers peuvent y contribuer\n- Mettre en œuvre les exigences légales et réglementaires en cybersécurité, y compris la protection de la vie privée\n- Établir une collaboration continue entre les équipes IT et OT pour l'efficacité de la sécurité et des opérations",
    ),
    "1.B": (
        "Gérer la gouvernance de la cybersécurité",
        "La stratégie, les attentes et les politiques de gestion des risques de cybersécurité de l'organisation sont établies.",
        "- Réviser les politiques de cybersécurité annuellement ; les mettre à jour en cas de changement des exigences, risques, menaces ou technologies\n- Communiquer et appliquer les politiques reflétant la stratégie et les priorités organisationnelles\n- Établir une gouvernance englobant les obligations réglementaires, juridiques, environnementales et opérationnelles\n- Développer des politiques spécifiques aux OT tenant compte des limitations des programmes IT et des priorités des fonctions critiques",
    ),
    "1.C": (
        "Gérer les plans de réponse aux incidents",
        "Identifier les améliorations en pratiquant les plans de cybersécurité et de réponse aux incidents pour maintenir et mettre à jour le programme de cybersécurité de l'organisation.",
        "- Développer, maintenir, mettre à jour et exercer régulièrement les plans de RI pour des scénarios courants et spécifiques à l'organisation\n- Garantir des exercices réalistes incluant toutes les parties prenantes\n- Réviser et tester les plans de RI au minimum annuellement\n- Prendre en compte les considérations de sûreté et de confinement spécifiques aux OT",
    ),
    "1.D": (
        "Signalement des incidents et divulgation des vulnérabilités de la chaîne d'approvisionnement",
        "Les organisations apprennent et répondent plus rapidement aux incidents ou violations connus chez les fournisseurs et prestataires de services.",
        "- Exiger des fournisseurs et prestataires qu'ils notifient les clients des incidents de sécurité et des vulnérabilités dans des délais adaptés au risque via des SLA et des contrats\n- Documenter et suivre les numéros de série, sommes de contrôle, certificats numériques et signatures des actifs OT pour vérifier l'authenticité du matériel, des logiciels et des micrologiciels",
    ),
    "1.E": (
        "Gérer les risques liés aux prestataires de services managés",
        "Les risques posés par un prestataire de services managés (MSP) sont identifiés, enregistrés, évalués, priorisés, surveillés et mis à jour tout au long de la relation.",
        "- Développer la compréhension des services et produits de sécurité du MSP\n- Comprendre les accords contractuels et combler proactivement les lacunes de sécurité hors du périmètre contractuel\n- S'assurer que les contrats précisent comment et quand les MSP notifient les clients des incidents affectant leur environnement",
    ),
    "2.A": (
        "Gérer les actifs organisationnels",
        "Un inventaire maintenu des actifs pour améliorer la résilience en cybersécurité en réduisant les temps d'arrêt, en facilitant la reprise, en renforçant les défenses et en améliorant la préparation.",
        "- Maintenir un inventaire régulièrement mis à jour de tous les actifs organisationnels incluant les données, le matériel, les logiciels, les systèmes, les installations et le personnel\n- Mettre à jour plus fréquemment les actifs IT/OT critiques",
    ),
    "2.B": (
        "Atténuer les vulnérabilités connues",
        "Réduction de la probabilité que des acteurs malveillants exploitent des vulnérabilités connues pour compromettre les réseaux de l'organisation.",
        "- Mettre en œuvre un programme de gestion des vulnérabilités pour corriger et atténuer les logiciels mal configurés en temps voulu\n- Suivre l'avancement de la réponse aux risques via les POA&M, les registres de risques et les rapports détaillés\n- Documenter les risques potentiels des changements proposés ; fournir des instructions de retour en arrière\n- Attribuer les responsabilités pour le traitement des divulgations de menaces, vulnérabilités ou incidents\n- Incorporer des contrôles de sécurité compensatoires pour les systèmes existants lorsque possible\n- Pour les actifs OT où la correction est impossible, appliquer des contrôles compensatoires (segmentation, surveillance)",
    ),
    "2.C": (
        "Obtenir une validation indépendante des contrôles de cybersécurité",
        "Valider que les contrôles de sécurité mis en œuvre sont correctement configurés et fonctionnent comme prévu.",
        "- Engager régulièrement des experts tiers en cybersécurité pour des tests d'intrusion, des bug bounties, des simulations d'incidents et des exercices sur table\n- Évaluer la capacité des adversaires à infiltrer et se déplacer latéralement dans les réseaux ciblant les systèmes critiques\n- S'assurer que les conclusions des tests sont traitées",
    ),
    "2.D": (
        "Maintenir un processus de divulgation et de signalement des vulnérabilités",
        "Les organisations apprennent plus rapidement les vulnérabilités ou faiblesses.",
        "- Maintenir une méthode publique et facilement accessible pour signaler aux équipes de sécurité les actifs vulnérables, mal configurés ou exploitables par courriel ou formulaire web\n- Accuser réception des soumissions valides et répondre dans des délais raisonnables\n- Atténuer les faiblesses validées et exploitables proportionnellement à leur sévérité\n- Protéger les personnes identifiant ou signalant les vulnérabilités de bonne foi\n- Appliquer les fichiers security.txt conformes à la RFC 9116 sur tous les domaines web publics",
    ),
    "2.E": (
        "Documenter la topologie réseau",
        "Répondre plus efficacement aux incidents et maintenir la continuité de service.",
        "- Maintenir une documentation précise décrivant la topologie réseau actuelle et les informations pertinentes pour tous les réseaux IT et OT\n- Effectuer des revues réseau et les suivre annuellement ; mettre à jour en cas de changement de topologie",
    ),
    "3.A": (
        "Changer les mots de passe par défaut",
        "Empêcher les acteurs malveillants d'utiliser les mots de passe par défaut pour obtenir un accès initial et se déplacer latéralement dans un réseau.",
        "- Exiger le changement des mots de passe par défaut du fabricant pour tout matériel, logiciel et micrologiciel avant la connexion au réseau\n- Si impossible (mots de passe codés en dur), documenter et mettre en œuvre des contrôles compensatoires ; surveiller les journaux de trafic réseau et de tentatives de connexion\n- Changer les mots de passe par défaut sur les systèmes OT existants ; établir une politique pour tous les nouveaux dispositifs",
    ),
    "3.B": (
        "Établir une robustesse minimale des mots de passe",
        "Les mots de passe de l'organisation sont plus difficiles à deviner ou craquer pour les acteurs malveillants.",
        "- Appliquer une politique système établissant une robustesse minimale des mots de passe incluant une longueur de 16 caractères ou plus pour tous les actifs IT et OT protégés par mot de passe\n- Utiliser des phrases de passe et des gestionnaires de mots de passe\n- Lorsque les longueurs minimales sont impossibles, appliquer des contrôles compensatoires et les enregistrer ; journaliser toutes les tentatives de connexion\n- Prioriser la mise à niveau ou le remplacement des actifs ne supportant pas une robustesse suffisante",
    ),
    "3.C": (
        "Créer des identifiants uniques",
        "Les adversaires ne peuvent pas réutiliser des identifiants compromis pour se déplacer latéralement dans l'organisation, en particulier entre les réseaux IT et OT.",
        "- Créer des identifiants distincts et séparés pour des services similaires et l'accès aux actifs entre les réseaux IT/OT\n- Les utilisateurs s'abstiennent de réutiliser les mots de passe entre les comptes, applications et services\n- Les administrateurs système et les comptes de service/machine ont des mots de passe uniques\n- Pas de mot de passe universel pour les comptes non personnels (NPE)\n- Utiliser des comptes basés sur les rôles pour les systèmes IT/OT lorsque possible",
    ),
    "3.D": (
        "Révoquer les identifiants du personnel sortant",
        "Empêcher l'accès non autorisé aux comptes ou ressources de l'organisation par d'anciens employés.",
        "- Établir un processus administratif défini et appliqué de départ pour le personnel, les prestataires et les fournisseurs, incluant la restitution des jetons physiques et badges et la révocation de tous les accès\n- Réviser les accès utilisateurs et désactiver les comptes inactifs après une période définie (par ex. 30 jours), idéalement via un processus automatisé",
    ),
    "3.E": (
        "Surveiller les tentatives de connexion infructueuses (automatisées)",
        "Protéger les organisations contre les attaques automatisées basées sur les identifiants.",
        "- Capturer et journaliser toutes les tentatives de connexion infructueuses conformément à la politique de sécurité de l'organisation\n- Notifier le personnel de sécurité après des tentatives consécutives infructueuses et des écarts par rapport au comportement normal\n- Journaliser et stocker les alertes dans le système de sécurité ou de tickets pertinent pour analyse rétrospective",
    ),
    "3.F": (
        "Mettre en œuvre l'authentification multifacteur",
        "Ajouter une couche de sécurité critique et supplémentaire pour protéger les comptes des actifs.",
        "- Exiger l'AMF en utilisant la méthode la plus forte disponible pour les actifs avec accès à distance\n- Options d'AMF classées par robustesse : (1) AMF résistante à l'hameçonnage (FIDO/WebAuthn ou basée sur PKI), (2) Jetons logiciels d'application mobile, (3) SMS/voix uniquement en l'absence d'autre option\n- Tous les comptes IT utilisent l'AMF ; prioriser les comptes à plus haut risque\n- OT : Activer l'AMF sur tous les comptes et systèmes accessibles à distance ; si indisponible, supprimer l'accès distant, ajouter la segmentation",
    ),
    "3.G": (
        "Les administrateurs maintiennent des comptes utilisateurs et privilégiés séparés",
        "Rendre plus difficile l'accès des acteurs malveillants aux comptes d'administrateur ou privilégiés, même si les comptes utilisateurs courants sont compromis.",
        "- Les comptes utilisateurs ne disposent pas de privilèges d'administrateur\n- Les administrateurs maintiennent des comptes utilisateurs séparés pour les activités non administratives\n- Réévaluer les privilèges périodiquement pour valider le besoin continu\n- Maintenir la séparation des tâches en répartissant les responsabilités entre plusieurs individus et rôles",
    ),
    "3.H": (
        "Mettre en œuvre les principes du moindre privilège",
        "Minimise l'accès non autorisé aux systèmes, données et processus, réduit les erreurs humaines et prévient les actions malveillantes.",
        "- Tous les comptes utilisateurs, rôles système et processus fonctionnent avec les privilèges minimaux nécessaires\n- Effectuer des revues trimestrielles des permissions d'accès et des attributions de rôles pour valider la conformité à la politique",
    ),
    "3.I": (
        "Mettre en œuvre la segmentation réseau logique et physique",
        "Limiter l'impact d'une compromission potentielle et empêcher les adversaires d'accéder aux données sensibles, aux espaces et/ou aux infrastructures critiques.",
        "- Placer des routeurs entre les réseaux créant des limites, augmentant les domaines de diffusion et filtrant le trafic\n- Utiliser les limites pour contenir les violations de sécurité en restreignant le trafic à des segments séparés et en isolant les segments lors d'une intrusion\n- Segmenter physiquement les enclaves OT (par ex. diodes de données) le cas échéant",
    ),
    "3.J": (
        "Mettre en œuvre la formation à la cybersécurité",
        "Les utilisateurs de l'organisation apprennent et adoptent des comportements plus sûrs.",
        "- Fournir une formation initiale à la cybersécurité avant que les nouveaux employés n'accèdent aux systèmes informatiques\n- Fournir au moins une formation annuelle couvrant la reconnaissance de l'ingénierie sociale, le signalement des attaques, l'utilisation acceptable et l'hygiène cyber de base\n- Identifier les rôles spécialisés nécessitant une formation complémentaire\n- Fournir une formation basée sur les rôles aux rôles spécialisés incluant les prestataires, partenaires et fournisseurs\n- Fournir au personnel OT une formation de sensibilisation à la sécurité",
    ),
    "3.K": (
        "Utiliser un chiffrement robuste",
        "Le chiffrement est déployé pour maintenir la confidentialité et l'intégrité des données sensibles sur le réseau de l'organisation.",
        "- Utiliser le chiffrement, les signatures numériques et les condensats cryptographiques pour protéger la confidentialité et l'intégrité des communications réseau\n- Identifier les données critiques à protéger en transit et au repos (données personnelles, informations propriétaires, programmes PLC, fichiers CAO/FAO)\n- Empêcher le stockage électronique en clair des données sensibles et des mots de passe\n- Stocker les identifiants de manière sécurisée via des gestionnaires de mots de passe\n- Utiliser le chiffrement pour les connexions OT externes lorsque la latence le permet",
    ),
    "3.L": (
        "Activer la sécurité des courriels",
        "Réduire les risques liés aux menaces courantes par courriel, telles que l'usurpation d'identité, l'hameçonnage et l'interception.",
        "- Activer STARTTLS sur toute l'infrastructure de messagerie d'entreprise\n- Activer le Sender Policy Framework (SPF)\n- Activer DomainKeys Identified Mail (DKIM)\n- Activer DMARC et le configurer sur « reject »",
    ),
    "3.M": (
        "Désactiver l'exécution automatique et les macros par défaut",
        "Réduire le risque lié aux macros intégrées et au code exécutable similaire.",
        "- Appliquer une politique système désactivant par défaut les macros ou le code embarqué similaire\n- Établir une politique pour les utilisateurs autorisés demandant l'activation des macros sur des actifs spécifiques\n- Désactiver l'exécution automatique (Autorun/AutoPlay) par défaut",
    ),
    "3.N": (
        "Établir des processus de gestion des changements",
        "Des politiques et procédures existent pour gérer les changements et configurations des systèmes.",
        "- Mettre en œuvre des politiques et processus de gestion sécurisée des changements\n- Appliquer des restrictions de configuration empêchant les modifications non autorisées\n- Tester et documenter les changements proposés dans des environnements hors production ; analyser les impacts sur la sécurité\n- Mettre en œuvre une fonctionnalité OT limitée ne permettant que les fonctions, protocoles et services nécessaires",
    ),
    "3.O": (
        "Maintenir les sauvegardes et la capacité de restauration des systèmes",
        "Les organisations réduisent les risques de perte de données et d'interruption de service tout en gérant, répondant et se remettant efficacement des incidents.",
        "- Développer la liste de toutes les sauvegardes maintenues incluant les supports d'installation, les clés de licence, les informations de configuration et les durées de rétention\n- Sauvegarder les systèmes d'opérations critiques en quasi-temps réel ; sauvegarder fréquemment tous les systèmes opérationnels\n- Stocker les sauvegardes hors site et hors ligne de manière sécurisée\n- Tester les sauvegardes et la récupération au minimum annuellement\n- Valider l'intégrité des sauvegardes avant d'initier la restauration\n- Vérifier l'absence d'indicateurs de compromission dans les supports de restauration\n- OT : Inclure les configurations des dispositifs, les rôles, les schémas techniques et les outils",
    ),
    "3.P": (
        "Maintenir un processus d'approbation du matériel et des logiciels",
        "Augmenter la visibilité sur les actifs technologiques déployés et réduire la probabilité de compromission par l'installation de matériel, micrologiciel ou logiciel non approuvé.",
        "- Mettre en œuvre une politique administrative exigeant la revue, les tests et l'approbation avant l'installation de tout nouveau matériel, micrologiciel ou logiciel\n- Maintenir une liste approuvée du matériel, des micrologiciels et des logiciels incluant les versions approuvées\n- Prendre en compte les exigences supplémentaires de l'environnement OT pour les correctifs et mises à jour afin de ne pas impacter les opérations ou la sûreté",
    ),
    "3.Q": (
        "Maintenir la collecte et le stockage des journaux",
        "Améliorer la visibilité pour détecter et répondre aux incidents cyber tout en protégeant les journaux de sécurité contre l'accès non autorisé et la falsification.",
        "- Collecter et stocker les journaux d'administration et de sécurité (systèmes d'exploitation, applications, IDS/IPS, pare-feux, DLP, VPN)\n- Stocker les journaux de manière centralisée (outil SIEM ou base de données) ; seuls les utilisateurs autorisés et authentifiés y accèdent\n- Conserver les journaux selon des durées adaptées au risque ou aux exigences réglementaires\n- Notifier les équipes de sécurité lorsque des fonctions critiques de journalisation sont désactivées\n- Pour les actifs OT avec des journaux non standards, collecter le trafic réseau entre ces actifs",
    ),
    "3.R": (
        "Interdire la connexion de dispositifs non autorisés",
        "Empêcher les acteurs malveillants d'obtenir un accès initial ou d'exfiltrer des données via des supports amovibles non autorisés.",
        "- Maintenir des politiques garantissant que les supports et matériels non autorisés ne se connectent pas aux actifs IT/OT\n- Établir des procédures pour retirer, désactiver ou sécuriser les ports physiques afin d'empêcher la connexion de dispositifs non autorisés",
    ),
    "3.S": (
        "Sécuriser les dispositifs exposés à Internet",
        "Les utilisateurs non autorisés ne peuvent pas obtenir un point d'ancrage initial dans le système en exploitant des faiblesses connues des actifs exposés à Internet.",
        "- Minimiser les actifs exposés à Internet autant que possible\n- Prioriser la mise à jour des logiciels via des correctifs en temps voulu\n- Désactiver toutes les applications, logiciels et protocoles réseau inutiles du système d'exploitation sur les actifs exposés à Internet\n- Ne jamais exposer les interfaces de gestion réseau sur l'Internet public\n- Segmenter logiquement les réseaux d'entreprise et de production selon les périmètres de confiance et les types de plateformes",
    ),
    "4.A": (
        "Établir la détection du code malveillant",
        "Permet l'identification précoce des menaces, renforce l'intégrité des systèmes, fournit des informations pour une remédiation plus rapide et minimise les temps d'arrêt.",
        "- Mettre en œuvre des mécanismes basés sur les signatures et non basés sur les signatures pour détecter et éradiquer le code malveillant sur les terminaux\n- S'assurer que l'antivirus est à jour, actif et configuré pour l'analyse automatique des courriels et supports amovibles\n- Utiliser un antivirus compatible OT avec des pratiques spéciales incluant les vérifications de compatibilité et les tests de performance",
    ),
    "4.B": (
        "Identifier les événements indésirables",
        "Les organisations peuvent identifier les événements de sécurité indésirables.",
        "- Définir des critères et processus clairs pour les événements indésirables ; escalader les événements suspects selon le plan de réponse aux incidents\n- Automatiser l'analyse des informations sur les événements pour accélérer les délais d'investigation\n- Former les analystes aux protocoles appropriés pour les incidents cyber suspectés\n- Prendre en compte les événements et anomalies spécifiques aux OT",
    ),
    "5.A": (
        "Établir des procédures de communication en cas d'incident",
        "Coordonner les méthodes de communication de crise entre les partenaires internes et externes de l'organisation et les fournisseurs critiques.",
        "- Concevoir un plan de communication identifiant les parties prenantes et les mécanismes de coordination lors des incidents\n- Collaborer avec les parties prenantes ; partager l'information de manière sécurisée selon les plans de réponse\n- Informer régulièrement la direction des incidents majeurs\n- Notifier les ressources humaines en cas d'activité malveillante interne\n- Établir et suivre les procédures de communication médiatique",
    ),
    "5.B": (
        "Établir des procédures de signalement des incidents",
        "La CISA et d'autres organisations sont mieux en mesure de fournir une assistance ou de comprendre la portée plus large d'un incident cyber.",
        "- Maintenir une politique et des procédures de signalement de tous les incidents confirmés aux entités externes (régulateurs, autorités sectorielles, ISAC, ISAO, CISA)\n- Signaler les incidents connus dans les délais réglementaires applicables ou dès que possible en toute sécurité",
    ),
    "6.A": (
        "Planification et préparation à la reprise après incident",
        "Les organisations sont capables de se remettre de manière sûre et efficace d'un incident de cybersécurité.",
        "- Exécuter les plans de récupération et de restauration des services pour les actifs critiques impactés par les incidents, incluant la capacité d'exécuter les fonctions essentielles en mode dégradé (opérations papier, communications radio)\n- Réaliser une analyse post-incident identifiant les axes d'amélioration\n- Intégrer les retours d'expérience, améliorer les capacités de détection et de réponse\n- Mettre à jour les politiques, procédures et formations ; s'assurer que les parties prenantes sont informées des changements",
    ),
}


def build_library():
    lib = {
        "convert_library_version": "v2 ; Compat Mode: [0] {[v2.1] (DEFAULT) Don't use any Compatibility Mode}",
        "urn": LIBRARY_URN,
        "locale": "en",
        "ref_id": "CISA-CPG-2.0",
        "name": "CISA Cybersecurity Performance Goals v2.0",
        "description": "CISA Cross-Sector Cybersecurity Performance Goals (CPG) 2.0 - Voluntary practices with high-impact security actions aligned to the NIST Cybersecurity Framework.",
        "copyright": "This document is provided by CISA (Cybersecurity and Infrastructure Security Agency) and is public domain.",
        "version": 4,
        "publication_date": "2025-03-04",
        "provider": "CISA",
        "packager": "intuitem",
        "translations": {
            "fr": {
                "name": "Objectifs de performance en cybersécurité CISA v2.0",
                "description": "Objectifs de performance en cybersécurité (CPG) 2.0 de la CISA - Pratiques volontaires avec des actions de sécurité à fort impact alignées sur le cadre de cybersécurité du NIST. Cette traduction française n'est pas une traduction officielle de la CISA.",
                "copyright": "Ce document est fourni par la CISA (Cybersecurity and Infrastructure Security Agency) et est du domaine public. La traduction française est une traduction non officielle fournie à titre indicatif.",
            },
        },
        "objects": {},
    }

    # --- Reference Controls ---
    rc_list = []
    for ref_id, name, category, csf_function, description in REFERENCE_CONTROLS:
        rc = {
            "urn": f"{RC_URN_PREFIX}:{ref_id.lower().replace('.', '-')}",
            "ref_id": ref_id,
            "name": name,
            "category": category,
            "csf_function": csf_function,
            "description": description,
        }
        if ref_id in RC_FR:
            name_fr, desc_fr = RC_FR[ref_id]
            rc["translations"] = {"fr": {"name": name_fr, "description": desc_fr}}
        rc_list.append(rc)
    lib["objects"]["reference_controls"] = rc_list

    # --- Threats ---
    threat_list = []
    for ref_id, name, description in THREATS:
        threat = {
            "urn": f"{THREAT_URN_PREFIX}:{ref_id.lower().replace('.', '-')}",
            "ref_id": ref_id,
            "name": name,
            "description": description,
        }
        if ref_id in THREATS_FR:
            name_fr, desc_fr = THREATS_FR[ref_id]
            threat["translations"] = {"fr": {"name": name_fr, "description": desc_fr}}
        threat_list.append(threat)
    lib["objects"]["threats"] = threat_list

    # --- Framework ---
    scores_def = []
    for score_val in (1, 2, 3, 4):
        sd = {
            "score": score_val,
            "name": {
                1: "Not Implemented",
                2: "Partially Implemented",
                3: "Largely Implemented",
                4: "Fully Implemented",
            }[score_val],
            "description": {
                1: "The goal is not addressed. The organization has not taken action on the recommended practices, or actions are entirely ad hoc with no documented approach.",
                2: "Some recommended actions are in place but implementation is incomplete or inconsistent. Practices may be ad hoc or limited to specific areas of the organization.",
                3: "Most recommended actions are systematically applied across the organization. Practices are documented, repeatable, and cover the majority of relevant assets and processes.",
                4: "All recommended actions are in place, tested, and continuously improved. Practices are organization-wide, regularly reviewed, and adapted based on lessons learned and evolving threats.",
            }[score_val],
        }
        name_fr, desc_fr = SCORES_FR[score_val]
        sd["translations"] = {"fr": {"name": name_fr, "description": desc_fr}}
        scores_def.append(sd)

    framework = {
        "urn": FRAMEWORK_URN,
        "ref_id": "CISA-CPG-2.0",
        "name": "CISA CPG v2.0",
        "description": "CISA Cross-Sector Cybersecurity Performance Goals 2.0",
        "min_score": 1,
        "max_score": 4,
        "scores_definition": scores_def,
        "requirement_nodes": [],
    }

    nodes = framework["requirement_nodes"]

    # Depth 1: Functions
    for func_ref, func_name, func_desc in FUNCTIONS:
        node = {
            "urn": f"{REQ_URN_PREFIX}:{func_ref.lower()}",
            "assessable": False,
            "depth": 1,
            "ref_id": func_ref,
            "name": func_name,
            "description": func_desc,
        }
        if func_ref in FUNCTIONS_FR:
            name_fr, desc_fr = FUNCTIONS_FR[func_ref]
            node["translations"] = {"fr": {"name": name_fr, "description": desc_fr}}
        nodes.append(node)

    # Depth 2: Goals
    func_ref_map = {
        "GV": "gv",
        "ID": "id",
        "PR": "pr",
        "DE": "de",
        "RS": "rs",
        "RC": "rc",
    }
    for (
        ref_id,
        name,
        func_ref,
        outcome,
        risk,
        actions,
        cost,
        impact,
        ease,
        ctrl_refs,
    ) in GOALS:
        goal_urn_id = ref_id.lower().replace(".", "-")
        annotation = (
            f"Outcome: {outcome}\n\n"
            f"TTP/Risk Addressed: {risk}\n\n"
            f"Recommended Actions:\n{actions}\n\n"
            f"Cost: {cost} | Impact: {impact} | Complexity: {ease}"
        )
        rc_urns = [
            f"{RC_URN_PREFIX}:{cr.lower().replace('.', '-')}" for cr in ctrl_refs
        ]
        threat_urns = [
            f"{THREAT_URN_PREFIX}:{tr.lower().replace('.', '-')}"
            for tr in GOAL_THREATS.get(ref_id, [])
        ]

        node = {
            "urn": f"{REQ_URN_PREFIX}:{goal_urn_id}",
            "assessable": True,
            "depth": 2,
            "parent_urn": f"{REQ_URN_PREFIX}:{func_ref_map[func_ref]}",
            "ref_id": ref_id,
            "name": name,
            "description": outcome,
            "annotation": annotation,
            "threats": threat_urns,
            "reference_controls": rc_urns,
        }
        if ref_id in GOALS_FR:
            name_fr, desc_fr, actions_fr = GOALS_FR[ref_id]
            # Find the French risk text from the mapped threats
            risk_fr = risk  # fallback to English
            goal_threat_ids = GOAL_THREATS.get(ref_id, [])
            if goal_threat_ids and goal_threat_ids[0] in THREATS_FR:
                _, risk_fr = THREATS_FR[goal_threat_ids[0]]
            cost_fr = {"Low": "Faible", "Moderate": "Modéré", "High": "Élevé"}.get(
                cost, cost
            )
            impact_fr = {"Low": "Faible", "Moderate": "Modéré", "High": "Élevé"}.get(
                impact, impact
            )
            ease_fr = {
                "Simple": "Simple",
                "Moderate": "Modéré",
                "Complex": "Complexe",
            }.get(ease, ease)
            annotation_fr = (
                f"Résultat attendu : {desc_fr}\n\n"
                f"TTP/Risque traité : {risk_fr}\n\n"
                f"Actions recommandées :\n{actions_fr}\n\n"
                f"Coût : {cost_fr} | Impact : {impact_fr} | Complexité : {ease_fr}"
            )
            node["translations"] = {
                "fr": {
                    "name": name_fr,
                    "description": desc_fr,
                    "annotation": annotation_fr,
                }
            }
        nodes.append(node)

    lib["objects"]["framework"] = framework
    return lib


def str_representer(dumper, data):
    """Use literal block style for multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def main():
    yaml.add_representer(str, str_representer)
    lib = build_library()

    output_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "backend/library/libraries/cisa-cpg-2.0.yaml"
    )
    with open(output_path, "w") as f:
        yaml.dump(
            lib,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )
    print(f"Generated {output_path}")
    # Print some stats
    rc_count = len(lib["objects"]["reference_controls"])
    goal_count = sum(
        1 for n in lib["objects"]["framework"]["requirement_nodes"] if n["assessable"]
    )
    func_count = sum(
        1
        for n in lib["objects"]["framework"]["requirement_nodes"]
        if not n["assessable"]
    )
    print(
        f"  {func_count} functions, {goal_count} goals, {rc_count} reference controls"
    )


if __name__ == "__main__":
    main()
