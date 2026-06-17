"""
Membership provenance helpers.

`User.user_groups` stays a plain M2M; this module keeps the invariant
"an edge exists iff >= 1 GroupMembershipSource backs it". Federation code
(the SSO adapter and the SCIM views) must mutate group membership only through
these helpers so the provenance side-table stays in sync. Manual edits made
directly on `user_groups` are handled by the m2m_changed receiver in iam.apps,
which stamps / clears `channel="manual"` rows.

Because no FK cascade can express a count-conditional delete, the M2M edge is
removed here in code, only once the last source backing it is gone — that is
what lets two IdP groups feed the same UserGroup and survive deleting one.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from iam.models import GroupMembershipSource, IdPGroupMapping

User = get_user_model()
Channel = GroupMembershipSource.Channel


def grant(user, user_group, mapping, channel):
    """Assert that `channel` (via `mapping`) puts `user` in `user_group`."""
    GroupMembershipSource.objects.get_or_create(
        user=user, user_group=user_group, source=mapping, channel=channel
    )
    user.user_groups.add(user_group)  # idempotent; the edge may already exist


def _reconcile_edges(pairs):
    """
    Drop every (user, group) M2M edge in `pairs` that no longer has any source.
    Uses `.remove()` (not a raw through delete) so cache-invalidation signals
    still fire. `pairs` is an iterable of (user_id, user_group_id).
    """
    orphaned = {}
    for user_id, group_id in set(pairs):
        if not GroupMembershipSource.objects.filter(
            user_id=user_id, user_group_id=group_id
        ).exists():
            orphaned.setdefault(user_id, []).append(group_id)
    if not orphaned:
        return
    users = User.objects.in_bulk(orphaned.keys())
    for user_id, group_ids in orphaned.items():
        user = users.get(user_id)
        if user is not None:
            user.user_groups.remove(*group_ids)


@transaction.atomic
def revoke_mapping(mapping, channel=None):
    """Remove the membership rows sourced from `mapping` (optionally limited to
    one channel) and drop any edge left unbacked."""
    rows = GroupMembershipSource.objects.filter(source=mapping)
    if channel is not None:
        rows = rows.filter(channel=channel)
    pairs = set(rows.values_list("user_id", "user_group_id"))
    rows.delete()
    _reconcile_edges(pairs)


@transaction.atomic
def delete_idp_group(idp_group):
    """Hard-delete an IdP group: cascade its routes + source rows, then drop
    any edge that is now unbacked."""
    pairs = set(
        GroupMembershipSource.objects.filter(
            source__idp_group=idp_group
        ).values_list("user_id", "user_group_id")
    )
    idp_group.delete()  # cascades mappings -> their GroupMembershipSource rows
    _reconcile_edges(pairs)


@transaction.atomic
def backfill_route(mapping):
    """
    A new route was added to an IdP group: grant its existing federated members
    (known from the group's other routes) into the new target, under the same
    channel. This makes a re-point (add the new route, then drop the old one)
    migrate members immediately. Manual memberships (null source) are skipped.
    """
    existing = list(
        GroupMembershipSource.objects.filter(source__idp_group=mapping.idp_group)
        .exclude(source=mapping)
        .values("user_id", "channel")
        .distinct()
    )
    if not existing:
        return
    users = User.objects.in_bulk({e["user_id"] for e in existing})
    for entry in existing:
        user = users.get(entry["user_id"])
        if user is not None:
            grant(user, mapping.user_group, mapping, entry["channel"])


# ---------------------------------------------------------------------------
# SCIM channel (members of an IdP group, fanned out over all its routes)
# ---------------------------------------------------------------------------

@transaction.atomic
def scim_add_members(idp_group, user_ids):
    mappings = list(idp_group.mappings.select_related("user_group"))
    if not mappings or not user_ids:
        return
    users = User.objects.in_bulk(user_ids)
    for user_id in user_ids:
        user = users.get(user_id)
        if user is None:
            continue
        for mapping in mappings:
            grant(user, mapping.user_group, mapping, Channel.SCIM)


@transaction.atomic
def scim_remove_members(idp_group, user_ids):
    if not user_ids:
        return
    rows = GroupMembershipSource.objects.filter(
        source__idp_group=idp_group,
        channel=Channel.SCIM,
        user_id__in=user_ids,
    )
    pairs = set(rows.values_list("user_id", "user_group_id"))
    rows.delete()
    _reconcile_edges(pairs)


@transaction.atomic
def scim_set_members(idp_group, user_ids):
    """Full replace of this IdP group's SCIM-channel membership."""
    target = set(map(str, user_ids))
    stale = GroupMembershipSource.objects.filter(
        source__idp_group=idp_group, channel=Channel.SCIM
    ).exclude(user_id__in=target)
    pairs = set(stale.values_list("user_id", "user_group_id"))
    stale.delete()
    _reconcile_edges(pairs)
    scim_add_members(idp_group, list(target))


# ---------------------------------------------------------------------------
# SSO/JWT channel (reconcile a user's memberships against IdP group claims)
# ---------------------------------------------------------------------------

@transaction.atomic
def sync_sso_user(user, claimed_external_ids, authoritative):
    """
    Reconcile the user's SSO-channel memberships against the IdP's group
    claims. Always additive; when `authoritative`, also removes SSO rows for
    routes the IdP no longer claims. Never touches manual or SCIM rows, so a
    hand-added or SCIM-provisioned membership is safe.
    """
    claimed_ids = set()
    if claimed_external_ids:
        mappings = IdPGroupMapping.objects.filter(
            idp_group__external_group_id__in=claimed_external_ids
        ).select_related("user_group")
        for mapping in mappings:
            grant(user, mapping.user_group, mapping, Channel.SSO)
            claimed_ids.add(mapping.id)

    if authoritative:
        stale = GroupMembershipSource.objects.filter(
            user=user, channel=Channel.SSO
        ).exclude(source_id__in=claimed_ids)
        pairs = set(stale.values_list("user_id", "user_group_id"))
        stale.delete()
        _reconcile_edges(pairs)
