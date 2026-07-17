# User Group Membership Management

## Overview

Domain managers can add and remove the members of the user groups attached to the domains they manage — without being global administrators. Previously, changing a user's group membership required write access on the `User` object, which lives in the global (root) folder and is reserved to administrators. Membership is now managed from the **group** side, where a domain manager already has authority.

## Why this is safe

User groups are attached to a folder (a domain). Membership is the reverse side of the `User` ↔ `UserGroup` relation, so it can be authorized on the group rather than on the user:

- Editing membership is gated by **`change_usergroup` on the group's folder**, not by `change_user` (which is global-admin-only). A domain manager holds `change_usergroup` on their domain (and, recursively, subdomains).
- Only the membership link (the M2M through-row) is written — **no `User` attribute is ever modified** this way. A domain manager cannot edit user accounts, only who belongs to their domain's groups.
- Adding a user to a domain group only grants that group's domain-scoped roles; it cannot escalate access beyond the manager's own authority.
- The last direct member of the built-in `BI-UG-ADM` administrators group is protected: membership management can never empty it (mirroring the safeguard on the user form).

This preserves the single golden source of access control (role assignments) and the existing RBAC model — see [Access control model](architecture/data-model.md#access-control-model).

## For domain managers

From a user group's detail page:

- **Add members** — the button opens a picker listing users **not already in the group**. Search, browse by columns, sort, paginate, select one or many, then confirm. Inactive users are hidden by default (toggle to include them).
- **Remove members** — in the group's **Users** tab, select one or more members and click **Remove from group**.

Both controls appear only for users who can change the group (i.e. `change_usergroup` on the group's folder).

## The entity picker

The picker is a general-purpose, scalable selector — it never loads the whole directory into the browser:

- Server-side **search**, **per-column filter**, **sort**, and **pagination** (a "show N entries" control) via the `/{model}/autocomplete` endpoint.
- A persistent selection tray that survives paging, searching, and switching between the list and columnar "Browse" views.

## API

Both actions are gated by `change_usergroup` on the group's folder:

| Method | Endpoint                             | Body                        |
| ------ | ------------------------------------ | --------------------------- |
| POST   | `/user-groups/{id}/add-members`      | `{ "users": [<uuid>, …] }`  |
| POST   | `/user-groups/{id}/remove-members`   | `{ "users": [<uuid>, …] }`  |

## Reuse (for developers)

The membership feature is built from reusable pieces so other models can adopt the same pattern:

- **Backend** — `AutocompleteMixin` (`core/views.py`) plus the `build_autocomplete_serializer` factory (`core/serializers.py`) give any viewset a lightweight, server-paginated `autocomplete` action. A model becomes pickable by mixing it in and setting `autocomplete_fields` (or overriding `autocomplete_serializer_class`). The generic `/{model}/autocomplete` frontend proxy route forwards to it.
- **Frontend** — `EntityPickerModal` plus the `openEntityPicker` helper (`$lib/utils/entityPicker.ts`) provide the scalable multi-select. Removal reuses `ModelTable`'s opt-in `selectable` mode together with a `removeFromParent` config on a reverse-foreign-key field in `crud.ts`, which POSTs the selected ids to a parent action endpoint.
