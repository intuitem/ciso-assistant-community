from datetime import date

import pytest
from rest_framework.test import APIClient

from core.models import RiskMatrix, Severity, Terminology, Vulnerability
from ebios_rm.models import EbiosRMStudy, FearedEvent
from iam.models import Folder, Role, RoleAssignment, User
from privacy.models import PersonalData, Processing
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


@pytest.fixture
def domain(app_config):
    return Folder.objects.create(
        name="Reader domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


@pytest.fixture
def reader_client(domain):
    user = User.objects.create_user("reader@tests.com")
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(name="BI-RL-AUD"),
        folder=Folder.get_root_folder(),
    ).perimeter_folders.add(domain)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_reader_cannot_batch_create_personal_data(reader_client, domain):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    category = Terminology.objects.filter(
        field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY, is_visible=True
    ).first()
    assert category is not None

    resp = reader_client.post(
        "/api/privacy/personal-data/batch-create/",
        {"processing": str(processing.id), "categories": [str(category.id)]},
        format="json",
    )

    assert resp.status_code == 403
    assert not PersonalData.objects.filter(processing=processing).exists()


@pytest.mark.django_db
def test_reader_cannot_refresh_vulnerability_due_dates(reader_client, domain):
    vulnerability = Vulnerability.objects.create(
        name="Log4Shell", folder=domain, severity=Severity.CRITICAL
    )
    Vulnerability.objects.filter(id=vulnerability.id).update(
        detected_at=date(2026, 1, 1), due_date=date(2030, 1, 1)
    )

    resp = reader_client.post("/api/vulnerabilities/refresh-due-dates/")

    assert resp.status_code == 200
    vulnerability.refresh_from_db()
    assert vulnerability.due_date == date(2030, 1, 1)


@pytest.mark.django_db
def test_feared_event_batch_create_hides_unviewable_study(reader_client):
    other = Folder.objects.create(
        name="Other domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    study = EbiosRMStudy.objects.create(
        name="Hidden study",
        folder=other,
        risk_matrix=RiskMatrix.objects.create(
            name="matrix", folder=other, json_definition=RISK_MATRIX_JSON_DEFINITION
        ),
    )
    FearedEvent.objects.create(name="Secret", ebios_rm_study=study)

    resp = reader_client.post(
        "/api/ebios-rm/feared-events/batch-create/",
        {"feared_events_text": "Secret", "ebios_rm_study": str(study.id)},
        format="json",
    )

    assert resp.status_code == 404
    assert "Secret" not in resp.content.decode()
