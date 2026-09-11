"""
Property test: the IAM resolver against a brute-force oracle.

The oracle below is a from-first-principles restatement, in plain Python sets,
of the access semantics settled for `Folder.default_role` and role assignments:

- EXPLICIT grants: every role assignment the user holds (direct, or carried by
  a group they belong to; inactive users hold none) covers its perimeter
  folders — plus, when recursive, every descendant of them.
- AMBIENT grants: grants carried by standard (builtin) groups make the user a
  member of their perimeter folders' audiences, unless the perimeter is an
  enclave or sits under one. A folder with a non-NULL `default_role` grants
  that role's permissions, on itself only, to the members of itself and of its
  descendants (inclusive membership). Third parties never receive anything
  ambient; principals granted only directly (the service-account path) or via
  custom groups have no memberships, so nothing carries anything.

Every primitive must agree with the oracle on randomized worlds that always
contain the boundary cases: direct-only principals, third parties placed in
standard groups, enclaves (nested included), custom groups carrying grants,
default roles on leaves, and grants on the default-role folder itself.

This is the safety net for refactoring `iam/models.py`: any restructuring must
keep this file green, untouched.
"""

import random

import pytest
from django.contrib.auth.models import Permission

from iam.models import Folder, Role, RoleAssignment, User, UserGroup

PERMISSION_POOL = [
    "view_appliedcontrol",
    "view_asset",
    "view_evidence",
    "view_threat",
    "change_appliedcontrol",
    "add_asset",
]

VIEW_PERMISSIONS = [p for p in PERMISSION_POOL if p.startswith("view_")]


# ---------------------------------------------------------------------------
# The oracle
# ---------------------------------------------------------------------------


class World:
    """An in-memory mirror of the generated fixtures, used by the oracle."""

    def __init__(self):
        self.parent = {}  # folder_id -> parent folder_id | None
        self.enclaves = set()  # folder ids with content_type ENCLAVE
        self.default_role = {}  # folder_id -> role_id (only non-NULL entries)
        self.role_perms = {}  # role_id -> set of codenames
        self.group_folder = {}  # group_id -> folder_id
        self.group_builtin = {}  # group_id -> bool
        self.memberships = {}  # user_id -> set of group ids
        self.user_flags = {}  # user_id -> (is_third_party, is_active)
        # assignments: (kind, principal_id, role_id, frozenset(perimeter ids), is_recursive)
        self.assignments = []

    # -- tree helpers -------------------------------------------------------

    def ancestors(self, folder_id):
        """Strict ancestors, nearest first."""
        chain = []
        current = self.parent.get(folder_id)
        while current is not None:
            chain.append(current)
            current = self.parent.get(current)
        return chain

    def descendants(self, folder_id):
        return {f for f in self.parent if folder_id in self.ancestors(f)}

    def under_enclave(self, folder_id):
        return folder_id in self.enclaves or any(
            a in self.enclaves for a in self.ancestors(folder_id)
        )

    # -- the user's effective assignments -------------------------------------

    def user_assignments(self, user_id):
        """Yield (role_id, perimeters, is_recursive, carrier_group_id | None)."""
        _is_third_party, is_active = self.user_flags[user_id]
        if not is_active:
            return []
        result = []
        for kind, principal_id, role_id, perimeters, recursive in self.assignments:
            if kind == "user" and principal_id == user_id:
                result.append((role_id, perimeters, recursive, None))
            elif kind == "group" and principal_id in self.memberships[user_id]:
                result.append((role_id, perimeters, recursive, principal_id))
        return result

    # -- grant source 1: explicit ---------------------------------------------

    def explicit_covered_folders(self, user_id, codename):
        covered = set()
        for role_id, perimeters, recursive, _carrier in self.user_assignments(user_id):
            if codename not in self.role_perms[role_id]:
                continue
            for p in perimeters:
                covered.add(p)
                if recursive:
                    covered |= self.descendants(p)
        return covered

    # -- grant source 2: ambient (default roles) ------------------------------

    def member_folders(self, user_id):
        """Folders whose default-role audience the user belongs to."""
        is_third_party, _is_active = self.user_flags[user_id]
        if is_third_party:
            return set()
        sources = set()
        for _role, perimeters, _rec, carrier in self.user_assignments(user_id):
            if carrier is None or not self.group_builtin[carrier]:
                continue  # direct or custom-group grants carry no membership
            for p in perimeters:
                if not self.under_enclave(p):
                    sources.add(p)
        audience = set()
        for s in sources:
            audience.add(s)  # inclusive membership
            audience |= set(self.ancestors(s))
        return audience

    def ambient_covered_folders(self, user_id, codename):
        return {
            f
            for f in self.member_folders(user_id)
            if f in self.default_role
            and codename in self.role_perms[self.default_role[f]]
        }

    # -- verdicts --------------------------------------------------------------

    def covered_folders(self, user_id, codename):
        return self.explicit_covered_folders(user_id, codename) | (
            self.ambient_covered_folders(user_id, codename)
        )

    def clamped_covered_folders(
        self, user_id, codename, root_id, focused_id=None, base_id=None
    ):
        """Bulk coverage under focus mode and/or a base folder, mirroring
        `get_allowed_folder_ids`: the effective base is the narrower of the two
        when nested (empty when disjoint); inside it, coverage applies; in focus
        mode a covered root stays reachable (#4470 parity)."""
        covered = self.covered_folders(user_id, codename)
        effective_base = base_id
        if focused_id is not None:
            if base_id is None:
                effective_base = focused_id
            elif base_id != focused_id:
                if focused_id in self.ancestors(base_id):
                    effective_base = base_id
                elif base_id in self.ancestors(focused_id):
                    effective_base = focused_id
                else:
                    return set()
        if effective_base is None:
            return covered
        scoped = {
            f
            for f in covered
            if f == effective_base or effective_base in self.ancestors(f)
        }
        if focused_id is not None and root_id in covered:
            scoped.add(root_id)
        return scoped

    def point_allowed_focused(self, user_id, codename, folder_id, root_id, focused_id):
        """Point verdict under focus mode: covered, and inside the focused
        subtree — except the root, which focus never hides."""
        if (
            folder_id != root_id
            and folder_id != focused_id
            and (focused_id not in self.ancestors(folder_id))
        ):
            return False
        return folder_id in self.covered_folders(user_id, codename)

    def all_codenames(self, user_id):
        """Everything get_permissions should report for the user."""
        codenames = set()
        for role_id, _perimeters, _rec, _carrier in self.user_assignments(user_id):
            codenames |= self.role_perms[role_id]
        for f in self.member_folders(user_id):
            if f in self.default_role:
                codenames |= self.role_perms[self.default_role[f]]
        return codenames


