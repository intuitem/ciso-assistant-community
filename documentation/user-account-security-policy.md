# User Account Security Policy

## Overview

A custom role holding user-management permissions (`add_user`, `change_user`, `delete_user`) must not be able to escalate to administrator, take over another account, or lock the deployment out of administration. This page documents the invariants enforced by the backend (`UserWriteSerializer` and `UserViewSet` in `core/`, plus the SSO settings serializer and the nightly expiry task), the rationale behind each rule, and the residual risks that were consciously accepted.

All guards fail loud: a denied operation returns HTTP 403 with a camelCase error key translated by the frontend (`messages/*.json`), never a silent drop. Full `PUT` payloads that echo back unchanged values always pass — only actual *changes* are guarded.

## Threat model

- **Escalation**: granting yourself (or an accomplice) admin-level privileges — via `is_superuser`, via group membership, or via any field that indirectly confers privilege.
- **Takeover**: capturing an existing account's power. The SSO adapter maps logins to accounts **by email**, so rewriting a user's email re-binds their identity: with SSO enabled it hands the account to whoever the IdP asserts the new address for, IdP-side MFA notwithstanding; with local auth it redirects password-reset mail.
- **Lockout**: a denial-of-service that leaves the deployment without any active administrator — by deactivation, expiry, deletion, or group-stripping.

## Principles

### 1. Privilege flows only through group membership

- `is_superuser` is a **deployment-owned bootstrap flag** (`CISO_ASSISTANT_SUPERUSER_EMAIL`, `createsuperuser`): it is never writable through the API, by anyone. The startup sync converts it into `BI-UG-ADM` membership; demoting a superuser is an ops action, not an API call.
- Changing a user's `user_groups` (add **or** remove, on create or update) requires **`change_usergroup` on each affected group's folder** — `change_user` alone manages people, never privileges. Since `BI-UG-ADM` lives in the root folder, only root-scoped holders can grant admin.
- The same primitive gates the group-side endpoints (`/user-groups/{id}/add-members`, `remove-members`) — see [User Group Membership Management](user-group-membership.md). Two directions, one rule.
- Only the delta is checked, and memberships in groups the requester cannot *see* are preserved rather than treated as removals — a full `PUT` from a limited-visibility client neither strips them silently nor fails spuriously.
- No builtin role holds `add_roleassignment`/`delete_roleassignment`; granting those to a custom role is an explicit "privilege manager" decision.

### 2. Email is an identity binding

Rewriting an email is an identity **re-binding** (takeover class), so beyond `change_user`:

- A **SCIM-managed** account's email (and names) are immutable through the API for everyone, admins included — SCIM is the authoritative write channel and a legitimate rename arrives through the SCIM endpoint itself.
- A **JIT-provisioned or SSO-only** account's email is admin-only: the authoritative address lives in the IdP, but no sync channel exists to repair drift, so an admin must be able to (an IdP-side rename would otherwise orphan the account and JIT-provision a duplicate). "SSO-only" is *no local password path* — Force SSO on and `keep_local_login` off — not the `is_local` property, which also reads False for a merely deactivated local account.
- A user **holding any group membership** requires `change_usergroup` on **all** their groups' folders — you may re-bind an identity only if you already control every grant it carries.
- Only group-less local users' emails are freely editable by user managers.

### 3. Lifecycle operations share one altitude

`is_active`, `expiry_date` (deferred deactivation — the nightly `deactivate_expired_users` task applies it), `keep_local_login`, and **deletion** are recoverable denial-of-service class, deliberately less strict than email:

| Target | Deactivate / expire / login-mode | Delete |
| --- | --- | --- |
| Non-admin account (grouped or not) | free for user managers (routine offboarding) | plain `delete_user` |
| Administrator account (direct or IdP-inherited) | `change_usergroup` on root | `change_usergroup` on root |
| SCIM-managed account | admin-only break-glass (`keep_local_login` can **never** be enabled) | admin-only |

Keeping all four operations at the same altitude matters: no operation may be the "bigger hammer" that bypasses another (e.g. deleting an admin you may not deactivate, or expiring an admin you may not deactivate).

### 4. The last active administrator is untouchable

The last active **directly-managed** member of `BI-UG-ADM` — the lockout-proof anchor that SCIM/IdP can never reach — is protected against every removal vector, for everyone including admins themselves:

- deletion and admin-group-stripping (long-standing viewset guards),
- deactivation and expiry-setting (`attemptToDeactivateOnlyAdminAccountError`), with the admin-group row locked around the update so concurrent requests cannot race into a zero-admin state,
- the nightly expiry task skips the last active admin (backstop for expiry dates that predate the guard),
- the `provision_user` workflow action refuses to deactivate it, mirroring `manage_group_membership` next to it,
- the SCIM protocol endpoints carry their own mirror guard (`_would_orphan_admins`).

Reactivation and clearing an expiry are always allowed.

### 5. SCIM accounts are IdP-owned

