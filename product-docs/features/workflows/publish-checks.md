---
description: "Every message the publish step can raise, and how to fix it"
---

# Publish checks

A draft can be saved in any state. Publishing requires a sound graph, so the builder runs the checks below and pins each message to the step or wire it concerns. Fix them and publish again.

## Structure

| Message | Fix |
|---|---|
| The graph needs at least one trigger node | Add a trigger from the palette |
| Trigger nodes cannot have incoming edges | Remove the connection into the trigger |
| This node cannot be reached from any trigger node | Connect it, or delete it |
| This node is in a loop with no exit, so no path from it can finish | Add a way out of the cycle. Any unconnected output ends a branch, so a plain leaf is fine |
| Nothing can follow a stop node: it ends the run | Remove the wire leaving the Stop run step |
| `{{nodes.x}}` references a node that does not exist | Fix the expression. Usually an imported file |
| `now`, `today` or `payload` is set by the engine on every run | Rename the variable |

## Conditions

| Message | Fix |
|---|---|
| This branch node has no default (otherwise) branch | The otherwise branch is created with every Condition. Seen on imported files: add it back |
| A branch is not connected to a next step | Connect every branch, or remove it |

## Loops

| Message | Fix |
|---|---|
| The collection is not a single `{{path}}` expression | Point the loop at exactly one list, for example `{{nodes.fetch.results}}` |
| A loop reads its own pages or iterates a collection, not both | Clear one of the two |
| The loop's read configuration is invalid | Same rules as a Read objects step |
| Edges leaving a loop must use its `each` or `done` port | Reconnect from the right port |
| Nothing is wired to the loop's `each` or `done` port, or the body never comes back to the loop | Connect both ports, and connect the last step of the body back to the loop's input |
| A path from the loop's `each` port leaves the body without returning to the loop | Everything reachable from `each` must return to the loop |
| A loop body step branches into parallel paths | Parallel fan-out inside a body is not supported. Use a Condition to choose a single path |

## Triggers

| Message | Fix |
|---|---|
| Trigger nodes need a valid trigger type | Pick Manual, Webhook, Schedule or Internal event |
| Invalid cron expression, or it fires more often than once a minute | Five-field cron, minute granularity |
| Unknown timezone | Use an IANA name such as `Europe/Paris` |
| This trigger needs a valid event | Pick an event from the list |
| The event filters are invalid | Rebuild the filter |
| A folder filter points outside this workflow's scope | Filter on a domain inside the workflow's subtree, or move the workflow |

## Steps

| Message | Fix |
|---|---|
| Secret 'X' does not exist | Create it in the secrets panel, spelled the same |
| A Read objects filter uses an unknown field or an operator the field type does not support | See the operator table in the [action reference](actions.md) |
| Update object has no object id | Set it, usually `{{item.id}}` |
| Update object has no fields and no relations | Add at least one |
| Set variables writes a reserved key | Remove `now`, `today` or `payload` |
| Attach evidence has no target | Set the evidence id |
| Attach evidence has no filename | Set it |
| Source is neither Text nor URL | Pick one |
| Source is URL but no URL is set | Set it |
| Unknown creatable model | Pick a model from the list |
| This model is built, not matched | Untick **Update when it already exists** for audits and entity assessments created from a framework |
| A choice field has a value the object does not accept | Use one of the listed values |
| The output variable is not a valid, declared, non-reserved variable | Pick a declared variable |

## Not available in this version

Task, sub-workflow and event steps exist for graphs made with earlier versions but cannot be added or imported. If you import a file that uses them, the import is refused with a message naming the step.
