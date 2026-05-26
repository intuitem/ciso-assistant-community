# Findings assessments

A **findings assessment** — called **Follow-up** in the UI — tracks the issues raised by a review and drives their remediation through to closure. Findings can come from a CISO Assistant audit, an internal security review, a penetration test, an external assessor's report, or any other source.

It's the place where the action plan meets reality: each non-compliance, observation, or recommendation gets an assignee, a due date, and a status, and is followed all the way to "fixed".

## Mental model

A findings assessment is an **assessment** scoped to a perimeter, in the same family as audits, risk assessments, and business impact analyses. Inside it sit individual **findings**, each with:

- A severity, often aligned with the assessor's severity scale.
- An assignee and a due date.
- A status from _open_ → _in progress_ → _remediated_ → _closed_.
- One or more linked applied controls that address it.

## Where findings come from

The same findings model serves several sources:

- **Audit findings** — non-compliances or partial compliances raised during an audit, especially when extended results are enabled (minor / major nonconformity, observation, opportunity for improvement, good practice).
- **External assessments** — penetration-test reports, third-party security reviews, regulator inspections.
- **Internal reviews** — self-imposed checks outside the formal audit cycle.

Because the model is uniform, dashboards aggregate across sources: you can see _all open findings due this quarter, across all reviews_, without preselecting which kind of review they came from.

## Driving remediation

Findings link to applied controls — closing a finding usually means standing up or updating one or more controls. The link is many-to-many: a single control can close several findings, and a single finding can require several controls.

## Related

- [Audits](audits.md)
- [Applied controls](applied-controls.md)
- [Vocabulary → Findings assessment](../introduction/vocabulary.md)
