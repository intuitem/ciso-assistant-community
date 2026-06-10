---
description: The append-only record of who changed what, and when
---

# Audit log

{% hint style="info" %}
The audit log is a **PRO** capability — both the instance-wide log and the per-object trail. The per-object trail is additionally gated by the `object_audit_trail` feature flag; see [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

CISO Assistant keeps an append-only audit log: every create, update, and delete on a tracked object is recorded with the user who made it, the timestamp, and exactly which fields changed. Two surfaces read from it — an instance-wide log for administrators, and a per-object trail on detail pages.

## The instance-wide log

Administrators open it from the sidebar under **Extra → Audit log**. It's available only to users holding the **view audit log** permission, which in practice means administrators.

The page is a single table of every recorded change across the instance:

- **Actor** — the user who made the change.
- **Action** — Create, Update, Delete, Access, or Login failed.
- **Content type** — the kind of object affected.
- **Timestamp**.
- **Folder** — the domain the object belongs to.

Filter by **action** and **content type**, and search by **actor** or **folder**. Open a row to see the full entry, including the object it referred to and the per-field `old → new` changes.

## Per-object audit trail

The **object audit trail** brings that same history to a single object's detail page, so you don't have to scan the instance-wide log to answer "what happened to *this* control?".

{% hint style="info" %}
Gated by the `object_audit_trail` feature flag (on by default) and the **Can view object audit trails** permission.
{% endhint %}

### Opening a trail

On an object's detail page, click the **Audit trail** button (clock icon) in the action bar. A panel opens listing that object's history, most recent first. If you don't hold the permission in the object's domain, the panel shows **Permission denied** instead.

### Reading the timeline

Each entry is one save, showing:

- an action badge — **Create**, **Update**, or **Delete**;
- the user who made the change and the timestamp;
- a per-field breakdown of what changed, as `old → new`.

All the changes from a single save are grouped into one entry, including related many-to-many edits. Reassigning an owner from one actor to another, for instance, reads as a single `alice@company.com → DIR` line rather than two separate rows.

### Who can see it

Visibility is governed by the **Can view object audit trails** permission. By default it's granted to the **Analyst**, **Domain manager**, and **Administrator** built-in roles, and you can add it to any custom role.

The permission is domain-scoped: a user sees an object's trail only when they hold the permission in that object's domain. Read-only **Reader** and **Approver** roles, external respondents (auditees), and third-party users don't get it. Because user accounts live in the global domain, account history is visible only to roles holding the permission there — in practice, administrators.

The trail shows the most recent 200 changes per object. Turning the `object_audit_trail` flag off hides the button everywhere and disables the lookup, without deleting any recorded history.

## What's never logged

Some data is deliberately kept out of the audit log:

- **Timestamps** (`created_at` / `updated_at`) — churn, not meaningful change.
- **Password hashes** — excluded from the user record's history entirely.

History exists only from the point an object starts being tracked; changes that predate audit logging aren't reconstructed.
