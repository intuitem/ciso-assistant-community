# Applied controls

An **applied control** is the main building block of the action plan: the actual action your team has implemented or will implement to address a security need. It can be technical, organisational, a process, a policy, a piece of documentation — anything that materially changes risk or compliance posture.

This is one of the most important objects in the platform. It's the place where _what the framework asks_ meets _what the organisation actually does_, and a single applied control can satisfy any number of requirements across any number of frameworks.

## Applied control

Applied controls are fundamental for both compliance and remediation. They can derive from a **reference control** for consistency, or be created independently. They are always defined by the organisation and can be attached to the global domain or to a specific domain.

## Reference control

A **reference control** is a template for an applied control. Reference controls facilitate the creation of applied controls and help keep them consistent across the organisation.

They can be provided by security frameworks imported from a library, or you can create your own — in the global domain or in a specific domain. Reference controls are optional but recommended.

## Policy

A **policy** is a specific type of applied control: a document describing what is expected from some part of your stakeholders. Putting your cybersecurity policies in CISO Assistant makes them readily available for audits, and lets you manage their lifecycle alongside the rest of your controls.

## What this page should cover

- Lifecycle states (planned → in design → in progress → active → on hold → deprecated) and how status rolls up into dashboards.
- How evidence attaches to applied controls.
- Cost, effort, ETA, category, function — and how those surface in analytics.
- Bulk operations: batch update of owner, status, folder, applied frameworks.

## For users

> _Draft._ Creating an applied control from scratch vs from a reference-control suggestion. Linking it to requirements. Adding evidence. Tracking implementation progress. Reading the analytics view.

## For implementers

> _Draft._ `AppliedControl` model, the many-to-many to `RequirementAssessment`, the reference-control library system, batch actions, the `analytics` view added in commit `40398b2b6`.

## Related

- [Vocabulary → Applied control / Reference control / Evidence](../introduction/vocabulary.md)
- [Philosophy → Decoupling principle](../introduction/philosophy.md)
- [Audits](audits.md)
