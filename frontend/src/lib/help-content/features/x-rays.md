---
description: Automated consistency and quality checks across every audit and risk assessment in the workspace
---

# X-rays

**X-rays** is the platform's standing quality-control surface — a single page that scans every audit and risk assessment you have access to and surfaces inconsistencies, missing data, and likely modelling mistakes. It's how you find _"the things you forgot"_ at the end of an assessment campaign without having to open each assessment one by one.

The page runs on every load — there's no "trigger" button. Findings are shown grouped by domain, then by assessment type, then by issue type, with a direct link from each finding to the object you need to fix.

## Where to find it

Sidebar → **X-rays**. Gated by the `xrays` feature flag, **default on** in both community and Enterprise editions.

The page is internal-user only; the sidebar entry is hidden for **Respondent** and **Third-party respondent** roles.

## What it covers

X-rays inspects two assessment families today:

- **Audits** (compliance assessments) — plus the requirement assessments, applied controls, and evidences they touch.
- **Risk assessments** — plus their risk scenarios, applied controls, and risk acceptances.

The findings page lists every domain you have access to, with two tabs per domain — one for audits, one for risk assessments — and the assessments inside each tab. Domain badges show the count of errors / warnings / info findings so you can spot the worst-affected domains at a glance.

If no domain has any assessment to inspect, the page shows _"You have to create at least one perimeter to use X-rays."_

## Severity tiers

Every finding is tagged with one of three severities:

| Tier | Icon | What it means |
|---|---|---|
| **Error** | 🐛 (red) | A modelling inconsistency that should be fixed before the assessment is considered complete (e.g. residual risk higher than current risk, expired risk acceptance, control listed in two places). |
| **Warning** | ⚠️ (amber) | A likely gap that the analyst should confirm or fill in (e.g. compliant requirement with no evidence, applied control without a cost estimate, empty risk assessment). |
| **Info** | ℹ️ (blue) | Hints and reminders — non-blocking, useful for hygiene (e.g. assessment still in progress, no author assigned, applied control without an external link). |

Within each assessment, findings are first grouped by **issue type** (so 17 controls missing an ETA become one section with 17 entries, not 17 separate sections), then listed individually so you can click straight through to fix each one.

## The catalogue of checks

Below is the full list of checks the platform runs today — useful when you want to know _why_ a finding showed up, or to predict what x-rays will say before you open the page.

### On audits

| Severity | Check | Triggers when |
|---|---|---|
| Info | Audit is still in progress | The audit's status is `in_progress` |
| Info | No author assigned to this audit | No author set on the audit |
| Info | Applied control has no reference control selected | An applied control linked to the audit isn't templated from a reference control |
| Warning | Requirement is marked compliant but has no evidence attached (direct or indirect) | A compliant requirement assessment can't point to any evidence — directly or through its applied controls |
| Warning | Requirement is marked compliant or partially compliant with no applied control | A compliant / partially-compliant requirement assessment has zero applied controls |
| Warning | Evidence has no file uploaded | An evidence object has no attachment and no external link on any revision |

### On risk assessments

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

The check list is intentionally opinionated — these are mistakes the team has seen across many engagements. New checks are added over time; treat x-rays as a living spot-check, not a complete audit-readiness oracle.

## The fix loop

X-rays is designed to be a **one-click-away-from-fixing** surface, not a static report:

1. Open **X-rays** — scan the domain badges, pick the domain with the most red.
2. Switch to the right tab (audits / risk assessments) and skim the issue-type groups.
3. Click any finding — the link opens the offending object's **edit** page directly (control, scenario, evidence, requirement assessment, risk acceptance).
4. Fix the issue, save, return to x-rays — the finding is gone on next refresh.

The "go straight to the edit page" behaviour matters: every finding the platform raises is something you can fix in one form. There's no triage step.

## When to use it

- **At assessment close-out** — sweep before declaring an audit or risk assessment _done_; catches missing evidences, undated controls, and modelling mistakes that survive a casual review.
- **Periodically across all domains** — as a hygiene check, especially before reporting cycles or steering-committee reviews.
- **After bulk imports** — when a CSV or Excel import landed many controls or scenarios, x-rays will surface the fields the import couldn't fill in (cost, effort, ETA, links).
- **When onboarding a new analyst** — give them x-rays as their first daily routine; the page teaches the platform's expectations through the issues it raises.

## Related

- [Applied controls](../concepts/applied-controls.md) — fields like ETA, effort, cost, and link that several x-rays checks target.
- [Risk assessments](../concepts/risk-assessments.md) — the residual-vs-current consistency checks live here.
- [Audits](../concepts/audits.md) — the compliance-side checks (evidence presence, controls on compliant requirements).
- [Evidence](../concepts/evidence.md) — the "no file or link" check.
- [Feature flags](../configuration/settings/feature-flags.md) — toggle the `xrays` flag.
