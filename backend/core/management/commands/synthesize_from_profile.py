import json
import random
import secrets
import uuid
from collections import Counter
from datetime import timedelta
from graphlib import CycleError, TopologicalSorter
from itertools import pairwise

import structlog
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.utils import timezone

logger = structlog.get_logger(__name__)

SKIP = {
    "core.StoredLibrary",
    "core.LoadedLibrary",
    "core.RiskMatrix",
    "core.Framework",
    "core.RequirementNode",
    "core.RequirementMappingSet",
    "core.RequirementMapping",
    "core.Comment",
    "global_settings.GlobalSettings",
    "iam.PersonalAccessToken",
    "metrology.BuiltinMetricSample",
}
DERIVED = {"core.RequirementAssessment", "core.Answer", "core.Actor"}
SKIP_M2M = {"iam.Folder.descendants"}
LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor. "
)


def has_urn(m):
    return any(f.name == "urn" for f in m._meta.concrete_fields)


def own_rows(m):
    qs = m._base_manager.all()
    return qs.filter(urn=None) if has_urn(m) else qs


def choice_value(f, key):
    return None if key in ("null", "None") else f.to_python(key)


def interp(d, q):
    points = [
        (0, d["min"]),
        (0.5, d["p50"]),
        (0.9, d["p90"]),
        (0.99, d["p99"]),
        (1, d["max"]),
    ]
    for (q0, v0), (q1, v1) in pairwise(points):
        if q <= q1:
            return round(v0 + (v1 - v0) * (q - q0) / ((q1 - q0) or 1))
    return d["max"]


def sample_counts(d, n, rng):
    if not d or n <= 0:
        return [0] * max(n, 0)
    top = [v for v in d["top"] if v > 0][:n]
    values = top + [interp(d, rng.random()) for _ in range(n - len(top))]
    rng.shuffle(values)
    return values


