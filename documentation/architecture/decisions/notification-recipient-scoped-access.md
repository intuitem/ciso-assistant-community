# Scope the notification inbox on the recipient alone, replacing folder RBAC rather than composing with it

- Status: Accepted
- Date: 2026-09-21
- Deciders: Abderrahmane Smimite (PR #4867)

## Context

Every other model in the product is reached through folder RBAC: a row carries a `folder`, and `RoleAssignment` decides who may see it. The notification centre stores one row per recipient per target, where the target is any model in the product, reached through a `GenericForeignKey`. The obvious move — give `Notification` a folder and let the existing machinery run — was tried and fails in both directions at once.

It denies the right people. Notifications are addressed by the producers to whoever the data names: an applied control's owner, a task's assignee, a team's members. None of that requires a role in the object's domain. A control owner who holds no role in the domain the control lives in is a normal, common situation, and folder gating makes their own notification invisible to them — a notification nobody can read is worse than no notification.

It permits the wrong people. The complement of "can view the target's domain" is not "is the recipient". Anyone holding a viewing role in that domain would have been able to read notifications addressed to someone else — including the read state, which is a record of what a specific named person has and has not looked at.

The second constraint is that the same message already leaves the building through email with no folder check at all. `core/email_utils.py` sends the identical context to the identical recipients, chosen the identical way. Folder-gating the in-app copy would not have withheld anything; it would only have made the two channels disagree.

## Decision

We will scope the inbox on `recipient` and nothing else. `Notification` declares `IAM_SCOPE_FIELD = Folder.IAM_NOT_IMPLEMENTED` and has no folder column; `NotificationViewSet.get_queryset` returns `Notification.objects.filter(recipient=self.request.user)` instead of calling `super()`, and `IsRecipient` re-checks `obj.recipient_id == request.user.id` at the object level. The inherited folder-RBAC enforcement points — the queryset, the permission class, the serializer's `_check_object_perm` — are each replaced, not layered on top of.

The domain of the target is still shown, as a derived, read-only label called `target_folder`. It is named that way and not `folder` precisely because it is not the IAM scope of the row: nothing in the access path reads it.

## Consequences

- **The recipient list is the access control list.** A producer choosing who to notify is choosing who may read that row. Producers must be reviewed with that in mind; adding a recipient is a disclosure decision, not a delivery convenience.
- **Never add a `folder` field to `Notification`, and never gate on `target_folder`.** Either would reintroduce the failure this decision exists to avoid. `target_folder` is a label; keep it out of permission code.
- **There is no administrative read path into an inbox, by design.** A global admin gets the same recipient-scoped queryset as anyone else and reads nobody else's notifications. Support cases that need one must be raised as their own decision, not solved by relaxing the queryset.
- **The write surface is one boolean.** `is_read` is the only writable field, `POST` is refused (405), and `batch-action` is restricted to delete and `is_read`. A user cannot forge a notification for someone else.
- **Replacing the queryset, the permission class and the serializer hook is not enough; inherited actions that ask their own permission question are a fourth site.** `cascade-info` was found doing exactly that. It runs `get_object()` first, so it was never a way into another user's inbox — but it then layers a folder-based check on top, asking for `delete_notification` in the target's domain. That question has no bearing on whether the row is the caller's, and it answered 403 for any recipient holding no role there, breaking the delete dialog for precisely the population this decision exists to serve. It is now overridden on the viewset (a notification is a leaf; nothing cascades, and `get_object()` is the check). `BaseModelViewSet` has three such self-asked questions — `_is_visible_to_requester`, `batch_action`, `cascade_info` — and every future one must be audited against this rule.
- **Retention is the only revocation.** A user removed from a team or from an object keeps the notifications already written for them until the sweep clears the condition or retention ages them out. Deleting the row is what revokes it; nothing re-evaluates access on read.
- Both halves of the trade are asserted in `backend/notifications/tests/test_access_boundaries.py` and must stay that way: a recipient with no role in the target's domain reads their own row, and a global admin reads nobody else's.

## Security considerations

**What is disclosed.** A notification carries the declared context values (an object's name, a count of days), the target's model and id, its domain name via `target_folder`, and `recipient_count`. A recipient therefore learns a small amount of metadata about an object in a domain they may hold no role in.

**Why we accept it.** That disclosure is already made, to the same people, by the email channel, which has never consulted folders. The recipient was named by the object's own data — they are the owner, the assignee, the team member — so the disclosure is the point of the feature, not a side effect of it. What a notification never does is grant access: `object_id` is a UUID, and the target's own endpoint is untouched by this decision, so following a notification into a domain the user cannot view is refused exactly as before.

**What limits it.** Producers declare their context keys in `NOTIFICATION_REGISTRY`, and the service writes only the declared keys — a producer cannot widen the payload by passing extra variables. Third-party users never receive an inbox row.

**One mechanism worth naming.** `BaseModelViewSet.list()` masks related objects the requester cannot view, but only for `FieldsRelatedField`. `target_folder` is a `SerializerMethodField`, so the masking does not apply and the domain name reaches the recipient whatever roles they hold. That is intended under this decision and is part of what the paragraph above accepts — but it means anything added to this serializer as a method field is exempt from the general masking, and must be judged on its own.

**Residual risks.**

- A producer that names a recipient carelessly discloses that context to them, with no second check to catch it. The registry review is the control.
- `recipient_count` tells a recipient how many others received the same row. It is a count, never a list, and this is deliberate: "am I the only one on this" without a roster.
- Read state is personal data about attention. It is deliberately not audit-logged, and it is not readable by anyone but the recipient.

## Alternatives considered

- **Folder RBAC as for every other model** — denies recipients their own notifications and grants role-holders other people's. This is the failure that forced the decision.
- **Folder RBAC composed with a recipient check (`recipient=me AND I can view the folder`)** — fixes the over-permission but keeps the under-permission: the owner with no role in the domain still cannot read their own row.
- **Recipient check composed with a fallback to folder RBAC (`recipient=me OR I can view the folder`)** — fixes the under-permission and keeps the over-permission: role-holders read other people's inboxes, including read state.
- **A stored `folder` column copied from the target at write time** — goes stale the moment the object moves domain, and a stale copy used for access is worse than none. This is also why the derived field is a label, not a column.
- **Suppressing notifications whose target the recipient cannot view** — silently drops the message rather than showing it, so a real obligation disappears with no trace, and the in-app channel would then contradict the email the same person just received. We may revisit this later and gate both channels on visibility, in a separate PR.
