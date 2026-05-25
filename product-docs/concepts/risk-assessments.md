# Risk assessments

> _Draft — placeholder._

A **risk assessment** (also called a _risk study_) is a scenario-based evaluation of risk over a perimeter. CISO Assistant supports both qualitative approaches (using configurable risk matrices) and quantitative approaches (Monte Carlo over loss distributions), as well as the structured EBIOS RM methodology.

## What this page should cover

- The three flavours: qualitative, quantitative, EBIOS RM — when to use each.
- Common building blocks: scenarios, threats, assets, applied controls, residual risk.
- Risk matrices as configurable libraries.
- How the same scenario can be reused across studies.

## For users

> _Draft._ Choosing an approach; building a scenario; using the risk matrix; capturing inherent vs residual risk; reading the heatmap and the treatment plan.

## For implementers

> _Draft._ `RiskAssessment`, `RiskScenario`, `RiskMatrix` models. The `ebios_rm` Django app and its object graph. The quantitative risk study simulation pipeline.

## Related

- [Assets](assets.md)
- [Applied controls](applied-controls.md)
- [Vocabulary → Threat / Risk assessment](../vocabulary.md)
