"""Deterministic demo dataset, assembled from per-module builders.

Each app contributes builders in a ``demo_builders`` module, discovered at run
time, so enterprise apps can add their own without shadowing community files.
Builders run in registration order (dependencies first) against one shared
:class:`DemoContext`, which carries the target domain, the date anchor and a
seeded RNG. Same checkout, same options, same data.

Entry points: :func:`seed` and the ``seed_demo`` management command.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from importlib import import_module
from pathlib import Path
from typing import ClassVar

from django.apps import apps
from django.conf import settings
from django.db import models, transaction
from django.db.models import ProtectedError
from django.utils.module_loading import module_has_submodule

SEED = 1337
# Bump when the dataset changes enough that loaded demos should be rebuilt.
DEMO_VERSION = 1
# Screenshots pin every date to this anchor so ETAs and due dates never drift.
FROZEN_ANCHOR = date(2026, 3, 2)
# The fictional company every builder writes about; builders use this constant
# rather than spelling the name, so renaming it is a one-line change.
COMPANY = "Halvard Devices"
# The payments subsidiary (DORA, PCI DSS). Product names never include the
# company name: thermostats are "Kelvin", cameras "Lookout", hubs "Keystone".
PAY_ENTITY = f"{COMPANY} Pay"
DEFAULT_DOMAIN = COMPANY
DEFAULT_DESCRIPTION = "Fictional maker of connected home devices, loaded as demo data."


class NotADemoDomain(Exception):
    """A root domain carries the demo name but no manifest: it is user data."""


@dataclass
class DemoContext:
    domain: models.Model
    anchor: date
    frozen: bool
    rng: random.Random
    out: Callable[[str], None] = print
    err: Callable[[str], None] = print
    # Objects one builder hands to the next ("assets", "controls", ...).
    refs: dict = field(default_factory=dict)

    def day(self, offset: int) -> date:
        """A date ``offset`` days from the anchor. Builders never write literals."""
        return self.anchor + timedelta(days=offset)

    @property
    def timestamp_base(self) -> datetime:
        # A live demo is stamped the day before it is seeded, so no row looks
        # created in the future; screenshots keep the frozen anchor.
        day = self.anchor if self.frozen else self.anchor - timedelta(days=1)
        return datetime.combine(day, time(9, 0), tzinfo=UTC)

    def folders(self) -> list:
        return [self.domain, *self.domain.get_sub_folders()]


class DemoBuilder:
    """One module's slice of the demo story.

    ``covers`` maps each model the builder populates to the lookup that reaches
    the demo domain from it; the coverage test counts through it.
    ``stamps`` lists ``(model, filter, order)`` for timestamp pinning: the order
    must be a natural, unique key, never ``id``, or rows shuffle on rebuild.
    Offsets restart per entry, so a model must be stamped by one builder only.
    ``feature_flags`` are switched on by a seed, so the data does not stay hidden.
    """

    name: str = ""
    depends: tuple[str, ...] = ()
    libraries: tuple[str, ...] = ()
    feature_flags: tuple[str, ...] = ()
    covers: ClassVar[dict] = {}

    def build(self, ctx: DemoContext) -> None:
        raise NotImplementedError

    def stamps(self, ctx: DemoContext) -> list[tuple]:
        return []


_registry: dict[str, DemoBuilder] = {}


def register(cls: type[DemoBuilder]) -> type[DemoBuilder]:
    if not cls.name:
        raise ValueError(f"{cls.__name__} has no name")
    if cls.name in _registry:
        raise ValueError(f"demo builder {cls.name!r} registered twice")
    _registry[cls.name] = cls()
    return cls


def discover() -> list:
    """Import every installed app's ``demo_builders`` module, registering its builders."""
    found = []
    for app in apps.get_app_configs():
        if module_has_submodule(app.module, "demo_builders"):
            found.append(import_module(f"{app.name}.demo_builders"))
    return found


