"""Seed the picker endpoints that sit below the AutocompleteSelect lazy threshold.

Everything created is tagged with PREFIX so `--clean` can remove it. Folders and
perimeters are delegated to `populate_domains`, which tags its own data.

  python seed_pickers.py [--target N] [--frameworks N] [--clean]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402

from core.models import (  # noqa: E402
    Evidence,
    FilteringLabel,
    Framework,
    LoadedLibrary,
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    StoredLibrary,
)
from iam.models import Folder, User  # noqa: E402

PREFIX = "ZZSEED"


def _root():
    return Folder.get_root_folder()


def clean():
    n, _ = Evidence.objects.filter(name__startswith=PREFIX).delete()
    print(f"  evidences deleted: {n}")
    n, _ = RiskAssessment.objects.filter(name__startswith=PREFIX).delete()
    print(f"  risk-assessments deleted: {n}")
    n, _ = FilteringLabel.objects.filter(label__startswith=PREFIX).delete()
    print(f"  filtering-labels deleted: {n}")
    n, _ = User.objects.filter(email__startswith=PREFIX.lower()).delete()
    print(f"  users deleted: {n}")
    print("  folders/perimeters: delegating to populate_domains --clean")
    call_command("populate_domains", clean=True)
    print("  frameworks: NOT removed (library imports are left in place)")


def seed_evidences(target):
    have = Evidence.objects.count()
    folder = _root()
    made = 0
    while have + made < target:
        i = made + 1
        Evidence.objects.create(
            name=f"{PREFIX} Evidence {i:04d}",
            description="seeded for lazy-picker click-through",
            folder=folder,
            status=Evidence.Status.DRAFT,
        )
        made += 1
    return have, made


def seed_labels(target):
    have = FilteringLabel.objects.count()
    folder = _root()
    made = 0
    while have + made < target:
        i = made + 1
        FilteringLabel.objects.create(label=f"{PREFIX}-{i:04d}", folder=folder)
        made += 1
    return have, made


def seed_users(target):
    have = User.objects.count()
    made = 0
    while have + made < target:
        i = made + 1
        User.objects._create_user(
            email=f"{PREFIX.lower()}-{i:04d}@seed.local",
            password=None,
            mailing=False,
            initial_group=None,
            first_name=f"Seed{i:04d}",
            last_name="Picker",
        )
        made += 1
    return have, made


def seed_risk_assessments(target):
    have = RiskAssessment.objects.count()
    matrix = RiskMatrix.objects.first()
    if matrix is None:
        print("  !! no RiskMatrix loaded - skipping risk-assessments")
        return have, 0
    perimeters = list(Perimeter.objects.all()[:50])
    if not perimeters:
        print("  !! no Perimeter - run populate_domains first")
        return have, 0
    made = 0
    while have + made < target:
        i = made + 1
        RiskAssessment.objects.create(
            name=f"{PREFIX} RA {i:04d}",
            description="seeded for lazy-picker click-through",
            folder=perimeters[i % len(perimeters)].folder,
            perimeter=perimeters[i % len(perimeters)],
            risk_matrix=matrix,
            version="1.0",
        )
        made += 1
    return have, made


def seed_frameworks(target):
    have = Framework.objects.count()
    if have >= target:
        return have, 0
    loaded = set(LoadedLibrary.objects.values_list("urn", flat=True))
    candidates = [
        s
        for s in StoredLibrary.objects.all()
        if (s.objects_meta or {}).get("framework") and s.urn not in loaded
    ]
    # Smallest first: a framework library's cost is its requirement count.
    candidates.sort(key=lambda s: (s.objects_meta or {}).get("framework", 0))
    made = 0
    for lib in candidates:
        if have + made >= target:
            break
        try:
            err = lib.load()
            if err:
                print(f"  skip {lib.urn}: {err}")
                continue
            made += 1
            print(f"  + {lib.urn} ({(lib.objects_meta or {}).get('framework')} reqs)")
        except Exception as e:
            print(f"  skip {lib.urn}: {type(e).__name__}")
    return have, made


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=120)
    p.add_argument("--frameworks", type=int, default=70)
    p.add_argument("--clean", action="store_true")
    a = p.parse_args()

    if a.clean:
        print("CLEANING seeded data")
        clean()
        return

    print(f"SEEDING to target={a.target}")
    print("\n[1/6] folders + perimeters (populate_domains)")
    call_command("populate_domains", domains=a.target, max_depth=3)

    for label, fn, tgt in (
        ("evidences", seed_evidences, a.target),
        ("filtering-labels", seed_labels, a.target),
        ("users", seed_users, a.target),
        ("risk-assessments", seed_risk_assessments, a.target),
        ("frameworks", seed_frameworks, a.frameworks),
    ):
        print(f"\n[{label}]")
        before, made = fn(tgt)
        print(f"  {before} -> {before + made}  (+{made})")


if __name__ == "__main__":
    main()
