# Applied controls

> _Draft — placeholder._

An **applied control** is a concrete security or organisational measure that your team has decided to implement. It lives inside a domain, has an owner, a status, a cost, and a history — and it can satisfy any number of requirements across any number of frameworks.

This is one of the most important objects in the platform: it's the place where _what the framework asks_ meets _what the organisation actually does_.

## What this page should cover

- The distinction between a **reference control** (defined by a framework, shipped via a library) and an **applied control** (your instance of it).
- The decoupling pay-off: one applied control answers many requirements.
- Lifecycle: planned → in design → in progress → active → on hold → deprecated.
- How evidence attaches to applied controls.
- Cost, effort, ETA, category, function — and how those roll up into dashboards.

## For users

> _Draft._ Creating an applied control from scratch vs from a reference control suggestion. Linking it to requirements. Adding evidence. Tracking implementation progress. Reading the analytics view.

## For implementers

> _Draft._ `AppliedControl` model, the many-to-many to `RequirementAssessment`, the reference-control library system, batch actions, the `analytics` view added in commit `40398b2b6`.

## Related

- [Vocabulary → Applied control / Reference control / Evidence](../vocabulary.md)
- [Philosophy → Decoupling principle](../philosophy.md)
- [Audits](audits.md)
