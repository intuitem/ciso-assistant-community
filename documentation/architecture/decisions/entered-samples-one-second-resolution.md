# Store entered metric samples at one-second resolution

- Status: Proposed
- Date: 2026-10-13
- Deciders: @eric-intuitem

## Context

Samples written by people, the API or workflows are stored as they arrive, with no limit on their rate and no retention: a source writing a hundred samples a second adds 8.6 million rows a day, kept forever. Metrology is heading towards real time, so fast sources will come. Formulas need no more than the last value of each period ([derived-metrics-from-other-metrics](derived-metrics-from-other-metrics.md)) and no chart can draw that many points, but an entry made by a person must never be lost.

The entry form sets the time to the minute only, and the form and the API both record `manual` as the source: the backend cannot tell a person from a script.

## Decision

Entered samples, manual and workflow, are stored at one-second resolution: their time is truncated to the second, and a unique constraint holds one sample per instance and second. A sample for a second that already holds one replaces it entirely: value, observation, evidence and source. The write is an update-or-create on that constraint, so concurrent writes for the same second end in one row. Through the API, replacing a sample takes the right to change samples as well as to add them, and moving a sample onto a taken second is refused. The entry form takes seconds and defaults to the current time, so two entries made at different moments never meet. Formula samples keep their own rule, one per period.

## Consequences

- At most one entered sample per instance and second, the last one written. A second entry for the same second replaces the first.
- Storage per metric is bounded by the clock, not by the sender's rate: at most 86,400 rows a day.
- Creating a sample through the API may update an existing one.
- Two entered samples can no longer share a time, so the latest one is never ambiguous.
- A formula's samples stay outside the constraint, so a separate index on instance and time serves the per-period reads of every input, entered or derived.
- Charts request samples at a resolution fitting their range (a minute, a quarter hour, a day) instead of every stored sample.
- The migration keeps the last of the entered samples already sharing a timestamp, then adds the constraint. Existing timestamps keep their fraction of a second. The data is small today; added later, the constraint would mean deduplicating years of samples.
- Schema: a unique constraint on the instance and second of entered samples.

## Security considerations

The resolution bounds storage for a sender using real timestamps. It does not stop a sender spreading its timestamps over many seconds or flooding the API with requests; rate limiting has to handle that.

## Alternatives considered

- Keeping every sample. Storage and every reader grow with the sender's rate.
- Merging only bursts (same second and written less than a second apart). Keeps every entry, but the bound is approximate under concurrent writes and the latest value can stay ambiguous.
- Thinning entered samples to the quarter hour. Enough for formulas, but loses the recent detail charts show.
- Telling people from scripts by the source. Both record `manual`, and API clients can set the source themselves.

## Open questions

- How long entered samples are kept. Today, forever: up to 31.5 million rows a year for a metric fed every second. Thinning to one per day after a horizon keeps formula results and the whole history of ordinary metrics; deleting after a horizon loses both.
- The API answer when a sample replaces another: 200 or 201.
- A bulk endpoint for real-time sources and history imports, which today send one request per sample.
