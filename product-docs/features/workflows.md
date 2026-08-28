---
description: Reference for the workflow builder — the steps you can place, what starts a run, the expression syntax, and the limits the engine enforces
---

# Workflow builder

This page is the reference for building workflows. For what a workflow _is_ and how it fits the rest of the platform, read [Workflows](../concepts/workflows.md) first.

## Steps

Drag steps from **Add a step** onto the canvas and connect them.

| Step | What it does |
|---|---|
| **Trigger** | Where a run starts. A workflow can carry several |
| **Action** | Does one thing — read, create, update, send, call, compute |
| **Condition** | Splits the path into branches |
| **Loop** | Repeats the steps on its **each item** port for every entry in a list, then continues from **done** |
| **Stop run** | Ends the run |

Branches are checked **from top to bottom — the first match runs**, and the **otherwise** branch runs if none match. Every branch must be wired to something, or publishing refuses.

A loop can keep one value per iteration with **Collect per item**, which lands in the loop's results — the usual way to build a digest out of rows you just read.

## Triggers

### Manual

Press **Execute**, then **Choose a trigger to run**. If the graph declares variables you can override them for that run only — **Run with variables**, _"values you change here apply to this run only"_ — which is how you test a graph before arming anything.

### Webhook

Publishing mints the URL, shown in the **Triggers** panel: _POST JSON to this URL to start the workflow at this trigger._ The request body arrives as `{{payload}}`, and **Incoming data → variables** maps fields of it onto named variables. Webhook triggers arrive **Enabled**, because nothing happens until someone calls the URL. The URL carries a secret you can rotate.

### Schedule

A **Cron expression** plus a timezone. The floor is one minute — `Minimum interval is 1 minute` — and an invalid expression is refused at publish. If the previous run is still going when the next occurrence comes round, the occurrence is skipped and recorded as **Skipped (previous run still active)** rather than piling up.

Missed occurrences (the instance was down) coalesce into one run on the next tick.

### On event

Pick an **Event** — a model and one of created / updated / deleted — and optionally narrow it with filters, so a run starts only when a field changed to something you care about rather than on every save.

Two behaviours are worth knowing:

- **One user action, one run per object.** A single request that touches many rows — a bulk edit, a mapping merge — starts one run per object rather than one run in total, and repeated changes to the _same_ object inside that request collapse into one. Repeats within five minutes of the same action and object are recorded as **Coalesced (same user action already handled)**.
- **Chains are bounded.** A run's own changes can trigger further workflows, up to five generations deep; beyond that the firing is recorded as **Skipped (too many chained triggers)**.

## Actions

| Action | Notes |
|---|---|
| **Read objects** | 16 models. Filters, ordering, and a row cap (25 by default, 100 maximum). The unpaged count is available for threshold conditions |
| **Create object** | 12 models. Can **update when it already exists**, matched on the entry's key — how a sync-style flow avoids duplicates |
| **Update object** | 14 models. Writes whitelisted fields and links; see the guardrails below |
| **Send email** | Recipients, subject, body. Fails the step when delivery fails |
| **HTTP request** | Outgoing call with headers, body and a timeout; secrets are referenced, never printed |
| **Date offset** | A base date plus days or weeks, into a variable — how deadline and expiry windows are built |
| **Set variables** | Writes named variables |
| **Log** | Writes a line into the run log |
| **Provision domain** | Creates a domain, optionally with its default user groups |
| **Provision user** | Creates or updates a user, with or without the onboarding email |
| **Manage group membership** | Adds or removes a user from a group |

Every action runs with the run-as user's permissions, checked live, and can only reach objects in the workflow's domain and the domains beneath it.

## Guardrails

`Update object` writes only what its registry allows. These are refused at publish and at run time:

| Never writable | Why |
|---|---|
| Requirement assessment **result**, **score**, documentation score | A workflow that answers an audit destroys its evidentiary value |
| Risk scenario **treatment** and its ratings | The treatment decision and the rating are the analyst's |
| Validation flows and risk acceptances, entirely | Approving, rejecting and revoking are human acts, and their history is written elsewhere |
| Incident **status** and **severity** | Each transition writes a timeline entry the engine cannot produce |
| Evidence and exception statuses, except expiry | A lapsed date is a fact; approving evidence is a judgment |
| Finding status **dismissed** | Dismissal is a person deciding it is not a problem |
| Any object's **name** | Identity stays stable, so create-if-missing keeps matching |

Values outside a field's allowed choices are refused too, so a typo in a status cannot reach a table as an unknown value.

## Expressions

Anywhere a field accepts text, `{{...}}` inserts a value:

| Expression | Resolves to |
|---|---|
| `{{my_variable}}` | A workflow variable |
| `{{nodes.<step>.<path>}}` | Something an earlier step returned, e.g. `{{nodes.fetch.results.0.name}}` |
| `{{payload.<path>}}` | The webhook body, or the event that started the run |
| `{{secrets.<name>}}` | A secret, in HTTP requests |
| `{{item}}`, `{{index}}` | The current entry inside a loop |
| `{{today}}`, `{{now}}` | The date and time the run started |

The syntax has **no functions and no operators** — there is no `{{today + 30d}}`. Arithmetic on dates is the **Date offset** action's job. `today`, `now` and `payload` belong to the engine: a graph cannot declare or overwrite them.

`{{today}}` and `{{now}}` are fixed when the run starts, so a retried step compares against the same date as its first attempt. A scheduled run reads them in the schedule's own timezone.

## Variables, secrets and results

**Variables** are the graph's named values: declared on the workflow, seeded from a webhook payload or a manual run, and written by **Set variables**, **Date offset** or a step's **Save results to variables**.

**Secrets** are write-only. You set a value, the builder never shows it again, and only `{{secrets.<name>}}` in an HTTP request can use it. A library that needs secrets declares them, and asks for the values when you install it.

## Limits

| | |
|---|---|
| Rows returned by a read | 25 by default, 100 maximum |
| Cron frequency | One minute minimum |
| Chained triggers | 5 generations |
| Event coalescing window | 5 minutes per action and object |
| Run time limit | Set per workflow; `0` means no limit, and runs that exceed it are stopped |

## Libraries and YAML

**Export as YAML** turns a workflow into a library document, and **Import workflow** reads one back. The format is a stable contract: it carries the graph, the declared variables, and the names of the secrets it needs — never their values. Imported workflows land as drafts, divorced from the library, with schedule and event triggers disabled.

The document can also carry per-step retry settings (attempts, delay, backoff) for authors who need them.
