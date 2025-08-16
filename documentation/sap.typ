
#set page(margin: 2cm, numbering: none)
#set text( size: 13pt)
#set heading(numbering: "1.")

#show heading.where(level: 1): it => {
  v(1.5em)
  it
  v(1em)
}
// Title page with a simple design
#place(
  top + left,
  dx: -2cm,
  dy: -2cm,
  rect(
    width: 8cm,
    height: 3cm,
    fill: gradient.linear(rgb("#51378D"), rgb("#7258A2"), angle: 45deg),
    radius: (bottom-right: 20pt)
  )
)

#place(
  bottom + right,
  dx: 2cm,
  dy: 2cm,
  rect(
    width: 6cm,
    height: 2cm,
    fill: gradient.linear(rgb("#64748b"), rgb("#94a3b8"), angle: 225deg),
    radius: (top-left: 15pt)
  )
)

#v(4cm)
#align(center)[
  #stack(
    dir: ttb,
    spacing: 1.5cm,

    [
      #text(size: 42pt, weight: "black", fill: rgb("#101010"))[
        SECURITY
      ]
      #text(size: 42pt, weight: "black", fill: rgb("#5D4495"))[
        ASSURANCE
      ]
      #text(size: 42pt, weight: "black", fill: rgb("#101010"))[
        PLAN
      ]
    ],

    [
      #rect(
        width: 12cm,
        stroke: none,
        inset: 1.5cm,
        radius: 6pt,
        fill: rgb("#f8fafc")
      )[
        #text(size: 26pt, weight: "semibold", fill: rgb("#334155"))[
          CISO Assistant
        ]
        #linebreak()
        #text(size: 18pt, weight: "medium", fill: rgb("#64748b"), style: "italic")[
          intuitem
        ]
      ]
    ],

    // Version and year
    [
      #v(1cm)
      #stack(
        dir: ltr,
        spacing: 2cm,
        [
          #rect(
            inset: 0.8cm,
            radius: 4pt,
            stroke: 1pt + rgb("#e2e8f0"),
            fill: white
          )[
            #text(size: 14pt, weight: "medium", fill: rgb("#475569"))[
              Version 1.3 - August 2025
            ]
          ]
        ],
      )
    ]
  )
]


#pagebreak()
#outline(depth: 1)
#set page(numbering: "1", number-align: center)
#counter(page).update(1)
#pagebreak()

= Introduction

Document purpose: This Security Assurance Plan explains the controls, processes, and evidence that Intuitem provides to protect customer data and ensure the availability, integrity, and confidentiality of the CISO Assistant platform.

Intended audience: Security, risk, compliance, procurement, and technical stakeholders at customer organizations.

Last updated: 2025-08-15



= Scope & Applicability

This plan covers Intuitem’s SaaS offering of CISO Assistant and the associated managed infrastructure, operations, and support services. Customer-managed (on-premises) deployments are covered where explicitly noted (see @srm).



= Security Governance

- Frameworks: Our program is aligned with NIST CSF for cybersecurity management and OWASP ASVS for application security.

- Policies & ownership: Security policies are owned by Intuitem leadership and reviewed at least annually.

- Roles: A designated Data Protection Officer (DPO) oversees data protection and privacy. Contact: #link("mailto:contact@intuitem.com"). To report a security issue, please use: #link("security@intuitem.com")

- Defense-in-depth: We apply a multi-layer approach combining preventive, detective, and corrective controls.



#pagebreak()
= Risk Management & Governance

- Process: We maintain an enterprise risk register that captures security, operational, and compliance risks.

- Methodology: Risks are assessed and rated using a combination of likelihood and impact, following ISO 27005 principles.

- Reviews: Risks are reviewed quarterly and after significant changes to systems or threat landscape.

- Mitigation linkage: Each high/critical risk has mapped mitigation measures, tracked to completion.

- Customer impact: Where relevant, risks and mitigations affecting customers are communicated through our account management process (support portal).



= Architecture & Hosting

- Primary region: France, operated across two cloud service providers (CSPs): Scaleway and OVH.
- Secondary region: Netherlands (used for resilience and disaster recovery).
- Platform: Kubernetes for orchestration, high availability, and auto-scaling.
- Network exposure: Only HTTPS (port 443) is publicly exposed; all other inbound traffic is denied by default.
- Encryption: TLS 1.3 for encryption-in-transit with automatically renewed Let’s Encrypt certificates—Encryption-at-rest at the disk level using a Server-Side Encryption with provider-managed keys.
- Special deployments: for specific cases, the hosting location can be agreed on with the customers to accommodate their needs.



= Data Isolation & Multi-Tenancy

- No data mixing: Customer data is never mixed. Each tenant runs as a dedicated, isolated application instance with separate storage volumes.
- Deployment-level controls: Isolation is enforced at the deployment and storage layers to prevent cross-tenant access.
- Decoupled storage: Data is separated from compute to support fast rebuilds and disaster recovery.
- Snapshots: Periodic volume snapshots are taken for recovery readiness.



= Access Control & Identity

- Least privilege & need-to-know: Access to production is restricted to a small subset of engineers.
- MFA everywhere: Multi-factor authentication (MFA) is enforced for all privileged access.
- Customer data access governance: Any access to customer data in production requires explicit authorization (e.g., a support ticket for debugging) and time-bound access.



= Data Retention & Secure Deletion

- Retention periods:
  - Production data: retained for the lifetime of the subscription and deleted within 30 days after termination unless otherwise agreed.
  - Backups: retained for 14 days before automated secure deletion.
  - Logs: retained per operational needs (default 90 days), anonymized or deleted thereafter.
