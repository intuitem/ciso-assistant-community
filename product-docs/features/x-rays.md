---
description: Automated consistency and quality checks across governance, risk, compliance and operations in the workspace
---

# X-rays

**X-rays** is the platform's standing quality-control surface — a single page that scans every audit, risk assessment, objective, evidence, finding, applied control and task you have access to and surfaces inconsistencies, missing data, and likely modelling mistakes. It's how you find _"the things you forgot"_ at the end of an assessment campaign without having to open each object one by one.

The page runs on every load — there's no "trigger" button. Issues are shown grouped by domain, then by area, then by rule, with a direct link from each affected object to the form where you fix it.

## Where to find it

Sidebar → **X-rays**. Gated by the `xrays` feature flag, **default on** in both community and Enterprise editions.

The sidebar entry is hidden for the **Third-party respondent** role.

## What it covers

X-rays groups its checks into the same four areas as the analytics page, one tab each:

- **Governance** — objectives, issues, evidences and findings of the domain.
- **Risk** — risk assessments, plus their risk scenarios, applied controls, and risk acceptances.
- **Compliance** — audits (compliance assessments), plus the requirement assessments, applied controls, and evidences they touch.
- **Operations** — applied controls and tasks of the domain.

The page lists every domain you have access to, with the four tabs per domain. **Risk** and **Compliance** list the assessments inside them; **Governance** and **Operations** list their rules directly. Domain badges show the count of errors / warnings / info so you can spot the worst-affected domains at a glance. A severity filter at the top lets you hide whole tiers, so you can sweep errors first and come back to the info items later.

Everything is collapsed by default:

1. A domain is a closed row carrying its issue counts per severity.
2. Opening it shows the four tabs, on whichever tab holds the most severe issues. On **Risk** and **Compliance**, each assessment is a closed card with its own counts.
3. Opening an assessment — or the **Governance** / **Operations** tab — lists the rules it trips, each with the number and kind of objects affected ("4 requirements").
4. Opening a rule shows those objects in a paginated table, with the columns that matter for triage (status, ETA, priority for a control; result and status for a requirement; treatment for a scenario; status, health and due date for an objective; status and expiry date for an evidence). Past ten objects, the table gains a search box that matches the name and every column.

Domains and assessments with no issue are not listed at all, and a domain's content is only built when you open it, so a workspace with hundreds of domains stays responsive.

A toolbar above the list carries a domain search, a sort (by severity, so the worst domains come first, or by name), and expand / collapse all.

If nothing is flagged anywhere, the page shows _"No issue detected. X-rays only lists domains that have issues."_

## Severity tiers

Every issue is tagged with one of three severities:

| Tier | Icon | What it means |
|---|---|---|
| **Error** | 🐛 (red) | A modelling inconsistency that should be fixed before the assessment is considered complete (e.g. residual risk higher than current risk, expired risk acceptance, control listed in two places). |
| **Warning** | ⚠️ (amber) | A likely gap that the analyst should confirm or fill in (e.g. compliant requirement with no evidence, applied control without a cost estimate, empty risk assessment). |
| **Info** | ℹ️ (blue) | Hints and reminders — non-blocking, useful for hygiene (e.g. assessment still in progress, no author assigned, applied control without an external link). |

Within each assessment, issues are grouped by **rule** (so 17 controls missing an ETA are one row saying 17, not 17 separate entries), and the objects behind a rule are called its **occurrences**. "Finding" names a different concept in the platform, see [findings assessments](../concepts/findings-assessments.md).

## The catalogue of checks

Below is the full list of checks the platform runs today — useful when you want to know _why_ an issue showed up, or to predict what x-rays will say before you open the page.

### Compliance: audits

