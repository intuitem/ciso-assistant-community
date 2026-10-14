---
description: "Symptoms and fixes for computed metrics: metrics you cannot pick, buttons that stay off, gaps, errors and values that move"
---

# Troubleshooting

Symptoms first, causes second. The metric's page and the editor's live result answer most questions: the page shows the last computation's error, the live result shows what each period gives.

## Picking metrics

### A metric does not show in the search

The search answers "No matching metric instance", or the metric is simply not in the list.

- Every word you type must appear in the metric's name, its definition's name or its domain. Try fewer words.
- The metric's result is a **level**. Formulas read numbers only.
- The metric is **deprecated**.
- You may not view it. Ask for read access to its domain.

### Compute from selection leaves some rows out

Rows that are levels or deprecated are left out, as in the search. At most 20 metrics can be combined: with more selected, the list says "Select at most 20 metrics to combine".

### "You cannot create metrics in a domain holding all these instances"

The new metric must live in a domain that holds every picked metric, and you need the right to create metric instances and metric definitions there. Pick metrics that sit closer together, or ask for that right in their common parent domain.

## The editor

### Create metric or Save stays off

- **Creating**: a name, a domain, at least one metric and a formula are all needed.
- **Editing**: nothing has changed yet, or the drawer shows that the domain does not hold every picked metric.

### The live result says a period is *skipped*

An input had no value for that period: no sample yet, or a sample too old to count. See [Missing values](formulas.md#missing-values) to compute anyway, and [Periods](formulas.md#periods) for how old a sample may be.

### The result is 0, or a whole number when you expected decimals

Two whole numbers divide into a whole number. Write `100.0` instead of `100`, or wrap one side in `double(…)`. See [Arithmetic](formulas.md#arithmetic-and-comparisons).

### "'*text*' is not one of the levels"

The formula returns a text that is not in the **Levels** list. Add the level, or fix the text: a formula returns a level's name or Ref ID, in any case.

### "Pick again the instances of: *name*"

A metric the formula read was deleted, or you can no longer view it. Pick a replacement and give it the same name, or rewrite the formula without it.

## After saving

### The new metric shows N/A

Its history is computed in the background, usually within seconds, and the page fills in by itself. If it stays empty after a minute, click **Refresh now**. If that says "The recomputation could not be queued." or "Still computing in the background. Reload the page in a moment to see it." and nothing changes, the background worker may be stopped: ask your administrator.

### Last computation error

The metric's page shows the error of the last computation under its value. The metric keeps its earlier results until the next computation succeeds.

| The error mentions | Cause | Fix |
|---|---|---|
| a period, then `expression:` and a reason such as `division by zero` | The formula failed although every input had a value | Guard it, for example `headcount == 0 ? null : …`, then **Refresh now** |
| `is not a level of this metric` | A level formula returned a text that is not one of its levels | Fix the formula or the levels |
| `the expression must return a number` | A number formula returned a text or a yes/no | Fix the formula |

### Past values changed

A computed metric's past periods are recomputed when an input sample is added, corrected or deleted, and when the formula changes. This keeps the series true to its inputs. A figure that must never move belongs in a report.

### Saving refused a change to a shared formula

See [When other metrics share the definition](editing.md#when-other-metrics-share-the-definition): some edits are refused because other metrics read this one.

## Buttons

### There is no Edit formula button

The metric is not computed: its samples are entered by hand or by an integration.

### There is no Use in a formula button

The metric's result is a level, and formulas read numbers only.

### There is no button to add a sample

Computed metrics take their samples from their formula only.
