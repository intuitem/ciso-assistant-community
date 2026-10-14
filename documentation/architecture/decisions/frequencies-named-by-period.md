# Name collection frequencies by their period

- Status: Proposed
- Date: 2026-10-13
- Deciders: @eric-intuitem

## Context

A metric instance's collection frequency sets three things: the period a metric formula computes on, when a plain metric turns stale (and so how old a value a formula may still read), and how often a dataset formula runs. The value `realtime`, labelled "Real-time (continuous)", has always meant fifteen minutes for all three; nothing about it is continuous. Metrology is heading towards shorter periods, and "real time" would then mean something else.

Instance writes, the instance filter and library presets take the value; instance reads return the label. Sample writes never carry it.

## Decision

Frequencies are named by their period. `realtime` becomes `15min`, labelled "Every 15 minutes", and a migration converts stored instances. Instance writes (library presets and formula composition included) and the instance filter accept `realtime` as a deprecated alias of `15min`, log each use, and refuse it, with an error naming the replacement, no later than the release that adds a shorter period. A shorter period such as `1min` is a new value. An existing value never changes meaning.

## Consequences

- Nothing changes for existing metrics: same period, same staleness threshold, same checks.
- API clients sending `realtime` keep working during the deprecation, then get an error naming `15min`. The release notes say so.
- The choices list, and the forms built on it, offer `15min` only.
- A new frequency comes with its period, staleness threshold, label and dataset interval. Formulas also need a backfill bound for periods under a day ([derived-metrics-from-other-metrics](derived-metrics-from-other-metrics.md)).
- Restoring a backup taken before the rename is not handled: it brings `realtime` back unconverted.

## Alternatives considered

- Redefining `realtime` as one minute. The frequency also sets the staleness threshold: sources built for fifteen minutes would turn stale and starve the formulas reading them.
- Keeping `realtime` and only relabelling it. The word stays ambiguous, and remains the obvious name for whatever comes next.
- "Quarter-hourly". Too close to `quarterly`, which means three months.
- Refusing `realtime` at once. Breaks scripts that create instances, for a rename that changes nothing else.
