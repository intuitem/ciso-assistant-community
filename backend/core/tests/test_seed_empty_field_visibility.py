"""Migration 0196 stores the new-audit template on audits saved without a
`field_visibility` map: until then the backend hid their fields by the code defaults while
pages and progress read the framework's template."""

import importlib

import pytest
from django.apps import apps

from core.models import ComplianceAssessment, Framework, Perimeter
from core.utils import AUDITOR_ONLY, build_initial_field_visibility
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
    # As written before save() filled the map: update() bypasses save().
    ComplianceAssessment.objects.filter(pk=empty.pk).update(field_visibility={})
    configured = audit(
        "configured",
        field_visibility={"result": {"auditor": "edit", "respondent": "hidden"}},
    )

    migration.seed_empty_field_visibility(apps, None)

    empty.refresh_from_db()
    configured.refresh_from_db()
    assert empty.field_visibility == build_initial_field_visibility(framework)
    assert empty.field_visibility["score"] == SCORE_FOR_EVERYONE["score"]
    assert configured.field_visibility == {
        "result": {"auditor": "edit", "respondent": "hidden"}
    }


def _audit_factory():
    root = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Template framework",
        urn="urn:test:fw-template-save",
        folder=root,
        field_visibility=SCORE_FOR_EVERYONE,
    )
    folder = Folder.objects.create(parent_folder=root, name="audits")
    perimeter = Perimeter.objects.create(name="perimeter", folder=folder)

    def audit(name, **kwargs):
        return ComplianceAssessment.objects.create(
            name=name, framework=framework, folder=folder, perimeter=perimeter, **kwargs
        )

    return audit


# save() keeps new empty maps from appearing after the migration: scripts and imports of
# old exports create audits without one.
@pytest.mark.django_db
def test_save_gives_an_audit_without_a_map_the_template():
    audit = _audit_factory()

    created = audit("created")
    created.refresh_from_db()
    assert created.field_visibility["score"] == SCORE_FOR_EVERYONE["score"]
    assert created.field_visibility["status"] == AUDITOR_ONLY

    configured = audit("configured", field_visibility={"result": AUDITOR_ONLY})
    configured.refresh_from_db()
    assert configured.field_visibility == {"result": AUDITOR_ONLY}


@pytest.mark.django_db
def test_save_with_update_fields_stores_the_template():
    emptied = _audit_factory()("emptied")
    ComplianceAssessment.objects.filter(pk=emptied.pk).update(field_visibility={})
    emptied.refresh_from_db()

    emptied.name = "renamed"
    emptied.save(update_fields=["name"])

    emptied.refresh_from_db()
    assert emptied.name == "renamed"
    assert emptied.field_visibility["score"] == SCORE_FOR_EVERYONE["score"]
