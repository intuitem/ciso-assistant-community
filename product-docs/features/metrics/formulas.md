---
description: "What a computed metric's formula can say: names, arithmetic, conditions, missing values, functions, levels, periods and history"
---

# Formula reference

A computed metric's formula is a short expression in [CEL](https://cel.dev), the language workflows also use. It runs once per period and returns the metric's value for that period: a number, or a level.

```
round(employees_trained * 100.0 / headcount, 1)
```

## What a formula can read

| Name | Holds |
|---|---|
| The input names, such as `employees_trained` | Each input's value for the period: its latest sample up to the end of the period. See [Periods](#periods) |
| `previous` | This metric's own result for the period before, or `null` for the first period |
| `today`, `now` | The period's end, as a date (`2026-10-31`) and as a date and time |

Click a name chip in the editor to insert it, or type: suggestions show each name with its current value.

## Arithmetic and comparisons

| Write | Means |
|---|---|
| `+` `-` `*` `/` | Add, subtract, multiply, divide |
| `%` | Remainder of a division, whole numbers only |
| `<` `<=` `>` `>=` `==` `!=` | Comparisons |
| `&&` `\|\|` `!` | And, or, not |
| `condition ? a : b` | `a` when the condition holds, `b` otherwise |
| `( )` | Grouping |

**Whole numbers stay whole.** Two whole numbers divide into a whole number: `212 / 238` is `0`. As soon as one side has decimals, the result keeps them: `212 * 100.0 / 238` is `89.07…`. Write `100.0` rather than `100` in a percentage, or wrap a value in `double(…)`.

## Functions

| Function | Returns | Example |
|---|---|---|
| `round(x)` | `x` rounded to a whole number, halves up | `round(2.5)` is `3` |
| `round(x, digits)` | `x` rounded to `digits` decimals | `round(89.0756, 1)` is `89.1` |
| `floor(x)`, `ceil(x)` | `x` rounded down, up | `ceil(4.2)` is `5` |
| `abs(x)` | `x` without its sign | `abs(previous - x)` |
| `min([…])`, `max([…])` | The smallest, the largest of a list | `max([france, germany, spain])` |
| `sum([…])`, `avg([…])` | The total, the average of a list | `avg([q1, q2, q3])` |
| `int(x)` | `x` without its decimals | `int(7.9)` is `7` |
| `double(x)` | `x` as a decimal number | `double(trained) / double(headcount)` |

## Missing values

An input has no value for a period when it has no sample yet, or when its latest sample is too old (see [Periods](#periods)). Its name then holds `null`.

- **By default, the period is skipped.** The formula fails on the missing value, and the period gets no result. The preview shows it as *skipped*.
- **To compute anyway**, say what a missing value means: `trained == null ? 0 : trained`.
- **To skip a period on purpose**, return `null`: `headcount == 0 ? null : clicks * 100.0 / headcount`.

`previous` is `null` for the first period, so a formula reading it usually starts with `previous == null ? … : …`.

{% hint style="warning" %}
A formula that fails while every input has a value stops the whole computation: for example a division by zero in one period. The metric keeps its earlier results and its page shows **Last computation error**, naming the period. Guard the division, as in the example above, then use **Refresh now**.
{% endhint %}

## Returning a level

A metric whose result is a **Level** returns one of its levels, by:

- its name, such as `"High"`;
- its Ref ID, such as `"high"`;
- or its position, `1` for the first.

Names and Ref IDs are matched without regard to case. A text that is not one of the levels is an error, which the editor warns about as you type: *'Medium' is not one of the levels*.

```
coverage >= 90.0 ? "On track" : coverage >= 60.0 ? "Behind" : "Off track"
```

## Examples

| Goal | Formula |
|---|---|
| Percentage of a whole | `round(trained * 100.0 / headcount, 1)` |
| Rate per thousand | `incidents * 1000.0 / headcount` |
| Change since the period before | `previous == null ? null : rate - previous` |
| Worst of several sites | `max([france, germany, spain])` |
| Three-way level | `score >= 80.0 ? "Good" : score >= 50.0 ? "Fair" : "Poor"` |
| Count a missing input as zero | `(late == null ? 0 : late) * 100.0 / total` |

## Periods

The metric's **collection frequency** cuts time into calendar periods, in UTC: quarter hours for real-time, then hours, days, weeks starting on Monday, months, quarters and years. The formula runs once per period.

An input's value for a period is its latest sample up to the end of that period, unless that sample is older than the input's own staleness threshold:

| Input's frequency | A sample still counts for |
|---|---|
| Real-time | 15 minutes |
| Hourly | 2 hours |
| Daily | 36 hours |
| Weekly | 8 days |
| Monthly | 32 days |
| Quarterly | 95 days |
| Yearly | 370 days |

So a monthly metric reading a yearly input gets the same yearly value every month until the next one arrives, and a monthly input that stopped reporting goes missing after 32 days.

## History

A computed metric's series is complete from the start:

- A new computed metric computes every period since its inputs' first sample, up to 1,000 periods back; for hourly and real-time metrics, the last week.
- When an input sample is added, corrected or deleted, the periods it affects are recomputed at the next run. Past values can change. A figure that must never move belongs in a report.
- Editing the formula recomputes the whole series.

The metric computes on its collection frequency, and on demand with **Refresh now**.

## Limits

- A formula is at most 2,000 characters.
- A formula reads at most 20 metrics.
- Input names start with a letter or `_`, hold letters, digits and `_`, are at most 64 characters, and cannot be `previous`, `metrics`, `now` or `today`.
- A metric cannot read itself, directly or through other formulas.
- Formulas read numbers only: a metric whose result is a level cannot be an input.
