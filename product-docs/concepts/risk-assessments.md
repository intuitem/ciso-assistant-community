# Risk assessments

A **risk assessment** (also called a _risk study_) is a scenario-based evaluation of risk over a perimeter. CISO Assistant supports qualitative approaches (configurable risk matrices), quantitative approaches (Monte Carlo over loss distributions), and the structured EBIOS RM methodology.

The platform follows the ISO 27005 risk-management workflow.

![ISO 27005 risk management workflow](../.gitbook/assets/iso27005.svg)

## Risk assessment

A risk assessment encompasses three steps:

- **Risk identification** — defining the risk scenarios.
- **Risk analysis** — assessing probability, impact, and strength of knowledge for each scenario.
- **Risk evaluation** — done automatically based on the selected risk matrix.

In CISO Assistant, **risk treatment is combined with the risk assessment** rather than tracked as a separate phase.

## Risk scenario

Scenarios can be defined directly from the risk-assessment view or separately via the scenarios view. The same scenario can be reused across multiple studies.

## Risk acceptance

Risk acceptance is when an organisation or individual decides to tolerate a certain level of risk without taking further action to reduce it. CISO Assistant provides a workflow to capture formal approval of risk acceptances by management — the approver must hold the **Approver** role.

For context on the process itself, see the [ENISA risk-management process](https://www.enisa.europa.eu/topics/risk-management/current-risk/risk-management-inventory/rm-process/risk-acceptance).

## Risk matrix

Risk levels are calculated as a function of the probability and impact of a scenario, using a configurable **risk matrix**. Matrices are imported from libraries — pick one of the built-in matrices or define your own via a custom library.

Most organisations define an official matrix to be used for all risk assessments, but CISO Assistant lets you choose a different matrix per assessment when needed. **The matrix cannot be changed once an assessment has been created.**

## For users

> _Draft._ Choosing an approach (qualitative / quantitative / EBIOS RM); building a scenario; using the risk matrix; capturing inherent vs residual risk; reading the heatmap and the treatment plan.

## For implementers

> _Draft._ `RiskAssessment`, `RiskScenario`, `RiskMatrix` models. The `ebios_rm` Django app and its object graph. The quantitative risk study simulation pipeline.

## Related

- [Assets](assets.md)
- [Applied controls](applied-controls.md)
- [Vocabulary → Threat / Risk assessment](../introduction/vocabulary.md)
