# Compute a journey's risk levels from the coverage of its audits

- Status: Proposed
- Date: 2026-11-14
- Deciders: @nas-tabchiche

## Context

A risk scenario's probability and impact are chosen by hand at each stage. The only automatic write is the control sync, which copies residual into current once every additional control is active. A scenario has no link to a requirement.

Some risk methods derive the levels instead. Requirements reduce named risks by a weight, on probability, on impact, or both. The current level counts what is met. The residual level counts what will be. Starting values often come from a form.

An audit already computes numbers: outcome rules of kind number, and declarative kinds beside them, evaluated on every change and stored on the audit. A journey gives a scenario a way to reach the audits, the results and the subject of its run, and gives a requirement its importance for the run. Both are decided in [composite-process-as-journey](composite-process-as-journey.md).

## Decision

A framework gains a coverage rule. It lists requirements with a weight each and yields two numbers: achieved and potential. The rule counts a requirement by its result or by its score. By result, a compliant requirement counts its weight, a partially compliant one half, any other nothing. By score, it counts its weight times its score over its maximum. Potential counts every listed requirement in full. A requirement counts in neither when it is hidden, not applicable, or recommended or nice to have for the run. The rule may ask that a result be accepted by a reviewer before it counts.

A preset's risk scenario may define probability and impact, at each stage, as CEL expressions. They read the run's results, its subject, and any value its audits compute, coverage or other. They follow an audit as it is filled, without waiting for it to be done. An expression returns a rank on the matrix's scale, 1 the lowest. It is rounded half up, as the evaluator's `round` does, and held within the scale.

A level defined this way is written by the computation only. It is recomputed when an audit's values, the run's results or the subject change. The scenario shows it as computed, with the figures it was computed from.

An analyst may override a computed level with a justification. An overridden level stops following until the override is removed.

The control sync does not apply to a computed level.

## Consequences

- The method travels with the libraries: weights in the framework, level expressions in the preset. The product ships no formula.
- An unassessed requirement counts for nothing, so a method that subtracts coverage starts at its worst and improves as the audit is filled.
- Changing a requirement's result can move a risk level. The scenario must say which requirements moved it.
- A recommended requirement is assessed and moves no level.
- With reviewed results only, a level moves on the reviewer's act, not on the respondent's answer.
- A method where a level can fall to none needs that level as the lowest rank of its matrix.
- A locked risk assessment is not recomputed, nor one whose journey is no longer open.
- An expression that fails leaves the level as it was and is reported on the scenario. A level is never guessed.
- A scenario outside a journey, or without expressions, is assessed by hand as today.
- Schema: per-level override flags on the scenario. One migration, no data step. The coverage rule is library content.
- Not decided here: whether a requirement under an accepted exception counts in the residual. A third figure for what is planned, between achieved and potential.

## Security considerations

A user who may change a requirement's result changes, through the computation, a level in a risk assessment they may only read. Between internal members we accept it: the level is a function of the audit, both sit in one folder, and the scenario names its inputs.

A questionnaire answered by a third party sits in an enclave, and its respondent cannot read the risk assessment at all. A coverage rule over such an audit should count reviewed results only. Nothing enforces this, the author of the framework owns it.

Overriding needs change rights on the scenario. Expressions come from a library and run in the existing evaluator.

## Alternatives considered

- **Weights on the requirement's threat link, scenarios matched by threat.** Both ends already name threats, and an audit already counts failing requirements per threat, so any framework would feed any scenario with no preset. The link carries no weight today, and existing libraries wrote it as documentation, not as a method.
- **Through applied controls and their impact.** The chain the platform already has, and the residual would follow the real action plan. It needs a control per requirement and scenario links kept by hand, where these methods weigh requirements.
- **Plain CEL, no coverage rule.** No new rule kind. Dozens of requirements times a three-way result per risk is unreadable, and a hidden requirement is a missing key.
- **A fixed formula.** Nothing to author. Methods differ between organisations, and their starting values come from their own forms.
- **Counting a result only once its audit is done.** One rule for conditions and levels. A level would stay at its worst for the whole assessment and jump at the end.
- **Showing the computed level as a suggestion beside the manual fields.** The analyst stays the only writer. Matrices, exports and reports read the fields, so someone would copy every level after every change.
