---
description: "Exhaustive reference card for workflows: lifecycle, triggers, steps, every action, expressions, Compute, permissions, limits and fixes"
---

# Cheat sheet

Every rule and subtlety of the workflow builder, grouped by topic. Each section links to the full page.

## 1. Prerequisites

| Requirement | Without it |
|---|---|
| **Workflows** feature flag on (**Extra > Settings > Feature flags**) | No menu entry, webhooks answer `404`, schedules and events do nothing. Turning it back on resumes everything |
| `view_workflow` in a domain | No menu entry |
| Background worker running | Schedules, event triggers, emails and time limits silently never happen |
| Email settings configured | Send email fails with `email is not configured` |
| AI provider configured (**Settings > Chat / AI assistant**) | AI steps fail with `no AI provider is reachable` |
| Inbound webhooks allowed on the instance | Every webhook URL answers `404` |

## 2. Lifecycle and versions

| Stage | Rule |
|---|---|
| Draft | Autosaved, no save button. Can be saved in any state |
| Editing a published version | The first change creates a new draft. The published version keeps running untouched |
| **Discard draft** | Deletes the draft, shows the published version again |
| **Publish** | Runs the [publish checks](publish-checks.md), then lists the permissions the workflow will use in your name |
| Run identity | The publisher. Checked live at each step. Republishing makes the new publisher the run identity |
| Publisher deleted | Amber **No run-as user** badge, automatic triggers stop. Republish |
| **Restore as a new draft** | From the **Workflow versions** panel. Blocked while a draft exists |
| **Enabled** switch (header) | Master switch for every automatic trigger. Rows keep their own state. Manual runs still work |
| **Time limit** (header) | Per run, `0` = none. Checked every minute, applies to runs already in flight |
| Undo / Redo | 50 steps. Edits within one second coalesce |

See [Workflow builder](README.md).

## 3. Triggers

### Overview

| Trigger | Starts when | State at publish | Payload | Limit |
|---|---|---|---|---|
| Manual | **Execute** is clicked | No state, not in the Triggers panel | None | One per workflow |
| Webhook | `POST` JSON to the trigger URL | **Enabled** | The posted body | |
| Schedule | A cron expression fires | **Disabled** | None | |
| On event | An object is created, updated or deleted | **Disabled** | Event payload (§6) | |

- A workflow needs at least one trigger, can have several, and a run starts at exactly one.
- A trigger's kind is fixed. To change it, delete it and add another.
- Nothing can be wired into a trigger.
- **Incoming data → variables** copies payload fields into variables at run start. Needed only to branch on them, since `{{payload}}` is always available.
- Renaming a registered trigger resets it at the next publish: new webhook URL, on/off state back to default.

### Webhook

```
https://<instance>/api/workflows/hooks/<workflow id>/<trigger ref>/<secret>/
```

| Answer | Meaning |
|---|---|
| `201` | Run started, body holds the run id |
| `404` | Wrong URL, wrong secret, trigger disabled, workflow paused, never published, flag off, or inbound webhooks disabled. Deliberately identical |
| `409` | The published version no longer has this trigger. Republish |
| `429` | Rate limited per sender |

- URL visible only after publish, and only to users who can change the workflow.
- Secret: 64 random characters. **Rotate secret** kills the old URL immediately.
- Disabling the row makes the URL answer `404` without rotating.

### Schedule

| Expression | Fires |
|---|---|
| `0 7 * * *` | Daily 07:00 |
| `30 8 * * 1` | Mondays 08:30 |
| `0 16 * * 5` | Fridays 16:00 |
| `0 6 1 * *` | 1st of the month 06:00 |
| `*/15 * * * *` | Every 15 minutes |

- Five fields, one minute minimum. **Timezone** is an IANA name, default `UTC`. It also sets `{{today}}` and `{{now}}`.
- Never overlaps itself: **Skipped (previous run still active)**.
- Occurrences missed while the worker was down collapse into one run. No catch-up storm.
- An occurrence falling while the workflow is paused is skipped.
- A new expression applies at the next publish, the row keeps its state.

### On event

