# Compute metrics from other metrics as aligned time series

- Status: Proposed
- Date: 2026-10-09
- Deciders: @nas-tabchiche, @ab-smith

## Context

A derived metric ([derived-metrics-from-workflow-reads](derived-metrics-from-workflow-reads.md)) reads objects as they are now, and other metrics only through their latest sample. A metric built from other metrics, such as a click rate from clicks and users trained or a group figure summed over its sites, has no history, misaligns inputs collected at different frequencies and ignores corrections to past inputs.

Objects have no recorded past, so a dataset value cannot be recomputed for an earlier date. Metric samples do have a past.

## Decision

A definition's formula reads either datasets or metric inputs, never both. A metric input names another definition. On an instance it resolves to that definition's instances in the instance's folder and its sub-folders, combined as one value (exactly one instance must match) or as the sum, average, minimum, maximum or count of all matches. Deprecated instances are never read. When the domain holds several, the instance picks the one a one-value input reads, or excludes some from a combined input; exclusions, not a list, so a new site is read without anyone ticking it. A pick that no longer matches is an error, never a fallback.

The output's collection frequency cuts time into calendar periods: quarter hours, hours, days, ISO weeks, months, quarters, years. Each input contributes its last sample at or before the end of a period, unless that sample is older than the input's staleness threshold. A period with a missing input is skipped unless the expression handles null. The expression runs once per period and may read the previous period's result.

The result is one stored sample per instance and period, replaced when recomputed. A new instance backfills from its inputs' earliest samples, up to a fixed number of periods. Creating, editing or deleting an input sample marks the periods it can affect, after commit; the sweep recomputes them. Editing the formula recomputes the whole series. An input may itself be derived: cycles are refused at save time and recomputation follows dependency order.

A dataset formula joins a metric formula through composition: it becomes a metric of its own, whose samples are its history from the day it was created.

## Consequences

- Past values of a derived metric change when inputs are corrected. Replaced values are not kept; each sample records when it was computed. A figure that must not move belongs in a report.
- "Old samples are never rewritten" from the previous ADR now holds for dataset formulas only.
- At most one derived sample per instance and period.
- Metric formulas use calendar periods; the dataset sampler keeps its rolling intervals.
- History older than a week keeps one value per day, as for dataset formulas.
- An output faster than all its inputs repeats values. The editor warns.
- Quantitative inputs only. Units are not converted; the author sets the output unit.
- Schema: inputs on the definition, the period on the sample, a recompute mark on the instance.

## Security considerations

Inputs never leave the instance's folder subtree, the boundary datasets already use. A viewer of the output sees a combination of instances they may not open, as they already see aggregates over objects they cannot open. Cycle refusal and the backfill cap bound worker cost.

## Alternatives considered

- Formulas on the instance, naming instances. Closer to a spreadsheet, but cannot ship in a library and must be rebuilt per domain.
- Evaluation on read. Targets, staleness and every other consumer of samples would need the engine.
- Freezing past results. Produces values nobody can reproduce from the inputs.
- Datasets and metric inputs in one formula. Past periods would silently use present-day objects.
- Inputs from sibling or parent folders. Breaks the subtree visibility rule.
