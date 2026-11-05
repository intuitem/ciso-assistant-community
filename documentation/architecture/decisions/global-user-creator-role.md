# Delegate user creation through a builtin "Global - User creator" group, granted non-recursively on Global

- Status: Proposed
- Date: 2026-10-01
- Deciders: @eric-intuitem
- Related: [is-published-field-removal](is-published-field-removal.md) (members and default roles), [service-accounts-composition](service-accounts-composition.md)

## Context

Only global administrators could create users. Users always live in the root folder (`UserManager._create_user` hard-codes it), creation is authorized by `add_user` on the root folder only (`UserWriteSerializer.create`), and the only builtin role holding `add_user` is Administrator. Domain managers can already place existing users in their own domain's groups (`change_usergroup` on the domain, via **Add members**), but they cannot create the person they want to place, so every onboarding goes through a global admin.

We want a non-admin — typically a domain manager, sometimes a specific person such as HR or a help desk, and provisioning service accounts — to be able to create users without gaining any other user-management power. The existing user serializer guards already keep creation narrow: putting the new user in a group requires `change_usergroup` on each group's folder, `is_superuser` is read-only, the account is created without a password and the invitation goes to the address itself, and editing or deleting users requires `change_user` / `delete_user` on Global, which stay administrator-only.

## Decision

We will ship a builtin role **User creator** (`BI-RL-UCR`) holding exactly `add_user` and `view_user`, and a builtin group `BI-UG-GUC`, displayed as **Global - User creator**, on the root folder, with a builtin role assignment whose only perimeter is Global and which is **not recursive**. Both are created idempotently by `ensure_user_creator_group()`, which `startup()` calls only when the `DELEGATED_USER_CREATION` setting is set. The enterprise settings set it, on the same pattern as `CONFIGURABLE_DEFAULT_ROLE`: the code is common, but a community edition instance never gets the role or the group. No migration is needed. The role's name is translated through `BUILTIN_ROLE_TRANSLATIONS`, and the group label is derived from it. Service accounts that provision users use this same named role (selected in the service account's builtin-role picker, domain Global) rather than a dedicated per-account role.

## Consequences

- **Enterprise only.** `TestUserCreatorEditionGate` checks that a community edition startup creates neither the role nor the group. Switching an instance from enterprise back to community edition leaves an existing role, group and memberships in place and working; nothing removes them, as with default roles on non-root folders.
- **Creating and placing a user are two separate rights.** A creator cannot put the new user in any group unless they also hold `change_usergroup` on that group's domain. For a domain manager, the flow is: create the user, then **Add members** on one of their domain's groups.
- **Creators cannot correct their own mistakes.** Fixing a typo, deactivating or deleting a user still needs an administrator.
- **A user created by someone who is not a domain manager has no groups** and sees nothing until someone with group rights places them.
- **Holders take a contributor seat.** `add_user` is a write permission and is deliberately *not* in `User.NON_SEAT_PERMISSIONS`: user administration is contributor work. Domain managers are already contributors, so nothing changes for them.
- **The group also makes its members members of Global.** Because the group is builtin, its members receive Global's default role (Baseline reader unless an administrator changed it). This changes nothing for domain managers, and gives someone whose only group is this one the read access they need to use the Users page.
- **`view_user` is part of the role itself** so that the role works without the default role: service accounts never receive it, and an enterprise instance may clear the root default role.
- **Required:** the role holds exactly `add_user` and `view_user`. Never add `change_user`, `delete_user` or `change_usergroup` to it: `change_usergroup` on Global is administrator-equivalent (it allows joining `BI-UG-ADM`), and the others remove the "admins fix mistakes" boundary this design relies on.
- **Required:** the assignment stays non-recursive. It is the first non-recursive builtin assignment; `Folder.create_default_ug_and_ra` forces recursion only on the per-domain groups it creates, so it does not touch this one. `TestGlobalUserCreatorGroup` locks both the permission set and the recursion flag.
- **Required:** any field added to `UserWriteSerializer` that is writable at creation must be reviewed against this role, since creation is now routinely reachable by non-admins.
- **Revisit if users ever become folder-scoped.** The role is only meaningful because users all live on Global.

## Security

**Conclusion: the group adds no significant risk.** It hands out one new capability — creating an account that holds no rights — plus read access to the user directory. Every path from there to more access is blocked by a server-side check that already existed and applies to anyone below administrator, whatever role they hold. None of those checks was written or relaxed for this decision.

### Why a holder cannot turn it into more access

1. **The accounts they create have no rights.** Adding a user to a group at creation requires `change_usergroup` on each group's folder, checked group by group (`UserWriteSerializer._enforce_group_membership_rights`), and the role has no such permission. `is_superuser` is read-only and an attempt to set it is refused, not silently ignored (`_enforce_superuser_immutable`). A user with no group is a member of no domain, so they don't even get a default role. The other fields accepted at creation (`keep_local_login`, `is_third_party`, `expiry_date`, `language`, `observation`) grant no rights.
2. **They cannot sign in as the accounts they create.** The account is created with an unusable password (`UserManager._create_user`). Credentials can only be set through the invitation or password-reset link sent to the address itself, or through an identity provider asserting that address. Creating `ceo@company.com` gives the creator nothing: the account is empty, and only the address owner can ever use it.
3. **They cannot touch existing accounts.** Editing, deactivating and deleting users require `change_user` / `delete_user` on Global, which only administrators hold. This rules out the one dangerous user-level attack, rewriting an existing user's email to take their account over through SSO, as well as deactivating administrators. Email addresses are unique, so creating an account never overwrites an existing one.
4. **They cannot raise their own rights.** The role holds no permission on groups, roles, role assignments or folders. Joining a group, their own included, needs `change_usergroup` on that group's folder, and joining `BI-UG-ADM` needs it on Global.
5. **The grant has no effect beyond user creation.** It is non-recursive and limited to Global, and `add_user` and `view_user` only apply to users, which exist only on Global. It gives nothing on any domain.
6. **Every creation is traceable.** `User` is registered with the audit log, group-membership changes included, so every account can be traced to whoever created it.

These properties are covered by tests on both code paths, human members and service accounts: `TestGlobalUserCreatorGroup` in `app_tests/api/test_api_users.py`, the existing `TestUserPrivilegeEscalationGuards`, and `test_user_creator_role_on_global_provisions_users` in `iam/tests/test_service_accounts.py`.

### Remaining risks, accepted as low

- **Invitation emails to arbitrary addresses.** A member can make the instance email anyone. This is limited to people an administrator put in the group, and each email maps to an audit-logged account creation.
- **Directory visibility.** Holders see every user's name and email, while group memberships stay filtered to groups they can see. With the default Baseline reader on Global, every member already sees this. If an administrator cleared the root default role, the exposure is new but limited to this group.
- **Wrong attributes on a pre-created account.** A creator can pre-create an account for someone who has not signed in yet with unhelpful settings, such as flagging an employee as a third party or setting an expiry date. They cannot change it afterwards, the effect is loss of access rather than extra access, and an administrator can correct it.
- **Leaked service account secret.** A service account holding this role can create empty accounts and read the directory, and nothing more. Its expiry date and secret rotation bound this, like for any service account.

### What would change this assessment

This conclusion holds only while the role keeps exactly `add_user` and `view_user` and the create path keeps its guards (see Consequences). Adding `change_user`, `delete_user` or `change_usergroup` to the role, or making a new creation-time field grant rights, would reopen these questions and requires a new decision.
