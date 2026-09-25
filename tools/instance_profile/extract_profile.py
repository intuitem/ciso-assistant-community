import json
from collections import Counter, defaultdict

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Count, Max
from django.db.models.functions import Length

OUT = "/tmp/instance_profile.json"
SKIP_APPS = {"auditlog", "django_structlog"}


def dist(values, zeros=0):
    values = sorted([0] * zeros + list(values))
    if not values:
        return None
    pick = lambda q: values[min(len(values) - 1, int(q * len(values)))]
    return {
        "n": len(values),
        "zeros": zeros + sum(1 for v in values[zeros:] if v == 0),
        "min": values[0],
        "p50": pick(0.5),
        "p90": pick(0.9),
        "p99": pick(0.99),
        "max": values[-1],
        "mean": round(sum(values) / len(values), 2),
        "top": values[-5:][::-1],
    }


def depth(edges, nodes):
    children = defaultdict(list)
    has_parent = set()
    for child, parent in edges:
        children[parent].append(child)
        has_parent.add(child)
    roots = [n for n in nodes if n not in has_parent]
    levels, seen, frontier, level = Counter(), set(), roots, 0
    while frontier:
        levels[level] = len(frontier)
        seen.update(frontier)
        frontier = [c for p in frontier for c in children[p] if c not in seen]
        level += 1
    return {
        "roots": len(roots),
        "max_depth": level - 1,
        "per_level": dict(levels),
        "unreached": len(nodes) - len(seen),
        "branching": dist([len(children[n]) for n in nodes]),
    }


def has_urn(m):
    return any(f.name == "urn" for f in m._meta.concrete_fields)


def by_urn(qs, path):
    rows = (
        qs.exclude(**{path: None})
        .values(path)
        .annotate(n=Count("pk"))
        .order_by("-n")[:100]
    )
    return {r[path]: r["n"] for r in rows}


def own_models():
    for m in apps.get_models():
        cfg = m._meta.app_config
        if cfg.label in SKIP_APPS or "site-packages" in cfg.path:
            continue
        if m._meta.proxy or not m._meta.managed:
            continue
        yield m


def profile_model(m):
    qs = m._base_manager.all()
    total = qs.count()
    out = {"count": total, "fk": {}, "m2m": {}, "choices": {}, "text": {}}
    if not total:
        return out
    if has_urn(m):
        out["with_urn"] = qs.exclude(urn=None).count()
    for f in m._meta.concrete_fields:
        if f.many_to_one or f.one_to_one:
            per_parent = (
                qs.exclude(**{f.attname: None})
                .values(f.attname)
                .annotate(n=Count("pk"))
                .values_list("n", flat=True)
            )
            entry = {
                "to": f.related_model._meta.label,
                "null": qs.filter(**{f.attname: None}).count(),
                "children_per_parent": dist(per_parent),
            }
            if has_urn(f.related_model):
                entry["by_urn"] = by_urn(qs, f.name + "__urn")
            if f.related_model is m:
                pairs = qs.exclude(**{f.attname: None}).values_list("pk", f.attname)
                entry["tree"] = depth(pairs, set(qs.values_list("pk", flat=True)))
            out["fk"][f.name] = entry
        elif f.choices:
            out["choices"][f.name] = dict(
                Counter(qs.values_list(f.attname, flat=True)).most_common(30)
            )
        elif isinstance(f, models.TextField):
            out["text"][f.name] = dist(
                qs.annotate(_l=Length(f.attname))
                .exclude(_l=None)
                .values_list("_l", flat=True)
            )
    for f in m._meta.many_to_many:
        through = f.remote_field.through
        src = f.m2m_field_name()
        dst = f.m2m_reverse_field_name()
        tq = through._base_manager.all()
        per_src = list(
            tq.values(src).annotate(n=Count("pk")).values_list("n", flat=True)
        )
        per_dst = list(
            tq.values(dst).annotate(n=Count("pk")).values_list("n", flat=True)
        )
        entry = {
            "to": f.related_model._meta.label,
            "edges": tq.count(),
            "per_source": dist(per_src, zeros=total - len(per_src)),
            "per_target": dist(per_dst),
        }
        if has_urn(f.related_model):
            entry["by_urn"] = by_urn(tq, dst + "__urn")
        if f.related_model is m:
            pairs = tq.values_list(src + "_id", dst + "_id")
            entry["tree"] = depth(pairs, set(qs.values_list("pk", flat=True)))
        out["m2m"][f.name] = entry
    return out


def library_urns():
    LoadedLibrary = apps.get_model("core", "LoadedLibrary")
    return sorted(LoadedLibrary.objects.values_list("urn", "version"))


def migration_heads():
    rows = MigrationRecorder.Migration.objects.values("app").annotate(last=Max("name"))
    return {r["app"]: r["last"] for r in rows}


profile = {
    "version": settings.VERSION,
    "build": settings.BUILD,
    "database": settings.DATABASES["default"]["ENGINE"],
    "migrations": migration_heads(),
    "libraries": library_urns(),
    "models": {},
    "errors": {},
}
for m in own_models():
    try:
        profile["models"][m._meta.label] = profile_model(m)
    except Exception as e:
        profile["errors"][m._meta.label] = type(e).__name__

with open(OUT, "w") as fh:
    json.dump(profile, fh, indent=1, default=str)

print(f"wrote {OUT}: {len(profile['models'])} models, {len(profile['errors'])} errors")
