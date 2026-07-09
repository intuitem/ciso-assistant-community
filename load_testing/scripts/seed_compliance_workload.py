#!/usr/bin/env python
"""Seed a compliance-assessment workload for load testing.

Creates a dedicated domain and N compliance assessments from an existing loaded
framework, then creates their requirement assessments. Also writes a JSON file with
assessment and requirement-assessment ids for Locust.

Run after migrations + library storage/loading. If no framework is loaded, this script
attempts to run `autoloadlibraries`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Local checkout: repo/backend/manage.py. Container image: /code/manage.py.
DJANGO_ROOT = (
    REPO_ROOT / "backend"
    if (REPO_ROOT / "backend" / "manage.py").exists()
    else REPO_ROOT
)
sys.path.insert(0, str(DJANGO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import transaction  # noqa: E402
from django.db.models import Count  # noqa: E402

from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    RequirementNode,
)  # noqa: E402
from iam.models import Folder  # noqa: E402


DEFAULT_NAME = "LOADTEST Compliance Workload"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assessments", type=int, default=50)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument(
        "--framework-ref-id", help="Optional exact framework ref_id to use"
    )
    parser.add_argument("--min-requirements", type=int, default=20)
    parser.add_argument("--synthetic-requirements", type=int, default=100)
    parser.add_argument("--out", default="load_testing/workload.json")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete the existing load-test domain first",
    )
    return parser.parse_args()


def _create_synthetic_framework(requirements: int) -> Framework:
    root = Folder.get_root_folder()
    fw, created = Framework.objects.get_or_create(
        urn="urn:intuitem:load-testing:framework",
        defaults={
            "folder": root,
            "ref_id": "LOADTEST-FW",
            "name": "Load Testing Synthetic Framework",
            "description": "Synthetic framework for concurrent compliance-assessment benchmarks.",
            "provider": "intuitem",
            "min_score": 0,
            "max_score": 100,
            "is_published": True,
        },
    )
    existing = RequirementNode.objects.filter(framework=fw).count()
    for i in range(existing + 1, requirements + 1):
        RequirementNode.objects.create(
            folder=root,
            framework=fw,
            urn=f"urn:intuitem:load-testing:framework:req:{i:04d}",
            ref_id=f"LT-{i:04d}",
            name=f"Load-test requirement {i:04d}",
            description="Synthetic assessable requirement used for load testing.",
            assessable=True,
            order_id=i,
            implementation_groups=[],
            is_published=True,
        )
    return fw


def _select_framework(
    ref_id: str | None, min_requirements: int, synthetic_requirements: int
) -> Framework:
    qs = Framework.objects.annotate(req_count=Count("requirement_nodes"))
    if ref_id:
        qs = qs.filter(ref_id=ref_id)
    fw = (
        qs.filter(req_count__gte=min_requirements)
        .order_by("-req_count", "name")
        .first()
    )
    if fw is None:
        # Startup stores libraries; this loads any autoload libraries not yet expanded into objects.
        call_command("autoloadlibraries")
        qs = Framework.objects.annotate(req_count=Count("requirement_nodes"))
        if ref_id:
            qs = qs.filter(ref_id=ref_id)
        fw = (
            qs.filter(req_count__gte=min_requirements)
            .order_by("-req_count", "name")
            .first()
        )
    if fw is None and not ref_id:
        fw = _create_synthetic_framework(max(min_requirements, synthetic_requirements))
    if fw is None:
        raise SystemExit(
            "No loaded framework found with enough requirements for the requested --framework-ref-id."
        )
    return fw


def _domain(name: str, fresh: bool) -> Folder:
    root = Folder.get_root_folder()
    if fresh:
        Folder.objects.filter(
            name=name, content_type=Folder.ContentType.DOMAIN
        ).delete()
    folder, _ = Folder.objects.get_or_create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        defaults={
            "parent_folder": root,
            "description": "Load-test compliance workload",
        },
    )
    return folder


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    framework = _select_framework(
        args.framework_ref_id, args.min_requirements, args.synthetic_requirements
    )
    folder = _domain(args.name, args.fresh)

    created = 0
    with transaction.atomic():
        existing = ComplianceAssessment.objects.filter(
            folder=folder, name__startswith=f"{args.name} #"
        ).count()
        for i in range(existing + 1, args.assessments + 1):
            ca = ComplianceAssessment.objects.create(
                name=f"{args.name} #{i:03d}",
                description="Seeded for concurrent requirement-assessment update benchmarks.",
                folder=folder,
                framework=framework,
            )
            ca.create_requirement_assessments()
            created += 1

    assessments = list(
        ComplianceAssessment.objects.filter(
            folder=folder, name__startswith=f"{args.name} #"
        )
        .order_by("name")
        .values_list("id", flat=True)
    )[: args.assessments]
    ras = list(
        RequirementAssessment.objects.filter(compliance_assessment_id__in=assessments)
        .order_by("compliance_assessment_id", "requirement__ref_id", "id")
        .values_list("id", flat=True)
    )
    req_count = RequirementNode.objects.filter(framework=framework).count()

    payload = {
        "folder_id": str(folder.id),
        "framework": {
            "id": str(framework.id),
            "name": framework.name,
            "ref_id": framework.ref_id,
            "requirement_count": req_count,
        },
        "created_assessments": created,
        "assessment_ids": [str(x) for x in assessments],
        "requirement_assessment_ids": [str(x) for x in ras],
    }
    out.write_text(json.dumps(payload, indent=2))
    print(
        f"Seeded {len(assessments)} compliance assessments / {len(ras)} requirement assessments "
        f"using {framework.ref_id or framework.name}. Wrote {out}."
    )


if __name__ == "__main__":
    main()