- Deletion method: Data is securely deleted using cryptographic erasure or provider-verified secure delete.
- Customer control: On request, customers can request early deletion of specific datasets.



= Secure Development Lifecycle (SDLC)

- Code review: All changes undergo peer review. We apply stricter controls for third-party contributions to our open-source components.
- SAST & DAST: Automated static (developer workstations and CI/CD) and dynamic analysis to detect implementation flaws and runtime issues.
- Software Composition Analysis (SCA): CI/CD pipelines continuously scan third-party libraries for vulnerabilities and license issues. Dependency versions are pinned; LTS versions are preferred and security patches applied promptly. SBOMs can be provided on request.
- Credential leakage detection: Commits are scanned to prevent secrets exposure; credentials are rotated immediately if detected.
- Contribution controls: Repository-level protections limit who can contribute, approve, merge, or trigger releases.
- Security training: Engineers receive regular training on secure coding practices and emerging threats.
- Threat modeling: Before each new feature, we run structured threat-modeling to identify security and operational risks.


#pagebreak()

= Privacy by Design & Default

- Principle: Privacy is embedded into our development and operational processes from the outset.
- Data minimization: Only collect and store the minimum personal data needed for service delivery.
- Pseudonymization/anonymization: Apply where feasible for analytics, testing, and troubleshooting.



= CI/CD & Change Management

- Secure pipelines: Releases are built and deployed via controlled CI/CD pipelines with staged environments.
- Separation of duties: Build, approval, and deploy steps are segregated and logged.
- Change logging: All changes are tracked and auditable (who, what, when).



= Secrets & Key Management

- Secrets storage: Operational secrets are stored in managed key store systems (eg, GitHub secret manager) or encrypted configuration stores.
- Rotation: Keys and credentials are rotated following policy or after potential exposure.



= Cryptography Policy

- Encryption-at-rest: AES-256 or equivalent industry-approved algorithms.
- Encryption-in-transit: TLS 1.3 with strong cipher suites, maintaining a good balance between security and browser compatibility.
- Key management: Keys are generated, stored, and rotated in secure systems; never hard-coded in source code. We have automated controls at the CI/CD level to double-check this.
- Lifecycle: Keys are retired and destroyed securely at the end of their lifecycle.



#pagebreak()
= Logging, Monitoring & Detection

- Coverage: Demo and production environments are continuously monitored for availability, performance, regressions, and security events.
- Retention & protection: Logs are retained per policy and protected from tampering.
- Alerting & response: Alerts are triaged by on-call staff with documented runbooks.



= Vulnerability & Patch Management

- Scanning: Regular vulnerability scans are performed on application components and container images. This information is publicly available through our GitHub repository or by scanning the application Docker images.
- Prioritization: Findings are risk-rated and remediated within target service levels.
- Patch cadence: We operate a strict schedule to patch the application, underlying systems, and dependencies.



= Incident Response (IR)

- IR Plan: A maintained Incident Response Plan defines detection, escalation, communication, and remediation procedures.
- Exercises: We conduct periodic incident simulations for team readiness.
- Forensics: We retain tooling and playbooks to scope incidents and support root-cause analysis.



= Business Continuity & Disaster Recovery (BC/DR)

- Provider diversity: Services run on two independent CSPs/infrastructures. If one provider is impaired, we can activate disaster-recovery mode and fail over to the other.
- Backups: Periodic backups every 24 hours with a 14-day retention.
- Restores: DR procedures and restores are tested regularly.



= Network & Infrastructure Security

- Zero-trust principles: Cluster control-plane access is tightly restricted. Access requires MFA as part of the general guideline.
- Ingress filtering: Only required services are exposed (HTTPS/443).
- Hardening: Kubernetes and workloads are configured following industry best practices.



= Customer Responsibilities (Shared Responsibility Model) <srm>

- Customers:
  - Manage user accounts, roles, and MFA inside the product.
  - Configure access settings to align with internal policies and organisation setup.
  - Can generate an export of their data as an extra layer of backup or portability needs.
- Report suspected security issues to #link("security@intuitem.com") promptly.
- For self-hosted/on-prem deployments, operate and secure the infrastructure stack per vendor guidance (see @dep).



= Compliance & Certification Roadmap

- Current: Alignment with GDPR, CCPA; use of ISO 27001 certified providers.
- Planned: Progressing toward ISO 27001 certification for Intuitem’s own ISMS, targeted for Q1/2026.



= Third-Party Risk Management

- Assessment: Third-party services are evaluated for security posture and data-handling obligations.
- Contractual controls: Data processing and confidentiality clauses are included where applicable.



#pagebreak()
= Assurance & Independent Testing

- External security audits & penetration testing: Conducted on a regular cadence by independent third parties.
- Artifacts available: Pentest report and remediation actions are publicly shared.
- Vulnerability disclosure: Instructions for reporting security issues are available in our public repository.



= Deployment Options <dep>

- SaaS (managed by Intuitem): Covered by this plan end-to-end.
- On-premises (PRO plan): Intuitem provides guidance and reference configurations; customers are responsible for the security of the hosting environment and operations.



= Change Control, Maintenance & Review

- This SAP is reviewed at least annually or following material changes to systems, providers, or regulations.
- In case of significant changes impacting the customers data or operations, they are notified by email.



= Contacts <contact>

- Security: #link("security@intuitem.com")
- Privacy (DPO): #link("contact@intuitem.com")
- General: #link("contact@intuitem.com")
