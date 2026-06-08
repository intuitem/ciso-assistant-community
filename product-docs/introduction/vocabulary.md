# Vocabulary

A glossary of the terms used in CISO Assistant. Where a user-facing term differs from the internal model name, both are given.

## A

- **Accreditation** — Formal authorisation that a system, environment, or product has met security and compliance requirements. Captured as an object in project-management workflows, often required for go-live.
- **Actor** — The unifying handle for anyone who can own or be assigned work in CISO Assistant. An actor wraps exactly one of three underlying objects: a [User](#u), a [Team](#t), or an [Entity](#e). Auto-created when its underlying object is created — not managed directly. See [Actors and teams](../concepts/actors-and-teams.md).
- **Applied control** — The main building block of the action plan: a concrete action your team has implemented or will implement. It can be technical, organisational, a process, a policy, a piece of documentation — anything that materially changes risk or compliance posture. Applied controls are always defined by the organisation and can be attached to the global domain or to a specific domain. They may derive from a reference control for consistency, or be created independently.
- **Asset** — Anything of value worth protecting. **Primary assets** are core resources directly contributing to the organisation's main objectives (business processes, data, intellectual property). **Supporting assets** indirectly aid primary functions (IT systems, services, locations, people).
- **Asset assessment** — A per-asset row inside a business impact analysis, capturing recovery posture (documented, tested, targets met), associated controls, evidence, and the escalation thresholds that describe how impact grows over time.
- **Assessment** — Umbrella term covering **audits** (compliance work), **risk assessments**, **business impact analyses**, and **entity assessments**.
- **Attack path** — In EBIOS RM, the route an attacker may take from a starting point — through stakeholders or supporting assets — to reach a target objective.
- **Audit** — The evaluation of a perimeter against a framework, producing a per-requirement view of status, score, and evidence. Internally a `ComplianceAssessment`.
- **Audit log** — Append-only record of significant actions taken in the platform (creations, edits, permission changes, logins). PRO feature.
- **Auditee mode** — A read-only UX mode aimed at external assessors who need to inspect an audit without being granted full access to the platform. Gated by the `auditee_mode` feature flag.

## B

- **Business impact analysis** (BIA) — A structured assessment of the operational, financial, and reputational impact of disruption to specific assets or business processes. Outputs feed into resilience planning.

## C

- **Campaign** — An orchestration object for running many audits in parallel — for example, one audit per perimeter against the same framework. PRO feature.
- **Catalog object** — A reusable building block of CISO Assistant: framework, threat, risk matrix, reference control, mapping, security advisory, CWE. Catalog objects are packaged into libraries.
- **Compliance assessment** — Internal model name for an **audit**. See **Audit**.
- **Contract** — A third-party agreement attached to a supplier entity or solution, with terms, dates, and renewal information.
- **Control** — Generic term. Disambiguate against **applied control** (concrete instance) and **reference control** (template).
- **Current risk** — The risk level given the **applied controls already in place** — the state of risk today. The middle tier of CISO Assistant's three-tier model: inherent (no controls) → current (existing controls) → residual (existing + planned controls).
- **Custom field** (also _custom attribute_) — An organisation-defined attribute that can be attached to platform objects (projects, risks, assets, suppliers, contracts, and more) to capture typed, filterable, searchable metadata beyond the built-in fields.
- **CWE** — Common Weakness Enumeration. A catalogued category of software weakness, used to tag vulnerabilities and security advisories.

## D

- **Dashboard** — A configurable view of metrics and progress indicators, scoped to a perimeter or a domain.
- **Data breach** — In a privacy register, an incident affecting personal data, with notification status and response actions.
- **Data contractor** — A third party involved in a processing as data processor, sub-processor, or joint controller. Distinct from a generic supplier entity — captures the privacy-specific role.
- **Data recipient** — A party (internal team, external service, public body) that personal data is disclosed to as part of a processing.
- **Data subject** — The category of individuals whose personal data is processed (customers, employees, prospects, etc.). Surfaces in the privacy register and right-request workflows.
- **Data transfer** — A record of cross-border or cross-entity movement of personal data, with destination, legal basis, and safeguards.
- **Document revision** — A single revision of a [Managed document](#m). Carries a version number and a lifecycle status (draft → in review → change requested → validated → published → deprecated).
- **Domain** — The top-level container in CISO Assistant: a business unit, subsidiary, project, or any boundary used for organising work and isolating permissions via role-based access control. Sub-domains nest underneath. Internally a `Folder`. _Demo_ and _Starter_ are reserved for internal features.

## E

- **EBIOS RM** — The French ANSSI risk-management method, supported natively in the platform as its own object graph (studies, feared events, stakeholders, strategic and operational scenarios, kill chains).
- **Elementary action** — In EBIOS RM, an atomic step an attacker can perform. Composed into operating modes.
- **Entity** — Scope of an external review — typically a vendor or third party.
- **Entity assessment** — The actual review of an entity. Can trigger or be linked to an audit.
- **Escalation threshold** — A point-in-time / impact pair attached to an asset assessment inside a BIA: "after 4 hours of outage, impact is _high_". Lets a BIA model how disruption escalates rather than recording a single worst-case impact.
- **Evidence** — A document, screenshot, configuration sample, or any other artifact attached to an applied control or requirement assessment to substantiate compliance.
- **Evidence revision** — A single versioned iteration of an evidence object. Replacing an attachment creates a new revision rather than overwriting the previous one; revisions carry a version number, an SHA-256 integrity hash, optional observation, and a link to the task occurrence that produced them when applicable.

## F

- **Feared event** — In EBIOS RM, the undesirable outcome to be avoided on a primary asset — for example, a confidentiality breach of customer data.
- **Filtering label** — A free-form tag that can be attached to most objects for categorisation, filtering, and reporting.
- **Findings assessment** — A formal record tracking issues raised by an audit, a security review, or an external assessor, used to drive remediation through to closure.
- **Focus mode** — A workspace mode that filters the entire UI to a single domain, hiding objects belonging to other domains. PRO feature.
- **Folder** — Internal model name for a **domain**. See **Domain**.
- **Framework** — A set of requirements covering patterns and expectations needed to comply with a regulation, prepare a certification, or establish a foundation. Shipped as a YAML library.

## G

- **Generic collection** — A flexible grouping object in project-management workflows: a "bag" of related items that doesn't fit a more specific schema.

## I

- **Incident** — A security or operational event being investigated or tracked. Distinct from a **risk** (potential) or a **vulnerability** (weakness).
- **Inherent risk** — The natural risk level of a scenario _without any applied controls_. The top tier of CISO Assistant's three-tier model — useful for ranking scenarios by their underlying severity, independently of the mitigation already in place. Surfaced in the UI when the `inherent_risk` feature flag is on.

## J

- **Journey** — An instance of a [Preset](#p) applied to a domain. Carries the scaffolded objects created at apply time and a step list with per-step statuses, notes, and completion timestamps. See [Journeys](../concepts/journeys.md).
- **Journey step** — One row of work inside a journey: a title, description, optional pointer to a target object or internal route, and a status (not started, in progress, done, skipped).

## K

- **Kill chain** — In EBIOS RM, an ordered sequence of attacker steps culminating in the target objective.

## L

- **Library** — Container object bundling one or more catalog objects (frameworks, matrices, threats, reference controls, mappings, security advisories).

## M

- **Managed document** — A document tracked through a controlled lifecycle (draft, in-review, validated, published, deprecated) and pinned to a parent object such as a policy. Each iteration is a [Document revision](#d).
- **Mapping** — Based on the [OLIR initiative](https://csrc.nist.gov/projects/olir). Allows moving an assessment from framework A to framework B while reusing existing requirement assessments.
- **Metric definition** — A reusable specification for a measurable indicator (formula, target, unit, scope). Defined once, instantiated per perimeter.
- **Metric instance** — A concrete sample of a metric definition for a given scope at a given point in time.

## O

- **Operating mode** — In EBIOS RM, a specific way an attacker can carry out an operational scenario, composed of elementary actions.
- **Operational scenario** — In EBIOS RM, the detailed "how" of a strategic scenario — the assets touched, the steps taken, and the techniques used.
- **Organisational issue** — A documented context element describing an internal or external problem affecting the organisation.
- **Organisational objective** — A documented strategic or operational goal of the organisation.

## P

- **Perimeter** — A scoped subset of a domain that an audit or risk assessment applies to. Unlike a domain, a perimeter does **not** enforce role-based access control. Perimeters were previously called "Projects".
- **Personal access token** (PAT) — A long-lived authentication token a user can issue from their profile to authenticate API calls. Alternative to session-based login; used by scripts, integrations, the CLI, and the MCP server.
- **Personal data** — In a privacy register, any data referring to an identified or identifiable individual.
- **Policy** — A specific type of applied control: a document describing what is expected from some part of your stakeholders. Lives in CISO Assistant so its lifecycle can be managed alongside the rest of your controls.
- **Preset** — A reusable template describing a guided workflow: a set of starter objects to scaffold (audit, risk assessment, etc.) plus an ordered list of steps to follow. Library-backed or authored locally; applied to a domain to produce a [Journey](#j).
- **Processing** — In a privacy register, an activity that operates on personal data (collection, storage, transfer, deletion). Captures purpose, lawful basis, recipients, and retention.
- **Processing nature** — A catalogued type of processing operation (collection, storage, transfer, disclosure, deletion, …) used to characterise a processing.
- **Project** — In the project-management module, a planned initiative with deliverables and milestones. Distinct from the legacy meaning of "project" in older CISO Assistant documentation — see **Perimeter**.
- **Purpose** — In a privacy register, the lawful reason for which personal data is processed.

## Q

- **Quantitative risk hypothesis** — A parameter set (loss-event frequency, magnitude distribution) feeding a quantitative risk scenario.
- **Quantitative risk scenario** — A scenario inside a quantitative risk study, evaluated via Monte-Carlo simulation over loss distributions.
- **Quantitative risk study** — A risk study using quantitative methods rather than a risk matrix. Sibling to qualitative risk assessment and EBIOS RM.

## R

- **Recap** — The roll-up view of a business impact analysis, aggregating asset assessments and their escalation thresholds into a single readout.
- **Recovery target** — A documented commitment for restoring an asset after disruption, typically a Recovery Time Objective (RTO) or Recovery Point Objective (RPO). Tracked on an asset assessment as "documented", "tested", and "targets met" flags.
- **Reference control** — A template for an applied control. Provided by frameworks via libraries, or defined locally. Optional but recommended for keeping applied controls consistent across the organisation.
- **Representative** — The person responsible for answering the questionnaire or requirements of an entity assessment.
- **Requirement** — A single normative statement inside a framework.
- **Requirement assessment** — The evaluation of one requirement inside an audit (status, score, evidence, applied controls).
- **Requirement mapping set** — Internal model name for the catalog object backing a **mapping** library. See **Mapping**.
- **Residual risk** — The risk level expected once all _planned_ applied controls have been implemented — the target state of the action plan. The bottom tier of CISO Assistant's three-tier model (inherent → current → residual), and the figure used as input to risk-acceptance decisions.
- **Responsibility matrix** — An assignment of actors to activities, used in project workflows and accreditation processes. Supports RACI, RASCI, and RAPID conventions.
- **Responsibility role** — The role attached to an actor on an activity inside a responsibility matrix (e.g. R/A/C/I in RACI, or R/A/S/C/I in RASCI). Defined per matrix.
- **Right request** — In a privacy register, a data-subject request under GDPR or equivalent (access, rectification, deletion, portability).
- **Risk acceptance** — Formal record of an organisation's decision to tolerate a residual risk without further treatment. Carries an approval workflow; approval requires the **Approver** role.
- **Risk assessment** (also _risk study_) — A scenario-based evaluation of risk over a perimeter.
- **Risk matrix** — A configurable lookup table that derives risk level from probability and impact. Imported from a library. The matrix is fixed per risk assessment once the assessment is created.
- **Risk scenario** — A building block of a risk assessment: combines threats, assets, and existing controls into a story whose probability and impact can be evaluated.
- **Role** — A bundle of permissions. Four built-in roles ship with the platform; PRO editions also support custom roles.
  - **Domain Manager** — can set up and access everything on a domain.
  - **Analyst** — can input and read data, but cannot change a domain's settings.
  - **Reader** — read-only on the domain's items.
  - **Approver** — can validate workflows on objects for a domain (e.g. risk acceptance).
- **Role assignment** — The attachment of a user (or user group) to a role within a domain. The unit of access control.
- **RO/TO couple** — In EBIOS RM, the pairing of a **Risk Origin** (who attacks) with a **Target Objective** (what they want). The seed for strategic and operational scenarios.

## S

- **Security advisory** — A catalogued security warning published by a vendor or CERT (e.g. CVE entries). Linked to vulnerabilities and affected assets.
- **Security exception** — A documented, time-bound deviation from a control or policy, approved through a workflow and tracked for review.
- **Severity** — The shared ordinal scale used to qualify vulnerabilities, incidents, and findings: undefined / info / low / medium / high / critical. Drives SLA escalation and visual emphasis in dashboards.
- **Solution** — A product or service provided by an entity.
- **Stakeholder** — In EBIOS RM, an internal or external party with a relationship to the studied system. Evaluated for trust level and dependency.
- **Strategic scenario** — In EBIOS RM, the high-level "what" of an attack: a Risk Origin, a Target Objective, a path through stakeholders, and an outcome.

## T

- **Task definition** — A reusable specification of a task: default assignee, owner, recurrence rule, expected evidence. Defining a task creates one or more **task occurrences** over time. Internally a `TaskTemplate`.
- **Task node** — Internal model name for a **task occurrence**. See **Task occurrence**.
- **Task occurrence** — A scheduled instance of a task definition, with a due date, a status (pending → in progress → completed/cancelled), and the evidence collected when the task ran. Internally a `TaskNode`.
- **Task template** — Internal model name for a **task definition**. See **Task definition**.
- **Team** — A named grouping of users used for collaborative ownership of objects, with a leader, optional deputies, members, and an optional team email for notification routing. Distinct from a [User group](#u) (which is role-scoped to a domain — see the disambiguation in [Actors and teams](../concepts/actors-and-teams.md)).
- **Terminology** — An organisation's overrides to the platform's default labels, used to align the UI with internal vocabulary.
- **Threat** — A catalogued source of harm — reusable across scenarios. Optional: assessments can be performed without referencing threats explicitly.

## U

- **URN** — Uniform Resource Name. A unique identifier used to link to catalog objects across libraries.
- **User** — A person with an account on the platform.
- **User group** — A combination of a role and a domain, on which you place users. Auto-created when a domain is created.

## V

- **Validation flow** — A configurable approval workflow that mirrors an organisation's internal review or management-approval process — peer-review, sign-off by a security lead, formal acceptance by a steering committee. Attached to objects whose state changes warrant such review (e.g. risk acceptance, audit close-out), it captures the human approval step inside the platform rather than enforcing it as a hard technical gate.
- **Vulnerability** — A weakness in a system or process that could be exploited by a threat. Tracked with severity, status, and linked applied controls.

## W

- **Webhook endpoint** — A registered URL CISO Assistant calls when configured events happen (e.g. an audit closed, an applied control updated). Used to notify external systems and trigger downstream automation.
