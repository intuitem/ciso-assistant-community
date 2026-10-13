# Compute metrics from other metrics as aligned time series

- Status: Proposed
- Date: 2026-10-09, updated 2026-10-13
- Deciders: @nas-tabchiche, @ab-smith, @eric-intuitem

## Context

A derived metric ([derived-metrics-from-workflow-reads](derived-metrics-from-workflow-reads.md)) reads objects as they are now, and other metrics only through their latest sample. A metric built from other metrics, such as a click rate from clicks and users trained or a group figure summed over its sites, has no history, misaligns inputs collected at different frequencies and ignores corrections to past inputs.

Objects have no recorded past, so a dataset value cannot be recomputed for an earlier date. Metric samples do have a past.

Inputs may also change fast, and metrology is heading towards real time. A source writing a sample every second must not turn into work per sample for the formulas reading it: no recompute per sample, no read of every sample in a period. A change should still reach those formulas within seconds, not at the next sweep. How fast samples are stored is decided in [entered-samples-one-second-resolution](entered-samples-one-second-resolution.md).

## Decision

A definition's formula reads either datasets or metric inputs, never both. A metric input names another definition. On an instance it resolves to that definition's instances in the instance's folder and its sub-folders, combined as one value (exactly one instance must match) or as the sum, average, minimum, maximum or count of all matches. Deprecated instances are never read. When the domain holds several, the instance may change how an input combines (the definition sets the default), pick the one a one-value input reads, or exclude some from a combined input; exclusions, not a list, so a new site is read without anyone ticking it. A pick that no longer matches is an error, never a fallback.

The output's collection frequency cuts time into calendar periods: quarter hours, hours, days, ISO weeks, months, quarters, years. Each input contributes its last sample at or before the end of a period, unless that sample is older than the input's staleness threshold. That sample is fetched on its own, one indexed lookup per input instance and period; the samples before it are never read. A period with a missing input is skipped unless the expression handles null. The expression runs once per period and may read the previous period's result.

The result is one stored sample per instance and period, replaced when recomputed. A new instance backfills from its inputs' earliest samples, up to a fixed number of periods. Creating, editing or deleting an input sample marks the periods it can affect, after commit. The first mark queues a recompute job two seconds later; marks made while it waits queue nothing more, through a flag in the task queue's storage that the web processes and the worker share. The job recomputes the marked instances in dependency order, and repeats while its own results mark further formulas, so a chain settles in one job. One job runs at a time. Every metric formula computation goes through it, a refresh and a new composition included. The sweep stays as a backstop: it marks the metric formulas whose interval has passed, from the period their last run reached, and still queues dataset formulas, whose new samples mark the formulas reading them. Editing the formula recomputes the whole series. An input may itself be derived: cycles are refused at save time.

A dataset formula joins a metric formula through composition: it becomes a metric of its own, whose samples are its history from the day it was created. A dataset formula reading another metric's latest value (`metrics.<ref_id>.value`) is not marked: it keeps updating at its own interval.

## Consequences

- Past values of a derived metric change when inputs are corrected. Replaced values are not kept; each sample records when it was computed. A figure that must not move belongs in a report.
- "Old samples are never rewritten" from the previous ADR now holds for dataset formulas only.
- At most one derived sample per instance and period.
- Metric formulas use calendar periods; the dataset sampler keeps its rolling intervals.
- History older than a week keeps one value per day, as for dataset formulas.
- An output faster than all its inputs repeats values. The editor warns.
- Quantitative inputs only. Units are not converted; the author sets the output unit.
- A change reaches the metric formulas reading it two seconds later, plus the worker's scheduler interval: a delayed task reaches the queue at the scheduler's next pass (`--scheduler-interval`, 60 seconds in today's deployed configurations). A dataset formula reading another metric's latest value catches up at its own interval.
- Under a steady stream of changes the job runs back to back on one worker thread; the deployed worker runs two, so other tasks keep being served.
- "Recompute now" on a metric formula answers after the job's delay instead of at once.
- A recompute costs periods times input instances, whatever the number of samples, through an index on the sample's instance and time.
- A period shorter than fifteen minutes ([frequencies-named-by-period](frequencies-named-by-period.md)) needs a backfill bound expressed as a duration (a week) for periods under a day, instead of a number of periods.
- Schema: inputs on the definition, the period on the sample, a recompute mark on the instance, an index on the sample's instance and time.

## Security considerations

Inputs never leave the instance's folder subtree, the boundary datasets already use. A viewer of the output sees a combination of instances they may not open, as they already see aggregates over objects they cannot open. Cycle refusal and the backfill cap bound worker cost, and so does one recompute job at a time under fast inputs.

## Alternatives considered

- Formulas on the instance, naming instances. Closer to a spreadsheet, but cannot ship in a library and must be rebuilt per domain.
- Evaluation on read. Targets, staleness and every other consumer of samples would need the engine.
- Freezing past results. Produces values nobody can reproduce from the inputs.
- Datasets and metric inputs in one formula. Past periods would silently use present-day objects.
- Inputs from sibling or parent folders. Breaks the subtree visibility rule.
- Recomputing only in the fifteen-minute sweep. A change waited up to fifteen minutes, and a chain of formulas moved one level per sweep.
- A job delay growing with the job's duration. Not needed once a recompute reads one value per period; a busy job holds one worker thread at most.
- Reading every sample of a period to keep the last one. Cost and memory grow with the sender's rate.
