# Philosophy

CISO Assistant is built around a small set of design principles. A lot of object boundaries, naming choices, and workflow shapes only make sense once you have these in mind.

## Decoupling principle

Decoupling compliance from security operations is the cornerstone of CISO Assistant's philosophy. The platform deliberately separates concerns that legacy GRC tools tend to entangle:

- **Security controls** are decoupled from **compliance requirements** — a single control can satisfy many requirements across many frameworks.
- **Risk assessments** are decoupled from **frameworks** — the same risk scenario can inform multiple compliance audits.
- **Assets** are decoupled from **threat scenarios** — assets exist independently of any specific risk study.

The payoff is reuse. One control answers many requirements. One assessment covers many frameworks. One asset participates in many scenarios.

{% embed url="https://vimeo.com/1022391133" %}
Decoupling concept — full screen is recommended for a better experience.
{% endembed %}
