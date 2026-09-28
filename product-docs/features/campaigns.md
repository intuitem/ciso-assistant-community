---
description: Run the same assessment across many targets at once
---

# Campaigns

A **campaign** runs one assessment exercise across many targets at the same time — the same framework, the same deadline, the same implementation groups — and gives you a single page to watch it from.

Without one, an annual ISO 27001 round across twelve perimeters is twelve audits you create by hand, twelve sets of assignments you wire up, and twelve pages you open in turn to find out where you stand. A campaign does the wiring and rolls the answer up.

Campaigns are a **PRO** feature, gated by the **campaigns** [feature flag](../configuration/settings/feature-flags.md).

## Two kinds

A campaign is either internal or third-party, chosen when you create it, and the choice decides what it targets:

| Kind | Targets | What it creates per target |
|---|---|---|
| **Internal campaign** | your own **perimeters** | an audit in the perimeter's domain, assigned to the perimeter's default assignees |
| **Third-party campaign** | your **third parties** | an entity assessment, with a questionnaire in the third party's workspace and access granted to its representatives |

The two are listed separately in the sidebar — under **Compliance** for internal campaigns, under **Third-party** for third-party ones — but they're the same object and the same page.

## Setting one up

Create the campaign with its **domain**, the **target frameworks**, and the targets themselves (**perimeters** or **third parties**). You can also set a **start date**, a **due date**, and the **selected implementation groups** to narrow the frameworks to the part you actually intend to assess.

Saving builds one assessment per target × framework, wired but **not yet under way**: assignments are created in draft, so nobody is notified while you're still arranging things. Internal targets take their assignees from the perimeter's default assignee; third-party targets take theirs from the entity's representatives.

## Starting it

**Start campaign** is what sends the work out. It moves every draft assignment to *in progress*, notifies whoever holds it, and moves audits that were still *planned* to *in progress* so they stop reading as empty in cross-audit reports.

It's re-runnable, and only picks up what is still in draft — so adding a target to a campaign already under way is a matter of adding it and pressing start again. That also covers the case where a target had nobody to answer for it: add the missing representative or default assignee, then start again to wire it.

Starting reports back how many assignments were notified, and calls out any target that still has nobody assigned rather than skipping it silently. A campaign with no assessments at all refuses to start.

## The dashboard

The campaign page answers "where is this round?" without opening its targets:

- **Completion** — the mean progress across targets, where every target counts equally whatever its size. Alongside it, how many targets are not started, in progress, and completed, and the days remaining against the due date.
- **Completion trend** — daily progress across the campaign, this one weighted by requirement count, so it reflects volume of work rather than number of targets. For a third-party campaign the same slot shows **review progress** instead.
- **Responses** — assignments by status, in respondent-facing order: draft, in progress, changes requested, submitted, closed.
- **Flagged** — how many individual requirements a reviewer has [asked for changes on](assignments.md#reviewing-item-by-item), across the whole campaign.
- **Furthest behind** — the three targets with the lowest progress.
- **Stale** — targets with no activity for at least 14 days, worth chasing regardless of how far along they are. A target can be at 60% and stalled, which the progress number alone won't tell you.

## Related

- [Audits](../concepts/audits.md)
- [Assignments / respondent mode](assignments.md)
- [Third-party risk](../concepts/third-party-risk.md)