| Severity | Check | Triggers when |
|---|---|---|
| Error | Requirement relies on an applied control past its expiry date | A compliant or partially-compliant requirement is justified by a control whose expiry date has passed |
| Info | Audit is still in progress | The audit's status is `in_progress` |
| Info | No author assigned to this audit | No author set on the audit |
| Info | Applied control has no reference control selected | An applied control linked to the audit isn't templated from a reference control |
| Info | Requirement is non-compliant while all its applied controls are active | Either the verdict or the control statuses are out of date |
| Info | Requirement is non-compliant with no observation | A non-compliant requirement records no observation |
| Info | Requirement is partially compliant with no observation | A partially-compliant requirement records no observation |
| Info | Requirement has a result while still marked to do | A result is recorded but the progress status is still `to_do` |
| Warning | Requirement is marked compliant but has no evidence attached (direct or indirect) | A compliant requirement assessment can't point to any evidence — directly or through its applied controls |
| Warning | Requirement is marked compliant or partially compliant with no applied control | A compliant / partially-compliant requirement assessment has zero applied controls |
| Warning | Requirement is compliant but none of its applied controls is active | The requirement has controls, but not one of them has reached `active` |
| Warning | Requirement relies on a deprecated or degraded applied control | A compliant or partially-compliant requirement is justified by a control that is `deprecated` or `degraded` |
| Warning | Requirement is partially compliant but none of its applied controls has started | Every linked control is still `to_do` or undefined |
| Warning | Requirement depends on an applied control whose ETA has passed | A linked control has an ETA in the past and isn't `active` yet |
| Warning | Every evidence supporting the requirement has expired | All evidence reachable from the requirement is past its expiry date or marked expired |
| Warning | Requirement relies on an evidence that was rejected | Evidence reachable from a compliant or partially-compliant requirement is marked `rejected` |
| Warning | Requirement is compliant but none of its evidence has left draft | Every evidence reachable from a compliant requirement is still `draft` |
| Warning | Requirement is not applicable with no justification | A requirement marked not applicable records no observation explaining why |
| Warning | Requirement is marked done but has no result | The progress status is `done` while the result is still `not_assessed` |
| Warning | Applied control is active but has no evidence attached | An applied control linked to the audit is `active` but has no evidence attached |
| Warning | Evidence has no file uploaded | An evidence object has no attachment and no external link on any revision |

{% hint style="info" %}
Requirement checks are skipped when the requirement isn't assessable, when it falls outside the audit's selected implementation groups, or when the audit hides a field the check reads — an audit that hides **Status** or **Result** isn't judged on it.
{% endhint %}

### Risk: risk assessments

| Severity | Check | Triggers when |
|---|---|---|
| Info | Risk assessment is still in progress | The assessment's status is `in_progress` |
| Info | No author assigned to this risk assessment | No author set on the assessment |
| Info | Applied control does not have an external link attached | An applied control has no `link` field set |
| Warning | Risk assessment is empty. No risk scenario declared yet | The assessment has zero scenarios |
| Warning | Current risk level has not been assessed | A scenario's `current_level` is unset |
| Warning | Risk accepted but no risk acceptance attached | A scenario with treatment `accept` isn't linked to any RiskAcceptance |
| Warning | Does not have an ETA | An applied control that isn't `active` has no ETA |
| Warning | Does not have an estimated effort | An applied control has no `effort` set |
| Warning | Does not have an estimated cost | An applied control has no `cost` set |
| Warning | Applied control is active but has no evidence attached | An applied control linked to a scenario is `active` but has no evidence attached |
| Warning | Acceptance has no expiry date | A risk acceptance has no `expiry_date` |
| Error | Residual risk level has not been assessed | `residual_level` unset while `current_level` is set |
| Error | Residual risk level is higher than the current one | `residual_level > current_level` — usually a data-entry mistake |
| Error | Residual risk probability is higher than the current one | `residual_proba > current_proba` |
| Error | Residual risk impact is higher than the current one | `residual_impact > current_impact` |
| Error | Residual risk level has been lowered without any specific measure | Residual is lower than current, but the scenario has no applied controls |
| Error | Appears in both existing and additional controls | A control is listed both as _existing_ and as _added_ on the same scenario |
| Error | Is marked as an existing control but its status is not active | An "existing" control on a scenario doesn't have status `active` |
| Error | ETA is in the past now. Consider updating its status or the date | An applied control's ETA is overdue and the control isn't `active` |
| Error | Acceptance has expired. Consider updating the status or the date | A risk acceptance's `expiry_date` is in the past |

### Governance

