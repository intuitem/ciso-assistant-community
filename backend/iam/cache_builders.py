"""
cache_builders.py

Snapshot cache builders + registration for IAM and Folder models.

Design goals:
- No circular imports: DO NOT import iam.models at runtime.
- Import-time registration is DB-free (only CacheRegistry.register calls).
- Actual DB work happens only when CacheRegistry.hydrate_all() rebuilds a snapshot.
- Snapshots are immutable-ish via MappingProxyType + frozenset/tuple.
- Manual invalidation is expected (no signals). Be careful with M2M changes.

Keys:
- folders
- iam.roles
- iam.groups
- iam.assignments
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from types import MappingProxyType
from typing import (
    Dict,
    FrozenSet,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from django.apps import apps
from django.contrib.auth.models import Permission
from django.db.models import Prefetch

from iam.snapshot_cache import CacheRegistry

# Only for type-checkers (no runtime import => no circular import)
if TYPE_CHECKING:
    from iam.models import Folder  # noqa: F401


# --------------------------------------------------------------------
# Cache keys
# --------------------------------------------------------------------
FOLDER_CACHE_KEY = "folders"
IAM_ROLES_KEY = "iam.roles"
IAM_GROUPS_KEY = "iam.groups"
IAM_ASSIGNMENTS_KEY = "iam.assignments"


class CacheNotReadyError(RuntimeError):
    """Raised when IAM caches are accessed before being marked ready."""


cache_ready: bool = False


def set_cache_ready(*, ready: bool = True) -> None:
    """Allow callers to toggle whether caches may touch the DB."""
    global cache_ready
    cache_ready = bool(ready)


def is_cache_ready() -> bool:
    return cache_ready


def _ensure_cache_ready() -> None:
    if not cache_ready:
        raise CacheNotReadyError("IAM caches are not ready to run DB queries")


# --------------------------------------------------------------------
# Folder snapshot cache
# --------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FolderCacheState:
    folders: Mapping[uuid.UUID, "Folder"]
    parent_map: Mapping[uuid.UUID, Optional[uuid.UUID]]
    children_map: Mapping[Optional[uuid.UUID], Tuple[uuid.UUID, ...]]
    depth_map: Mapping[uuid.UUID, int]
    root_ids: Tuple[uuid.UUID, ...]
    root_folder_id: Optional[uuid.UUID]


def build_folder_cache_state() -> FolderCacheState:
    """
    Build immutable folder tree snapshot.
    """
    Folder = apps.get_model("iam", "Folder")

    folders = list(
        Folder.objects.all()
        .select_related("parent_folder")
        .only("id", "name", "parent_folder_id", "content_type", "builtin")
    )

    folders_by_id: Dict[uuid.UUID, "Folder"] = {folder.id: folder for folder in folders}
    parent_map: Dict[uuid.UUID, Optional[uuid.UUID]] = {
        folder.id: folder.parent_folder_id for folder in folders
    }

    children_map: defaultdict[Optional[uuid.UUID], List[uuid.UUID]] = defaultdict(list)
    root_folder_id: Optional[uuid.UUID] = None
    for folder in folders:
        children_map[folder.parent_folder_id].append(folder.id)
        if root_folder_id is None and folder.content_type == Folder.ContentType.ROOT:
            root_folder_id = folder.id

    # Stable ordering for traversal
    for child_list in children_map.values():
        child_list.sort(key=lambda fid: folders_by_id[fid].name.casefold())

    depth_map: Dict[uuid.UUID, int] = {}

    def _depth(current_id: uuid.UUID) -> int:
        if current_id in depth_map:
            return depth_map[current_id]
        parent_id = parent_map[current_id]
        depth_val = 0 if parent_id is None else _depth(parent_id) + 1
        depth_map[current_id] = depth_val
        return depth_val

    for folder_id in folders_by_id:
        _depth(folder_id)

    return FolderCacheState(
        folders=MappingProxyType(folders_by_id),
        parent_map=MappingProxyType(parent_map),
        children_map=MappingProxyType(
            {parent: tuple(children) for parent, children in children_map.items()}
        ),
        depth_map=MappingProxyType(depth_map),
        root_ids=tuple(children_map.get(None, ())),
        root_folder_id=root_folder_id,
    )


def invalidate_folders_cache() -> Optional[int]:
    return CacheRegistry.invalidate(FOLDER_CACHE_KEY)


def ensure_cached_folder(state: FolderCacheState, folder_id: uuid.UUID) -> "Folder":
    if folder_id not in state.folders:
        raise KeyError(f"Folder {folder_id} is not cached")
    return state.folders[folder_id]


def path_ids_from_root(
    state: FolderCacheState, folder_id: uuid.UUID
) -> Tuple[uuid.UUID, ...]:
    ensure_cached_folder(state, folder_id)
    path: List[uuid.UUID] = []
    current = folder_id
    while current is not None:
        path.append(current)
        current = state.parent_map.get(current)
    path.reverse()
    return tuple(path)


def iter_descendant_ids(
    state: FolderCacheState, start_id: uuid.UUID, *, include_start: bool
) -> Iterator[uuid.UUID]:
    """
    Yield descendant folder ids using the cached tree.
    Depth-first traversal, stable order.
    """
    stack: List[Tuple[uuid.UUID, bool]] = [(start_id, include_start)]
    while stack:
        current, include_current = stack.pop()
        if include_current:
            yield current
        for child in reversed(state.children_map.get(current, ())):
            stack.append((child, True))


def get_sub_folders_cached(folder_id: uuid.UUID) -> Iterator["Folder"]:
    state = get_folder_state()
    ensure_cached_folder(state, folder_id)
    for descendant_id in iter_descendant_ids(state, folder_id, include_start=False):
        yield state.folders[descendant_id]


def get_parent_folders_cached(folder_id: uuid.UUID) -> Iterator["Folder"]:
    state = get_folder_state()
    ensure_cached_folder(state, folder_id)
    current = state.parent_map.get(folder_id)
    while current is not None:
        yield state.folders[current]
        current = state.parent_map.get(current)


def get_folder_path(
    folder_id: uuid.UUID, *, include_root: bool = False
) -> List["Folder"]:
    """
    Return the ordered list of folders from root to the requested folder.
    """
    state = get_folder_state()
    ids = path_ids_from_root(state, folder_id)
    folders = [state.folders[fid] for fid in ids]
    if include_root:
        return folders
    return folders[1:] if len(folders) > 1 else folders


# --------------------------------------------------------------------
# IAM Roles cache: role_id -> permission codenames
# --------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RolesCacheState:
    role_permissions: Mapping[uuid.UUID, FrozenSet[str]]


def build_roles_cache_state() -> RolesCacheState:
    Role = apps.get_model("iam", "Role")

    roles = (
        Role.objects.all()
        .only("id")
        .prefetch_related(
            Prefetch(
                "permissions",
                queryset=Permission.objects.only("codename"),
            )
        )
    )

    role_permissions: Dict[uuid.UUID, FrozenSet[str]] = {}
    for role in roles:
        role_permissions[role.id] = frozenset(
            p.codename for p in role.permissions.all() if p.codename
        )

    return RolesCacheState(role_permissions=MappingProxyType(role_permissions))


def invalidate_roles_cache() -> Optional[int]:
    return CacheRegistry.invalidate(IAM_ROLES_KEY)


# --------------------------------------------------------------------
# IAM Groups cache: user_id -> group_ids (M2M)
# NOTE: you said you'll manage M2M later; keeping the builder here anyway.
# --------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GroupsCacheState:
    user_group_ids: Mapping[uuid.UUID, FrozenSet[uuid.UUID]]


def build_groups_cache_state() -> GroupsCacheState:
    User = apps.get_model("iam", "User")

    through = User.user_groups.through  # type: ignore[attr-defined]
    rows = through.objects.all().values_list("user_id", "usergroup_id")

    mapping: Dict[uuid.UUID, set[uuid.UUID]] = {}
    for user_id, group_id in rows:
        mapping.setdefault(user_id, set()).add(group_id)

    frozen: Dict[uuid.UUID, FrozenSet[uuid.UUID]] = {
        u: frozenset(gids) for u, gids in mapping.items()
    }
    return GroupsCacheState(user_group_ids=MappingProxyType(frozen))


def invalidate_groups_cache() -> Optional[int]:
    return CacheRegistry.invalidate(IAM_GROUPS_KEY)


# --------------------------------------------------------------------
# IAM Assignments cache: by user / by group
# --------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AssignmentLite:
    role_id: uuid.UUID
    is_recursive: bool
    perimeter_folder_ids: FrozenSet[uuid.UUID]


@dataclass(frozen=True, slots=True)
class AssignmentsCacheState:
    by_user: Mapping[uuid.UUID, Tuple[AssignmentLite, ...]]
    by_group: Mapping[uuid.UUID, Tuple[AssignmentLite, ...]]


def build_assignments_cache_state() -> AssignmentsCacheState:
    RoleAssignment = apps.get_model("iam", "RoleAssignment")

    ras = (
        RoleAssignment.objects.all()
        .only("id", "user_id", "user_group_id", "role_id", "is_recursive")
        .prefetch_related(
            Prefetch(
                "perimeter_folders",
                queryset=RoleAssignment.perimeter_folders.rel.model.objects.only("id"),
            )
        )
    )

    by_user: Dict[uuid.UUID, List[AssignmentLite]] = {}
    by_group: Dict[uuid.UUID, List[AssignmentLite]] = {}

    for ra in ras:
        lite = AssignmentLite(
            role_id=ra.role_id,
            is_recursive=ra.is_recursive,
            perimeter_folder_ids=frozenset(pf.id for pf in ra.perimeter_folders.all()),
        )
        if ra.user_id:
            by_user.setdefault(ra.user_id, []).append(lite)
        if ra.user_group_id:
            by_group.setdefault(ra.user_group_id, []).append(lite)

    return AssignmentsCacheState(
        by_user=MappingProxyType({k: tuple(v) for k, v in by_user.items()}),
        by_group=MappingProxyType({k: tuple(v) for k, v in by_group.items()}),
    )


def invalidate_assignments_cache() -> Optional[int]:
    return CacheRegistry.invalidate(IAM_ASSIGNMENTS_KEY)


# --------------------------------------------------------------------
# Registration (DB-free)
# --------------------------------------------------------------------
def register_all_caches(*, allow_replace: bool = False) -> None:
    """
    Optional explicit registration entrypoint, useful for AppConfig.ready().
    Safe to call multiple times.
    """
    # If your CacheRegistry.register does NOT accept allow_replace,
    # just remove the kwarg and keep idempotency in CacheRegistry itself.
    try:
        CacheRegistry.register(
            FOLDER_CACHE_KEY, build_folder_cache_state, allow_replace=allow_replace
        )
        CacheRegistry.register(
            IAM_ROLES_KEY, build_roles_cache_state, allow_replace=allow_replace
        )
        CacheRegistry.register(
            IAM_GROUPS_KEY, build_groups_cache_state, allow_replace=allow_replace
        )
        CacheRegistry.register(
            IAM_ASSIGNMENTS_KEY,
            build_assignments_cache_state,
            allow_replace=allow_replace,
        )
    except TypeError:
        # Backward-compatible: register() without allow_replace
        CacheRegistry.register(FOLDER_CACHE_KEY, build_folder_cache_state)
        CacheRegistry.register(IAM_ROLES_KEY, build_roles_cache_state)
        CacheRegistry.register(IAM_GROUPS_KEY, build_groups_cache_state)
        CacheRegistry.register(IAM_ASSIGNMENTS_KEY, build_assignments_cache_state)


# Import-time registration (DB-free).
# If you prefer explicit registration, delete these lines and call register_all_caches()
# in iam/apps.py -> IamConfig.ready().
CacheRegistry.register(FOLDER_CACHE_KEY, build_folder_cache_state)
CacheRegistry.register(IAM_ROLES_KEY, build_roles_cache_state)
CacheRegistry.register(IAM_GROUPS_KEY, build_groups_cache_state)
CacheRegistry.register(IAM_ASSIGNMENTS_KEY, build_assignments_cache_state)


def get_folder_state(*, force_reload: bool = False) -> FolderCacheState:
    """
    Convenience accessor for folder cache state.
    """
    _ensure_cache_ready()
    state_map = CacheRegistry.hydrate_all(force_reload=force_reload)
    return state_map[FOLDER_CACHE_KEY]


def get_roles_state(*, force_reload: bool = False) -> RolesCacheState:
    _ensure_cache_ready()
    state_map = CacheRegistry.hydrate_all(force_reload=force_reload)
    return state_map[IAM_ROLES_KEY]


def get_groups_state(*, force_reload: bool = False) -> GroupsCacheState:
    _ensure_cache_ready()
    state_map = CacheRegistry.hydrate_all(force_reload=force_reload)
    return state_map[IAM_GROUPS_KEY]


def get_assignments_state(*, force_reload: bool = False) -> AssignmentsCacheState:
    _ensure_cache_ready()
    state_map = CacheRegistry.hydrate_all(force_reload=force_reload)
    return state_map[IAM_ASSIGNMENTS_KEY]


__all__ = [
    "FOLDER_CACHE_KEY",
    "IAM_ROLES_KEY",
    "IAM_GROUPS_KEY",
    "IAM_ASSIGNMENTS_KEY",
    "CacheNotReadyError",
    "is_cache_ready",
    "set_cache_ready",
    "FolderCacheState",
    "RolesCacheState",
    "GroupsCacheState",
    "AssignmentLite",
    "AssignmentsCacheState",
    "build_folder_cache_state",
    "build_roles_cache_state",
    "build_groups_cache_state",
    "build_assignments_cache_state",
    "register_all_caches",
    # helpers used from models.py
    "get_sub_folders_cached",
    "get_parent_folders_cached",
    "get_folder_path",
    "invalidate_folders_cache",
    "invalidate_roles_cache",
    "invalidate_groups_cache",
    "invalidate_assignments_cache",
    "iter_descendant_ids",
    "get_folder_state",
    "get_roles_state",
    "get_groups_state",
    "get_assignments_state",
]
