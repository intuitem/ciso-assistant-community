# Gate a model's sensitive fields with `view_<model>_full`; `view_<model>` stays the base view

- Status: Proposed
- Date: 2026-10-30
- Deciders: @nas-tabchiche
- Related: [is-published-field-removal](is-published-field-removal.md) (members and default roles), [global-user-creator-role](global-user-creator-role.md)

## Context

Global's default role (Baseline reader) grants `view_user` to every domain member, so that pickers and owner fields work. The same permission serves every user's sign-in and administration details to all of them: superuser flag, MFA status, expiry date, local login, SCIM and JIT provisioning and the administrators' observation. Most members need a user's name and email, not these details.

Access reviews need to read these details without being able to change them, so `change_user` cannot be the only way to see them.

Compliance assessments already split a view this way, additively and default-deny: `view_complianceassessment` gives the respondent view, and `view_compliance_assessment_full` adds the auditor view (`AUDITOR_VIEW_PERM` in `core/utils.py`).

## Decision

We will use one convention for views that only some viewers may get in full: `view_<model>` keeps giving the base view, and a custom permission `view_<model>_full` adds the sensitive part. The IAM kernel does not change. Row visibility still resolves `view_<model>` alone, and the full part is a folder-scoped `is_access_allowed` check on the object's folder.

First application beyond compliance assessments: `view_user_full`, listed in the role editor as **View full user record**.

- `USER_FULL_VIEW_FIELDS` lists the fields it gates: `is_superuser`, `has_mfa_enabled`, `expiry_date`, `keep_local_login`, `is_scim_managed`, `is_jit_provisioned` and `observation`. The edit form (`/api/users/<id>/object/`) also gates `is_local` and the raw `user_groups` membership.
- `has_full_user_view(request, user)` is the only gate. It is true for the user themself, and for holders of `view_user_full` or `change_user` on the user's folder.
- Every path that serves a user's data applies it:
  - user list and detail;
  - the edit form;
  - filters on these fields, which only match fully viewed users and the requester;
  - ordering on these fields, honoured only when the requester fully views every listed user;
  - the folder members list (`/api/folders/<id>/users/`), which orders on email, names and `is_active` only;
  - the enterprise object audit trail of a user. The audit log records every field, so without the full view of that user, the trail leaves out these fields and login activity, and drops the updates that only touched them.
- Built-in roles: Administrator and Reader hold `view_user_full`. Baseline reader, Analyst, Approver, Domain manager and User creator keep `view_user` only.
- A data migration adds `view_user_full` to every custom role that holds `view_user`, except the role set as Global's default role.

## Consequences

- **Row visibility is unchanged.** `view_user` means what it meant: pickers, owner fields and every check that uses it behave as before, for every model.
- **Only Global assignments make a difference.** Users live in Global, so a Global reader sees full records and a reader on a domain doesn't.
- **The Users page is listed for holders of the full view on Global.** Other members reach users through pickers and references.
- **Custom roles keep what they serve today**, through the migration. The exception is a custom role used as Global's default role: it stops serving these details to every member. Where that role is also assigned to a group that needs the full view, an administrator adds `view_user_full` to that group's role.
- **User creator stays exactly `add_user` and `view_user`**, as its own decision requires. Creators don't read back the details they set at creation, and can't change them afterwards anyway.
- **Existing API clients:**
  - Tokens without the full view (Analyst, Approver or Domain manager on Global, readers on a domain, Baseline reader only) stop receiving these fields on user list, detail and edit-form responses.
  - Their filters on these fields match only themselves.
  - Ordering on these fields is ignored, and the default order no longer puts superusers first.
  - Service accounts that run access reviews need Reader on Global, or a custom role with `view_user_full`.
  - The release notes say so.
- **New sensitive parts of other models use `view_<model>_full`**, with the model name as Django spells it. `view_compliance_assessment_full` keeps its historical spelling.

## Security

**Conclusion: the decision adds no significant risk; it removes an exposure.** Before it, every domain member could read every user's sign-in and administration details. After it, only explicit grants do. The decision adds one permission that only reveals fields, and leaves the IAM kernel and row visibility as they were.

### Why the details can't reach someone without the full view

1. **One gate, on every read path.** List, detail, the edit form, filters, ordering, the folder members list and the enterprise audit trail all go through `has_full_user_view()` or `USER_FULL_VIEW_FIELDS`. Other places that embed users (owner fields, pickers, webhooks, chat, workflow reads) serialize identity fields only.
2. **Mistakes hide data, they don't expose it.** The grant is additive, so every way of getting it wrong hides the fields:
   - a role that lacks it;
   - a new custom role built by ticking View;
   - an older backend rebooting and resetting the built-in roles.
3. **No new path to rows.** The kernel and every `view_*` check are untouched, so no model, users included, becomes visible to anyone new.
4. **The upgrade can't widen access.** The migration only grants `view_user_full` to custom roles that already served these fields through `view_user`. It skips Global's default role, the one role that would serve them to every member.

Tests cover each read path for a member without the full view, a Global reader, a `change_user` holder and the user themself: `app_tests/api/test_api_users.py`, and the enterprise tests for the audit trail.

### Remaining risks, accepted as low

- **A broad grant.** `view_user_full` is a view permission, so it is eligible for a default role. An administrator who adds it to Global's default role serves full records to every member. That takes an explicit choice, and the permission's label says what it gives.
- **`change_user` implies the full view.** Its holders can already change these fields, so reading them adds nothing.

### What would change this assessment

- A new endpoint, serializer or export that serializes users without going through the gate.
- Users becoming folder-scoped.
- `view_user_full` added to Baseline reader or another role that every member holds.

Each of these reopens the question and requires a new decision.
