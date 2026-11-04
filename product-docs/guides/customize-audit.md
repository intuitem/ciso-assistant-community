---
description: Reference for every setting on an audit — visibility, scoring, lifecycle, attachments
---

# Customize your audit

Once the basics are in place (framework × perimeter), an audit exposes a set of settings that let you shape _what's visible to whom_, _how scores are computed_, and _how the assessment behaves over its lifecycle_. All of them sit under the **More** dropdown on the audit edit form.

This page is the reference for that dropdown. The pre-requisite "Basic audit" walkthrough covers creation; come here when you need to tune a live audit.

## Field visibility

Audits are routinely shared across two roles: **auditors** (the team running the audit) and **respondents** (the people answering — typically domain owners or third-party contacts). Different organisations want different things visible to each.

The **Field visibility** panel inside an audit's edit form sets, for every assessable field, what each role can do with it. There is one column per role, **Auditor** and **Respondent**, and each takes one of three access levels:

| Access | Meaning |
|---|---|
| **Edit** _(green)_ | The role sees the field and can change it. |
| **Read** | The role sees the field but cannot change it. |
| **Hidden** _(rose)_ | The field does not appear for that role. |

Pick the auditor's access first: it decides which respondent options are offered. The common combinations are:

| Auditor | Respondent | Use when |
|---|---|---|
| Edit | Edit | Both roles fill the field in. |
| Edit | Read | The auditor fills it in and shares it, e.g. the result once the review is done. |
| Edit | Hidden | The field is sensitive or internal-only. |
| Read | Edit | The respondent fills it in and the auditor reviews it without changing it. |
| Hidden | Hidden | The field shouldn't appear at all for this audit. |

Options that don't make sense are greyed out:

- The respondent never sees a field hidden from the auditor.
- Lowering the auditor's access never raises the respondent's. For _Read_ / _Edit_ on a field the respondent can't edit yet, set the respondent to _Edit_ first.
- A visible field needs someone who can edit it. **Result** and **Score** are the exception, since they can be computed from the answers: _Read_ for both roles is allowed there.
- **Respondent alignment** is only filled in by the respondent, so whenever it is shown, the respondent has _Edit_.
- **Comments** have no _Read_ level: a role either takes part in the thread or doesn't see it.

A field set to _Read_ shows as disabled for that role in table mode, on the requirement edit page and in the respondent view. Changes that role sends anyway to the requirement assessment or its answers through the API are ignored.

The panel applies all the rules above. When `field_visibility` is saved through the API instead, only an unknown role or access level, or a field shown to the respondent while hidden from the auditor, is rejected.

### Fields you can configure

In the order they appear on the panel (mirroring the respondent view). Defaults are shown as _Auditor / Respondent_:

| Field | Default | Notes |
|---|---|---|
| **Answers** | Edit / Edit | Questionnaire answers when the framework defines auto-questions. |
| **Respondent alignment** | Hidden / Hidden | The respondent's own answer to "Are you aligned with this requirement?", asked on requirements without questions. Only the respondent fills it in; the auditor sees it as a badge. |
| **Status** | Edit / Hidden | The lifecycle status of the requirement assessment. |
| **Result** | Edit / Edit | Compliant / partial / non-compliant / N/A. Also shows the framework's yes/no outcome rules on the audit page (e.g. the [CCB conformity criteria](../features/framework-specific/cyfun.md#checking-the-ccb-conformity-criteria) for CyFun 2025). |
| **Extended result** | Edit / Hidden | Free-form qualifier alongside the result. Cannot be more permissive than **Result**. |
| **Score** | Hidden / Hidden | Numeric score. Also shows the values the framework's number rules compute. |
| **Documentation score** | Hidden / Hidden | Companion score for documentation maturity. Cannot be more permissive than **Score**. |
| **Applied controls** | Edit / Edit | The controls linked to this requirement. |
| **Task templates** | Hidden / Hidden | Tasks linked to this requirement. Off unless the audit opts in. |
| **Evidences** | Edit / Edit | Files / links proving the requirement. |
| **Observation** | Edit / Edit | Free-text commentary. |
| **Comments** | Edit / Edit | Per-row comments. Only visible when the `comments` feature flag is on. No _Read_ level. |

