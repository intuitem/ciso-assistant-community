# Vocabulary

A glossary of the terms used in CISO Assistant. Where a user-facing term differs from the internal model name, both are given.

## A

- **Accreditation** — Formal authorisation that a system, environment, or product has met security and compliance requirements. Captured as an object in project-management workflows, often required for go-live.
- **Actor** — A person responsible for, or assigned to, an applied control, a requirement assessment, or a task. Actors are independent of platform user accounts: an actor can represent an external party who has no login.
- **Applied control** — The main building block of the action plan: a concrete action your team has implemented or will implement. It can be technical, organisational, a process, a policy, a piece of documentation — anything that materially changes risk or compliance posture. Applied controls are always defined by the organisation and can be attached to the global domain or to a specific domain. They may derive from a reference control for consistency, or be created independently.
- **Asset** — Anything of value worth protecting. **Primary assets** are core resources directly contributing to the organisation's main objectives (business processes, data, intellectual property). **Supporting assets** indirectly aid primary functions (IT systems, services, locations, people).
- **Assessment** — Umbrella term covering **audits** (compliance work), **risk assessments**, **business impact analyses**, and **entity assessments**.
- **Attack path** — In EBIOS RM, the route an attacker may take from a starting point — through stakeholders or supporting assets — to reach a target objective.
- **Audit** — The evaluation of a perimeter against a framework, producing a per-requirement view of status, score, and evidence. Internally a `ComplianceAssessment`.
- **Audit log** — Append-only record of significant actions taken in the platform (creations, edits, permission changes, logins). Enterprise feature.

## B

- **Business impact analysis** (BIA) — A structured assessment of the operational, financial, and reputational impact of disruption to specific assets or business processes. Outputs feed into resilience planning.

## C

- **Campaign** — An orchestration object for running many audits in parallel — for example, one audit per perimeter against the same framework. Enterprise feature.
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
- **Domain** — The top-level container in CISO Assistant: a business unit, subsidiary, project, or any boundary used for organising work and isolating permissions via role-based access control. Sub-domains nest underneath. Internally a `Folder`. _Demo_ and _Starter_ are reserved for internal features.

## E

- **EBIOS RM** — The French ANSSI risk-management method, supported natively in the platform as its own object graph (studies, feared events, stakeholders, strategic and operational scenarios, kill chains).
- **Elementary action** — In EBIOS RM, an atomic step an attacker can perform. Composed into operating modes.
- **Entity** — Scope of an external review — typically a vendor or third party.
- **Entity assessment** — The actual review of an entity. Can trigger or be linked to an audit.
- **Evidence** — A document, screenshot, configuration sample, or any other artifact attached to an applied control or requirement assessment to substantiate compliance.

## F

- **Feared event** — In EBIOS RM, the undesirable outcome to be avoided on a primary asset — for example, a confidentiality breach of customer data.
- **Filtering label** — A free-form tag that can be attached to most objects for categorisation, filtering, and reporting.
- **Findings assessment** — A formal record tracking issues raised by an audit, a security review, or an external assessor, used to drive remediation through to closure.
- **Folder** — Internal model name for a **domain**. See **Domain**.
- **Framework** — A set of requirements covering patterns and expectations needed to comply with a regulation, prepare a certification, or establish a foundation. Shipped as a YAML library.

## G

- **Generic collection** — A flexible grouping object in project-management workflows: a "bag" of related items that doesn't fit a more specific schema.

## I

- **Incident** — A security or operational event being investigated or tracked. Distinct from a **risk** (potential) or a **vulnerability** (weakness).
- **Inherent risk** — The natural risk level of a scenario _without any applied controls_. The top tier of CISO Assistant's three-tier model — useful for ranking scenarios by their underlying severity, independently of the mitigation already in place. Surfaced in the UI when the `inherent_risk` feature flag is on.

## K

- **Kill chain** — In EBIOS RM, an ordered sequence of attacker steps culminating in the target objective.

## L

- **Library** — Container object bundling one or more catalog objects (frameworks, matrices, threats, reference controls, mappings, security advisories).

## M

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
- **Processing** — In a privacy register, an activity that operates on personal data (collection, storage, transfer, deletion). Captures purpose, lawful basis, recipients, and retention.
- **Preset** (also _preset journey_) — A bundle of pre-configured libraries and starter steps that can be loaded at once to bootstrap a fresh organisation or domain along a recognised journey (e.g. a starter SOC 2 setup).
- **Project** — In the project-management module, a planned initiative with deliverables and milestones. Distinct from the legacy meaning of "project" in older CISO Assistant documentation — see **Perimeter**.
- **Purpose** — In a privacy register, the lawful reason for which personal data is processed.

