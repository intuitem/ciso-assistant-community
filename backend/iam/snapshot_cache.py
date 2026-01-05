"""
Generic versioned snapshot caching logic for Django with:
- One DB table for all cache versions
- OR import-time self-registration via CacheRegistry.register(...)
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Dict, Generic, Mapping, Optional, Sequence, Tuple, TypeVar

from django.db import models, transaction
from django.db.models import F
from django.db.utils import OperationalError, ProgrammingError

T = TypeVar("T")


# -----------------------------
# DB model: one row per cache key
# -----------------------------
class CacheVersion(models.Model):
    """
    One row per cache namespace key.
    Example keys: "folders", "iam.roles", "iam.memberships", "iam.assignments"
    """

    key = models.CharField(max_length=100, primary_key=True)
    version = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cache version"
        verbose_name_plural = "Cache versions"

    def __str__(self) -> str:
        return f"{self.key}={self.version}"


# -----------------------------
# Version store (fetch-all + ensure + atomic bump)
# -----------------------------
@dataclass(frozen=True, slots=True)
class VersionSnapshot:
    versions: Mapping[str, int]


class VersionStore:
    """
    Fetch all cache versions, creating missing keys if needed.
    """

    @staticmethod
    def ensure_and_get_versions(keys: Sequence[str]) -> VersionSnapshot:
        """
        Return versions for the provided keys, creating rows when missing.

        In the common case (all keys exist) this executes a single SELECT.
        If some keys are missing we insert them and re-query.
        """
        if not keys:
            return VersionSnapshot(versions={})

        rows = CacheVersion.objects.filter(key__in=keys).values_list("key", "version")
        versions = {k: int(v) for k, v in rows}

        missing = [k for k in keys if k not in versions]
        if missing:
            CacheVersion.objects.bulk_create(
                [CacheVersion(key=k, version=1) for k in missing],
                ignore_conflicts=True,
            )
            rows = CacheVersion.objects.filter(key__in=keys).values_list(
                "key", "version"
            )
            versions = {k: int(v) for k, v in rows}

        return VersionSnapshot(versions=versions)

    @staticmethod
    def bump(key: str) -> int:
        with transaction.atomic():
            obj, _ = CacheVersion.objects.select_for_update().get_or_create(
                key=key, defaults={"version": 1}
            )
            obj.version = F("version") + 1
            obj.save(update_fields=["version"])
            obj.refresh_from_db(fields=["version"])
            return int(obj.version)


# -----------------------------
# Versioned in-process snapshot cache
# -----------------------------
@dataclass(frozen=True, slots=True)
class _Snapshot(Generic[T]):
    version: int
    value: T


class VersionedSnapshotCache(Generic[T]):
    """
    Process-local immutable snapshot cache keyed by a DB version row in CacheVersion.
    """

    def __init__(self, *, key: str, builder: Callable[[], T]):
        self.key = key
        self._builder = builder
        self._snapshot: Optional[_Snapshot[T]] = None

    def get(self, versions: Mapping[str, int], *, force_reload: bool = False) -> T:
        """
        Return snapshot, rebuilding if version differs.

        IMPORTANT: We fail loudly if the key is missing from versions, because it indicates
        the CacheVersion row was not created (hydrate_all must run first).
        """
        if self.key not in versions:
            raise KeyError(
                f"Cache key '{self.key}' missing from CacheVersion table. "
                f"Ensure CacheRegistry.hydrate_all() ran before accessing this cache."
            )

        v = int(versions[self.key])

        if (
            not force_reload
            and self._snapshot is not None
            and self._snapshot.version == v
        ):
            return self._snapshot.value

        value = self._builder()
        self._snapshot = _Snapshot(version=v, value=value)
        return value

    def invalidate(self) -> Optional[int]:
        """
        Best-effort invalidation: if the CacheVersion table isn't available yet
        (e.g. during migrations), do not crash the caller.
        """
        try:
            new_v = VersionStore.bump(self.key)
        except (OperationalError, ProgrammingError):
            # Still clear local snapshot so this process rebuilds next time it can.
            self._snapshot = None
            return None

        self._snapshot = None
        return new_v

    def clear_local(self) -> None:
        self._snapshot = None


class CacheRegistry:
    """
    Global registry for caches.
    - Register caches at import time via CacheRegistry.register(key, builder) (DB-free)
    - At runtime, call hydrate_all() to ensure rows exist, fetch versions once, and hydrate all caches.
    """

    _caches: Dict[str, VersionedSnapshotCache] = {}
    _last_versions: Optional[Mapping[str, int]] = None
    _last_fetched_at: Optional[float] = None
    _MIN_FETCH_INTERVAL_MS = 500.0

    @classmethod
    def register(
        cls,
        key: str,
        builder: Callable[[], object],
        *,
        allow_replace: bool = False,
    ) -> None:
        """
        Register a single cache (DB-free). Safe to call at import time.

        If key already exists:
          - allow_replace=False -> no-op
          - allow_replace=True  -> replace cache/builder
        """
        if key in cls._caches and not allow_replace:
            return

        cls._caches[key] = VersionedSnapshotCache(key=key, builder=builder)

    @classmethod
    def hydrate_all(cls, *, force_reload: bool = False) -> Mapping[str, object]:
        """
        Ensure version rows exist, fetch ALL versions once, and hydrate all registered caches.
        Returns {key: snapshot_value}.
        """
        if not cls._caches:
            raise RuntimeError(
                "No caches registered. Call CacheRegistry.register(...) before hydrate_all()."
            )

        keys = tuple(cls._caches.keys())

        now = time.monotonic() * 1000.0
        versions: Mapping[str, int] | None = None
        if (
            not force_reload
            and cls._last_versions is not None
            and cls._last_fetched_at is not None
            and now - cls._last_fetched_at < cls._MIN_FETCH_INTERVAL_MS
        ):
            versions = cls._last_versions

        if versions is None:
            versions = VersionStore.ensure_and_get_versions(list(keys)).versions
            cls._last_versions = versions
            cls._last_fetched_at = now

        # Hydrate each cache
        return {
            key: cache.get(versions, force_reload=force_reload)
            for key, cache in cls._caches.items()
        }

    @classmethod
    def get_cache(cls, key: str) -> VersionedSnapshotCache:
        try:
            return cls._caches[key]
        except KeyError as e:
            raise KeyError(f"Unknown cache key: {key}") from e

    @classmethod
    def invalidate(cls, key: str) -> Optional[int]:
        return cls.get_cache(key).invalidate()

    @classmethod
    def keys(cls) -> Tuple[str, ...]:
        return tuple(cls._caches.keys())

    @classmethod
    def clear(cls) -> None:
        """
        Useful for tests: clears registered caches.
        """
        cls._caches.clear()
