"""`has_sensitive_personal_data` is computed from the processing's personal
data on every read, so it clears once no sensitive item is left."""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import Terminology
from core.startup import startup
from iam.models import Folder, User, UserGroup
from privacy.models import PersonalData, Processing

PROCESSINGS_URL = "/api/privacy/processings/"


@pytest.fixture
def client(db):
    startup(sender=None)
    admin = User.objects.create_superuser("admin@sensitive-flag-tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
    )
    return client


@pytest.fixture
def domain(db):
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(), name="Sensitive flag domain"
    )


@pytest.fixture
def contact_details(client):
    return Terminology.objects.get(
        field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY,
        name="privacy_contact_details",
    )


def _flag(client, processing):
    response = client.get(f"{PROCESSINGS_URL}{processing.id}/")
    assert response.status_code == 200
    return response.json()["has_sensitive_personal_data"]


def _sensitive_item(processing, category, name="Emergency contact"):
    return PersonalData.objects.create(
        processing=processing, name=name, category=category, is_sensitive=True
    )


def test_deleting_the_last_sensitive_item_clears_the_flag(
    client, domain, contact_details
):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)
    assert _flag(client, processing) is True

    response = client.delete(f"/api/privacy/personal-data/{item.id}/")
    assert response.status_code == 204
    assert _flag(client, processing) is False


def test_another_sensitive_item_keeps_the_flag(client, domain, contact_details):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)
    _sensitive_item(processing, contact_details, name="Home address")

    item.delete()
    assert _flag(client, processing) is True


def test_unmarking_the_item_clears_the_flag(client, domain, contact_details):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)

    item.is_sensitive = False
    item.save()
    assert _flag(client, processing) is False


def test_moving_the_item_moves_the_flag(client, domain, contact_details):
    payroll = Processing.objects.create(name="Payroll", folder=domain)
    hiring = Processing.objects.create(name="Hiring", folder=domain)
    item = _sensitive_item(payroll, contact_details)

    item.processing = hiring
    item.save()
    assert _flag(client, payroll) is False
    assert _flag(client, hiring) is True


def test_the_flag_cannot_be_written(client, domain, contact_details):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    _sensitive_item(processing, contact_details)

    response = client.patch(
        f"{PROCESSINGS_URL}{processing.id}/",
        {"has_sensitive_personal_data": False},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["has_sensitive_personal_data"] is True
    assert _flag(client, processing) is True


def test_create_reports_the_flag(client, domain):
    response = client.post(
        PROCESSINGS_URL,
        {"name": "Payroll", "folder": str(domain.id)},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["has_sensitive_personal_data"] is False


def test_the_list_reports_the_flag(client, domain, contact_details):
    payroll = Processing.objects.create(name="Payroll", folder=domain)
    Processing.objects.create(name="Hiring", folder=domain)
    _sensitive_item(payroll, contact_details)

    response = client.get(PROCESSINGS_URL, {"folder": str(domain.id)})
    assert response.status_code == 200
    flags = {
        row["name"]: row["has_sensitive_personal_data"]
        for row in response.json()["results"]
    }
    assert flags == {"Payroll": True, "Hiring": False}


def test_the_list_sorts_on_the_flag(client, domain, contact_details):
    Processing.objects.create(name="Hiring", folder=domain)
    payroll = Processing.objects.create(name="Payroll", folder=domain)
    _sensitive_item(payroll, contact_details)

    for ordering, expected in (
        ("has_sensitive_personal_data", ["Hiring", "Payroll"]),
        ("-has_sensitive_personal_data", ["Payroll", "Hiring"]),
    ):
        response = client.get(
            PROCESSINGS_URL, {"folder": str(domain.id), "ordering": ordering}
        )
        assert response.status_code == 200
        assert [row["name"] for row in response.json()["results"]] == expected
