---
description: In-context discussion threads on audits, risk scenarios, applied controls, and findings — author-attributed, with a processed toggle and edit history
---

# Comments

Comments are short, dated, author-attributed notes attached directly to an object. They're the place for the back-and-forth that happens while work is in progress — clarifications, follow-up questions, agreed next steps — without touching the object's formal fields, status, or score.

The panel is **collapsed by default** and shows the comment count next to the **Comments** heading, so it stays out of the way until you open it.

## Where comments appear

A comment is always attached to exactly one object. Comments are supported on:

| Object | Where you find the panel |
|---|---|
| **Requirement assessment** | On the requirement detail and the respondent-mode assessment view |
| **Risk scenario** | On the risk-scenario detail page and its edit form |
| **Applied control** | On the applied-control detail page |
| **Finding** | On the finding detail page |

## Anatomy of a comment

Each comment carries:

- a **body** (free text),
- an **author** (the user who posted it),
- a **creation timestamp**, shown as relative time ("just now", "5 minutes ago") and as a full date once it ages,
- an **active / processed** state.

Comments are ordered oldest-first, so a thread reads top to bottom like a conversation. Write in the composer at the bottom and **Post** — or press **Ctrl+Enter**.

## Processed vs. active

Every comment is **active** when posted. Once a thread is resolved, its author can **Mark as processed** (and **Mark as active** to reopen it). Processed comments stay in the history but can be filtered out of the default view: when a thread has processed comments, a **Hide processed** / **Show processed (n)** toggle appears in the panel header.

This keeps long threads readable — settled points collapse away without being deleted.

## Edited comments

Comments can be edited by their author. The first time a comment's body actually changes, it's flagged as **edited**, and that marker stays on the comment from then on — so the thread always reflects when wording was changed after the fact. The original posting is what other participants saw; the **edited** tag tells them it was revised.

## Who can do what

| Action | Who |
|---|---|
| Post a comment | Anyone with comment access in the object's [domain](../concepts/domains.md) |
| Edit a comment | The author only |
| Delete a comment | The author, or an administrator |

Respondents and auditees can post, edit, and delete their **own** comments on the objects they're assigned, so the discussion is two-way.

## Author privacy in respondent mode

Comments are author-attributed, but a participant only sees an author's name and email if they're allowed to see that user. Third-party respondents and auditees have no access to the user directory, so for any comment they didn't write themselves the author is shown as the **Client name** configured in [branding settings](../configuration/settings/branding.md), falling back to `***` when none is set. Their own comments still appear under their own name — internal reviewers' identities never leak into the third-party view.

## Enabling comments

- The **comments** [feature flag](../configuration/settings/feature-flags.md) is the master switch (default **on**). When off, the panel disappears from every object.
- On audits, **Comments** is also a [field-visibility](../guides/customize-audit.md) option — per audit you can make the thread visible to respondents, auditor-only, or hidden. This lets you keep comments enabled platform-wide while still hiding the discussion from third-party respondents on a sensitive audit.

## Related

- [Audits](../concepts/audits.md) — comments in the audit workflow
- [Assignments / respondent mode](assignments.md) — the third-party review flow comments support
- [Branding](../configuration/settings/branding.md) — sets the **Client name** used as the masked-author label
- [Feature flags](../configuration/settings/feature-flags.md) — the **comments** switch
