---
description: "Every action type with its settings, outputs and the permission it requires"
---

# Action reference

This page lists every action type, its settings as they appear in the inspector, what it writes to `{{nodes.<ref>}}` and the permission the run identity must hold.

Fields marked *expr* accept [expressions](expressions.md).

## Data steps

### Log

Writes a line to the run log. Use it to see what an expression resolves to.

| Setting | |
|---|---|
| Message *expr* | The text to log |

Output: `message`. No permission required.

### Set variables

Assigns values to workflow variables for the rest of the run.

| Setting | |
|---|---|
| Variables | One row per variable: the variable key and its new value *expr* |

Output: the assigned values, keyed by variable. Refuses the reserved keys `now`, `today` and `payload`. No permission required.

### Date offset

Computes a date by adding days and weeks to a base date. Use it for due dates.

| Setting | |
|---|---|
| Base date *expr* | An ISO date. Empty means the run's `today` |
| Days *expr* | Whole number, may be negative |
| Weeks *expr* | Whole number, may be negative |
| Store the result in | Optional. A declared variable that receives the result |

Output: `result` (ISO date), `base`. No permission required.

### Compute

Set variables with operators. Each row names a variable and gives a [CEL](https://cel.dev) expression that computes it: a risk score from likelihood and impact, a ratio between two Read objects counts, a loop counter, an SLA picked by severity.

| Setting | |
|---|---|
| Expressions | One row per variable: the variable key and its expression |

#### A first Compute step

Multiply two numbers and log the result:

{% stepper %}
{% step %}
**Declare the inputs.** Open the **Variables** toggle, add `A` and `B` as `number`, and give each a **Default**, say `2`. Add `result` as `number` too.
{% endstep %}

{% step %}
**Add the step.** Wire an **Action** after the trigger and pick **Compute** in the **Action** select.
{% endstep %}

{% step %}
**Write the row.** Under **Expressions**, click **+** (**Add a row**), pick `result` in the key select and type `A * B`. The row shows `= 4` and `int` underneath: that is the value a run would compute, using the defaults.
{% endstep %}

{% step %}
**Use the result.** Wire another **Action** after it, pick **Log** and set **Message** to `Result: {{result}}`, publish and run. The run log reads `Result: 4`.
{% endstep %}
{% endstepper %}

Things people often ask:

- **Do I have to declare the variable first?** Yes. The key of a row is picked from the declared variables, one row per variable, so **+** adds nothing while every declared variable already has a row. Declare one more in the **Variables** panel, intermediate values included.
- **Two ways to read the result.** `{{result}}` reads the variable, which a later row, step or loop iteration may overwrite. `{{nodes.<ref>.result}}` reads what this step computed.
- **Braces or not.** Inside an expression, write paths bare: `A * B`, not `{{A}} * {{B}}`. Braces are for the other steps' settings.
- **Text.** Strings use single or double quotes, and `+` joins them: `'Score: ' + string(score)`. A number has to go through `string(...)` first.
- **A field that may be missing.** Reading one fails the step. Guard it with `has(...)`: `has(payload.priority) ? payload.priority : 'medium'`.
- **The preview shows an error.** It is the error the run would log, against the current data. Fix the row, or click **Use as reference data** on a run in the **Runs** panel whose data looks like what the step will see.

Expressions read the same things `{{ }}` does, without the braces: a variable by its key, `payload.some.path`, `nodes.<ref>.<path>`, `item` and `index` inside a loop. Rows run in order and each can use the ones above it, so an intermediate value does not need its own step.

```
score        = likelihood * impact
label        = score > 12 ? 'high' : 'low'
coverage     = round(double(nodes.done.count) / double(nodes.total.count) * 100.0, 1)
sla_days     = payload.severity == 'critical' ? 1 : 30
worst        = max(nodes.fetch.results.map(r, r.score))
total        = total + item
```

A `number` variable holds an int or a double depending on what wrote it, so unlike canonical CEL the two mix: when one side of an operator is a double, the other is promoted (`3 * 2.5` is `7.5`). An expression with only ints stays int, so dividing two ints drops the remainder as in CEL (`7 / 2` is `3`, `7 / 2.0` is `3.5`). A number and a string do not mix. The step fails with a message that names the row and the problem.

On top of CEL's own `size`, `has`, `int`, `double`, `string`, `timestamp` and the `map`, `filter`, `exists`, `all` macros, these functions are available: `sum` and `avg` over a list of numbers; `min` and `max` over a list of numbers, of strings (ISO dates sort correctly) or of timestamps; `round(x)`, `round(x, digits)` (half up: `round(2.5)` is `3`), `floor`, `ceil`, `abs`. `%` takes two ints. The macros nest at most two deep: `a.map(x, b.filter(y, y > x))` is fine, a third level inside is refused, because each level multiplies the work.

In the editor, each row shows its result as you type, `= 16` with the type, evaluated against the reference run shown under **Available data** or, before any run, against the variables' defaults. A row that cannot be evaluated shows the same error the run would log. Typing opens suggestions: variables with their current value, `nodes.<ref>.` paths, `item` and `index` inside a loop, functions, and list or string methods after a dot. Clicking a value under **Available data** inserts its path.

Output: the computed values, keyed by variable. Refuses the reserved keys `now`, `today` and `payload`. Syntax errors are caught when you publish; type errors, missing fields and division by zero fail the step at run time and are not retried. No permission required.

### Read objects

Queries objects of one kind inside the workflow's scope.

| Setting | |
|---|---|
| Object to read | One of the readable objects below |
| Mode | **List matching objects** returns a page, **First match only** returns a single object |
| Filters | A tree of conditions on the object's fields. Values are *expr* |
| Order by | A field. Tick **Newest / highest first** for descending. Default: newest first |
| Max results | Page size, default 25, capped by the instance (500 by default) |
| Start at *expr* | Offset of the page, for manual paging |
| Extra data to include | Values costly enough that they are only computed when asked for. Offered for the objects that have any |

Output in list mode: `count` (total matches, not just this page), `results` (list of rows), `offset`, `next_offset` (0 when there is no further page). Output in first mode: `found` (boolean), `object` (a row or null). A miss is not an error.

Only objects inside the workflow's domain and sub-domains are returned, further narrowed to what the run identity may view. Permission: `view_<model>`.

Each row carries `id`, `name`, `created_at`, `updated_at` plus the fields below. Filters and ordering accept the same fields.

| Model | Fields |
|---|---|
| `applied_control` | description, ref_id, status, eta, expiry_date, priority, link |
| `evidence` | description, status |
| `incident` | description, ref_id, status, severity, link |
| `asset` | description, ref_id, type, reference_link |
| `vulnerability` | description, ref_id, status, severity, eta, due_date |
| `security_exception` | description, ref_id, status, severity, expiration_date |
| `entity` | description, ref_id, mission, reference_link, is_active, default_dependency, default_penetration, default_maturity, default_trust |
| `findings_assessment` | description, ref_id, status, eta, due_date |
| `finding` | description, ref_id, status, severity, eta, due_date, priority |
| `compliance_assessment` | description, ref_id, status, eta, due_date, plus computed `computed_outcome`, `scores`, `requirements` (total and count per result) |
| `risk_assessment` | description, ref_id, status, eta, due_date |
| `entity_assessment` | description, status, eta, due_date |
| `document_container` | description, ref_id, document_type |
| `managed_document` | description, locale, default_locale, container, plus `document_type` and `current_revision` (id, version number, status). A locale variant with no title of its own reads under the document's name |
| `document_revision` | version_number, status, source, change_summary, content, published_at, document. `content` is the markdown itself, so a long one is truncated in `{{nodes.…}}`; map it to a variable to pass a whole document to an AI step |
| `requirement_assessment` | status, result, extended_result, score, is_scored, documentation_score, eta, due_date, observation, compliance_assessment, plus `requirement` (id, ref_id, name, description), `applied_controls` (each with its own `evidences`) and `evidences` attached to the requirement itself, all narrowed to what the run may see. Every evidence says whether anything is `attached`. Only assessable requirements |
| `risk_scenario` | description, ref_id, treatment, inherent_level, current_level, residual_level, risk_assessment. Level filters ignore unrated scenarios |
| `risk_acceptance` | description, state, expiry_date, justification |
| `validation_flow` | ref_id, status, validation_deadline |
| `task_node` | status, due_date, scheduled_date, observation, task_template. One occurrence of a task. It has no name of its own, so `name` reads as the task's name with the occurrence's date |

Fields with display labels (status, severity, priority, type) filter on the stored value and render as the label. Filter on `active`, read back `Active`.

Filter operators depend on the field type:

| Field type | Operators |
|---|---|
| Text | equals, not equals, in, not in, contains, is null |
| Number, date | equals, not equals, greater, less, greater or equal, less or equal, in, not in, is null |
| Boolean | equals, not equals, is null |
| Reference (another object) | equals, not equals, in, not in, is null |

`in` and `not in` take a comma-separated list.

#### Including the quality check

**Audit** and **Requirement** offer `quality_check` under **Extra data to include** — the same findings the [X-rays](../x-rays.md) page shows, as `{errors, warnings, info, count}`, plus three values for building on them: `flagged` (true when there is an error or a warning), `messages` (the finding sentences) and `text` (those sentences as an indented markdown list, ready to nest under a heading a document writes). It is off by default because resolving it walks the whole audit with its controls and evidences, and it is computed for every row a step reads: ask for it on a **First match only** read, or on a short page.

**Requirement** also offers `applied_controls` and `evidences`: what is claimed to satisfy the requirement, each control with the evidence attached to it, and each evidence saying whether anything is actually attached. Off by default for the same reason — they are the heaviest thing a row can carry, and a page of 500 rows holding all three is how a read outgrows what one step's output can hold.

A run can then branch on it. Branch on `flagged` rather than on `count`: `count` includes the informational findings, which are observations rather than something to act on.

| | |
|---|---|
| Trigger | Audit updated, condition on `status`, **Only when changed**, equals `done` |
| Read objects | Audit, First match only, filter `id` equals `{{payload.object_id}}`, include `quality_check` |
| Set variables | `flagged` = `{{nodes.check.object.quality_check.flagged}}` — a condition reads a declared variable, never a path |
| Condition | `flagged` is `true` |
| Send email | "This audit was closed with open quality findings" |

Reading the audit's own quality check covers every requirement in one call, which is cheaper than reading the requirements and asking each for its own.

## Write steps

### Create object

Creates an object in the workflow's domain.

| Setting | |
|---|---|
| Object to create | One of the creatable objects below |
| Fields | One row per field. Values are *expr* |
| Update when it already exists | When on, matches an existing object by name and updates it instead of creating a duplicate. Matching happens in the domain the object lands in, which is the workflow's own unless noted below |

Output: `created_object_id`, `created_object_name`, `created_object_model`, `created` (false when an existing object was updated).

Permission: `add_<model>`, plus `change_<model>` when **Update when it already exists** is on. Creating an audit or a questionnaire from a framework also needs `add_complianceassessment`.

Reference fields accept an id, a urn, or a name. Names resolve in the workflow's subtree and the root only.

Some objects live in their parent's domain rather than the workflow's: a purpose belongs to its processing, a risk scenario to its risk assessment, an external rating to its entity. **Update when it already exists** matches in the domain the object will land in, so a workflow in a parent domain still finds the object it created last time.

| Model | Fields | References |
|---|---|---|
| `applied_control` | name, description, ref_id | |
| `evidence` | name, description | |
| `incident` | name, description, ref_id, status, severity, link | |
| `asset` | name, description, ref_id, type, reference_link | |
| `vulnerability` | name, description, ref_id, status, severity | |
| `security_exception` | name, description, ref_id, severity, expiration_date | |
| `entity` | name, description, ref_id, mission, reference_link | |
| `findings_assessment` | name, description, ref_id | |
| `finding` | name, description, ref_id, severity, status | findings_assessment |
| `compliance_assessment` | name, description, ref_id | perimeter, framework, implementation_groups. With a framework, the audit is built with its requirements. Upsert not available |
| `risk_scenario` | name, description, ref_id | risk_assessment |
| `risk_assessment` | name, description, ref_id | risk_matrix, perimeter |
| `business_impact_analysis` | name, description, eta, due_date | perimeter, risk_matrix |
| `asset_assessment` | observation | asset, bia |
| `processing` | name, description and processing fields | |
| `purpose` | name, description, legal_basis, article_9_condition | processing |
| `personal_data` | name, description and data fields | processing, category |
| `data_subject` | name, **category**, description | processing |
| `data_recipient` | name, **category**, description | processing |
| `data_contractor` | name, **relationship_type**, **country**, description, documentation_link | processing, entity |
| `data_transfer` | name, **country**, description, transfer_mechanism, guarantees, documentation_link | processing, entity |
| `document_container` | name, description, ref_id, document_type | |
| `managed_document` | name, description, locale, template_used | **container**, content. The first draft revision is created with it, seeded from `content` or from the template named by `template_used`. One document per locale. Upsert not available |
| `document_revision` | content, change_summary | **document**. Opens the next draft, numbered after the last revision and cloning the current content when `content` is left empty. Only one draft may be open at a time. Upsert not available |
| `entity_assessment` | name, description | entity, perimeter, framework, implementation_groups. With a framework, the questionnaire and its enclave are built too. Upsert not available |
| `entity_score` | **score**, **as_of**, scale_max, grade, url, observation | entity, provider |
| `timeline_entry` | **entry**, entry_type, timestamp, observation | incident |
| `task_template` | name, description, ref_id | `assigned_to` (actors), `task_date`, and links to `applied_controls`, `compliance_assessments`, `evidences`, `documents`. Creates the occurrence with it, so the task shows on the board. **Update when it already exists** re-dates that occurrence rather than adding a second one |
| `validation_flow` | request_notes | `approver` (actor), `validation_deadline`, and what is being validated — links to `compliance_assessments`, `evidences`, `policies`, `findings_assessments`, `security_exceptions`. Opens with its submission event. Upsert not available |
| `right_request` | name, **requested_on**, description, ref_id, due_date, request_type, observation | |

**Bold** marks a field the object cannot be stored without: publishing refuses a step that leaves one empty, rather than letting the run write a blank. An object whose name the model requires needs one too, unless **Update when it already exists** is on — where the name is optional on the object itself (a managed document, a privacy record), the step may leave it empty.

Choice fields (status, severity, type, legal_basis) must receive one of the object's accepted values. Anything else fails the step permanently. `timeline_entry` accepts only `detection`, `mitigation` and `observation` as its type: `severity_changed` and `status_changed` record a change someone made to the incident, so a run may not write them.

Four of these are where a run files what an external system reported, and each is worth knowing about:

* **External rating** (`entity_score`) is one reading per provider per day, dated. Turn on **Update when it already exists** and a re-run on the same day corrects that day's reading instead of failing on the duplicate.
* **Timeline Entry** (`timeline_entry`) adds an observation to an incident without touching its status or severity.
* **Task** (`task_template`) attaches work. A run creates a dated, assigned task and the occurrence that puts it on the board; recurrence stays something you set up by hand.
* **Validation flow** (`validation_flow`) asks for sign-off. Name an `approver` and what is being validated — audits, evidences, policies, findings assessments or security exceptions. The requester is the run's own identity.
* **Right Request** (`right_request`) opens a request in **New**. Closing it stays with whoever handles it.

### Create or update in bulk

Creates or updates one object per entry of a list, in a single step. Use it after an HTTP request that follows pages: a loop around Create object costs two steps per entry, so a few thousand devices run out of steps, while this step takes them all at once.

| Setting | |
|---|---|
| Object to create | One of the creatable objects that can be matched |
| Items | A list from an earlier step, such as `{{nodes.list_devices.items}}` |
| Fields | Same as Create object. Each value reads the current entry as `{{item.<path>}}` |
| On item failure | Continue and count the failure, or stop the run |

Every entry is matched and updated the way **Update when it already exists** does on Create object. A failing entry is rolled back on its own and the rest still land.

Output: `model`, `received`, `created`, `updated`, `failed`, `errors` (the first 20, each with its `index` and `reason`), `truncated` (true when the list held more entries than `WORKFLOW_UPSERT_MAX_ITEMS`, which defaults to `WORKFLOW_NODE_OUTPUT_MAX_ITEMS`, 10 000 by default; the rest are skipped).

Permission: `add_<model>` and `change_<model>`.

### Update object

Changes fields and relations on one existing object.

| Setting | |
|---|---|
| Object to update | One of the updatable objects below |
| Which one (id) *expr* | Usually `{{item.id}}` or a created object's id |
| Fields | One row per field. Empty values are ignored |
| Links | One row per relation with an operation (**Add**, **Remove**, **Replace**) and a list of ids *expr* |

Output: `object_id`, `str`, `updated_fields`, `relations` (per relation: operation and count).

The object must be inside the workflow's subtree and changeable by the run identity. Permission: `change_<model>`.

| Model | Writable fields | Relations |
|---|---|---|
| `applied_control` | status, priority, effort, start_date, eta, expiry_date, description, ref_id, link, observation | owner, evidences, assets, filtering_labels |
| `evidence` | status (`expired`, `missing` only), expiry_date, description | owner, filtering_labels |
| `incident` | description, ref_id, link | owners, assets, applied_controls, filtering_labels |
| `asset` | description, ref_id, reference_link, observation | owner, security_exceptions, filtering_labels |
| `vulnerability` | status, severity, description, ref_id, eta, due_date | applied_controls, assets, security_exceptions, filtering_labels |
| `security_exception` | status (`expired`, `deprecated` only), severity, description, ref_id, expiration_date, observation | owners, evidences |
| `entity` | description, ref_id, mission, reference_link | filtering_labels |
| `findings_assessment` | status (planning states), eta, due_date, description, ref_id, observation | evidences, filtering_labels |
| `finding` | status, severity, priority, eta, due_date, description, ref_id, observation | owner, applied_controls, evidences, filtering_labels |
| `compliance_assessment` | status (planning states), eta, due_date, description, ref_id, observation | evidences, assets |
| `risk_assessment` | status (planning states), eta, due_date, description, ref_id, observation | |
| `entity_assessment` | status (planning states), eta, due_date, description, observation | |
| `requirement_assessment` | status, eta, due_date, observation | applied_controls, evidences, security_exceptions |
| `risk_scenario` | description, ref_id | applied_controls, owner, assets |
| `document_container` | description, ref_id, document_type | applied_controls, assets, filtering_labels |
| `managed_document` | description | |
| `document_revision` | content, change_summary — while the revision is still being drafted | |

Planning states are `planned`, `in_progress`, `in_review`, `done`, `deprecated`. Names are never writable. Results, scores, levels and decisions are never writable.

A document revision's status is not writable either, and a submitted, validated or published revision's markdown cannot be touched at all — the same rule the document editor applies. Publishing deprecates the revision it replaces and repoints the document at the new one, which a field write would not do. A workflow writes the draft; someone publishes it, and the rewrite is recorded in the document's edit history under the identity the workflow runs as.

**Replace** replaces the whole relation. It refuses to detach objects outside the workflow's scope, so a workflow cannot silently unlink a parent-domain object.

### Attach a file to an evidence

Adds a file to an existing evidence.

| Setting | |
|---|---|
| Evidence *expr* | The evidence id |
| File name *expr* | Name of the attached file |
| Source | **Text** writes the rendered text as the file. **URL** downloads the file |
| Content *expr* | With source Text |
| URL *expr* | With source URL. Secrets allowed |
| Find the task occurrence automatically | Off by default. Works out the occurrence from the evidence |
| Task occurrence *expr* | Optional. The occurrence this file answers for, when you name it yourself |
| Continue when the answer is an error | With source URL. Off by default |
| Continue when the tool cannot be reached | With source URL. Off by default |
| File it as a new revision | Off by default. Off replaces the file on the evidence's latest revision. On files a new revision and leaves the previous one untouched. Either way an approved evidence goes back to **In review** |

Output: `object_id`, `attached`, `status` (the HTTP status with source URL, empty with source Text), `unreachable`, `host`, `reason`, `revision_id`, `version`, `filename`, `bytes`, `task_node_id`. Every key is reported on both outcomes, empty where it does not apply, so an output mapping cannot break on one branch. Permissions: `change_evidence` and `add_evidencerevision`.

{% hint style="info" %}
**Close the loop with a recurring task.** A task that expects an evidence shows it as provided once a revision filed *for that occurrence* exists. A collected file that answers for no occurrence satisfies nothing, however good the file is — so the task keeps asking.

Filing a file never changes the occurrence's status. Attaching the work and deciding the work is done are different calls, and only the second one is a person's.

Turn on **Find the task occurrence automatically** and the step works it out from the evidence — there is nothing to look up and nothing to pass. It answers for the occurrence that is **due and not yet settled**: `completed` and `cancelled` are done with, `in_progress` is not, because someone may file a file and deliberately leave the occurrence open. Of the occurrences that are owed it takes the **most recent one whose due date has passed**, so a period nobody ever closed does not swallow every later file.

This has to be worked out at run time rather than configured: the occurrence due now has a different id every period, so it can never be a setting.

If nothing is owed — the task has not started, or every occurrence is settled — the file is still filed and simply answers for nothing. The step reports `task_node_id`, so a graph can tell the two apart. If **two different tasks** expect the same evidence, the step refuses rather than guessing, and you name the occurrence yourself.

To name it yourself instead, leave the setting off and pass an id to **Task occurrence** — from a Read objects step on **Task occurrence**, filtering on `status` and ordering by `due_date`. Either way the step refuses an occurrence whose task does not expect this evidence, because neither the tick nor the link would ever read it.
{% endhint %}

{% hint style="info" %}
A step that runs on a schedule needs **File it as a new revision** on. With it off, every run overwrites the same revision, so a nightly collection keeps one file and no history. Either way the evidence moves back to **In review** if it was approved: a file nobody has looked at yet does not inherit the previous one's approval.
{% endhint %}

{% hint style="info" %}
**When the tool is down, the run stops — unless you say otherwise.** By default a source that answers `4xx`/`5xx`, or that never answers at all, fails this step. That is the safe reading: a collection that could not run must not look like one that ran and found nothing.

The two **Continue when…** settings turn each of those into an outcome the graph can route on. Nothing is filed either way; the difference is that the step returns `attached` as `false` instead of failing, and fills in `unreachable`, `host` and `reason`. Branch on `attached`, not on `status` — `status` is reported on both outcomes, so it tells you *what* happened, not *whether* it worked. A source that could not be reached reports `status` `0`, which no real answer can produce, so one branch handles both a bad answer and no answer.

Map `attached` into a variable with an output mapping and branch on it — then log the outage and email whoever owns the tool. Without that branch, opting in only hides the problem. The **Evidence collection** template in the library is wired this way.
{% endhint %}

Downloads respect the instance's attachment size limit and file extension allowlist. Redirects are not followed. A URL containing a secret must use `https`. A refused file name leaves no empty revision behind. Errors are reported by host only, never with the full URL, so a secret in a query string cannot leak into the log.

### Record a measurement

Files a number against a metric instance, as a dated sample.

| Setting | |
|---|---|
| Metric Instance *expr* | The metric instance id |
| Value *expr* | A number for a quantitative metric, a choice index for a qualitative one |
| Timestamp *expr* | Optional ISO timestamp. Empty means the moment of the run |
| Observation *expr* | Optional note stored with the sample |
| Evidence Revision *expr* | Optional. The revision the number came from, usually `{{nodes.<attach step>.revision_id}}` |

Output: `object_id`, `metric_instance_id`, `value`, `timestamp`. Permission: `add_custommetricsample`.

The metric definition decides the shape of the value, so you write a plain number either way: a quantitative metric stores it as the result, a qualitative one as the index of one of its options, counted from 1. An index past the last option is refused, as is a value that is not a number and a timestamp in the future.

The metric instance must be inside the workflow's domain or a sub-domain. The sample is a reading, not a verdict: nothing on the metric instance itself changes.

### Post scan results

Files a batch of results against a technical posture, for one asset. Each result is `pass`, `fail`, `not_applicable`, `error` or `not_checked`.

| Setting | |
|---|---|
| Technical posture *expr* | The posture assessment id |
| Asset *expr* | The asset the scan ran against |
| Results *expr* | A step output, or a JSON list of rows carrying `ref_id`, `result`, `actual`, `expected` and `message` |
| Tool *expr* | Optional name of the scanner, shown on the run |
| Run id *expr* | Optional. Reuse one to patch that run instead of starting a new one |

Output: `run_id`, `created`, `updated`, `unknown_count`, `unknown_ref_ids` (the first 20), `enrolled_asset`. Permission: `change_postureassessment`.

Each row's `ref_id` is matched against the requirements of the posture's framework, so a scanner that reports benchmark numbers needs no mapping table. `result` must be one of `pass`, `fail`, `not_applicable`, `error` or `not_checked`; anything else fails the step. Rows whose `ref_id` matches nothing are counted and reported rather than failing the run, which is what you want when a scanner covers more than the framework does.

{% hint style="info" %}
Set **Run id** to a value the step can compute the same way twice, and a retried or re-delivered batch patches the same run instead of stacking duplicates. Leave it empty and every run starts a new one, which is what a nightly scan wants.
{% endhint %}

The posture assessment must be inside the workflow's domain or a sub-domain and changeable by the run identity. An asset not yet in the posture's scope is added to it, provided the run identity may view it.

## Notification and integration steps

### Send email

| Setting | |
|---|---|
| Recipients (comma-separated) *expr* | Addresses. `Name <address>` is accepted |
| Subject *expr* | |
| Body *expr* | Plain text |

Output: `recipients`, `subject`. No permission required.

Delivery happens in the background worker. The step waits for the result. Each recipient gets an individual message. If any address fails, the step fails. The instance's email settings must be configured. The platform toggle that mutes digest notifications does not apply to workflow emails: a Send email step you authored always sends.

### HTTP request

| Setting | |
|---|---|
| Method | GET, POST, PUT, PATCH, DELETE |
| URL *expr* | `https` or `http`. Secrets allowed |
| Headers | Values are *expr*, secrets allowed |
| Body (JSON or raw text) *expr* | Sent as JSON when it parses as JSON, as raw text otherwise |
| Timeout (seconds) | 1 to 30, default 15 |
| Continue when the answer is an error | Off by default |
| Continue when the tool cannot be reached | Off by default |

Output: `status`, `body` (parsed JSON, or the first 5000 characters of text), `unreachable`, `host`, `reason`, `items`, `count`, `pages`, `truncated`. Every key is reported on both outcomes, so a condition cannot resolve to nothing on one branch. No permission required.

By default a `4xx` or `5xx` answer fails the step, and a tool that never answered at all fails it too. That is the safe reading: a collection that could not run must not look like one that ran and found nothing.

The two checkboxes turn each of those into an outcome the graph can route on instead. Map `status` into a variable with an output mapping, then branch on it. A tool that could not be reached is reported as `status` `0`, which no real answer can produce, so one branch handles both a bad answer and no answer. The output also carries `unreachable`, `host` and `reason` (the error class, such as `ConnectionError`).

Use them when the step is followed by a branch that does something about the failure — log it, email the owner, open a task. Without that branch, opting in only hides the problem.

#### Paging and OAuth

**Follow pages** gathers every page of a list API into `items`:

| Setting | |
|---|---|
| Path to the items | Where the list sits in each answer, such as `value` or `data` |
| Path to the next page | What leads to the next page, such as `@odata.nextLink` or `pagination.nextCursor` |
| Cursor parameter | Optional. When set, the value at the next-page path is a cursor sent as this query parameter. When empty, it is the full URL of the next page, which must stay on the same host |
| Offset parameter | Optional, for APIs that page with an offset such as `$skip` instead of a link. Each page adds the number of items received to it, and paging stops at the first empty page. Replaces the next-page path |
| Count only, keep no items | Count the items without keeping them, for APIs that offer no count of their own. Nothing from the answer is stored |
| Fields to keep | Optional, comma-separated. Each item keeps only these fields. Use it when the API returns large records and the step needs a few fields: it keeps big lists within what one step can store |
| Page limit | 1 to 50, default 10 |

Paging stops when there is no next page, at the page limit, or when the items reach what one step's output can hold: `WORKFLOW_NODE_OUTPUT_MAX_ITEMS` items (10 000 by default), or about 90% of `WORKFLOW_NODE_OUTPUT_BUDGET` characters (5 000 000 by default). Both are environment variables of the backend. `pages` says how many were read, `count` how many items were gathered, and `truncated` is true when a limit cut the list short. When paging, `body` is left empty: the items are in `items`, and keeping every raw page as well would double what the run stores.

**Sign in with OAuth client credentials** fetches a token before the request and sends it as a bearer token. It takes a **Token URL** (must be `https`), a **Client ID**, a **Client secret** and an optional **Scope**, all *expr*. The client secret must be a workflow secret, such as `{{secrets.client_secret}}`: publishing refuses one typed in as text. The token never appears in the output or the run log.

A run keeps every item it gathered, but the builder shows a preview: lists in step outputs and variables are cut to their first 50 entries, followed by a note saying how many more there are. Expressions and the steps themselves always read the full list.

Output mappings accept keys that contain dots, so `body.@odata.count` reads a Microsoft Graph count.

Redirects are not followed. Private addresses are refused. A secret, an `Authorization` header or `oauth` requires `https`. Errors are reported by host only, never with the full URL, so a secret in a query string cannot leak into the log.

## Identity steps

These steps administer users and domains. They are meant for onboarding and directory-sync flows.

### Provision domain

Creates a domain, or finds one with the same name under the same parent.

| Setting | |
|---|---|
| Folder name *expr* | |
| Parent folder *expr* | A folder id. Empty means the workflow's own domain. Must be inside the workflow's subtree |
| Create default access groups | Also create the built-in groups and role assignments of the domain |

Output: `folder_id`, `folder_name`, `created`. Permissions: `add_folder`, `change_folder`.

### Provision user

Creates a user by email, or updates the existing one.

| Setting | |
|---|---|
| Email *expr* | Matched case-insensitively |
| First name, Last name *expr* | Only overwrite when non-empty |
| Send onboarding email | Send the welcome email to a newly created user |
| Active | Optional. When set, activates or deactivates the account. When omitted, activation is left alone, so a routine sync never re-activates an offboarded user |

Output: `user_id`, `user_email`, `created`. Permissions: `add_user`, `change_user`, checked at the root domain because users are global.

### Manage group membership

Adds a user to a group or removes them.

| Setting | |
|---|---|
| User *expr* | An email, or a variable holding one |
| Domain | The domain whose group to use |
| Group | Reader, Approver, Analyst, Domain manager or Respondent |
| Operation | **Add** or **Remove** |

Output: `user_id`, `group_id`, `group_name`, `operation`. Permission: `change_usergroup`. The domain must be inside the workflow's subtree. Removing the last global administrator is refused.

## AI steps

These two steps send text to a model and put the answer in the step's output. Neither needs a permission: they read no objects and write none.

{% hint style="warning" %}
They use the provider configured in **Extra** → **Settings**, under **Chat / AI assistant** — the same one the chat assistant uses. There is no separate provider for workflows, so that section has to be filled in before an AI step can work, and it only appears once the prerequisites in [Hosted AI providers](../../integrations/ai-providers.md) are met. Until then an AI step fails with `no AI provider is reachable`.
{% endhint %}

The call runs in the background worker, because inference can take minutes and the engine must not hold its locks meanwhile. The step waits for the answer.

### Ask AI for values

Asks the model for a small set of named values, and fails the step unless the answer matches the shape you asked for. This is the one to use before a Condition: a value with a fixed list of choices is something a branch can route on.

| Setting | |
|---|---|
| Instruction *expr* | What the model must do, for example `Classify the severity of this finding.` |
| Input to work on *expr* | The text to work from, usually an expression |
| Values to return | One row per value: a **Name**, a type (**Choice**, **Text**, **Number**, **Yes/no**) and, for a choice, its allowed values |
| Attempts before failing | 1 to 5, default 2. A reply that does not match the shape is asked for again before the step fails |

Output: one key per value you defined, so `{{nodes.<ref>.severity}}`. `_input_truncated` is added and set to true when the input was cut.

### Ask AI for text

Asks the model for prose — a summary, a description, an explanatory note.

| Setting | |
|---|---|
| Instruction *expr* | What the model must write |
| Input to work on *expr* | The text to work from |
| Maximum words | 1 to 2000, default 200 |

Output: `text`, plus `_input_truncated` when the input was cut.

For anything longer than a note — a drafted policy, say — map `text` to a variable in the step's outputs and write `{{that_variable}}` into the field. A `{{nodes.…}}` reference is shortened to 1 000 characters (it says so, in the value itself); a variable carries the whole text.

### What the model is and is not allowed to do

{% hint style="warning" %}
An AI answer cannot be written into a field that accepts a fixed set of values — a status, a severity, a result — whether the step creates the object or updates one. Publishing refuses it, and routing the answer through a variable first does not get around the check: the builder follows where the value came from. Branch on the answer with a Condition and write the value you want on each branch.

The reason is the audit trail. A field with a fixed set of values is read as a decision someone made; letting a model fill it in would record a guess as a fact.
{% endhint %}

The input is capped at 20 000 characters and cut rather than refused, so a step never fails just because a document was long — check `_input_truncated` in the output if that matters to you. A generated text is stored up to 20 000 characters, so the word limit is what actually bounds it.

The step tells the model that its input is data and not instructions, so text inside a fetched document cannot redirect it. Treat that as a reduction in risk and not as a guarantee: do not let a model's answer reach anything you would not let the document's author write.

A run may complete 50 AI steps by default. A loop over 500 rows with an AI step in its body stops at the budget rather than running up a bill, and the step says so. Deployments can change the limit with `WORKFLOW_AI_MAX_CALLS_PER_RUN`.

If no provider answers, the step fails with `no AI provider is reachable` and the node's retry policy applies, so a provider restart does not necessarily lose the run. Provider errors are reported without the endpoint or any key.

## Failures

A step fails on a network error, a missing or out-of-scope object, a missing permission, or a value the object does not accept. The run stops with the step in red and the reason in its log. Fix the cause and run again. See [Runs](runs.md#when-a-run-fails).