| Severity | Check | Triggers when |
|---|---|---|
| Warning | Objective has no applied control nor task | An active objective in `draft` or `in_progress` is linked to no applied control and no task |
| Warning | Objective is past its due date and not achieved | An active objective's due date has passed and its status is neither `achieved` nor `deprecated` |
| Warning | Objective is achieved but its health is at risk or off track | Status `achieved` while health is `at_risk` or `off_track` |
| Info | Objective has no tracking metric | An active objective in `draft` or `in_progress` has no metric |
| Info | Issue is not addressed by any objective | An `active` issue is linked to no objective |
| Warning | Evidence is missing | An evidence's status is `missing` |
| Warning | Evidence is expired | An evidence's status is `expired` |
| Warning | Evidence expiry date has passed but its status is not expired | The expiry date is in the past while the status was never moved to `expired` |
| Warning | Finding has no status | A finding's status is undefined |
| Warning | Finding has no severity | A finding's severity is undefined |
| Warning | Open finding has no applied control | A finding that is `identified`, `confirmed`, `assigned` or `in_progress` is linked to no applied control |

### Operations

| Severity | Check | Triggers when |
|---|---|---|
| Warning | Applied control has no owner | A control that isn't `deprecated` has no owner |
| Warning | Planned applied control has no ETA | A control in `to_do`, `in_progress` or `on_hold` has no ETA |
| Warning | Applied control has no status | A control's status is undefined |
| Warning | Task has no assignee | An enabled task has nobody assigned |
| Warning | Task occurrence is past its due date | A `pending` or `in_progress` occurrence of an enabled task has a due date in the past |

{% hint style="info" %}
Governance and Operations checks only look at objects you are allowed to view.
{% endhint %}

The check list is intentionally opinionated — these are mistakes the team has seen across many engagements. New checks are added over time; treat x-rays as a living spot-check, not a complete audit-readiness oracle.

## The fix loop

X-rays is designed to be a **one-click-away-from-fixing** surface, not a static report:

1. Open **X-rays** — the domains come sorted worst-first, so the top row is where the fire is.
2. Open it, switch to the right tab (**Governance**, **Risk**, **Compliance**, **Operations**), open an assessment where there is one, skim the rules it trips.
3. Open a rule and click any row — the link opens the offending object's **edit** page directly (control, scenario, evidence, requirement assessment, risk acceptance, objective, finding, task).
4. Fix it and save, or cancel — you land back on x-rays, and the row is gone.

The "go straight to the edit page" behaviour matters: every issue the platform raises is something you can fix in one form. There's no triage step.

## For a single assessment

The checks for one audit or risk assessment are available through the API, in one response:

- `GET /api/compliance-assessments/{id}/x-rays/`
- `GET /api/risk-assessments/{id}/x-rays/`

The response carries the assessment's own checks under `assessment`, and the **Governance** and **Operations** checks under `governance` and `operations`, restricted to the objects the assessment touches — for an audit, the applied controls and evidences of its requirements, the findings of its findings assessments, and its tasks; for a risk assessment, the applied controls of its scenarios, their evidences, and its tasks. Respondents get a `403` on an audit.

## When to use it

- **At assessment close-out** — sweep before declaring an audit or risk assessment _done_; catches missing evidences, undated controls, and modelling mistakes that survive a casual review.
- **Periodically across all domains** — as a hygiene check, especially before reporting cycles or steering-committee reviews.
- **After bulk imports** — when a CSV or Excel import landed many controls or scenarios, x-rays will surface the fields the import couldn't fill in (cost, effort, ETA, links).
- **When onboarding a new analyst** — give them x-rays as their first daily routine; the page teaches the platform's expectations through the issues it raises.

## Related

- [Applied controls](../concepts/applied-controls.md) — fields like ETA, effort, cost, and link that several x-rays checks target.
- [Risk assessments](../concepts/risk-assessments.md) — the residual-vs-current consistency checks live here.
- [Audits](../concepts/audits.md) — the compliance-side checks (evidence presence, controls on compliant requirements).
- [Evidence](../concepts/evidence.md) — the "no file or link" and expiry checks.
- [Findings assessments](../concepts/findings-assessments.md) — the findings checked in **Governance**.
- [Tasks](../concepts/tasks.md) — the tasks and occurrences checked in **Operations**.
- [Feature flags](../configuration/settings/feature-flags.md) — toggle the `xrays` flag.
