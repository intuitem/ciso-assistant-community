# Reduce a model's view with `view_<model>_restricted`; `view_<model>` keeps the full view

- Status: Proposed
- Date: 2026-10-30
- Deciders: @nas-tabchiche
- Related: [is-published-field-removal](is-published-field-removal.md), [global-user-creator-role](global-user-creator-role.md)

## Context

Some roles must see a model's objects without seeing everything about them. Users are the current case: Global's default role (baseline reader) grants `view_user` to every domain member so pickers and owner fields work, and that permission also covered account details (MFA, expiry date, local login, provisioning, superuser flag, observation). Limiting them to holders of `change_user` would leave `view_user` meaning less than it says.

Compliance assessments solve this the other way round: `view_complianceassessment` alone is the respondent view, and `view_compliance_assessment_full` adds the auditor view. Either way, the role editor's View checkbox no longer describes what a role sees, and introducing a reduced view changes the meaning of existing grants.

## Decision

We will keep Django's meaning: `view_<model>` is the full view. A reduced view is a separate custom permission, `view_<model>_restricted`. Wherever the IAM kernel resolves the `("view", Model)` pair to decide which objects a principal sees, either permission counts; checks given an explicit `Permission` stay exact. Serializers serve the reduced shape when the requester lacks `view_<model>` on the object's folder.

First application: `view_user_restricted`. The baseline reader role swaps `view_user` for it, and account fields go to the user themself and to holders of `view_user` or `change_user` on the user's folder.

## Consequences

- New reduced views use this convention; no new `_full` permissions. `view_compliance_assessment_full` moves to `view_complianceassessment_restricted` in its own change, with a data migration giving the restricted permission to every role that holds `view_complianceassessment` without `_full`, so no role gains the auditor view on upgrade.
- Holding both permissions is the full view. Custom roles holding `view_user` keep the full view they have today.
- Built-in roles: Reader, Administrator and User creator keep `view_user`; Baseline reader, Analyst, Approver and Domain manager move to `view_user_restricted`; Administrator also holds the restricted one, as it holds every permission. Users live in Global, so only Global assignments see a difference.
- The users page is listed for `view_user` holders; restricted holders reach users through pickers and references.
- Restricted permissions are `view_*`, so they stay eligible for default roles.
- Code asking "can fully view" checks the explicit permission, not the pair.

## Security considerations

- A role author who ticks View grants the full view. Accepted: the checkbox says what it does, with the restricted permission listed beside it.
- Enterprise tenants whose configured default role holds `view_user` keep serving account details to every member. The upgrade note tells them to switch to `view_user_restricted`; we don't rewrite customer roles.
- The kernel change sits on every model's row-visibility path. It only adds an alternative for models that declare one; output for all other models must stay identical, and tests pin that.

## Alternatives considered

- `view_user_full`, the compliance-assessment pattern: default-deny for new roles, but every existing custom role's `view_user` silently shrinks and the View checkbox misleads.
- `change_user` as the only gate for account fields: no read-only access review of accounts.
- Per-field permissions: too fine-grained for the role editor.
