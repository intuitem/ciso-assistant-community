"""Migration 0196 stores the new-audit template on audits saved without a
`field_visibility` map: until then the backend hid their fields by the code defaults while
pages and progress read the framework's template."""

import importlib

import pytest
from django.apps import apps

from core.models import ComplianceAssessment, Framework, Perimeter
from core.utils import build_initial_field_visibility
from iam.models import Folder

migration = importlib.import_module("core.migrations.0196_seed_empty_field_visibility")

# CyFun 2025's template departs from the code defaults on score.
SCORE_FOR_EVERYONE = {"score": {"auditor": "edit", "respondent": "edit"}}


@pytest.mark.django_db
def test_seeds_audits_without_a_map_and_leaves_the_others():
    root = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Template framework",
        urn="urn:test:fw-template",
        folder=root,
        field_visibility=SCORE_FOR_EVERYONE,
    )
    folder = Folder.objects.create(parent_folder=root, name="audits")
    perimeter = Perimeter.objects.create(name="perimeter", folder=folder)

    def audit(name, **kwargs):
        return ComplianceAssessment.objects.create(
            name=name, framework=framework, folder=folder, perimeter=perimeter, **kwargs
        )

    empty = audit("empty")
    configured = audit(
        "configured", field_visibility={"result": {"auditor": "edit", "respondent": "hidden"}}
    )

    migration.seed_empty_field_visibility(apps, None)

    empty.refresh_from_db()
    configured.refresh_from_db()
    assert empty.field_visibility == build_initial_field_visibility(framework)
    assert empty.field_visibility["score"] == SCORE_FOR_EVERYONE["score"]
    assert configured.field_visibility == {
        "result": {"auditor": "edit", "respondent": "hidden"}
    }
