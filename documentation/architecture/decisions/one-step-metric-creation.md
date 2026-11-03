# Create a metric in one step

- Status: Accepted
- Date: 2026-10-26, accepted 2026-11-03
- Deciders: @nas-tabchiche

## Context

A metric is two objects: a definition (name, kind, unit, direction, default target) and an instance in a domain, which holds the samples. Entering a first value takes three forms in three places. Computed metrics already skip the first: the compose modal creates the definition under the hood, in the metric's domain, and reuses one when the formula matches.

Two definition settings do not fit what people measure. `higher_is_better` is a boolean, so a count of assets reads as good when it grows. Values are shown at full precision, so authors wrap every formula in `round()` to get one decimal on a percentage.

How a definition is spread across a group's domains and monitored there is decided in [deploy-definitions-to-domains](deploy-definitions-to-domains.md).

## Decision

A metric is created in one form: name, domain, kind, unit, decimals, frequency, direction, target. The form creates a definition in the metric's domain, named after the metric and suffixed when the domain already has one, as compose does. While the name is typed, the form offers a definition the user can read with a similar name and the same kind; the hint never blocks. A definition gains a merge action: its instances move to the chosen definition and it is deleted; kind and unit must match.

Direction becomes three-way: higher is better, lower is better, none. None means no good or bad colouring, no trend colour, and an optional target. It is stored as the existing boolean made nullable.

A definition carries a number of decimals, defaulted by unit: one for a percentage, zero for a count. It applies wherever a value is shown. Stored values and exports keep full precision, and formulas read raw values.

## Consequences

- A domain manager creates and feeds a metric without meeting a definition.
- The similar-name hint reaches library, global and group-level definitions only. Two sibling domains defining the same metric independently is caught after the fact, by the merge, by someone who sees both domains.
- A merge keeps the chosen definition's direction, decimals and default target. An instance with a target of its own keeps it.
- Readers of `higher_is_better` handle null. A library definition without a direction keeps today's default, higher.
- Schema: the direction boolean becomes nullable and the definition gains decimals. One migration, no data step.
- The merge ships with the creation release, not later.

## Security considerations

A definition created by the form lives in the metric's domain under the metric's permissions; nothing new becomes readable. The similar-name lookup returns only definitions the user can already read, so it reveals no name from a sibling domain. A merge requires change rights on both definitions and on every instance it moves.

## Alternatives considered

- Creating implicit definitions one level up so siblings find them. Leaks names across domains.
- Blocking creation on a similar name. False positives, and the person cannot open the other domain to judge.
- A `direction` choice field replacing the boolean. Cleaner, but a data migration and a library loader shim for the same information.
- Rounding in the formula. Every author rewrites it, the stored series loses precision, and the preview disagrees with the value.