- **SCIM writes identity and lifecycle** (email, names, active) through its own endpoints; those fields are immutable or admin-break-glass through the app API (see above).
- **Local-only concepts stay locally manageable**: direct `user_groups` (essential when IdP-group role inheritance is off), `observation`, `expiry_date` metadata, etc. — under their own guards.
- `keep_local_login` can never be *enabled* on a SCIM account (a SCIM identity stays SSO-only — no password backdoor, admin or not); disabling a legacy flag is admin-only. Note that SCIM itself never sets this flag: it is a purely local attribute.
- **Deleting** the account (admin-only) is the escape hatch for a decommissioned SCIM integration.
- SSO cannot be **disabled** while SCIM/JIT users lack a local-login fallback (`errorSsoRequiredForManagedUsers`). The guard applies to the enabled→disabled *transition* only, and a payload omitting `is_enabled`/`force_sso`/`provider`/`client_id` keeps the stored value instead of resetting it — re-saving a disabled configuration (configure-then-enable) stays possible.
- The SSO settings write replaces the stored value wholesale, but the serializer builds nested `settings` sections only for the dotted sources a payload actually carries, so every real save omits some section (an OIDC save renders no SAML accordion, hence no `settings.advanced.*`). Omitted sections — and omitted leaves inside a section the payload does touch, the SP private key above all — are merged back from the stored value rather than dropped.

## Error keys

| Key | Meaning |
| --- | --- |
| `cannotChangeSuperuserStatus` | `is_superuser` is not an API concept |
| `missingPermissionToManageUserGroupMembership` | group delta requires `change_usergroup` on that group's folder |
| `emailChangeRequiresUserGroupManagementRights` | email of a grouped user |
| `emailChangeOfIdpManagedUserRequiresAdmin` | email of a JIT/SSO-only account |
| `fieldManagedByScim` | identity field of a SCIM account |
| `scimAccountFieldRequiresAdmin` | lifecycle field of a SCIM account |
| `scimAccountCannotEnableLocalLogin` | password fallback on a SCIM account |
| `adminAccountLifecycleChangeRequiresAdminRights` | lifecycle field of an admin account |
| `deletingAdminAccountRequiresAdminRights` | deleting an admin account |
| `attemptToDeactivateOnlyAdminAccountError` | deactivating/expiring the last active admin |
| `attemptToDeleteOnlyAdminAccountError` / `attemptToRemoveOnlyAdminUserGroup` | pre-existing last-admin guards |
| `onlyAdminCanDeleteScimAccount` | deleting a SCIM account |
| `errorSsoRequiredForManagedUsers` | disabling SSO would strand SSO-only users |

## Accepted residual risks and follow-ups

- **Pre-onboarding email swap**: the email rule checks *current* groups, so a group-less account's email can be rewritten before anyone grants it groups (including via delete-and-recreate of a non-admin account). Whoever grants group membership vouches for the identity behind the email.
- **Force-SSO deployments**: with Force SSO enabled, every user without `keep_local_login` is SSO-only, so *all* email changes become admin-only. Intended.
- **Stable-identifier SSO matching** (OIDC `sub` / SAML NameID, as `scim_external_id` already does for SCIM) would remove the email-matching fragility at the root; email would remain a first-login bootstrap only. Design follow-up.
- **Detach from SCIM**: an explicit, audited, admin-only action converting a SCIM account to a local one is the realistic decommission path (deletion destroys attribution history). Follow-up; until then, deletion is the escape hatch.
- **Workflow `provision_user` altitude**: the action is gated at publish time on `add_user`/`change_user` at the root, so a workflow author holding those can still deactivate a *non-last* administrator, which the API itself would require `change_usergroup` on the root for. Only the lockout invariant (the last active admin) and SCIM identity immutability are enforced at execute time, because the requester-relative half of the rule has no requester to check against once the workflow runs. Raising the action's declared permissions to include `change_usergroup` is the follow-up.
- **Translations**: the error keys ship with `en`/`fr` messages; other locales fall back to the raw key until the translation pipeline runs.

## Observability

Every denied guard trip is logged as a structured warning — `denied privileged user operation` with `guard` (e.g. `superuser`, `group_membership`, `scim_identity`, `admin_lifecycle`, `last_active_admin`, `admin_delete`), `requester`, `target`, and the error keys — so escalation attempts are visible in the logs, not just as 403s in the client. The user detail and edit payloads expose read-only `is_scim_managed` / `is_jit_provisioned` flags so API consumers (and, later, the edit form) can tell which fields the guards will refuse.

## Implementation trap: never ask the relation

Every guard that needs to know "is this target an administrator?" queries `UserGroup.objects.filter(user=..., name="BI-UG-ADM")`, never `instance.user_groups.filter(...)`, and `User.is_admin()` does the same.

`UserViewSet.get_queryset` prefetches `user_groups` filtered to the *requester's* viewable groups. Django keeps that filtered queryset in the prefetch cache, so `instance.user_groups.filter(...)` clones it and inherits the `id__in=viewable` restriction instead of hitting the database clean. A requester who cannot see `BI-UG-ADM` — any custom role holding `change_user` without root-scoped `view_usergroup` — would therefore be told that no target is an administrator, silently disabling the deactivation, expiry, local-login and deletion guards on administrator accounts, up to deleting the last one. `TestBlindUserManagerGuards` pins this.
