# Philosophy

> _Draft — placeholder. Fill in as the design principles solidify._

CISO Assistant is built around a small set of design principles. Knowing them up front makes the rest of the documentation much easier to follow — a lot of object boundaries, naming choices, and workflow shapes only make sense once you have these in mind.

## Decoupling principle

The platform deliberately separates concerns that legacy GRC tools tend to entangle:

- **Security controls** are decoupled from **compliance requirements** — a single control can satisfy many requirements across many frameworks.
- **Risk assessments** are decoupled from **frameworks** — the same risk scenario can inform multiple compliance audits.
- **Assets** are decoupled from **threat scenarios** — assets exist independently of any specific risk study.

The payoff: reuse. One control answers many requirements. One assessment covers many frameworks. One asset participates in many scenarios.

## Domains as the unit of scoping

> _Draft._ Explain how a **domain** is the universal scoping and permission unit — every business object lives inside one, and visibility cascades through sub-domains. Internally a domain is a `Folder`; users only ever see the word "domain".

## Library-driven content

> _Draft._ Explain that frameworks, threats, matrices, mappings, and reference controls all ship as YAML libraries, and that the user-facing catalogue is the published surface of those libraries.

## Open by default, extensible by design

> _Draft._ Open-source core, enterprise edition for advanced features, public REST API, MCP server for AI integrations, YAML libraries for community contributions.

## Audit-grade traceability

> _Draft._ Every assessable object has a status, an owner, a history, and a path back to the requirements it satisfies. This page should explain why this matters and how it shows up in the UI and API.