- Any audited object: controls, findings, vulnerabilities, audits, requirement assessments, risk acceptances, validation flows, entities, users, tokens, and more.
- Fires only for objects in the workflow's domain subtree, whatever the filters say. A folder filter outside the subtree is refused at publish.
- Objects without a domain (users, tokens) live in the root: only a root workflow sees them.
- Filters: a run starts when **any** group matches, a group matches when **all** its conditions do. Quick chips: `status`, `folder`, `filtering_labels`.
- **Only when changed**: off = state after the event ("status is done"), on = transition ("status just became done"). Use it to fire once.
- One user action on one object = one run per trigger (**Coalesced**). A bulk edit still gives one run per object.
- Runs can trigger other runs up to 5 levels deep, then **Skipped (too many chained triggers)**.
- Starts typically within a second.

### Triggers panel results

| Result | Meaning |
|---|---|
| Triggered | A run started |
| Skipped (previous run still active) | Schedule overlap |
| Skipped (not published) | Published version no longer has this trigger |
| Skipped (too many chained triggers) | Depth above 5 |
| Coalesced (same user action already handled) | Expected, one run started |
| Error | Engine refused to start. Check run identity and last publish |

Rows are keyed by step ref. Same ref and kind across publishes = state, secret and history kept. On the canvas: pulsing green dot = enabled, grey = disabled.

See [Triggers](triggers.md).

## 4. Steps and wiring

| Step | Rule |
|---|---|
| Action | Does one thing. A failure fails the run |
| Condition | Exactly one branch taken, first true from top to bottom, else **otherwise** |
| Loop | **each item** port starts an iteration, **done** continues after the last |
| Stop run | Ends the whole run, including other paths and loops. Completed unless a step already failed. Nothing can follow it |

- Several wires out of a step (not a Condition): all run, one after the other.
- A step with several incoming wires runs once per arriving path. No join step: chain paths that must both finish.
- A path just ends when its last step has no outgoing wire.

### Condition

- Compares a **variable** (never a step output directly) to a value. The value can be an expression.
- Several conditions on a branch: **AND** or **OR**.
- **otherwise** cannot be deleted or reordered. Every branch must be wired.
- Comparison follows the variable type (§7).

### Loop

| Setting | Rule |
|---|---|
| **For each item in** | A list from an earlier step, or **Custom expression…** with a single `{{path}}` |
| Objects page by page | The loop runs its own Read objects. Ids frozen at start. Not both modes at once |
| **Collect per item** | Expression evaluated after each successful iteration, accumulated in `results` |
| **On item failure** | **Continue and collect errors** (amber marker) or **Stop the run** |

- Inside the body: `{{item}}`, `{{item.<path>}}`, `{{index}}` (from 0). Nested loop: `{{item}}` is the innermost.
- The body is a single path, may contain Conditions and nested Loops, no parallel fan-out, and every path must return to the Loop's input.
- Output: `count`, `results`, `errors`, `pages`. Run view shows `×N`.
- Caps: 500 items, 20 pages, then stops cleanly with the reason in `errors`.
- Over 100 rows, let the loop read its own pages: a referenced Read objects result keeps only 100 entries.

See [Steps](steps.md).

## 5. Actions

### Summary

| Action | Key outputs | Permission |
|---|---|---|
| Log | `message` | None |
| Set variables | Assigned values | None |
| Date offset | `result`, `base` | None |
| Compute | Computed values | None |
| Read objects, list | `count` (all matches), `results`, `offset`, `next_offset` (0 = last page) | `view_<model>` |
| Read objects, first match | `found`, `object` (a miss is not an error) | `view_<model>` |
| Read objects, numbers | One value per alias | `view_<model>` |
| Create object | `created_object_id`, `created_object_name`, `created_object_model`, `created` | `add_<model>` (+ `change_<model>` with upsert) |
| Create or update in bulk | `model`, `received`, `created`, `updated`, `failed`, `errors` (first 20), `truncated` | `add_<model>`, `change_<model>` |
| Update object | `object_id`, `str`, `updated_fields`, `relations` | `change_<model>` |
| Attach a file to an evidence | `attached`, `status`, `unreachable`, `host`, `reason`, `revision_id`, `version`, `filename`, `bytes`, `task_node_id`, `object_id` | `change_evidence`, `add_evidencerevision` |
| Record a measurement | `object_id`, `metric_instance_id`, `value`, `timestamp` | `add_custommetricsample` |
| Post scan results | `run_id`, `created`, `updated`, `unknown_count`, `unknown_ref_ids`, `enrolled_asset` | `change_postureassessment` |
| Send email | `recipients`, `subject` | None |
| HTTP request | `status`, `body`, `items`, `count`, `pages`, `truncated`, `unreachable`, `host`, `reason` | None |
| Ask AI for values | One key per value, `_input_truncated` | None |
| Ask AI for text | `text`, `_input_truncated` | None |
| Provision domain | `folder_id`, `folder_name`, `created` | `add_folder`, `change_folder` |
| Provision user | `user_id`, `user_email`, `created` | `add_user`, `change_user` (at root) |
| Manage group membership | `user_id`, `group_id`, `group_name`, `operation` | `change_usergroup` |

