from datetime import date

import pytest
from rest_framework.test import APIClient

from core.models import Severity, Terminology, Vulnerability
from iam.models import Folder, Role, RoleAssignment, User
from privacy.models import PersonalData, Processing


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

    reader_client.post("/api/vulnerabilities/refresh-due-dates/")

    vulnerability.refresh_from_db()
    assert vulnerability.due_date == date(2030, 1, 1)