### Parent / child constraints

Two pairs are linked — for each role, a child cannot be more permissive than its parent:

- **Documentation score** ≤ **Score**
- **Extended result** ≤ **Result**

If you lower the parent's access (e.g. flip _Score_ to _Hidden_ for the auditor), the child auto-clamps. Disallowed choices for a child are greyed out in real time.

### Where defaults come from

Defaults cascade:

1. **Audit-level override** — what you set in this panel. Wins if present.
2. **Framework defaults** — each framework can ship its own `field_visibility` shape. When you pick a framework on the create form, the panel previews the framework's defaults.
3. **Platform defaults** — the safety net (`Score`, `Documentation score`, `Respondent alignment` and `Task templates` default to _Hidden_ for both roles; `Status` and `Extended result` to _Edit_ for the auditor and _Hidden_ for the respondent; everything else to _Edit_ for both).

Open the panel on an existing audit and change access as needed; changes save on the next form submit.

{% hint style="info" %}
The audit's stored `field_visibility` is the runtime source of truth. The framework's defaults are only consulted to seed a new audit — overrides on the framework after the audit exists won't propagate.
{% endhint %}

## Scoring

These settings shape the scale requirements are scored on and how the platform turns per-requirement scores into a global score.

### Choosing the score scale

The **Score scale** picker sets the scale every requirement of the audit is scored on. It sits under **More**, just after the **Field visibility** panel, on both the create and the edit form.

{% hint style="info" %}
The picker only offers scales once scoring is visible to auditors. **Score** defaults to _Hidden_, so first set the auditor to _Edit_ or _Read_ on **Score** in **Field visibility**; until then the picker shows a reminder instead of the options.
{% endhint %}

Pick one of the options:

