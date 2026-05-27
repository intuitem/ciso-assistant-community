# Philosophy

CISO Assistant is built around a small set of design principles. A lot of object boundaries, naming choices, and workflow shapes only make sense once you have these in mind.

## Applied controls at the centre

The **applied control** is the unifying object in CISO Assistant. Everything the organisation _does_ to manage risk and prove compliance is captured as an applied control — a technical safeguard, an organisational process, a documented policy, a tested recovery plan. Once that's in place, the rest of the platform connects to it:

- An **audit** assesses requirements; each requirement assessment links to the applied controls that satisfy it.
- A **risk scenario** lowers its current and residual levels by attaching the applied controls in place and planned.
- A **task** records that an applied control was actually exercised on a given date and produces the evidence to prove it.
- **Evidence** lives on an applied control — and through it, substantiates every requirement and scenario the control supports.
- An **incident** response invokes applied controls; a **vulnerability** is mitigated by them; a **policy** _is_ one.

Authoring an applied control once and reusing it across all the places it applies — instead of redoing the same work per audit, per risk study, per framework — is the productivity gain that justifies the whole architecture.

## Decoupling principle

The corollary of putting applied controls at the centre is that everything around them must be decoupled, so that one applied control can serve many consumers without being rewritten for each:

- **Security controls** are decoupled from **compliance requirements** — a single applied control can satisfy many requirements across many frameworks.
- **Risk assessments** are decoupled from **frameworks** — the same risk scenario can inform multiple compliance audits.
- **Assets** are decoupled from **threat scenarios** — assets exist independently of any specific risk study and can be reused across them.

The payoff is reuse, end-to-end. One applied control answers many requirements. One assessment covers many frameworks. One asset participates in many scenarios. One evidence file substantiates everything the underlying control supports.

{% embed url="https://vimeo.com/1022391133" %}
Decoupling concept — full screen is recommended for a better experience.
{% endembed %}
