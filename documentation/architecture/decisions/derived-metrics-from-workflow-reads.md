# Derive metrics from workflow reads and CEL, not from a new query layer

- Status: Proposed
- Date: 2026-10-07
- Deciders: @nas-tabchiche

## Context

Some metrics are a function of data already in the instance: average audit progress across domains, the share of applied controls that are active, the number of controls past their ETA. The metrology app has the whole metric lifecycle (library-shippable definition, folder-scoped instance with target and frequency, samples, dashboards) but no way to produce a sample from the data. Samples are typed in or pushed by a workflow.

The workflow engine has both halves: `read_objects` reads a whitelisted model through a validated filter tree within a folder subtree, and the compute action evaluates CEL with an editor, a live preview and save-time validation. A cron workflow can record such a metric today, but it takes four nodes, a read can only count, and audit progress is not a readable column. A metrics-specific query and formula layer would duplicate both halves. Every aggregate must run on SQLite and PostgreSQL.

## Decision

A derived metric is one or more named datasets plus a single CEL expression over them. A dataset is an unchanged `read_objects` configuration with `mode: "aggregate"`, stated explicitly next to `list` and `first`, and an `aggregates` list. The list never implies the mode; the metric form writes the mode itself. Aggregate mode returns scalars and breakdown maps, never rows.

The expression refers to datasets by name and may also use the metric's previous sample, the latest written sample of other instances in the same subtree, and the current time. For a qualitative definition it returns a level name. The formula lives on the definition so it can ship in a library; the instance binds it to a folder scope.

Recomputation is periodic, at the instance's collection frequency, or manual, by a refresh that enqueues the same task. Real-time maps to the shortest tick. No object change triggers a recomputation. If event-driven freshness is ever added, it marks an instance for the next sweep after commit and never computes inside the request.

The read vocabulary, filter tree, aggregate mode and CEL evaluator move to core and are shared by workflows and metrics.

Each aggregate function runs in one fixed place, decided by its definition, not by the author. Count, distinct count, sum, average, min, max, group-by and duration annotations run in the database in a fixed number of queries. Median, percentile, standard deviation and aggregates over Python-computed values run in the worker, streaming rows up to a hard ceiling. Reaching the ceiling fails the sample. It never truncates.

## Consequences

- One vocabulary. Anything added for metrics appears in workflows, and the reverse. No metrics-only way to describe objects.
- Never write a SQL version of a computation the product already does in Python just to serve a metric. Run it in the worker. Audit progress already has two forms that must agree; do not add another pair.
- Reaching across objects requires a relation predicate (existence or count) declared on the model's read entry as a database annotation. Filters still cannot name fields of related objects.
- CEL stays pure: no database access, never the filter language.
- Worker-side aggregates cost time per row. Each sample runs under a time budget and a per-instance lock. The preview shows the row count.
- Manual refresh never computes inline. Preview is the only inline path and writes nothing.
- Regular ticks accumulate samples. A retention or downsampling rule ships with the sampler.
- An aggregate is offered only once proven on both databases. Duration subtraction is expected to be portable through Django; percentiles are not, hence the worker.
- In aggregate mode, paging, ordering, `include` and an empty aggregates list are errors. Computed values are reached through an aggregate's field.
- Editing a definition's formula changes every bound instance from then on. Old samples are never rewritten.
- One schema migration: formula on the definition, scope on the instance.

## Security considerations

The sampler has no run identity. It reads every object in the instance's folder subtree, and anyone who may view the instance sees the aggregate, including over sub-folders they cannot open. Folder-level builtin snapshots already compute without a viewer identity; the subtree reach is new, since they read direct members only. Datasets and referenced instances must all lie inside the instance's subtree, so a metric never reaches data outside the folder it was created in. Creating one requires the right to add metric instances there.

The filter whitelist is the second boundary: concrete columns only, no paths into related objects, relation predicates limited to existence and counts. The CEL evaluator is pure and terminates. The row ceiling and time budget bound worker cost.

Residual risk: a narrow count can reveal that an object exists in a sub-folder the viewer cannot open. Accepted: the number is an aggregate chosen by someone allowed to create metrics in that folder, and the object's own endpoint still refuses the viewer.

## Alternatives considered

- A metrics-specific dataset DSL. Duplicates the read vocabulary under a second name.
- A derived metric stored as a workflow. A definition must ship in a library, bind to many folders and be edited in a form, not a graph.
- CEL functions that query the database. Breaks purity, and preview, provenance and safe scheduling with it.
- Row lists inside CEL with comprehension macros as the only aggregate mechanism. Unbounded Python-side cost. Possible later extension of the worker-side aggregates.
- ORM-only aggregation. Forces a second SQL implementation of every Python computation.
- Live evaluation on dashboard read. No history, no staleness, Python aggregates on the request path.
- Recompute on object change. A bulk edit recomputes once per row on the write path, the dependency map through annotations is transitive, and one sample per burst breaks the series' regular spacing. SQLite's single writer makes it worse.