def builders(names: list[str] | None = None) -> list[DemoBuilder]:
    """Registered builders in run order, restricted to ``names`` plus dependencies."""
    discover()
    if names is None:
        wanted = set(_registry)
    else:
        unknown = set(names) - set(_registry)
        if unknown:
            raise ValueError(f"unknown demo modules: {', '.join(sorted(unknown))}")
        wanted = set()
        pending = list(names)
        while pending:
            name = pending.pop()
            if name not in wanted:
                wanted.add(name)
                pending.extend(_registry[name].depends)
    ordered, placed = [], set()

    # Registration order, with each dependency placed before its dependents.
    def place(name, chain=()):
        if name in placed:
            return
        if name in chain:
            raise ValueError(f"demo builder cycle: {' -> '.join((*chain, name))}")
        builder = _registry[name]
        for dep in builder.depends:
            if dep not in _registry:
                raise ValueError(f"{name} depends on unknown demo module {dep!r}")
            place(dep, (*chain, name))
        placed.add(name)
        ordered.append(builder)

    for name in _registry:
        if name in wanted:
            place(name)
    return ordered


def demo_domain_filter(name: str) -> dict:
    """The only lookup allowed to find (and flush) a demo domain.

    A bare name filter would match, and cascade-delete, a same-named folder
    anywhere in someone's tree.
    """
    from iam.models import Folder

    return {
        "name": name,
        "parent_folder": Folder.get_root_folder(),
        "content_type": Folder.ContentType.DOMAIN,
    }


def _inside(obj, folder_ids: set) -> bool:
    """Whether ``obj`` belongs to the demo tree: by its folder or, for folderless
    link rows, by every folder-scoped object it points at."""
    if hasattr(obj, "folder_id"):
        return obj.folder_id in folder_ids
    targets = [
        getattr(obj, f.name)
        for f in obj._meta.concrete_fields
        if f.is_relation and f.many_to_one
    ]
    scoped = [t for t in targets if t is not None and hasattr(t, "folder_id")]
    return bool(scoped) and all(t.folder_id in folder_ids for t in scoped)


def _scoped_models() -> list:
    """Concrete, table-owning models carrying a folder (MTI children share the
    parent's rows, and some apps declare models whose table may be absent)."""
    return [
        m
        for m in apps.get_models()
        if hasattr(m, "folder_id")
        and m._meta.managed
        and not m._meta.proxy
        and not m._meta.parents
    ]


def _stored_files(folder_ids: set) -> list[tuple]:
    """(storage, name) for every file attached to a row in the demo folders and
    to no row outside them (a reseed into another domain reuses blobs)."""
    found = []
    for model in _scoped_models():
        file_fields = [
            f for f in model._meta.concrete_fields if isinstance(f, models.FileField)
        ]
        if not file_fields:
            continue
        rows = model._base_manager.filter(folder_id__in=folder_ids)
        outside = model._base_manager.exclude(folder_id__in=folder_ids)
        for row in rows.only(*(f.name for f in file_fields)):
            for f in file_fields:
                value = getattr(row, f.name)
                if value and not outside.filter(**{f.name: value.name}).exists():
                    found.append((value.storage, value.name))
    return found


def _object_ids(folder_ids: set) -> set:
    """Primary keys of every folder-scoped row in the demo tree."""
    ids = set()
    for model in _scoped_models():
        ids.update(
            model._base_manager.filter(folder_id__in=folder_ids).values_list(
                "pk", flat=True
            )
        )
    return ids


def _contents(folder_ids: set) -> set[tuple[str, str]]:
    """(model label, pk) of the demo folders and every folder-scoped row in them."""
    found = {("iam.Folder", str(pk)) for pk in folder_ids}
    for model in _scoped_models():
        label = model._meta.label
        found.update(
            (label, str(pk))
            for pk in model._base_manager.filter(folder_id__in=folder_ids)
            .values_list("pk", flat=True)
            .iterator()
        )
    return found


def _folder_ids(domain) -> set:
    return {domain.pk, *(f.pk for f in domain.get_sub_folders())}


