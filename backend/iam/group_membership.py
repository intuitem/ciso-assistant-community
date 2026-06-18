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

from collections import defaultdict

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
    `pairs` is an iterable of (user_id, user_group_id).

    Bulk path: one query finds which candidate pairs still have a backing
    source, then the orphaned edges are deleted straight through the join table
    (one delete per distinct group). That bypasses m2m_changed, so the groups
    cache is invalidated explicitly — the per-pair signal walk would otherwise
    dominate when a large route is removed.
    """
    pairs = set(pairs)
    if not pairs:
        return
    user_ids = {u for u, _ in pairs}
    group_ids = {g for _, g in pairs}
    still_backed = set(
        GroupMembershipSource.objects.filter(
            user_id__in=user_ids, user_group_id__in=group_ids
        ).values_list("user_id", "user_group_id")
    )
    orphaned = pairs - still_backed
    if not orphaned:
        return
    by_group = defaultdict(list)
    for user_id, group_id in orphaned:
        by_group[group_id].append(user_id)
    Through = User.user_groups.through
    for group_id, uids in by_group.items():
        Through.objects.filter(usergroup_id=group_id, user_id__in=uids).delete()
    from iam.cache_builders import invalidate_groups_cache

    invalidate_groups_cache()


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

# ---------------------------------------------------------------------------
# SCIM channel (members of an IdP group, fanned out over all its routes)
# ---------------------------------------------------------------------------

@transaction.atomic
def scim_add_members(idp_group, user_ids):
    """Add SCIM-channel members across all of the IdP group's routes.

    Bulk path: an IdP can push thousands of members in one PATCH, so this
    avoids per-user round-trips. Source rows are written first (so the manual
    stamping in the m2m_changed receiver is skipped), then the M2M edges are
    inserted straight through the join table and the groups cache is
    invalidated once — the receiver's per-pair work would otherwise dominate.
    """
    mappings = list(idp_group.mappings.all())
    if not mappings or not user_ids:
        return
    # filter() coerces the string ids SCIM sends and drops unknown users.
    valid_ids = list(User.objects.filter(id__in=user_ids).values_list("id", flat=True))
    if not valid_ids:
        return
    group_ids = {m.user_group_id for m in mappings}

    GroupMembershipSource.objects.bulk_create(
        [
            GroupMembershipSource(
                user_id=uid,
                user_group_id=m.user_group_id,
                source=m,
                channel=Channel.SCIM,
            )
            for uid in valid_ids
            for m in mappings
        ],
        ignore_conflicts=True,  # unique constraint dedups re-pushes
    )

    Through = User.user_groups.through
    existing = set(
        Through.objects.filter(
            user_id__in=valid_ids, usergroup_id__in=group_ids
        ).values_list("user_id", "usergroup_id")
    )
    new_edges = [
        Through(user_id=uid, usergroup_id=gid)
        for uid in valid_ids
        for gid in group_ids
        if (uid, gid) not in existing
    ]
    if new_edges:
        Through.objects.bulk_create(new_edges, ignore_conflicts=True)
        # bulk_create bypasses m2m_changed; invalidate the IAM groups cache
        # ourselves (provenance is already written above, so no manual stamp).
        from iam.cache_builders import invalidate_groups_cache

        invalidate_groups_cache()


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
