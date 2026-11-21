from datetime import date, timedelta

import pytest

from core.models import ComplianceAssessment, Framework
from core.tasks import lock_overdue_compliance_assessments
from global_settings.models import GlobalSettings
from iam.models import Folder
from tprm.models import Entity, EntityAssessment

pytestmark = pytest.mark.django_db


@pytest.fixture
def overdue_audit():
    folder = Folder.objects.create(name="Vendors")
    audit = ComplianceAssessment.objects.create(
        name="Vendor questionnaire",
        framework=Framework.objects.create(name="Questionnaire"),
        folder=folder,
        status=ComplianceAssessment.Status.IN_PROGRESS,
        due_date=date.today() - timedelta(days=1),
    )
    EntityAssessment.objects.create(
        name="Vendor review",
        entity=Entity.objects.create(name="Vendor", folder=folder),
        folder=folder,
        compliance_assessment=audit,
    )
    return audit


def set_auto_lock(enabled):
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.GENERAL,
        defaults={
            "value": {"auto_lock_overdue_assessments": enabled},
            "folder": Folder.get_root_folder(),
        },
    )


@pytest.mark.parametrize("enabled", [False, None])
def test_overdue_audit_untouched_when_auto_lock_off(overdue_audit, enabled):
    if enabled is not None:
        set_auto_lock(enabled)
    lock_overdue_compliance_assessments.call_local()
    overdue_audit.refresh_from_db()
    assert not overdue_audit.is_locked
    assert overdue_audit.status == ComplianceAssessment.Status.IN_PROGRESS


def test_overdue_audit_locked_when_auto_lock_on(overdue_audit):
    set_auto_lock(True)
    lock_overdue_compliance_assessments.call_local()
    overdue_audit.refresh_from_db()
    assert overdue_audit.is_locked
    assert overdue_audit.status == ComplianceAssessment.Status.IN_REVIEW
