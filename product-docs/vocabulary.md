# Vocabulary

> _Draft — placeholder._ Working glossary. Add entries as concepts are introduced; link from feature pages back to the relevant term.

Terms are listed alphabetically. Where the user-facing term differs from the internal model name, both are given so end users and implementers can cross-reference.

## A

- **Applied control** — _Draft._ A specific implementation of a security measure inside a domain, tracked with status, owner, cost, and evidence.
- **Asset** — _Draft._ Anything of value worth protecting. Distinguished as _primary_ (business process, data) or _supporting_ (system, person, location).
- **Assessment** — _Draft._ Umbrella term covering **audits** (compliance work) and **risk assessments**.
- **Audit** — _Draft._ The evaluation of a perimeter against a framework, producing a per-requirement view of status, score, and evidence. Internally a `ComplianceAssessment`.

## C

- **Compliance assessment** — Internal model name for an **audit**. See **Audit**.
- **Control** — _Draft._ Disambiguate against **applied control** and **reference control**.

## D

- **Domain** — _Draft._ The top-level container in CISO Assistant: a business unit, subsidiary, project, or any boundary used for organising work and isolating permissions. Sub-domains nest underneath. Internally a `Folder`.

## E

- **EBIOS RM** — _Draft._ The French ANSSI risk-management method, supported natively as its own object graph.
- **Evidence** — _Draft._ Files or references attached to applied controls and requirement assessments to substantiate compliance.

## F

- **Folder** — Internal model name for a **domain**. See **Domain**.
- **Framework** — _Draft._ A normative set of requirements (ISO 27001, NIST CSF, SOC 2, …) shipped as a YAML library.

## P

- **Perimeter** — _Draft._ A scoped subset of a domain that an audit or risk assessment applies to.

## R

- **Reference control** — _Draft._ A control defined by a framework or library, intended to be instantiated as an applied control.
- **Requirement** — _Draft._ A single normative statement inside a framework.
- **Requirement assessment** — _Draft._ The evaluation of one requirement inside an audit (status, score, evidence, applied controls).
- **Risk assessment / risk study** — _Draft._ A scenario-based evaluation of risk over a perimeter.

## T

- **Threat** — _Draft._ A catalogued source of harm, reusable across scenarios.

> _Add more entries as needed. Aim for one-paragraph definitions, not essays — link to the relevant concept page for depth._
