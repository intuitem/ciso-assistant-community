---
description: Build, publish and arm a workflow that emails a reviewer whenever an audit moves to review
---

# Building your first workflow

This walkthrough builds the smallest workflow worth having: when an audit moves to **In review**, someone gets an email. Four steps on the canvas, and every concept you need for bigger ones — a trigger, an action, publishing, and arming.

Read [Workflows](../concepts/workflows.md) first if you haven't; the [builder reference](../features/workflows.md) has the details this guide skips.

{% stepper %}
{% step %}
### Create the workflow

Open the **Workflows** list at `/workflows` and create one. Give it a name — _"Audit in review → notify reviewer"_ — and pick the **domain** it belongs to. That domain is the boundary: the workflow will only ever see and touch objects in it and the domains beneath it.
{% endstep %}

{% step %}
### Declare the recipient as a variable

In the **Variables** panel, add a variable named `notify_emails`, and put the reviewer's address in its default value.

Using a variable rather than typing an address into the email step is the habit worth forming: it is the one thing someone must change when they reuse the workflow, and it keeps the graph portable.
{% endstep %}

{% step %}
### Draw the graph

From **Add a step**, place a **Trigger**, an **Action** and a **Stop run** on the canvas, then connect them in that order.

The builder saves as you go, and nothing here can run yet — it's a draft.
{% endstep %}

{% step %}
### Configure the trigger

Select the trigger step and set its **Trigger type** to **On event**. For **Event**, choose the audit's _updated_ event.

Then narrow it: add a condition on the status field so the run starts only when the status becomes _In review_, rather than on every save of every audit. Without the filter this fires far more often than you want — every observation typed into an audit is an update.
{% endstep %}

{% step %}
### Configure the email

Select the action step, set its type to **Send email**, and fill in:

- **Recipients**: `{{notify_emails}}`
- **Subject**: something like `Audit ready for review: {{payload.object_repr}}`
- **Body**: whatever your reviewer needs. `{{payload.object_repr}}` is the audit's name, `{{now}}` is the moment the run started.

The `{{...}}` syntax inserts values; the hint under the field spells it out. There are no functions or operators — if you need "in 30 days", that's the **Date offset** action.
{% endstep %}

{% step %}
### Publish

Press **Publish**. The builder validates the whole graph and refuses if something is unwired or misconfigured — that check is the reason a half-finished workflow can never be live.

The confirmation names what you're agreeing to: _"once published, this workflow runs as you, using these permissions"_. The run will act with **your** rights, so it can only read and write what you could.
{% endstep %}

{% step %}
### Arm the trigger

Open the **Triggers** panel. The event trigger is there, **Disabled** — publishing never arms a trigger by itself. Switch it to **Enabled**.

This is where you'll come back to see **Last fired**, and why a firing was skipped.
{% endstep %}

{% step %}
### Watch it run

Move an audit in that domain to **In review**. Open the **Runs** panel: the run is listed with its trigger, its variables and what each step returned.

**Show on canvas** replays the path the run took, which is the fastest way to see where something stopped.
{% endstep %}
{% endstepper %}

## Testing without waiting for the real thing

Add a second trigger step of type **Manual** wired into the same action, and you can press **Execute** whenever you like. **Run with variables** lets you override values for that one run — handy for pointing the email at yourself while you tune the wording.

A manual run is also the safest way to try a workflow that reads or writes: it does exactly what the armed version would do, but only when you ask.

## When something goes wrong

- **The run failed** — open it in **Runs**. The failing step carries the reason: a missing permission for the run-as user, a value a field refuses, an email that could not be delivered.
- **Nothing happened** — check the **Triggers** panel. An event trigger that is still **Disabled**, or a workflow showing **Paused**, explains most silences. The panel also records skips: a previous run still going, or a repeat of a change already handled.
- **The expression printed nothing** — pick a past run as **Use as reference data**. The builder then previews what each `{{expression}}` resolves to while you edit, instead of guessing.

## Where to go next

The same four moves — trigger, action, publish, arm — build the rest:

- Swap the trigger for a **Schedule** and the action for **Read objects** to get a weekly digest.
- Add a **Condition** after the trigger to route approved and rejected differently.
- Add **Create object** and **Update object** to open a remediation control and link it to the requirement that needs it.

Ready-made examples install from the **Libraries** page under the **Workflows** tile — install one, open it, and read how it's wired.
