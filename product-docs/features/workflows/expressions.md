---
description: "The {{ }} syntax for referencing variables, payloads, step outputs, loop items and secrets"
---

# Expressions

Every text field in a step can contain expressions. An expression is a path wrapped in double curly braces. When the step runs, the engine replaces each expression with the value it points to.

```
Overdue controls: {{nodes.fetch_late.count}} on {{today}}
```

That is the whole language. There are no functions, no operators and no filters. If you need to compute something, use a step (Set variables, Date offset, a Condition) rather than an expression.

## What you can reference

| Expression | Resolves to | Available |
|---|---|---|
| `{{my_variable}}` | A workflow variable, by its key | Everywhere |
| `{{today}}` | The run's date, `YYYY-MM-DD` | Everywhere |
| `{{now}}` | The run's start time, ISO 8601 with offset | Everywhere |
| `{{payload}}` | The whole trigger payload as JSON | Webhook and event runs |
| `{{payload.some.path}}` | One value inside the trigger payload | Webhook and event runs |
| `{{nodes.<ref>.<path>}}` | The output of an earlier step | After that step ran |
| `{{item}}` and `{{item.<path>}}` | The current element of the loop | Inside a loop body |
| `{{index}}` | The position of the current element, starting at 0 | Inside a loop body |
| `{{secrets.<NAME>}}` | The value of a workflow secret | HTTP request and Attach a file to an evidence only |

`today`, `now` and `payload` are written by the engine at the start of every run. You cannot declare a variable with one of those names, and a Set variables step cannot overwrite them.

Whitespace inside the braces is fine: `{{ today }}` and `{{today}}` are the same.

## Paths

A path is a list of segments separated by dots. Each segment either names a key in an object or, when it is a number, picks an element of a list.

```
{{payload.vulnerabilities.0.id}}
{{nodes.fetch_late.results.2.name}}
```

If any segment of the path does not exist, the whole expression renders as an empty string. Nothing fails. This is deliberate: a missing optional field in a webhook payload should not break the run. It also means a typo in a path is silent, so check the run log the first time you use a new path.

## How values render

| Value | Renders as |
|---|---|
| Text, number, boolean | As-is, converted to text (`true`, `42`) |
| Object or list | JSON |
| Missing | Empty string |

Rendering objects and lists as JSON lets you pass a whole structure along. `{{nodes.fetch.body}}` in the body of an HTTP request sends the previous response through unchanged, and the request step detects that the body is JSON and sends it with the right content type.

Where a field expects a list (the collection of a loop, the ids of a link), the engine does not render the expression to text. It looks the path up directly and uses the actual list.

## Time

`{{today}}` and `{{now}}` are frozen when the run starts and stay the same for the whole run, including retries. A retried step compares against the same date as the first attempt.

For a scheduled trigger, both are computed in the schedule's timezone. For every other trigger, the deployment's default timezone applies.

## Step references

Each step has a **ref**, a short identifier derived from its label: `Past their ETA` becomes `past_their_eta`. The builder derives the ref for you and keeps it in sync when you rename the step, rewriting every `{{nodes.<old_ref>...}}` expression in the workflow at the same time. You never have to edit refs by hand.

What each step exposes under `{{nodes.<ref>}}` is listed in the [action reference](actions.md). Two common ones:

| Step | Useful outputs |
|---|---|
| Read objects, list mode | `count`, `results` (a list of rows), `next_offset` |
| Create object | `created_object_id`, `created_object_name`, `created` |

Outputs are kept for the whole run and are visible in the run log and the Available data browser, so you can inspect exactly what a step produced before referencing it downstream.

## Payloads

A webhook run's payload is the JSON body the caller posted. An internal event run's payload is built by CISO Assistant and always has the same shape:

| Key | Meaning |
|---|---|
| `event_key` | What happened, for example `appliedcontrol.updated` |
| `model` | The kind of object, for example `appliedcontrol` |
| `operation` | `created`, `updated` or `deleted` |
| `object_id` | The object's id |
| `object_repr` | The object's display name |
| `changes` | For each changed field, a pair `[old, new]` |
| `new_values` | For each changed field, the new value |
| `folder_id` | The object's domain |
| `actor_email` | Who made the change, when known |
| `timestamp` | When |

`{{payload.new_values.status}}` is the idiom for "the status it just changed to". `{{payload.object_repr}}` is the idiom for naming the object in an email.

## Limits worth knowing

- A step's stored output is capped so runs stay inspectable: text longer than 1000 characters is cut, lists and objects keep their first 100 entries, and a run's outputs share a budget of about 32 KB. Paths into a capped structure keep working. If you need to iterate over more than 100 rows, let a loop read its own pages instead of referencing a Read objects result.
- Secrets only resolve inside an HTTP request or an Attach a file to an evidence step. Anywhere else, `{{secrets.X}}` renders as empty, and the run log never contains secret values.

## Examples

Email subject with a count and a date:

```
Overdue controls: {{nodes.fetch_late.count}} on {{today}}
```

Filter value comparing a date field to the run's date:

```
{{today}}
```

Loop over a list posted by a scanner, then reference the current element:

```
Collection:  {{payload.vulnerabilities}}
Name:        {{item.id}}
Description: {{item.summary}}
```

Chain a created object into the next step:

```
Evidence:    {{nodes.make_evidence.created_object_id}}
```

Authenticated HTTP request:

```
URL:     https://api.example.com/tickets
Header:  Authorization = Bearer {{secrets.ITSM_TOKEN}}
Body:    {"title": "{{payload.object_repr}} went live on {{today}}"}
```
