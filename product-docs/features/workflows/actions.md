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
| `data_subject` | name, description, category | processing |
| `data_recipient` | name, description, category | processing |
| `data_contractor` | name, description and contractor fields | processing, entity |
| `data_transfer` | name, description and transfer fields | processing, entity |
| `entity_assessment` | name, description | entity, perimeter, framework, implementation_groups. With a framework, the questionnaire and its enclave are built too. Upsert not available |

Choice fields (status, severity, type, legal_basis) must receive one of the object's accepted values. Anything else fails the step permanently.

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

Adds a file to an existing evidence, as its latest revision.

| Setting | |
|---|---|
| Evidence *expr* | The evidence id |
| File name *expr* | Name of the attached file |
| Source | **Text** writes the rendered text as the file. **URL** downloads the file |
| Content *expr* | With source Text |
| URL *expr* | With source URL. Secrets allowed |

Output: `object_id`, `revision_id`, `filename`, `bytes`. Permission: `change_evidence`.

Downloads respect the instance's attachment size limit and file extension allowlist. Redirects are not followed. A URL containing a secret must use `https`.

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

## Failures

A step fails on a network error, a missing or out-of-scope object, a missing permission, or a value the object does not accept. The run stops with the step in red and the reason in its log. Fix the cause and run again. See [Runs](runs.md#when-a-run-fails).
