"""Run-authorization kernel access (spec D34).

This module is the ONLY place in the workflows app allowed to touch iam
authorization primitives, so the engine's authz surface stays auditable in
one file. PR #4364 rewrites the iam kernel (removes
get_accessible_object_ids); when it lands, migrate this file first, then
grep workflows/ for the remaining RoleAssignment call sites in views.py.

Deliberately unoptimized for now (user decision — correctness first):
- no codename->Permission caching (one Permission query per check),
- no per-run memoization (loops re-check identical (codename, folder) pairs),
- viewable_ids materializes id lists; becomes a queryset filter post-#4364.
"""

from django.contrib.auth.models import Permission

from iam.models import Folder, RoleAssignment


def can(user, codename, folder) -> bool:
    """May ``user`` exercise ``codename`` in ``folder``?

    Fail-closed on missing or inactive identities. Superusers get NO special
    treatment here (spec D34 amendment): every user's verdict comes from the
    iam kernel unchanged.
    """
    if user is None or not user.is_active:
        return False
    permission = Permission.objects.filter(codename=codename).first()
    if permission is None:
        return False
    return RoleAssignment.is_access_allowed(user=user, perm=permission, folder=folder)


def viewable_ids(user, model) -> set:
    """Ids of ``model`` rows ``user`` may view — the same primitive the API
    list views use (BaseModelViewSet.get_queryset), so engine reads see
    exactly what the API would show the identity."""
    if user is None or not user.is_active:
        return set()
    (view_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, model
    )
    return set(view_ids)
