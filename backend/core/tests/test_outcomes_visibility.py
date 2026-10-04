"""Outcomes have their own field visibility, independent of the result's."""

import importlib

import pytest
from django.apps import apps

from core.models import ComplianceAssessment, Framework
from core.utils import AUDITOR_ONLY, THIRD_PARTY_VISIBILITY
from iam.models import Folder

migration = importlib.import_module(
    "core.migrations.0193_compliance_assessment_outcomes_visibility"
)


def _audit(field_visibility):
    root = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Outcomes",
        urn=f"urn:test:framework:outcomes-{len(field_visibility)}",
        folder=root,
    )
    audit = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, folder=root
    )
    # Saved as is: the serializer would seed the defaults.
    ComplianceAssessment.objects.filter(pk=audit.pk).update(
        field_visibility=field_visibility
    )
    return audit


def test_third_party_audits_hide_outcomes_from_respondents():
    assert THIRD_PARTY_VISIBILITY["outcomes"] == AUDITOR_ONLY


@pytest.mark.django_db
class TestMigrationKeepsCurrentVisibility:
    def test_outcomes_start_from_the_result_visibility(self):
        audit = _audit({"result": AUDITOR_ONLY})
        migration.copy_result_visibility_to_outcomes(apps, None)
        audit.refresh_from_db()
        assert audit.field_visibility["outcomes"] == AUDITOR_ONLY

    def test_explicit_outcomes_visibility_is_kept(self):
        hidden = {"auditor": "hidden", "respondent": "hidden"}
        audit = _audit({"result": AUDITOR_ONLY, "outcomes": hidden})
        migration.copy_result_visibility_to_outcomes(apps, None)
        audit.refresh_from_db()
        assert audit.field_visibility["outcomes"] == hidden

    def test_no_result_entry_leaves_outcomes_visible(self):
        audit = _audit({})
        migration.copy_result_visibility_to_outcomes(apps, None)
        audit.refresh_from_db()
        assert "outcomes" not in audit.field_visibility
