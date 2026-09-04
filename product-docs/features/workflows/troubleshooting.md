---
description: "Symptoms and fixes: triggers that do not fire, failed runs, empty expressions, refused publishes"
---

# Troubleshooting

Symptoms first, causes second. Most answers are one panel away: the Runs panel shows what a run did, the Triggers panel shows why a trigger did or did not fire.

## The Workflows entry is not in the sidebar

- The **Workflows** feature flag is off. Turn it on under **Extra > Settings > Feature flags**.
- Your user lacks `view_workflow` in any domain.

## A trigger does not fire

Open the **Triggers** panel and read the row.

| What you see | Cause | Fix |
|---|---|---|
| Switch on **Disabled** | Schedules and event triggers arrive disabled at publish | Enable it |
| No row for the trigger | The workflow was never published, or the trigger was added after the last publish | Publish |
| Header shows **Paused** | The workflow's master switch is off | Turn **Enabled** on in the header |
| **No run-as user** badge | The publisher's account was deleted | Republish |
| Result **Skipped (previous run still active)** | Schedule overlap protection. The previous run is still running or stuck | Check the Runs panel. Wait for it to finish, or space the schedule out |
| Result **Skipped (too many chained triggers)** | Event chain deeper than five workflows | Break the cycle between workflows |
| Result **Coalesced** | Several audit entries from one user action | Expected. One run started |
| Nothing at all, schedule never advances | The background worker is not running | Ask your administrator to start it. Schedules, events, emails and time limits all depend on it |
| Event triggers never fire | The changed object lives outside the workflow's domain subtree | Move the workflow up, or filter differently |

## A webhook call answers 404

The URL is wrong, the trigger is disabled, the workflow is paused, the version was never published, or inbound webhooks are disabled on the instance. All of these answer the same `404` on purpose. Copy the URL again from the Triggers panel: renaming the trigger step changed it, and rotating the secret changed it.

A `409` means the published version no longer contains that trigger step. Publish again.

## A run failed

Expand the run and read the red `error` line. The message names the step and the reason.

| Message contains | Meaning | Fix |
|---|---|---|
| `Authorization denied: '...' lacks view_...` | The run identity lost a role, or never had it in this domain | Grant the role, or have someone with it republish. Then run again |
| `no run identity (republish the workflow)` | The publisher's account is gone | Republish |
| `email is not configured` | SMTP is not set up on the instance | Configure email settings |
| `invalid recipient` | An address in Recipients is malformed, or an expression rendered empty | Check the expression against the reference run |
| `HTTP 4xx from '...'` | The remote refused | Check the URL, the token, the body |
| `credentials require an https URL` | A secret or Authorization header over `http` | Use `https` |
| `BlockedRequestError for host` | The URL points at a private or internal address | Use a public host |
| `is not an accepted <model>.<field>` | A choice field got a value the object does not accept | Use one of the listed values |
| `a workflow may not set ...` | The field records a decision, not a fact | Leave it to a person |
| `no <model> '<id>' in this workflow's scope` | Update target is outside the domain subtree, or not changeable by the run identity | Check the id expression and the scope |
| `did not resolve to a list` | The loop collection points at something that is not a list | Pick the list from the collection select |
| `deferred action was never delivered` | The worker never picked up an email for 15 minutes | Ask your administrator to check the worker. Run again |
| `Run exceeded its N s time limit` | The time limit hit | Raise it, or find the slow step |

## An expression renders empty

A missing path renders as an empty string rather than failing. Pin a run as reference data, open the step, and use **Available data**: it shows the real structure, and clicking a value inserts the correct path. Common causes:

- `{{node.x}}` instead of `{{nodes.x}}`.
- A ref typed by hand that does not match the step's actual ref. Check the monospace ref badge in the inspector.
- A path into `payload` that the sender does not actually send.
- `{{secrets.X}}` outside an HTTP request or Attach a file step. Secrets do not resolve anywhere else.
- `{{item}}` outside a loop body.

## A Condition always takes the otherwise branch

- The variable was never set. Conditions compare variables, not step outputs. Add **Save results to variables** on the producing step, or a Set variables step.
- The variable's type does not match the comparison. A `string` variable holding `12` compared with `gt 10` compares as text. Declare it as `number`.
- The value is an expression that renders empty. Check the run log.

## Publish is refused

The panel bottom-right lists every problem, and each affected step has a red **!** badge. Every message is explained in [Publish checks](publish-checks.md). The ones people hit most:

- **This branch node has no default (otherwise) branch.** Every Condition needs one. It is created with the step, so this usually means an imported file.
- **A branch is not connected to a next step.** Wire it or delete it.
- **Nothing is wired to the loop's 'each' port** or **'done' port**, or **the loop body never returns to the loop**. A loop needs both ports wired and the last body step wired back to the loop's input.
- **Secret 'X' does not exist.** Create it in the Variables panel, spelled exactly the same.
- **The graph needs at least one trigger node.**

## The builder shows "This draft no longer exists"

The draft was discarded from another tab or by someone else. The builder reloaded the latest version. Your unsaved edit was not applied.

## A loop stopped early

The default caps are 500 items and 20 pages. The loop's `errors` output records `stopped after 500 items`. Narrow the filters, or ask your administrator to raise the caps.

## A scheduled digest ran twice, or not at the hour I expected

Check the **Timezone** on the schedule. `{{today}}` and the cron expression both use it. A blank timezone means UTC.