def write_manifest(ctx: DemoContext, before: set[tuple[str, str]]):
    """Record what this run created, keeping earlier entries that still exist.

    Rows that were already there and aren't in the old manifest belong to
    someone else, so a rerun over a domain with user additions never claims them.
    """
    from core.models import DemoManifest

    after = _contents(_folder_ids(ctx.domain))
    manifest = DemoManifest.objects.filter(domain=ctx.domain).first()
    earlier = {tuple(e) for e in manifest.contents} if manifest else set()
    contents = sorted((earlier & after) | (after - before))
    return DemoManifest.objects.update_or_create(
        domain=ctx.domain,
        defaults={
            "version": DEMO_VERSION,
            "anchor": ctx.anchor,
            "contents": [list(e) for e in contents],
        },
    )[0]


def _delete_history(object_ids: set) -> int:
    """Metric history points at objects by id, with no FK to cascade through."""
    from core.models import HistoricalMetric
    from metrology.models import BuiltinMetricSample

    ids = list(object_ids)
    deleted = 0
    for model in (HistoricalMetric, BuiltinMetricSample):
        for start in range(0, len(ids), 500):
            batch = ids[start : start + 500]
            deleted += model.objects.filter(object_id__in=batch).delete()[0]
    return deleted


def flush(name: str = DEFAULT_DOMAIN) -> int:
    """Delete the demo domain and everything under it.

    Django's PROTECT fires even when the protecting rows are themselves part of
    the cascade (kill chain steps, DORA reports, solution subcontractors). Such
    blockers are deleted first, but only when every one of them belongs to the
    demo tree; a single outside reference aborts the whole flush.
    """
    from core.models import DemoManifest
    from iam.models import Folder

    domain = Folder.objects.filter(**demo_domain_filter(name)).first()
    if domain is None:
        return 0
    if not DemoManifest.objects.filter(domain=domain).exists():
        raise NotADemoDomain(f"{name!r} has no demo manifest, refusing to delete it")
    folder_ids = _folder_ids(domain)
    cleared = 0
    with transaction.atomic():
        files = _stored_files(folder_ids)
        object_ids = _object_ids(folder_ids) | folder_ids
        # Deleting rows leaves their files in storage, and every reseed would
        # write suffixed copies next to them; drop them once the delete commits.
        transaction.on_commit(
            lambda: [storage.delete(n) for storage, n in files if storage.exists(n)]
        )
        for _ in range(20):
            try:
                with transaction.atomic():
                    deleted, _ = Folder.objects.filter(pk=domain.pk).delete()
                return cleared + deleted + _delete_history(object_ids)
            except ProtectedError as error:
                blockers = list(error.protected_objects)
                outside = [b for b in blockers if not _inside(b, folder_ids)]
                if outside:
                    raise
                for blocker in blockers:
                    # Base manager: a filtering default manager could hide the row.
                    cleared += (
                        type(blocker)._base_manager.filter(pk=blocker.pk).delete()[0]
                    )
    raise RuntimeError(f"could not flush demo domain {name!r}: protection loop")


def _library_files() -> dict[str, Path]:
    """URN -> file for the shipped libraries, read from each file's header."""
    index = {}
    for path in sorted(Path(settings.LIBRARIES_PATH).glob("*.yaml")):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("urn:"):
                    index[line.split(":", 1)[1].strip()] = path
                    break
    return index


def load_libraries(urns: list[str], ctx_out, ctx_err) -> None:
    from core.models import StoredLibrary

    files = None
    for urn in urns:
        stored = StoredLibrary.objects.filter(urn=urn).order_by("-version").first()
        if stored is None:
            # A fresh test database has no stored libraries; store the shipped one.
            files = files if files is not None else _library_files()
            if urn in files:
                stored, _ = StoredLibrary.store_library_file(files[urn], builtin=True)
        if stored is None:
            ctx_err(f"missing stored library {urn}")
            continue
        error = stored.load()
        ctx_out(f"library {urn.split(':')[-1]}: {error or 'loaded'}")