class Command(BaseCommand):
    help = "Generate synthetic data matching an instance profile produced by tools/instance_profile/extract_profile.py"

    def add_arguments(self, parser):
        parser.add_argument("profile")
        parser.add_argument("--scale", type=float, default=1.0)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--skip-libraries", action="store_true")

    def handle(self, *args, **options):
        with open(options["profile"]) as fh:
            self.profile = json.load(fh)
        self.scale = options["scale"]
        self.rng = random.Random(options["seed"])
        self.token = secrets.token_hex(3)
        self.errors = Counter()
        self.report = {}
        if not options["skip_libraries"]:
            self.load_libraries()
        order = self.generation_order()
        self.pending = set(order)
        self.deferred = []
        self.created = {}
        for label in order:
            if label in DERIVED:
                self.reshape_choices(label)
            else:
                self.generate(label)
            self.pending.discard(label)
        self.fill_deferred()
        for label in order:
            self.link_m2m(label)
        self.print_report(order)

    def model(self, label):
        try:
            return apps.get_model(label)
        except LookupError:
            return None

    def load_libraries(self):
        StoredLibrary = apps.get_model("core", "StoredLibrary")
        LoadedLibrary = apps.get_model("core", "LoadedLibrary")
        loaded = set(LoadedLibrary.objects.values_list("urn", flat=True))
        for urn, version in self.profile["libraries"]:
            if urn in loaded:
                continue
            stored = StoredLibrary.objects.filter(urn=urn).order_by("-version").first()
            if stored is None:
                self.stdout.write(
                    self.style.WARNING(f"library missing locally: {urn} v{version}")
                )
                continue
            if stored.version != version:
                self.stdout.write(
                    self.style.WARNING(
                        f"library version differs: {urn} profile v{version}, local v{stored.version}"
                    )
                )
            error = stored.load()
            if error:
                self.stdout.write(
                    self.style.WARNING(f"library not loaded: {urn}: {error}")
                )
            loaded = set(LoadedLibrary.objects.values_list("urn", flat=True))
        self.stdout.write(f"libraries loaded: {len(loaded)}")

    def generation_order(self):
        labels = [
            label
            for label, entry in self.profile["models"].items()
            if entry["count"] and label not in SKIP and self.model(label)
        ]
        wanted = set(labels)

        def deps(required_only):
            graph = {}
            for label in labels:
                m = self.model(label)
                graph[label] = {
                    f.related_model._meta.label
                    for f in m._meta.concrete_fields
                    if f.is_relation
                    and f.related_model is not m
                    and f.related_model._meta.label in wanted
                    and not (required_only and f.null)
                }
            return graph

        for required_only in (False, True):
            try:
                return list(TopologicalSorter(deps(required_only)).static_order())
            except CycleError:
                continue
        return labels

    def generate(self, label):
        m = self.model(label)
        entry = self.profile["models"][label]
        library_rows = entry.get("with_urn")
        if library_rows is None and has_urn(m):
            library_rows = m._base_manager.exclude(urn=None).count()
        own = max(0, entry["count"] - (library_rows or 0))
        target = round(own * self.scale)
        existing = own_rows(m).count()
        n = target - existing
        self.report[label] = [target, existing, 0]
        if n <= 0:
            return
        plans = self.field_plans(m, entry, n)
        tree = self.tree_plan(m, entry, n)
        by_level = {}
        roots = list(own_rows(m).values_list("pk", flat=True)[:50])
        weights = {}
        created = self.created.setdefault(label, [])
        for i in range(n):
            values = {name: plan[i] for name, plan in plans.items()}
            if tree:
                field, levels, branching = tree
                level = levels[i]
                parents = by_level.get(level - 1) or ([] if level == 0 else roots)
                if level - 1 not in weights and parents:
                    weights[level - 1] = [
                        w or 0.001
                        for w in sample_counts(branching, len(parents), self.rng)
                    ]
                values[field] = (
                    self.rng.choices(parents, weights[level - 1])[0]
                    if parents
                    else None
                )
            obj = self.save_with_retries(m, values, plans)
            if obj is None:
                continue
            self.report[label][2] += 1
            created.append(obj.pk)
            if tree:
                by_level.setdefault(tree[1][i], []).append(obj.pk)
        self.stdout.write(f"{label}: +{self.report[label][2]}/{n}")

    def save_with_retries(self, m, values, plans, attempts=3):
        label = m._meta.label
        fk_names = [
            f.attname
            for f in m._meta.concrete_fields
            if f.is_relation and f.attname in plans
        ]
        for attempt in range(attempts):
            obj = m(**values)
            try:
                with transaction.atomic():
                    obj.save()
                    self.after_create(obj)
                return obj
            except Exception as e:
                if attempt < attempts - 1 and fk_names:
                    for name in fk_names:
                        values[name] = self.rng.choice(plans[name])
                    continue
                key = (label, type(e).__name__)
                if not self.errors[key]:
                    logger.warning("synthesize_row_failed", model=label, error=e)
                self.errors[key] += 1
        return None

    def after_create(self, obj):
        if obj._meta.label == "core.ComplianceAssessment":
            obj.create_requirement_assessments()

    def field_plans(self, m, entry, n):
        plans = {}
        total = entry["count"]
        unique = set(getattr(m, "fields_to_check", []))
        for group in m._meta.unique_together:
            unique.update(group)
        for constraint in m._meta.constraints:
            if (
                isinstance(constraint, models.UniqueConstraint)
                and constraint.condition is None
            ):
                unique.update(constraint.fields)
        offset = m._base_manager.count()
        for f in m._meta.concrete_fields:
            if (
                f.primary_key
                or getattr(f, "auto_now", False)
                or getattr(f, "auto_now_add", False)
            ):
                continue
            if isinstance(f, models.GeneratedField):
                continue
            if f.is_relation:
                if f.related_model is m:
                    continue
                fk = entry["fk"].get(f.name)
                if f.null and f.related_model._meta.label in self.pending:
                    self.deferred.append((m, f, fk, total))
                    continue
                if fk or not f.null:
                    plans[f.attname] = self.fk_plan(f, fk, total, n)
                continue
            if f.choices and f.name in entry["choices"]:
                plans[f.attname] = self.choice_plan(
                    m, f, entry["choices"][f.name], total, n
                )
                continue
            if f.name == "urn":
                continue
            if f.name in unique:
                value = self.unique_filler(f, m._meta.model_name, offset)
                if value is not None:
                    plans[f.attname] = [value(i) for i in range(n)]
                    continue
            value = self.filler(
                f, entry.get("text", {}).get(f.name), m._meta.model_name
            )
            if value is not None:
                plans[f.attname] = [value(i) for i in range(n)]
        return plans

    def fk_plan(self, f, fk, total, n):
        pool = list(f.related_model._base_manager.values_list("pk", flat=True))
        n_null = round(n * fk["null"] / total) if fk and f.null else 0
        n_linked = n - n_null
        if f.one_to_one:
            used = set(f.model._base_manager.values_list(f.attname, flat=True))
            free = [p for p in pool if p not in used]
            ids = self.rng.sample(free, min(len(free), n_linked))
            return ids + [None] * (n - len(ids))
        ids = []
        if fk and fk.get("by_urn"):
            urn_map = dict(
                f.related_model._base_manager.filter(
                    urn__in=list(fk["by_urn"])
                ).values_list("urn", "pk")
            )
            for urn, count in fk["by_urn"].items():
                if urn in urn_map:
                    ids += [urn_map[urn]] * round(count * n / total)
        if len(ids) < n_linked and pool:
            d = fk["children_per_parent"] if fk else None
            k = (
                min(len(pool), max(1, round(d["n"] * n / total)))
                if d
                else min(len(pool), 1 + n // 10)
            )
            parents = self.rng.sample(pool, k)
            counts = sample_counts(d, k, self.rng) if d else [1] * k
            ids += [p for p, c in zip(parents, counts) for _ in range(c)]
            while len(ids) < n_linked:
                ids.append(self.rng.choice(parents))
        self.rng.shuffle(ids)
        ids = ids[:n_linked] + [None] * (n - min(len(ids), n_linked))
        self.rng.shuffle(ids)
        return ids

    def choice_plan(self, m, f, distribution, total, n):
        wanted = Counter({choice_value(f, k): v for k, v in distribution.items()})
        existing = Counter(own_rows(m).values_list(f.attname, flat=True))
        remaining = Counter(
            {k: max(0, round(v * self.scale) - existing[k]) for k, v in wanted.items()}
        )
        values = list(remaining.elements())
        keys, weights = list(wanted), list(wanted.values())
        while len(values) < n:
            values.append(self.rng.choices(keys, weights)[0])
        self.rng.shuffle(values)
        return values[:n]

    def unique_filler(self, f, model_name, offset):
        if isinstance(f, (models.CharField, models.TextField)):
            size = f.max_length or 200
            return lambda i: f"{model_name} {self.token} {offset + i}"[-size:]
        if isinstance(f, models.IntegerField):
            return lambda i: offset + i + 1
        if isinstance(f, models.DateTimeField):
            return lambda i: timezone.now() + timedelta(days=offset + i)
        if isinstance(f, models.DateField):
            return lambda i: timezone.now().date() + timedelta(days=offset + i)
        return None

    def filler(self, f, text_dist, model_name):
        if isinstance(f, models.TextField) and text_dist:
            return lambda i: self.lorem(text_dist)
        if f.name == "name" or (not f.has_default() and not f.null and not f.blank):
            if isinstance(f, models.EmailField):
                return lambda i: f"synthetic-{self.token}-{i}@example.invalid"
            if isinstance(f, models.URLField):
                return lambda i: f"https://example.com/{self.token}/{i}"
            if isinstance(f, (models.CharField, models.TextField)):
                size = f.max_length or 200
                return lambda i: f"{model_name} {self.token} {i}"[-size:]
            if isinstance(f, models.BooleanField):
                return lambda i: False
            if isinstance(
                f, (models.IntegerField, models.FloatField, models.DecimalField)
            ):
                return lambda i: 0
            if isinstance(f, models.DateTimeField):
                return lambda i: timezone.now()
            if isinstance(f, models.DateField):
                return lambda i: timezone.now().date()
            if isinstance(f, models.DurationField):
                return lambda i: timedelta(0)
            if isinstance(f, models.JSONField):
                return lambda i: {}
            if isinstance(f, models.UUIDField):
                return lambda i: uuid.uuid4()
        return None

    def lorem(self, text_dist):
        size = interp(text_dist, self.rng.random())
        return (LOREM * (1 + size // len(LOREM)))[:size]

    def tree_plan(self, m, entry, n):
        for f in m._meta.concrete_fields:
            fk = entry["fk"].get(f.name)
            if f.is_relation and f.related_model is m and fk and fk.get("tree"):
                counts = {
                    int(k): round(c * self.scale)
                    for k, c in fk["tree"]["per_level"].items()
                }
                counts[0] = max(0, counts.get(0, 0) - own_rows(m).count())
                levels = [lvl for lvl, c in counts.items() for _ in range(c)]
                return (
                    f.attname,
                    sorted((levels + [0] * n)[:n]),
                    fk["tree"]["branching"],
                )
        return None

    def reshape_choices(self, label):
        m = self.model(label)
        entry = self.profile["models"][label]
        rows = list(own_rows(m))
        self.report[label] = [round(entry["count"] * self.scale), len(rows), 0]
        fields = []
        for f in m._meta.concrete_fields:
            distribution = entry["choices"].get(f.name)
            if not (f.choices and distribution):
                continue
            keys = [choice_value(f, k) for k in distribution]
            values = self.rng.choices(keys, list(distribution.values()), k=len(rows))
            for row, value in zip(rows, values):
                setattr(row, f.attname, value)
            fields.append(f.attname)
        if fields and rows:
            m._base_manager.bulk_update(rows, fields, batch_size=1000)
        self.stdout.write(f"{label}: reshaped {len(rows)} rows on {fields}")

    def link_m2m(self, label):
        m = self.model(label)
        entry = self.profile["models"][label]
        for f in m._meta.many_to_many:
            spec = entry["m2m"].get(f.name)
            through = f.remote_field.through
            if (
                not spec
                or not through._meta.auto_created
                or f"{label}.{f.name}" in SKIP_M2M
            ):
                continue
            sources = list(own_rows(m).values_list("pk", flat=True))
            pool = list(f.related_model._base_manager.values_list("pk", flat=True))
            if not sources or not pool:
                continue
            src, dst = f.m2m_field_name() + "_id", f.m2m_reverse_field_name() + "_id"
            if f.related_model is m and spec.get("tree"):
                pairs = self.dag_pairs(sources, spec)
            else:
                pairs = self.bipartite_pairs(f, spec, sources, pool)
            through._base_manager.bulk_create(
                [through(**{src: s, dst: t}) for s, t in pairs],
                batch_size=1000,
                ignore_conflicts=True,
            )
            self.stdout.write(f"{label}.{f.name}: {len(pairs)} links")

    def weighted_unique(self, items, weights, k):
        chosen = set()
        for _ in range(k * 5):
            if len(chosen) >= k:
                break
            chosen.add(self.rng.choices(items, weights)[0])
        return chosen

    def fill_deferred(self):
        for m, f, fk, total in self.deferred:
            pks = self.created.get(m._meta.label, [])
            if not fk or not pks:
                continue
            values = dict(zip(pks, self.fk_plan(f, fk, total, len(pks))))
            rows = list(m._base_manager.filter(pk__in=pks))
            for row in rows:
                setattr(row, f.attname, values[row.pk])
            m._base_manager.bulk_update(rows, [f.attname], batch_size=1000)
            self.stdout.write(
                f"{m._meta.label}.{f.name}: linked {sum(v is not None for v in values.values())} deferred"
            )

    def bipartite_pairs(self, f, spec, sources, pool):
        target_total = self.profile["models"].get(f.related_model._meta.label, {}).get(
            "count"
        ) or len(pool)
        per_target = spec["per_target"]
        k = (
            min(len(pool), max(1, round(per_target["n"] * len(pool) / target_total)))
            if per_target
            else 1
        )
        targets = self.rng.sample(pool, k)
        weights = [w + 0.01 for w in sample_counts(per_target, k, self.rng)]
        if spec.get("by_urn"):
            urn_map = dict(
                f.related_model._base_manager.filter(
                    urn__in=list(spec["by_urn"])
                ).values_list("urn", "pk")
            )
            for urn, count in spec["by_urn"].items():
                if urn in urn_map:
                    targets.append(urn_map[urn])
                    weights.append(count)
        pairs = set()
        for s, c in zip(
            sources, sample_counts(spec["per_source"], len(sources), self.rng)
        ):
            for t in self.weighted_unique(targets, weights, min(c, len(targets))):
                pairs.add((s, t))
        return pairs

    def dag_pairs(self, sources, spec):
        nodes = sources[:]
        self.rng.shuffle(nodes)
        per_level = sorted(spec["tree"]["per_level"].items(), key=lambda x: int(x[0]))
        total = sum(c for _, c in per_level) or 1
        levels, start = [], 0
        for _, c in per_level:
            size = round(c * len(nodes) / total)
            levels.append(nodes[start : start + size])
            start += size
        pairs = set()
        for upper, lower in pairwise(levels):
            if not upper:
                break
            for node, c in zip(
                lower, sample_counts(spec["per_source"], len(lower), self.rng)
            ):
                for parent in self.rng.sample(upper, min(len(upper), max(1, c))):
                    pairs.add((node, parent))
        return pairs

    def print_report(self, order):
        self.stdout.write("\nmodel\ttarget\tbefore\tcreated\tnow")
        for label in order:
            if label not in self.report:
                continue
            target, before, created = self.report[label]
            now = own_rows(self.model(label)).count()
            style = self.style.SUCCESS if now >= target * 0.9 else self.style.WARNING
            self.stdout.write(style(f"{label}\t{target}\t{before}\t{created}\t{now}"))
        if self.errors:
            self.stdout.write("\nerrors:")
            for (label, kind), count in self.errors.most_common():
                self.stdout.write(self.style.ERROR(f"{label}\t{kind}\t{count}"))
        missing = [
            label
            for label in self.profile["models"]
            if self.profile["models"][label]["count"] and not self.model(label)
        ]
        if missing:
            self.stdout.write(
                self.style.WARNING(f"\nmodels absent locally: {', '.join(missing)}")
            )
