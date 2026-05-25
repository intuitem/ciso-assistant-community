# Vocabulary

A glossary of the terms used in CISO Assistant. Where a user-facing term differs from the internal model name, both are given.

## A

- **Applied control** — The main building block of the action plan: a concrete action your team has implemented or will implement. It can be technical, organisational, a process, a policy, a piece of documentation — anything that materially changes risk or compliance posture. Applied controls are always defined by the organisation and can be attached to the global domain or to a specific domain. They may derive from a reference control for consistency, or be created independently.
- **Asset** — Anything of value worth protecting. **Primary assets** are core resources directly contributing to the organisation's main objectives (business processes, data, intellectual property). **Supporting assets** indirectly aid primary functions (IT systems, services, locations, people).
- **Assessment** — Umbrella term covering **audits** (compliance work) and **risk assessments**.
- **Audit** — The evaluation of a perimeter against a framework, producing a per-requirement view of status, score, and evidence. Internally a `ComplianceAssessment`.

## C

- **Catalog object** — A reusable building block of CISO Assistant: framework, threat, risk matrix, reference control, mapping. Catalog objects are packaged into libraries.
- **Compliance assessment** — Internal model name for an **audit**. See **Audit**.
- **Control** — Generic term. Disambiguate against **applied control** (concrete instance) and **reference control** (template).

## D

- **Domain** — The top-level container in CISO Assistant: a business unit, subsidiary, project, or any boundary used for organising work and isolating permissions via role-based access control. Sub-domains nest underneath. Internally a `Folder`. _Demo_ and _Starter_ are reserved for internal features.

## E

- **EBIOS RM** — The French ANSSI risk-management method, supported natively in the platform as its own object graph.
- **Entity** — Scope of an external review — typically a vendor or third party.
- **Entity assessment** — The actual review of an entity. Can trigger or be linked to an audit.
- **Evidence** — A document, screenshot, configuration sample, or any other artifact attached to an applied control or requirement assessment to substantiate compliance.

## F

- **Folder** — Internal model name for a **domain**. See **Domain**.
- **Framework** — A set of requirements covering patterns and expectations needed to comply with a regulation, prepare a certification, or establish a foundation. Shipped as a YAML library.

## L

- **Library** — Container object bundling one or more catalog objects (frameworks, matrices, threats, reference controls, mappings).

## M

- **Mapping** — Based on the [OLIR initiative](https://csrc.nist.gov/projects/olir). Allows moving an assessment from framework A to framework B while reusing existing requirement assessments.

## P

- **Perimeter** — A scoped subset of a domain that an audit or risk assessment applies to. Unlike a domain, a perimeter does **not** enforce role-based access control. Perimeters were previously called "Projects".

## R

- **Reference control** — A template for an applied control. Provided by frameworks via libraries, or defined locally. Optional but recommended for keeping applied controls consistent across the organisation.
- **Representative** — The person responsible for answering the questionnaire or requirements of an entity assessment.
- **Requirement** — A single normative statement inside a framework.
- **Requirement assessment** — The evaluation of one requirement inside an audit (status, score, evidence, applied controls).
- **Risk assessment** (also _risk study_) — A scenario-based evaluation of risk over a perimeter.
- **Role** — A bundle of permissions. Four roles ship built-in:
  - **Domain Manager** — can set up and access everything on a domain.
  - **Analyst** — can input and read data, but cannot change a domain's settings.
  - **Reader** — read-only on the domain's items.
  - **Approver** — can validate workflows on objects for a domain (e.g. risk acceptance).

## S

- **Solution** — A product or service provided by an entity.

## T

- **Task** — The main building block of the task-management module. Can be one-time or recurring; supports assignment.
- **Threat** — A catalogued source of harm — reusable across scenarios. Optional: assessments can be performed without referencing threats explicitly.

## U

- **URN** — Uniform Resource Name. Unique identifier used to link to catalog objects across libraries.
- **User group** — A combination of a role and a domain, on which you place users. Auto-created when a domain is created.
