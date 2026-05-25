---
description: Recurring and one-off operational work tracked against owners, schedules, and evidence
---

# Tasks

Tasks are how CISO Assistant tracks the operational work that keeps controls effective: the weekly access review, the monthly backup test, the quarterly policy refresh, the one-off offboarding checklist. They are deliberately separate from applied controls — a control says _what is done_; a task says _that someone has actually done it on a given date_.

## Definition vs occurrence

Tasks come in two layers, mirroring the **template → instance** pattern used elsewhere in the platform:

- A **task definition** is the reusable spec — the title, description, owner, expected evidence, and the recurrence rule (`every Monday`, `the 1st of each month`, `every 90 days`). It says _what should happen_ and _how often_. Internally a `TaskTemplate`.
- A **task occurrence** is a single scheduled run produced from a definition — the actual row with a due date, a status (pending → in progress → completed / cancelled), and the evidence collected when the work was done. Internally a `TaskNode`.

A one-off task is just a definition that produces a single occurrence.

## Lifecycle

1. **Define.** Create a task definition with the owner, the cadence, and what's expected when the task runs.
2. **Schedule.** Occurrences are materialised from the recurrence rule. The platform creates them as their due dates come into view, so the list of upcoming work is always visible.
3. **Work the occurrence.** When a due date arrives, the assignee opens the occurrence, records what they did, attaches evidence, and marks it completed.
4. **Iterate.** Edit the definition to adjust the cadence, owner, or expected evidence — existing occurrences keep their state; future occurrences pick up the change.

## Why tasks (and not just calendar reminders)

The point of tracking tasks inside the platform — rather than in a calendar or ticketing system — is so that the **evidence** of execution lives next to the rest of your compliance record. An auditor asking "show me proof of monthly backup testing" can be answered by pointing at the task and walking through the completed occurrences with their attached evidence.

## Related

- [Applied controls](applied-controls.md)
- [Evidence](evidence.md)
- [Vocabulary → Task definition / Task occurrence](../introduction/vocabulary.md)
