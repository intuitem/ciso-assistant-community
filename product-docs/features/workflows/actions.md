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
| `requirement_assessment` | status, result, extended_result, score, is_scored, documentation_score, eta, due_date, compliance_assessment, plus `requirement` (id, ref_id, name). Only assessable requirements |
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

## Write steps

### Create object

Creates an object in the workflow's domain.

| Setting | |
|---|---|
| Object to create | One of the creatable objects below |
| Fields | One row per field. Values are *expr* |
| Update when it already exists | When on, matches an existing object by name in the workflow's domain and updates it instead of creating a duplicate |

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
| `entity_assessment` | name, description | entity, perimeter, framework, implementation_groups. With a framework, the questionnaire and its enclave are built too. Upsert not available |
| `entity_score` | **score**, **as_of**, scale_max, grade, url, observation | entity, provider |
| `timeline_entry` | **entry**, entry_type, timestamp, observation | incident |
| `task_template` | name, description, ref_id, task_date | |
| `right_request` | name, **requested_on**, description, ref_id, due_date, request_type, observation | |

**Bold** marks a field the object cannot be stored without: publishing refuses a step that leaves one empty, rather than letting the run write a blank. Every object that has a name needs one too, unless **Update when it already exists** is on.

Choice fields (status, severity, type, legal_basis) must receive one of the object's accepted values. Anything else fails the step permanently. `timeline_entry` accepts only `detection`, `mitigation` and `observation` as its type: `severity_changed` and `status_changed` record a change someone made to the incident, so a run may not write them.

Four of these are where a run files what an external system reported, and each is worth knowing about:

* **External rating** (`entity_score`) is one reading per provider per day, dated. Turn on **Update when it already exists** and a re-run on the same day corrects that day's reading instead of failing on the duplicate.
* **Timeline Entry** (`timeline_entry`) adds an observation to an incident without touching its status or severity.
* **Task** (`task_template`) attaches work. A run creates a dated task; recurrence stays something you set up by hand.
* **Right Request** (`right_request`) opens a request in **New**. Closing it stays with whoever handles it.

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

Planning states are `planned`, `in_progress`, `in_review`, `done`, `deprecated`. Names are never writable. Results, scores, levels and decisions are never writable.

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
| Task occurrence *expr* | Optional. The occurrence this file answers for |
| File it as a new revision | Off by default. Off replaces the file on the evidence's latest revision. On files a new revision and leaves the previous one untouched |

Output: `object_id`, `revision_id`, `version`, `filename`, `bytes`, `task_node_id`. Permission: `change_evidence`, plus `add_evidencerevision` when **File it as a new revision** is on.

{% hint style="info" %}
**Set Task occurrence to close the loop with a recurring task.** A task that expects an evidence shows it as provided once a revision filed *for that occurrence* exists. A collected file with no occurrence set satisfies nothing, however good the file is — so the task keeps asking.

Find this week's occurrence with a Read objects step on **Task occurrence**, filtering on `status` and ordering by `due_date`, then pass `{{nodes.<that step>.object.id}}` here. The step refuses an occurrence whose task does not expect this evidence, because neither the tick nor the link would ever read it.
{% endhint %}

{% hint style="info" %}
A step that runs on a schedule needs **File it as a new revision** on. With it off, every run overwrites the same revision, so a nightly collection keeps one file and no history. With it on, each run files its own revision and the evidence moves back to **In review**: a file nobody has looked at yet does not inherit the previous one's approval.
{% endhint %}

Downloads respect the instance's attachment size limit and file extension allowlist. Redirects are not followed. A URL containing a secret must use `https`. A refused file name leaves no empty revision behind.

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

Files a batch of pass/fail verdicts against a technical posture, for one asset.

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

Output: `status`, `body` (parsed JSON, or the first 5000 characters of text). No permission required. Any `4xx` or `5xx` answer fails the step.

Redirects are not followed. Private addresses are refused. A secret or an `Authorization` header requires `https`. Errors are reported by host only, never with the full URL, so a secret in a query string cannot leak into the log.

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

### What the model is and is not allowed to do

{% hint style="warning" %}
An AI answer cannot be written into a field that accepts a fixed set of values — a status, a severity, a result. Publishing refuses it, and routing the answer through a variable first does not get around the check: the builder follows where the value came from. Branch on the answer with a Condition and write the value you want on each branch.

The reason is the audit trail. A field with a fixed set of values is read as a decision someone made; letting a model fill it in would record a guess as a fact.
{% endhint %}

The input is capped at 20 000 characters and cut rather than refused, so a step never fails just because a document was long — check `_input_truncated` in the output if that matters to you. A generated text is stored up to 5 000 characters.

The step tells the model that its input is data and not instructions, so text inside a fetched document cannot redirect it. Treat that as a reduction in risk and not as a guarantee: do not let a model's answer reach anything you would not let the document's author write.

A run may complete 50 AI steps by default. A loop over 500 rows with an AI step in its body stops at the budget rather than running up a bill, and the step says so. Deployments can change the limit with `WORKFLOW_AI_MAX_CALLS_PER_RUN`.

If no provider answers, the step fails with `no AI provider is reachable` and the node's retry policy applies, so a provider restart does not necessarily lose the run. Provider errors are reported without the endpoint or any key.

## Failures

A step fails on a network error, a missing or out-of-scope object, a missing permission, or a value the object does not accept. The run stops with the step in red and the reason in its log. Fix the cause and run again. See [Runs](runs.md#when-a-run-fails).
