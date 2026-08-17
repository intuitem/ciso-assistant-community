# Risk assessments

A **risk assessment** (also called a _risk study_) is a scenario-based evaluation of risk over a perimeter. CISO Assistant supports qualitative approaches (configurable risk matrices), quantitative approaches (Monte Carlo over loss distributions), and the structured EBIOS RM methodology.

The platform follows the ISO 27005 risk-management workflow.

![ISO 27005 risk management workflow](../.gitbook/assets/iso27005.svg)

## Mental model

```mermaid
graph LR
  D[Domain] -->|scopes| RA[Risk assessment]
  P[Perimeter] -.->|narrows| RA
  RM[Risk matrix] -->|scales| RA
  RA -->|comprises| RS[Risk scenario]
  RS -->|impacts| A[Assets]
  RS -->|materialises| T[Threats]
  RS -->|mitigated by| AC[Applied controls]
```

A risk assessment always lives inside a **domain** (the mandatory IAM scope) and is bound to one **risk matrix** that supplies the probability × impact scale (the matrix can be swapped later; existing scores are clamped to the new scale). A **perimeter** can optionally narrow the assessment to a specific service or process inside the domain. The assessment is composed of **risk scenarios**; each scenario links to the **assets** it impacts, the **threats** it materialises, and the **applied controls** that mitigate it (split between _existing_ and _planned_ to drive the three-tier risk model below).

| User-facing | Internal | Notes |
|---|---|---|
| Risk assessment | `RiskAssessment` | Also called "Risk study" in the UI |
| Risk scenario | `RiskScenario` | A row inside the assessment |
| Risk matrix | `RiskMatrix` | Can be changed; existing scenario scores are clamped to the new scale's bounds |
| Domain | `Folder` | Required; drives IAM scoping |
| Threat | `Threat` | Catalog entry from a library |

## Risk assessment

A risk assessment encompasses three steps:

- **Risk identification** — defining the risk scenarios.
- **Risk analysis** — assessing probability, impact, and strength of knowledge for each scenario.
- **Risk evaluation** — done automatically based on the selected risk matrix.

In CISO Assistant, **risk treatment is combined with the risk assessment** rather than tracked as a separate phase.

## Risk scenario

Scenarios can be defined directly from the risk-assessment view or separately via the scenarios view. The same scenario can be reused across multiple studies.

## Risk levels: inherent, current, residual

CISO Assistant tracks three risk levels for each scenario, reflecting where the organisation stands along the treatment journey:

- **Inherent risk** — the natural level of the scenario _without any controls in place_. The starting point. Surfaced in the UI when the `inherent_risk` feature flag is on.
- **Current risk** — the level given the applied controls _already in place_. The state of risk today.
- **Residual risk** — the level expected once all _planned_ applied controls have been implemented. The target state, and the figure used in risk-acceptance decisions.

Each level has its own probability, impact, and overall level fields. The assessment's consistency check flags a scenario whose **residual** risk exceeds its **current** risk (on level, probability, or impact), and also flags a residual lowered below current when no applied control justifies the reduction.

## Risk acceptance

Risk acceptance is when an organisation or individual decides to tolerate a certain level of risk without taking further action to reduce it. CISO Assistant provides a workflow to capture formal approval of risk acceptances by management — the approver must hold the **Approver** role.

For the formal definition, see [ISO 31073:2022, term 3.3.32 — risk acceptance](https://www.iso.org/obp/ui/#iso:std:iso:31073:ed-1:v1:en:term:3.3.32).

## Risk matrix

Risk levels are calculated as a function of the probability and impact of a scenario, using a configurable **risk matrix**. Matrices are imported from libraries — pick one of the built-in matrices or define your own via a custom library.

Most organisations define an official matrix to be used for all risk assessments, but CISO Assistant lets you choose a different matrix per assessment when needed. The matrix **can be changed** after the assessment has been created. When you do, each scenario's existing probability and impact values are clamped to the new scale's bounds — a score that falls outside the new range is clipped to the nearest valid value, and unrated scenarios stay unrated. There is no proportional rescaling, so review the scenarios afterwards and correct any score that no longer reflects your intent.

## Related

- [Assets](assets.md)
- [Applied controls](applied-controls.md)
- [Vocabulary → Threat / Risk assessment](../introduction/vocabulary.md)