### Read objects

- Modes: **List matching objects**, **First match only**, **Numbers about the matches**.
- Page size 25 by default, capped at 500. Default order: newest first.
- Rows carry `id`, `name`, `created_at`, `updated_at` plus model fields. Filter on stored values (`active`), read back labels (`Active`).
- `…_count` fields (`evidences_count`, `applied_controls_count`) filter and aggregate like numbers: "controls with no evidence" = `evidences_count` equals `0`.
- Requirement assessments: only assessable ones. Risk scenario level filters ignore unrated scenarios.
- `document_revision.content` is truncated under `{{nodes…}}`: map it to a variable to pass the whole text.
- **Extra data to include**: `quality_check` on audits and requirements (`errors`, `warnings`, `info`, `count`, `flagged`, `messages`, `text`). Branch on `flagged`, not `count`. Expensive: use it on a first-match read or a short page.

| Field type | Filter operators |
|---|---|
| Text | equals, not equals, in, not in, contains, is null |
| Number, date | equals, not equals, greater, less, greater or equal, less or equal, in, not in, is null |
| Boolean | equals, not equals, is null |
| Reference | equals, not equals, in, not in, is null |

**Numbers about the matches**: Count, Count distinct, Sum, Average, Minimum, Maximum run in the database. Median, Percentile (`p` 0 to 100), Standard deviation, and anything over a computed value (an audit's `progress`) run in the worker, up to 10 000 rows, and fail beyond. **Group by** gives a map per value, every choice listed with zeroes, empty values under `null`. No page, order or extra data. A Loop cannot page an aggregate read. Default aliases: `count`, `avg_priority`, `by_status`.

### Create object

- Created in the workflow's domain. Some objects live in their parent's domain: purpose, risk scenario, external rating.
- References accept an id, a urn or a name. Names resolve in the workflow's subtree and the root only, never in intermediate parents.
- **Update when it already exists** matches by name in the landing domain. Not available for audits, entity assessments, managed documents, document revisions, validation flows.
- Bold fields in the [action reference](actions.md#create-object) are mandatory and checked at publish.
- Choice fields must receive an accepted value, otherwise the step fails permanently.
- `timeline_entry` type: only `detection`, `mitigation`, `observation`.
- `entity_score`: one reading per provider per day. Turn upsert on to correct same-day re-runs.
- `task_template`: creates the occurrence too. Upsert re-dates it.
- `validation_flow`: the requester is the run identity.
- `right_request`: opens in **New**.

### Create or update in bulk

- One step for a whole list (`{{item.<path>}}` per entry). Use it after a paged HTTP request: a loop costs two steps per entry.
- Every entry is upserted. A failing entry rolls back alone.
- Up to 10 000 entries by default, beyond that `truncated` is true.

### Update object

- Target in the workflow's subtree and changeable by the run identity.
- Empty field values are ignored. Links: **Add**, **Remove**, **Replace**. **Replace** refuses to detach out-of-scope objects.
- Never writable: names, results, scores, levels, decisions, revision status.

| Object | Status restriction |
|---|---|
| Evidence | `expired`, `missing` only |
| Security exception | `expired`, `deprecated` only |
| Audit, risk assessment, entity assessment, findings binder | Planning states: `planned`, `in_progress`, `in_review`, `done`, `deprecated` |
| Requirement assessment | Status, dates, observation. Never result or score |
| Document revision | Content and change summary while still a draft |

### Attach a file to an evidence

- Source **Text** (rendered content) or **URL** (download, secrets allowed).
- **File it as a new revision** off = overwrite the latest revision, on = new revision. Turn it on for scheduled runs. Either way an approved evidence goes back to **In review**.
- **Find the task occurrence automatically**: answers the most recent occurrence due and not settled (`completed` and `cancelled` are settled, `in_progress` is not). Refuses if two tasks expect the evidence. Never changes the occurrence status.
- A file that answers no occurrence satisfies no task.
- **Continue when the answer is an error** / **when the tool cannot be reached**: nothing filed, `attached` = `false`. Branch on `attached`, not `status`. Unreachable = `status` `0`.
- Respects size limit and extension allowlist. No redirects.

### Record a measurement

- Quantitative metric: the number. Qualitative: option index from 1.
- Refused: index past the last option, non-number, future timestamp, computed metric.
- Empty timestamp = run time. Nothing changes on the metric instance itself.

### Post scan results

- Results: `pass`, `fail`, `not_applicable`, `error`, `not_checked`. Rows carry `ref_id`, `result`, `actual`, `expected`, `message`.
- `ref_id` matched against the posture's framework. Unknown refs are counted, not fatal.
- Same **Run id** patches the same run (idempotent retries). Empty = new run each time.
- An asset not yet in scope is added.

### Send email

- Comma-separated recipients, `Name <address>` accepted. Plain text body.
- One message per recipient. Any failed address fails the step.
- Sent through the worker, the step waits. Ignores the platform's digest mute toggle.

### HTTP request

- GET, POST, PUT, PATCH, DELETE. Timeout 1 to 30 s, default 15.
- Body sent as JSON if it parses, raw text otherwise. `body` = parsed JSON or first 5000 characters.
- `4xx`, `5xx` and unreachable fail the step unless the **Continue when…** boxes are ticked. Unreachable = `status` `0`.
- **Follow pages**: items path, next-page path, cursor or offset parameter, **Count only**, **Fields to keep**, page limit 1 to 50 (default 10). Stops at 10 000 items or ~90% of 5 000 000 characters. `body` empty when paging.
- **OAuth client credentials**: token URL in `https`, client secret must be `{{secrets.…}}`. Token never logged.
- Output mapping keys may contain dots: `body.@odata.count`.
- No redirects, private addresses refused. Secret, `Authorization` header or OAuth require `https`. Errors show the host only.

### Identity steps

| Step | Rule |
|---|---|
| Provision domain | Finds or creates by name under the parent. Parent must be in the subtree. Optional default access groups |
| Provision user | Matched by email, case-insensitive. Names overwrite only when non-empty. **Active** omitted = left alone, so a sync never re-activates an offboarded user |
| Manage group membership | Reader, Approver, Analyst, Domain manager, Respondent. Domain in the subtree. Removing the last global admin is refused |

### AI steps

- Use the chat assistant's provider. Run in the worker.
- **Ask AI for values**: types Choice, Text, Number, Yes/no. 1 to 5 attempts, default 2. Use it before a Condition.
- **Ask AI for text**: 1 to 2000 words, default 200. Map `text` to a variable: `{{nodes…}}` cuts at 1000 characters.
- Input capped at 20 000 characters, cut not refused (`_input_truncated`).
- An AI answer can never be written to a choice field (status, severity, result), even through a variable. Branch on it and write a fixed value per branch.
- 50 AI steps per run by default (`WORKFLOW_AI_MAX_CALLS_PER_RUN`).

See [Action reference](actions.md).

## 6. Expressions

| Expression | Value | Where |
|---|---|---|
| `{{my_var}}` | A variable | Everywhere |
| `{{today}}` | Run date `YYYY-MM-DD` | Everywhere |
| `{{now}}` | Run start, ISO 8601 with offset | Everywhere |
| `{{payload}}`, `{{payload.path}}` | Trigger payload | Webhook and event runs |
| `{{nodes.<ref>.<path>}}` | Output of an earlier step | After that step ran |
| `{{item}}`, `{{item.<path>}}`, `{{index}}` | Loop element, position from 0 | Loop body |
| `{{secrets.NAME}}` | Workflow secret | HTTP request and Attach a file only. Empty elsewhere |

- No functions or operators in `{{ }}`. Use Compute, Date offset or a Condition.
- `{{ today }}` = `{{today}}`. `{{list.0.id}}` picks by position.
- A missing path renders empty, silently. Typos too.
- Objects and lists render as JSON. A list field (loop collection, link ids) takes the real list.
- `{{today}}` and `{{now}}` are frozen for the run, retries included. Schedule runs use the schedule's timezone, others the deployment's.
- Refs derive from the label (`Past their ETA` → `past_their_eta`). Renaming rewrites every reference.

### Event payload

| Key | Content |
|---|---|
| `event_key` | `appliedcontrol.updated` |
| `model`, `operation` | `appliedcontrol`, `created` / `updated` / `deleted` |
| `object_id`, `object_repr` | Id, display name |
| `changes.<field>` | `[old, new]` |
| `new_values.<field>` | New value |
| `folder_id`, `actor_email`, `timestamp` | Domain, author when known, when |

### Stored output caps

Text over 1000 characters is cut, lists and objects keep 100 entries, about 32 KB per run. The builder previews 50 entries of a list, steps read the full list.

See [Expressions](expressions.md).

## 7. Variables and secrets

| Type | Compared as |
|---|---|
| `string` | Text |
| `number` | Numerically |
| `boolean` | `true`, `1`, `yes` = true |
| `date` | Text |
| `json` | Text |

- Keys: letters, digits, underscores, starting with a letter or underscore. Reserved: `now`, `today`, `payload`.
- The default must fit the type, otherwise publish refuses it.
- Values come from: default, trigger mapping, **Save results to variables**, Set variables, Date offset **Store the result in**, Compute, **Run with variables**.
- `{{var}}` can be overwritten later. `{{nodes.<ref>.x}}` is what that step produced.
- Secrets: per workflow, write-only, never exported, never logged, `https` only, must exist to publish (`secret_missing`).

See [Variables and secrets](variables-and-secrets.md).

## 8. Compute (CEL)

| Example | |
|---|---|
| `score = likelihood * impact` | Arithmetic |
| `label = score > 12 ? 'high' : 'low'` | Ternary |
| `coverage = round(double(nodes.done.count) / double(nodes.total.count) * 100.0, 1)` | Ratio |
| `sla_days = payload.severity == 'critical' ? 1 : 30` | Choice |
| `worst = max(nodes.fetch.results.map(r, r.score))` | List macro |
| `total = total + item` | Loop accumulator |
| `'Score: ' + string(score)` | Text concat |
| `has(payload.priority) ? payload.priority : 'medium'` | Missing-field guard |

- Each row's key must be a declared variable. Rows run in order and see the rows above.
- No braces: `A * B`, not `{{A}} * {{B}}`.
- Int and double mix (`3 * 2.5` = `7.5`), but int / int truncates (`7 / 2` = `3`). Number and string do not mix.
- Reading a missing field fails the step. Guard with `has(...)`.
- Functions: `size`, `has`, `int`, `double`, `string`, `timestamp`, `map`, `filter`, `exists`, `all`, `sum`, `avg`, `min`, `max`, `round(x[, digits])` (half up), `floor`, `ceil`, `abs`. `%` takes two ints. Macros nest two levels max.
- Syntax errors fail at publish. Type errors, missing fields, division by zero fail at run time, no retry.
- Each row previews its result against the reference run, or the defaults before any run.

## 9. Permissions and scope

| Operation | Reach |
|---|---|
| Read, Update, Attach a file | Workflow domain and sub-domains, narrowed to what the run identity may see or change |
| Create | Workflow domain. References may come from parents and root |
| On event | Objects in the subtree only |
| Provision domain | Under the workflow domain |
| Group membership | Groups in the subtree |
| Secrets | The workflow's own |

- You can only automate what you could do yourself. Publishing grants nothing.
- Losing a role makes runs fail with `Authorization denied` at the step that needs it.
- A sub-domain workflow never sees a sibling sub-domain. Put it in the root to span everything.
- Draft runs (Execute on a draft) act as the clicker. Published runs act as the publisher.

See [Permissions and security](permissions-and-security.md).

## 10. Runs

| Start | Runs as | Conditions |
|---|---|---|
| **Execute** on a draft | You | Always works |
| **Execute** on a published version | Publisher | Always works, even paused |
| Webhook, schedule, event | Publisher | Published version, trigger enabled, workflow enabled |

- **Execute** starts from Manual. Without one, a picker asks which trigger.
- **Run with variables** overrides values for one run, type-checked.
- Statuses: Active (running or waiting on email), Completed, Failed.
- Buttons: **Use as reference data** (real values everywhere in the builder), **Show on canvas**, **Replay**.
- Runs are history: never edited, resumed or deleted. Fix and run again.
- Safety nets: 5000 step executions per run, email waiting more than 15 minutes fails (`deferred action was never delivered`).

| Log event | Meaning |
|---|---|
| `instance_started` | Starting variables |
| `node_entered` | Step started |
| `action_executed` | Action done, data holds the output |
| `loop_completed` | Count and item errors |
| `authorization_denied` | Missing permission, named |
| `run_terminated` | Stop run or time limit |
| `instance_completed` | All paths finished |
| `error` | Step failed, reason in the message |

See [Runs](runs.md).

## 11. Export, import and templates

- **Export** takes the draft if any, else the published version. Carries variables, steps, wires and secret **names**. Not: secret values, webhook URLs, run history, trigger states, positions.
- **Import** asks for a domain and the required secrets. Arrives as a draft, automatic triggers disabled, layout recomputed. Missing references are warnings. Importing twice gives `(2)`.
- Task, sub-workflow and event steps from old versions are refused at import.
- Library templates: **Preview workflow**, **Instantiate workflow** in a domain. The copy is yours, no sync either way.
- Templates never render a judgment, carry a `notify_emails`-like variable, and arrive with triggers disabled.
- Good first runs: **Read-only explorer**. Reference examples: **Overdue applied controls** (loop), **Validation decided** (branches), **Third-party portfolio review** (paged loop).

See [Sharing workflows](sharing.md) and [Template catalog](templates.md).

## 12. Limits

| Limit | Default | Setting |
|---|---|---|
| Read objects page | 25, max 500 | Deployment |
| Loop items | 500 | Deployment |
| Paged loop pages | 20 | Deployment |
| Step executions per run | 5000 | |
| Chained event depth | 5 | |
| Schedule interval | 1 minute | |
| HTTP timeout | 1 to 30 s, default 15 | |
| HTTP pages | 1 to 50, default 10 | |
| HTTP / bulk items | 10 000 | `WORKFLOW_NODE_OUTPUT_MAX_ITEMS`, `WORKFLOW_UPSERT_MAX_ITEMS` |
| HTTP paged characters | ~90% of 5 000 000 | `WORKFLOW_NODE_OUTPUT_BUDGET` |
| Worker-side aggregates | 10 000 rows | Deployment |
| Stored step output | 1000 chars, 100 entries, ~32 KB per run | |
| AI calls per run | 50 | `WORKFLOW_AI_MAX_CALLS_PER_RUN` |
| AI input / output | 20 000 characters | |
| Email wait | 15 minutes | |

## 13. Quick fixes

| Symptom | Cause | Fix |
|---|---|---|
| No Workflows menu | Flag off, or no `view_workflow` | Enable the flag, grant the role |
| Trigger never fires | Disabled, paused, not published, or worker down | Triggers panel, header switch, publish, check the worker |
| Event trigger silent | Object outside the subtree | Move the workflow up |
| Webhook `404` | URL changed (rename, rotation) or something disabled | Copy the URL again from the Triggers panel |
| Webhook `409` | Trigger removed from the published version | Republish |
| `Authorization denied` | Publisher lacks the permission | Grant it, or republish as someone who has it |
| `no run identity` / **No run-as user** | Publisher deleted | Republish |
| `invalid recipient` | Bad address or empty expression | Check against the reference run |
| `credentials require an https URL` | Secret or auth header over `http` | Use `https` |
| `BlockedRequestError for host` | Private address | Use a public host |
| `is not an accepted <model>.<field>` | Bad choice value | Use a listed value |
| `a workflow may not set ...` | Decision field | Leave it to a person |
| `no <model> '<id>' in this workflow's scope` | Target outside subtree or not changeable | Check the id and scope |
| `did not resolve to a list` | Loop collection is not a list | Pick it from the select |
| Expression renders empty | `node.` instead of `nodes.`, wrong ref, absent payload path, secret outside HTTP, `item` outside a loop | Use **Available data** with a pinned run |
| Condition always **otherwise** | Variable never set, or wrong type | **Save results to variables**, declare as `number` |
| Loop stopped early | 500 items or 20 pages | Narrow filters, or raise the caps |
| Schedule at the wrong hour or twice | Timezone | Set the schedule's **Timezone** |
| "This draft no longer exists" | Draft discarded elsewhere | Last edit lost, redo it |

See [Troubleshooting](troubleshooting.md) and [Publish checks](publish-checks.md).

## 14. Keyboard shortcuts

| Keys | Effect |
|---|---|
| ⌘Z, Ctrl+Z | Undo |
| ⇧⌘Z, Ctrl+Shift+Z, Ctrl+Y | Redo |
| Delete, Backspace | Delete selected steps or wires |
| Enter, Escape | Confirm or cancel the inline variable creator |
| C (list page) | New workflow |

Undo and redo are suppressed while a text field has focus.
