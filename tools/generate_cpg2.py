#!/usr/bin/env python3
"""Generate CISA CPG 2.0 framework YAML for CISO Assistant."""

import yaml
import sys

# --- Data ---

LIBRARY_URN = "urn:intuitem:risk:library:cisa-cpg-2.0"
FRAMEWORK_URN = "urn:intuitem:risk:framework:cisa-cpg-2.0"
REQ_URN_PREFIX = "urn:intuitem:risk:req_node:cisa-cpg-2.0"
RC_URN_PREFIX = "urn:intuitem:risk:function:cisa-cpg-2.0"

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
        ["RC.09", "RC.10"],
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
        ["RC.14"],
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
        ["RC.15"],
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
        ["RC.18"],
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
        ["RC.19"],
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
        ["RC.32"],
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
        ["RC.34"],
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
        ["RC.37"],
    ),
]


def build_library():
    lib = {
        "convert_library_version": "v2 ; Compat Mode: [0] {[v2.1] (DEFAULT) Don't use any Compatibility Mode}",
        "urn": LIBRARY_URN,
        "locale": "en",
        "ref_id": "CISA-CPG-2.0",
        "name": "CISA Cybersecurity Performance Goals v2.0",
        "description": "CISA Cross-Sector Cybersecurity Performance Goals (CPG) 2.0 - Voluntary practices with high-impact security actions aligned to the NIST Cybersecurity Framework.",
        "copyright": "This document is provided by CISA (Cybersecurity and Infrastructure Security Agency) and is public domain.",
        "version": 1,
        "publication_date": "2025-03-04",
        "provider": "CISA",
        "packager": "intuitem",
        "objects": {},
    }

    # --- Reference Controls ---
    rc_list = []
    for ref_id, name, category, csf_function, description in REFERENCE_CONTROLS:
        rc_list.append(
            {
                "urn": f"{RC_URN_PREFIX}:{ref_id.lower().replace('.', '-')}",
                "ref_id": ref_id,
                "name": name,
                "category": category,
                "csf_function": csf_function,
                "description": description,
            }
        )
    lib["objects"]["reference_controls"] = rc_list

    # --- Framework ---
    framework = {
        "urn": FRAMEWORK_URN,
        "ref_id": "CISA-CPG-2.0",
        "name": "CISA CPG v2.0",
        "description": "CISA Cross-Sector Cybersecurity Performance Goals 2.0",
        "min_score": 1,
        "max_score": 4,
        "scores_definition": [
            {
                "score": 1,
                "name": "Not Implemented",
                "description": "The goal is not addressed. The organization has not taken action on the recommended practices, or actions are entirely ad hoc with no documented approach.",
            },
            {
                "score": 2,
                "name": "Partially Implemented",
                "description": "Some recommended actions are in place but implementation is incomplete or inconsistent. Practices may be ad hoc or limited to specific areas of the organization.",
            },
            {
                "score": 3,
                "name": "Largely Implemented",
                "description": "Most recommended actions are systematically applied across the organization. Practices are documented, repeatable, and cover the majority of relevant assets and processes.",
            },
            {
                "score": 4,
                "name": "Fully Implemented",
                "description": "All recommended actions are in place, tested, and continuously improved. Practices are organization-wide, regularly reviewed, and adapted based on lessons learned and evolving threats.",
            },
        ],
        "requirement_nodes": [],
    }

    func_map = {f[0]: f for f in FUNCTIONS}
    nodes = framework["requirement_nodes"]

    # Depth 1: Functions
    for func_ref, func_name, func_desc in FUNCTIONS:
        nodes.append(
            {
                "urn": f"{REQ_URN_PREFIX}:{func_ref.lower()}",
                "assessable": False,
                "depth": 1,
                "ref_id": func_ref,
                "name": func_name,
                "description": func_desc,
            }
        )

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

        nodes.append(
            {
                "urn": f"{REQ_URN_PREFIX}:{goal_urn_id}",
                "assessable": True,
                "depth": 2,
                "parent_urn": f"{REQ_URN_PREFIX}:{func_ref_map[func_ref]}",
                "ref_id": ref_id,
                "name": name,
                "description": outcome,
                "annotation": annotation,
                "reference_controls": rc_urns,
            }
        )

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
