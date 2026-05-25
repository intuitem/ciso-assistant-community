# Evidence

**Evidence** is anything that substantiates a claim in CISO Assistant — that a control has been implemented, that a requirement is met, or that a process is being followed as described.

Evidence is the connective tissue between what the audit asks and what the organisation actually does.

## What counts as evidence

- An uploaded file — PDF, screenshot, configuration export, signed approval, exported policy.
- A link to an external system — a Jira ticket, a Confluence page, a Git commit, a monitoring dashboard, a signed agreement.
- A free-form description, when the proof is the assertion itself (rare but allowed).

## What evidence attaches to

Evidence attaches to two places:

- **Applied controls** — proof that the control is in place and working.
- **Requirement assessments** — proof that a specific compliance requirement is met.

Because the same applied control can satisfy many requirements across many frameworks, a single piece of evidence often substantiates compliance against several requirements at once — without duplication.

## Lifecycle

Evidence isn't attached once and forgotten. Each piece carries metadata — description, timestamp, expiry, owner — and a status. Auditors regularly refresh evidence: a yearly penetration-test report needs to be re-uploaded each year; an exported configuration needs to be re-pulled after each significant change.

## Related

- [Applied controls](applied-controls.md)
- [Audits](audits.md)
- [Vocabulary → Evidence](../introduction/vocabulary.md)
