---
description: Reference for every setting on an audit — visibility, scoring, lifecycle, attachments
---

# Customize your audit

Once the basics are in place (framework × perimeter), an audit exposes a set of settings that let you shape _what's visible to whom_, _how scores are computed_, and _how the assessment behaves over its lifecycle_. All of them sit under the **More** dropdown on the audit edit form.

This page is the reference for that dropdown. The pre-requisite "Basic audit" walkthrough covers creation; come here when you need to tune a live audit.

## Field visibility

Audits are routinely shared across two roles: **auditors** (the team running the audit) and **respondents** (the people answering — typically domain owners or third-party contacts). Different organisations want different things visible to each.

The **Field visibility** panel inside an audit's edit form lets you switch every assessable field to one of three states:

| Pill | Auditor | Respondent | Use when |
|---|---|---|---|
| **Auditor + Respondent** _(green)_ | edit | edit | Both roles need full access. |
| **Auditor only** _(amber)_ | edit | hidden | The field is sensitive or internal-only. |
| **Hidden** _(rose)_ | hidden | hidden | The field shouldn't appear at all for this audit. |

### Fields you can configure

In the order they appear on the panel (mirroring the respondent view):

| Field | Default | Notes |
|---|---|---|
| **Answers** | Auditor + Respondent | Questionnaire answers when the framework defines auto-questions. |
| **Respondent alignment** | Hidden | Whether the respondent's answer matches the auditor's expectation. The "Auditor only" pill is greyed out — only the respondent can populate this. |
| **Status** | Auditor only | The lifecycle status of the requirement assessment. |
| **Result** | Auditor + Respondent | Compliant / partial / non-compliant / N/A. |
| **Extended result** | Auditor only | Free-form qualifier alongside the result. Cannot be more permissive than **Result**. |
| **Score** | Hidden | Numeric score. |
| **Documentation score** | Hidden | Companion score for documentation maturity. Cannot be more permissive than **Score**. |
| **Applied controls** | Auditor + Respondent | The controls linked to this requirement. |
| **Evidences** | Auditor + Respondent | Files / links proving the requirement. |
| **Observation** | Auditor + Respondent | Free-text commentary. |
| **Comments** | Auditor + Respondent | Per-row comments. Only visible when the `comments` feature flag is on. |

### Parent / child constraints

Two pairs are linked — a child cannot be more permissive than its parent:

- **Documentation score** ≤ **Score**
- **Extended result** ≤ **Result**

If you lower the parent's permissiveness (e.g. flip _Score_ to _Hidden_), the child auto-clamps. Disallowed pill choices for a child are greyed out in real time.

### Where defaults come from

Defaults cascade — most permissive wins gets you _Auditor + Respondent_; everything else is set per framework:

1. **Audit-level override** — what you set in this panel. Wins if present.
2. **Framework defaults** — each framework can ship its own `field_visibility` shape. When you pick a framework on the create form, the panel's pills preview the framework's defaults.
3. **Platform defaults** — the safety net (`Score`, `Documentation score`, `Respondent alignment` default to _Hidden_; `Status` and `Extended result` default to _Auditor only_; everything else to _Auditor + Respondent_).

Open the panel on an existing audit and toggle pills as needed; changes save on the next form submit.

{% hint style="info" %}
The audit's stored `field_visibility` is the runtime source of truth. The framework's defaults are only consulted to seed a new audit — overrides on the framework after the audit exists won't propagate.
{% endhint %}

## Scoring

Three settings shape how the platform turns per-requirement scores into a global score:

### Score calculation method

The **Score calculation method** select offers three modes:

- **Average** _(default)_ — weighted mean of all requirement scores.
- **Sum** — weighted total of all requirement scores.
- **Average of averages** — groups requirements by parent section, averages each section, then averages the section averages. Useful when sections are unevenly populated and you don't want a verbose section to dominate.

### Target score

The **Target score** is the maturity level you're aiming for. Two uses:

- Drives the "you are X% of the way to your target" view.
- Acts as the substitute value for **Not Applicable** requirements when the anchor toggle is on.

If left blank, the platform substitutes the framework's maximum score.

### Anchor N/A to target score

The **Anchor N/A to target score** checkbox controls how _Not Applicable_ requirements are treated:

- **Off** _(default)_ — N/A requirements are excluded from the score entirely.
- **On** — N/A requirements are included with their score replaced by the **Target score**. Use this when "we're already at our target on this dimension" should count toward the overall maturity, rather than being ignored.

## Lifecycle controls

### Lock

The **Locked** checkbox freezes the audit after sign-off. While locked:

- The audit itself, its requirement assessments, and linked applied controls are all read-only.
- Create / Edit / Delete actions are disabled on the audit's detail page.
- Auto-sync (see below) is skipped on locked audits.

Unlock by un-checking the box.

This setting is hidden from third-party users — they can't lock or unlock audits they answer.

### Automatic daily sync to actions

The **Automatic daily sync to actions** checkbox enables a daily background job that pushes the audit's state to the linked applied controls (status, ETA, etc.). Locked audits are skipped.

Off by default. Turn on for audits where the controls should always reflect the latest requirement-assessment status without manual nudging.

This setting is hidden from third-party users.

### ETA and Due date

- **ETA** — estimated time of arrival. Informational; the audit isn't blocked when it passes.
- **Due date** — the date by which the audit must be completed. Drives overdue indicators across dashboards.

### Suggest controls _(create-time only)_

The **Suggest controls** checkbox appears only on the **create** form, and only when the chosen framework ships reference controls. When ticked, the platform pre-populates applied controls from each requirement's suggested reference controls during creation. Saves a manual round-trip for first-time imports.

## Attachments

The **More** dropdown also lets you bind:

- **Assets** — assets in scope of the audit. M2M.
- **Evidences** — overall audit-level evidences (cross-cutting). Per-requirement evidence is set on the requirement assessment itself.
- **Authors** — actors writing the audit. M2M.
- **Reviewers** — actors reviewing / approving. M2M.
- **Observation** — Markdown commentary about the audit as a whole.
- **Reference** (`ref_id`) — short identifier (e.g. `AUD-2026-Q1`).

## Where settings live

Most settings are **edit-time on the audit** — open the audit's edit form and expand **More**.

Framework-level defaults for **Field visibility** can be set by the framework author (see the framework builder). Platform-level defaults are codified in `backend/core/utils.py` (`DEFAULT_VISIBILITY`) and apply when neither the framework nor the audit overrides a field.

## What's next

- [Basic audit](basic-audit.md) — the create-and-run walkthrough.
- [Audits](../concepts/audits.md) — the underlying model.
- [Auditee mode](../introduction/vocabulary.md) — how the respondent view actually renders these visibility choices.