## Q

- **Quantitative risk hypothesis** — A parameter set (loss-event frequency, magnitude distribution) feeding a quantitative risk scenario.
- **Quantitative risk scenario** — A scenario inside a quantitative risk study, evaluated via Monte-Carlo simulation over loss distributions.
- **Quantitative risk study** — A risk study using quantitative methods rather than a risk matrix. Sibling to qualitative risk assessment and EBIOS RM.

## R

- **Reference control** — A template for an applied control. Provided by frameworks via libraries, or defined locally. Optional but recommended for keeping applied controls consistent across the organisation.
- **Representative** — The person responsible for answering the questionnaire or requirements of an entity assessment.
- **Requirement** — A single normative statement inside a framework.
- **Requirement assessment** — The evaluation of one requirement inside an audit (status, score, evidence, applied controls).
- **Requirement mapping set** — Internal model name for the catalog object backing a **mapping** library. See **Mapping**.
- **Residual risk** — The risk level expected once all _planned_ applied controls have been implemented — the target state of the action plan. The bottom tier of CISO Assistant's three-tier model (inherent → current → residual), and the figure used as input to risk-acceptance decisions.
- **Responsibility matrix** — A RACI-style assignment of actors to activities, used in project workflows and accreditation processes.
- **Right request** — In a privacy register, a data-subject request under GDPR or equivalent (access, rectification, deletion, portability).
- **Risk acceptance** — Formal record of an organisation's decision to tolerate a residual risk without further treatment. Carries an approval workflow; approval requires the **Approver** role.
- **Risk assessment** (also _risk study_) — A scenario-based evaluation of risk over a perimeter.
- **Risk matrix** — A configurable lookup table that derives risk level from probability and impact. Imported from a library. The matrix is fixed per risk assessment once the assessment is created.
- **Risk scenario** — A building block of a risk assessment: combines threats, assets, and existing controls into a story whose probability and impact can be evaluated.
- **Role** — A bundle of permissions. Four built-in roles ship with the platform; Enterprise editions also support custom roles.
  - **Domain Manager** — can set up and access everything on a domain.
  - **Analyst** — can input and read data, but cannot change a domain's settings.
  - **Reader** — read-only on the domain's items.
  - **Approver** — can validate workflows on objects for a domain (e.g. risk acceptance).
- **Role assignment** — The attachment of a user (or user group) to a role within a domain. The unit of access control.
- **RO/TO couple** — In EBIOS RM, the pairing of a **Risk Origin** (who attacks) with a **Target Objective** (what they want). The seed for strategic and operational scenarios.

## S

- **Security advisory** — A catalogued security warning published by a vendor or CERT (e.g. CVE entries). Linked to vulnerabilities and affected assets.
- **Security exception** — A documented, time-bound deviation from a control or policy, approved through a workflow and tracked for review.
- **Solution** — A product or service provided by an entity.
- **Stakeholder** — In EBIOS RM, an internal or external party with a relationship to the studied system. Evaluated for trust level and dependency.
- **Strategic scenario** — In EBIOS RM, the high-level "what" of an attack: a Risk Origin, a Target Objective, a path through stakeholders, and an outcome.

## T

- **Task** — The main building block of the task-management module. Can be one-time or recurring; supports assignment.
- **Task template** — A reusable specification for a task (default assignee, owner, schedule, expected evidence). Tasks are instantiated from templates.
- **Team** — A named grouping of users used for collaborative ownership of objects. Distinct from a user group (which is role-scoped to a domain).
- **Terminology** — An organisation's overrides to the platform's default labels, used to align the UI with internal vocabulary.
- **Threat** — A catalogued source of harm — reusable across scenarios. Optional: assessments can be performed without referencing threats explicitly.

## U

- **URN** — Uniform Resource Name. A unique identifier used to link to catalog objects across libraries.
- **User** — A person with an account on the platform.
- **User group** — A combination of a role and a domain, on which you place users. Auto-created when a domain is created.

## V

- **Validation flow** — A configurable approval workflow that can gate state transitions on objects (e.g. risk acceptance, audit close-out). Enterprise feature.
- **Vulnerability** — A weakness in a system or process that could be exploited by a threat. Tracked with severity, status, and linked applied controls.

## W

- **Webhook endpoint** — A registered URL CISO Assistant calls when configured events happen (e.g. an audit closed, an applied control updated). Used to notify external systems and trigger downstream automation.