| Option | Scale | Offered when |
|---|---|---|
| **Framework** | The framework's own range and level labels. | The framework declares a scale of its own (level labels, or a range other than 0–100). |
| **Baseline audit** | The scale of the audit you are copying. | Creating a copy of an audit on the same framework. |
| **Organisation** | The organisation default, set in [general settings](../configuration/settings/general.md#audits) (0–5 unless changed). | Always. |
| **0–100** · _Percentage (%)_ | No level labels. | Always. |
| **0–5** · _e.g. ISO 33020_ | Incomplete, Performed, Managed, Established, Predictable, Innovating. | Always. |
| **1–5** · _e.g. CMMI_ | Initial, Managed, Defined, Quantitatively managed, Optimized. | Always. |
| **1–4** · _e.g. NIST_ | Partial, Risk-informed, Repeatable, Adaptive. | Always. |
| **0–3** · _e.g. C2M2_ | Incomplete, Initial, Managed, Defined. | Always. |
| **Current scale** | The scale the audit already has. | Editing an audit whose scale matches none of the other options. |

The preset matching the organisation default is not repeated: the **Organisation** option stands for it. Preset level labels follow the interface language. Below the options, the **Levels** line previews the labels of the selected scale, or reads _No level labels: scores are shown as numbers._

On a new audit the picker pre-selects, in this order: the **Baseline audit** for a copy, otherwise the **Framework** scale when the framework has one, otherwise the **Organisation** default. Audits created through the API without any scale get the framework's scale; the organisation default is only proposed by the form.

#### Frameworks with a fixed scale

When the framework's questionnaire computes scores from its answers, or some of its requirements carry their own scale, the scale cannot be changed. Only **Framework** is offered, with the note _This framework computes scores from its questions, so its scale cannot be changed._

#### Changing the scale of an existing audit

Picking a scale with a different range announces the conversion under the picker: _Existing scores, documentation scores and target will be converted proportionally from 0–100 to 0–5._ (with the actual ranges). When there is something to convert, **Save** opens a confirmation panel titled _Saving will convert existing values from … to …_ that counts the scored requirements, unticked scores and documentation scores affected, and the target change. Confirm with **Convert and save**, or **Cancel** to keep editing.

- Values are converted proportionally and rounded to whole numbers, halves rounded up — 40 on 0–100 becomes 2 on 0–5.
- The **Target score** is converted too (to two decimals), unless you change it in the same save; a target you set yourself must fall within the new range.
- Requirements with their own scale keep their scores.
- The score history before today stays on the previous scale.
- Rounding means converting back will not restore the original values exactly.

Switching to an option with the same range only changes the level labels; scores are left as they are. The scale of a [locked](#lock) audit cannot change unless the same save unlocks it.

When copying an audit, picking a scale other than the baseline's converts the carried-over scores the same way.

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

### Per-requirement scale override

By default every requirement in an audit is scored on the audit's [score scale](#choosing-the-score-scale) (e.g. 0..5). When a framework needs a few requirements scored on a different scale — for example a binary "Yes / No" check inside an otherwise maturity-style framework — those requirements can ship their own scale:

- `min_score` / `max_score` override the bounds of the audit-level scale for that requirement only.
- `scores_definition_ref` overrides the labels. The framework declares an **alternatives registry** keyed by name, and each requirement references an entry by name. Two requirements pointing at the same name share the same definition without duplication.

Per-requirement overrides are defined when the library is authored (Excel converter or YAML loader). They are not editable through the platform UI.

#### How scores aggregate

Each requirement assessment is normalised against its own resolved scale before being aggregated into the global audit score:

- **Average** and **Average of averages** — every requirement contributes a ratio in `[0..1]` (its score over its own range), the audit weighted-averages those ratios, then denormalises onto the audit's scale. A binary requirement scored 1/1 contributes 100%, exactly like a 5/5 on a 0..5 requirement.
- **Sum** — kept as a raw weighted sum on each requirement's own scale. The audit's theoretical maximum aggregates the per-requirement maxes, so 100% remains achievable when every requirement hits its own ceiling.

The donut display in the requirement tree mirrors the same normalisation: each node's fill is computed against its resolved range, so an offset scale like 1..4 renders the minimum at 0% (not 25%).

#### Anchor N/A with mixed scales

When **Anchor N/A to target score** is on and the audit's **Target score** is set, that target is projected onto each N/A requirement's range as a ratio. A target of 4/5 contributes 80% on a 0..5 requirement and 0.8/1 on a binary one — the contribution is consistent regardless of the underlying scale.

### Overriding an automatic score

When a framework ships auto-questions, the requirement's score is computed from the answers and is read-only by default: editing it directly has no effect, since every recompute would overwrite it.

To deviate from the computed value for a specific reason, an auditor can toggle **Override score** on the requirement. Turning it on:

- unlocks the score field so a manual value can be entered;
- pins that value — subsequent answer changes no longer recompute the score (the result, when it is answer-driven, still follows the answers);
- keeps the automatic score visible next to the manual one, with a warning when the two diverge, so the deviation stays auditable. That automatic value is a live preview computed from the answers entered so far; the questionnaire has to be fully answered before it is the value the audit would actually store.

Turning **Override score** back off hands the score back to the questionnaire and immediately recomputes it from the current answers.

On **import**, a score supplied for a question-driven requirement is treated as an override automatically: the imported value is kept instead of being recomputed from the imported answers. This is what lets a filled-in scoring template drive the audit even when the framework defines questions. Add an `is_score_overridden` column to the sheet to decide explicitly per row — a falsy value there hands the score back to the questionnaire.

**Cloning** an audit carries the pin over: a requirement pinned in the baseline stays pinned in the copy, with the same score.

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