def freeze_timestamps(ctx: DemoContext, selected: list[DemoBuilder]) -> None:
    """Pin created_at / updated_at to fixed, *distinct* values.

    Both are auto_now_add / auto_now, so without this every run stamps the
    current time and every "Created at" column drifts. A bulk ``update()``
    bypasses ``save()`` and therefore the auto fields.

    The stamps must also be unique per row. ``BaseModelViewSet`` orders by
    ``created_at`` and ``SmartOrderingFilter`` appends ``pk`` as the
    pagination tiebreaker — and ``pk`` is a random UUID. Giving every row
    the same timestamp therefore hands row order to the UUIDs, and lists
    come back shuffled after each database rebuild.

    Every entry is scoped: this can run against a populated database, and an
    unfiltered update() would rewrite timestamps on unrelated records.
    """
    base = ctx.timestamp_base
    for builder in selected:
        for model, scope, order in builder.stamps(ctx):
            fields = {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}
            stamped = {"created_at", "updated_at"} & fields
            if not stamped:
                continue
            for offset, pk in enumerate(
                model.objects.filter(**scope)
                .order_by(*order)
                .values_list("pk", flat=True)
            ):
                stamp = base + timedelta(minutes=offset)
                model.objects.filter(pk=pk).update(**{n: stamp for n in stamped})
    ctx.out(f"timestamps pinned from {base:%Y-%m-%d %H:%M} UTC, staggered")


def seed(
    *,
    domain_name: str = DEFAULT_DOMAIN,
    description: str = DEFAULT_DESCRIPTION,
    modules: list[str] | None = None,
    frozen: bool = False,
    reset: bool = False,
    enable_flags: bool = True,
    out: Callable[[str], None] = print,
    err: Callable[[str], None] = print,
) -> DemoContext:
    from core.models import DemoManifest
    from iam.models import Folder

    selected = builders(modules)
    if reset:
        out(f"flushed {flush(domain_name)} objects under {domain_name}")

    urns = list(dict.fromkeys(urn for b in selected for urn in b.libraries))
    load_libraries(urns, out, err)

    with transaction.atomic():
        # The lookup carries the same constraints as flush(): matching on name
        # alone would seed into a folder the scoped delete never cleans up.
        domain, created = Folder.objects.get_or_create(
            **demo_domain_filter(domain_name),
            defaults={"description": description, "create_iam_groups": True},
        )
        if not created and not DemoManifest.objects.filter(domain=domain).exists():
            raise NotADemoDomain(
                f"{domain_name!r} has no demo manifest, refusing to seed into it"
            )
        before = set() if created else _contents(_folder_ids(domain))
        if created:
            Folder.create_default_ug_and_ra(domain)
        ctx = DemoContext(
            domain=domain,
            anchor=FROZEN_ANCHOR if frozen else date.today(),
            frozen=frozen,
            rng=random.Random(SEED),
            out=out,
            err=err,
        )
        for builder in selected:
            # One stream per builder: adding or reordering builders never
            # shifts the draws, and so the content, of another.
            ctx.rng = random.Random(f"{SEED}:{builder.name}")
            builder.build(ctx)
        freeze_timestamps(ctx, selected)
        write_manifest(ctx, before)
        if enable_flags:
            enable_feature_flags([f for b in selected for f in b.feature_flags], out)
    return ctx


def enable_feature_flags(flags: list[str], out: Callable[[str], None]) -> None:
    """Switch on the modules the demo fills; flags are never switched off."""
    from global_settings.models import GlobalSettings
    from global_settings.utils import (
        clear_feature_flags_cache,
        get_supported_feature_flags,
    )

    settings_row, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    value = dict(settings_row.value or {})
    off = sorted(
        f for f in set(flags) & get_supported_feature_flags() if not value.get(f)
    )
    if not off:
        return
    value.update(dict.fromkeys(off, True))
    settings_row.value = value
    settings_row.save()
    transaction.on_commit(clear_feature_flags_cache)
    out(f"feature flags enabled: {', '.join(off)}")