# ---------------------------------------------------------------------------
# World generation
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_root():
    """Detach any default role on the root so worlds start neutral."""
    root = Folder.get_root_folder()
    original = root.default_role
    root.default_role = None
    root.save()
    yield root
    root.default_role = original
    root.save()


def build_world(rng: random.Random, tag: str, root: Folder):
    world = World()
    world.parent[root.id] = None

    permissions = {c: Permission.objects.get(codename=c) for c in PERMISSION_POOL}

    # --- folders: two domains under root, children under them, an enclave, a
    # domain nested under the enclave, and a guaranteed leaf.
    folders = {root.id: root}

    def add_folder(name, parent, content_type=Folder.ContentType.DOMAIN):
        f = Folder.objects.create(
            name=f"{tag}-{name}", parent_folder=parent, content_type=content_type
        )
        folders[f.id] = f
        world.parent[f.id] = parent.id
        if content_type == Folder.ContentType.ENCLAVE:
            world.enclaves.add(f.id)
        return f

    d1 = add_folder("d1", root)
    d2 = add_folder("d2", root)
    d1a = add_folder("d1a", d1)
    d1b_leaf = add_folder("d1b-leaf", d1)
    d2a = add_folder("d2a", d2)
    enclave = add_folder("enclave", d1, Folder.ContentType.ENCLAVE)
    under_enclave = add_folder("under-enclave", enclave)  # nested configuration
    for i in range(rng.randint(0, 3)):
        parent = rng.choice([d1, d2, d1a, d2a])
        add_folder(f"extra{i}", parent)

    domain_folders = [
        f for fid, f in folders.items() if fid not in world.enclaves and fid != root.id
    ]
    domain_folders = [f for f in domain_folders if not world.under_enclave(f.id)]

    # --- roles: random view/write mixes, plus a guaranteed view-only role.
    roles = []

    def add_role(name, codenames):
        r = Role.objects.create(name=f"{tag}-{name}")
        r.permissions.set([permissions[c] for c in codenames])
        world.role_perms[r.id] = set(codenames)
        roles.append(r)
        return r

    view_only = add_role("view-only", rng.sample(VIEW_PERMISSIONS, 2))
    add_role("wide-view", VIEW_PERMISSIONS)
    add_role("writer", rng.sample(PERMISSION_POOL, 3))
    add_role("narrow", [rng.choice(PERMISSION_POOL)])

    # --- default roles (view-only, per the production validator): on the root,
    # on a mid domain, and on a leaf (inclusive membership makes leaves live).
    view_only_roles = [
        r for r in roles if world.role_perms[r.id] <= set(VIEW_PERMISSIONS)
    ]
    for f in [root, d1, d1b_leaf, rng.choice(domain_folders)]:
        if rng.random() < 0.8 and f.id not in world.default_role:
            dr = rng.choice(view_only_roles)
            f.default_role = dr
            f.save()
            world.default_role[f.id] = dr.id

    # --- groups: builtin on domains, one builtin on the enclave and one under
    # it (the respondent pattern), one custom group.
    groups = []

    def add_group(name, folder, builtin):
        g = UserGroup.objects.create(
            name=f"{tag}-{name}", folder=folder, builtin=builtin
        )
        world.group_folder[g.id] = folder.id
        world.group_builtin[g.id] = builtin
        groups.append(g)
        return g

    g_d1 = add_group("g-d1", d1, True)
    g_d1a = add_group("g-d1a", d1a, True)
    g_leaf = add_group("g-leaf", d1b_leaf, True)
    g_d2 = add_group("g-d2", d2, True)
    g_enclave = add_group("g-enclave", enclave, True)
    g_under_enclave = add_group("g-under-enclave", under_enclave, True)
    g_custom = add_group("g-custom", d1, False)

    # --- users: every archetype the boundaries need.
    users = []

    def add_user(name, groups_in, is_third_party=False, is_active=True):
        u = User.objects.create_user(f"{tag}-{name}@oracle.test")
        for g in groups_in:
            g.user_set.add(u)
        if is_third_party or not is_active:
            u.is_third_party = is_third_party
            u.is_active = is_active
            u.save()
        world.memberships[u.id] = {g.id for g in groups_in}
        world.user_flags[u.id] = (is_third_party, is_active)
        users.append(u)
        return u

    add_user("member-d1a", [g_d1a])
    add_user("member-d1", [g_d1])  # grant on the default-role folder itself
    add_user("member-leaf", [g_leaf])
    add_user("multi", [g_d1a, g_d2])
    add_user("custom-only", [g_custom])
    add_user("third-party", [g_enclave], is_third_party=True)
    add_user("third-party-misplaced", [g_d1], is_third_party=True)
    add_user("respondent-nested", [g_under_enclave])
    add_user("inactive", [g_d1], is_active=False)
    direct_user = add_user("direct-only", [])  # the machine path

    # --- assignments.
    def add_assignment(principal, role, perimeters, recursive):
        ra = RoleAssignment.objects.create(
            **(
                {"user_group": principal}
                if isinstance(principal, UserGroup)
                else {"user": principal}
            ),
            role=role,
            is_recursive=recursive,
        )
        for p in perimeters:
            ra.perimeter_folders.add(p)
        world.assignments.append(
            (
                "group" if isinstance(principal, UserGroup) else "user",
                principal.id,
                role.id,
                frozenset(p.id for p in perimeters),
                recursive,
            )
        )

    # Guaranteed structure: every group carries at least one grant, so
    # membership and reach coincide the way production provisioning works.
    add_assignment(g_d1, rng.choice(roles), [d1], True)
    add_assignment(g_d1a, rng.choice(roles), [d1a], rng.random() < 0.5)
    add_assignment(g_leaf, view_only, [d1b_leaf], False)
    add_assignment(g_d2, rng.choice(roles), [d2], True)
    add_assignment(g_enclave, rng.choice(roles), [enclave], True)
    add_assignment(g_under_enclave, rng.choice(roles), [under_enclave], True)
    add_assignment(g_custom, rng.choice(roles), [d1], rng.random() < 0.5)
    add_assignment(direct_user, rng.choice(roles), [d1], rng.random() < 0.5)
    # A couple of random extras, including multi-perimeter ones.
    for _ in range(rng.randint(1, 3)):
        principal = rng.choice(groups + [direct_user])
        perimeters = rng.sample(
            domain_folders, min(rng.randint(1, 2), len(domain_folders))
        )
        add_assignment(principal, rng.choice(roles), perimeters, rng.random() < 0.5)

    named = {
        "root": root,
        "d1": d1,
        "d1a": d1a,
        "d1b_leaf": d1b_leaf,
        "d2": d2,
        "enclave": enclave,
    }
    return world, folders, users, permissions, named


# ---------------------------------------------------------------------------
# The properties
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_resolver_matches_oracle(seed, clean_root):
    rng = random.Random(seed)
    world, folders, users, permissions, _named = build_world(
        rng, f"oracle{seed}", clean_root
    )

    for user in users:
        for codename, permission in permissions.items():
            expected = world.covered_folders(user.id, codename)

            # Point check ⟺ oracle, on every folder of the world.
            for fid, folder in folders.items():
                got = RoleAssignment.is_access_allowed(user, permission, folder)
                assert got == (fid in expected), (
                    f"seed={seed} is_access_allowed mismatch: user={user.email} "
                    f"perm={codename} folder={folder.name}: got {got}, "
                    f"oracle says {fid in expected}"
                )

            # Bulk check ⟺ oracle (which also pins point ⟺ bulk equivalence).
            bulk = set(RoleAssignment.get_allowed_folder_ids(user, permission)) & set(
                folders
            )
            assert bulk == expected, (
                f"seed={seed} get_allowed_folder_ids mismatch: user={user.email} "
                f"perm={codename}: extra={bulk - expected}, missing={expected - bulk}"
            )


@pytest.mark.django_db
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_permission_listings_match_oracle(seed, clean_root):
    rng = random.Random(seed)
    world, folders, users, permissions, _named = build_world(
        rng, f"listing{seed}", clean_root
    )

    for user in users:
        expected_codenames = world.all_codenames(user.id) & set(PERMISSION_POOL)

        got_codenames = set(RoleAssignment.get_permissions(user)) & set(PERMISSION_POOL)
        assert got_codenames == expected_codenames, (
            f"seed={seed} get_permissions mismatch for {user.email}: "
            f"extra={got_codenames - expected_codenames}, "
            f"missing={expected_codenames - got_codenames}"
        )

        for codename in PERMISSION_POOL:
            anywhere = RoleAssignment.has_permission_anywhere(user, codename)
            assert anywhere == (codename in expected_codenames), (
                f"seed={seed} has_permission_anywhere mismatch for {user.email} "
                f"/ {codename}: got {anywhere}"
            )


@pytest.mark.django_db
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_focus_and_base_folder_match_oracle(seed, clean_root):
    from core.context import focus_folder_id_var

    rng = random.Random(seed)
    world, folders, users, permissions, named = build_world(
        rng, f"focus{seed}", clean_root
    )
    root_id = clean_root.id

    focus_candidates = [named["d1"], named["d1a"]]
    base_combos = [
        (None, named["d1"]),  # base only, no focus
        (named["d1"], None),  # focus only
        (named["d1"], named["d1a"]),  # base nested under focus
        (named["d1a"], named["d1"]),  # focus nested under base
        (named["d1"], named["d2"]),  # disjoint → empty
    ]

    for user in users:
        for codename, permission in permissions.items():
            # Point checks under focus.
            for focused in focus_candidates:
                token = focus_folder_id_var.set(focused.id)
                try:
                    for fid, folder in folders.items():
                        got = RoleAssignment.is_access_allowed(user, permission, folder)
                        expected = world.point_allowed_focused(
                            user.id, codename, fid, root_id, focused.id
                        )
                        assert got == expected, (
                            f"seed={seed} focused point mismatch: user={user.email} "
                            f"perm={codename} folder={folder.name} "
                            f"focus={focused.name}: got {got}, oracle {expected}"
                        )
                finally:
                    focus_folder_id_var.reset(token)

            # Bulk checks under every focus/base combination.
            for focused, base in base_combos:
                token = (
                    focus_folder_id_var.set(focused.id) if focused is not None else None
                )
                try:
                    bulk = set(
                        RoleAssignment.get_allowed_folder_ids(
                            user, permission, base_folder=base
                        )
                    ) & set(folders)
                    expected = world.clamped_covered_folders(
                        user.id,
                        codename,
                        root_id,
                        focused_id=focused.id if focused is not None else None,
                        base_id=base.id if base is not None else None,
                    )
                    assert bulk == expected, (
                        f"seed={seed} clamped bulk mismatch: user={user.email} "
                        f"perm={codename} focus={focused.name if focused else None} "
                        f"base={base.name if base else None}: "
                        f"extra={bulk - expected}, missing={expected - bulk}"
                    )
                finally:
                    if token is not None:
                        focus_folder_id_var.reset(token)
