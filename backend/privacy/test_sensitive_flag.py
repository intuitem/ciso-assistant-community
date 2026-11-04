"""`Processing.has_sensitive_personal_data` follows its personal data, both
ways: it clears once no sensitive item is left on the processing."""

import importlib

import pytest
from django.apps import apps
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import Terminology
from core.startup import startup
from iam.models import Folder, User, UserGroup
from privacy.models import (
    PersonalData,
    Processing,
    create_default_privacy_terminologies,
)

recompute_sensitive_flag = importlib.import_module(
    "privacy.migrations.0025_recompute_has_sensitive_personal_data"
).recompute_sensitive_flag


@pytest.fixture
def domain(db):
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(), name="Sensitive flag domain"
    )


@pytest.fixture
def contact_details(db):
    create_default_privacy_terminologies()
    return Terminology.objects.get(
        field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY,
        name="privacy_contact_details",
    )


def _flag(processing):
    processing.refresh_from_db()
    return processing.has_sensitive_personal_data


def _sensitive_item(processing, category, name="Emergency contact"):
    return PersonalData.objects.create(
        processing=processing, name=name, category=category, is_sensitive=True
    )


def test_deleting_the_last_sensitive_item_clears_the_flag(domain, contact_details):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)
    assert _flag(processing) is True

    item.delete()
    assert _flag(processing) is False


def test_another_sensitive_item_keeps_the_flag(domain, contact_details):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)
    _sensitive_item(processing, contact_details, name="Home address")

    item.delete()
    assert _flag(processing) is True


def test_unmarking_the_item_clears_the_flag(domain, contact_details):
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)

    item.is_sensitive = False
    item.save()
    assert _flag(processing) is False


def test_moving_the_item_moves_the_flag(domain, contact_details):
    payroll = Processing.objects.create(name="Payroll", folder=domain)
    hiring = Processing.objects.create(name="Hiring", folder=domain)
    item = _sensitive_item(payroll, contact_details)

    item.processing = hiring
    item.save()
    assert _flag(payroll) is False
    assert _flag(hiring) is True


def test_deleting_through_the_api_clears_the_flag(domain, contact_details):
    startup(sender=None)
    admin = User.objects.create_superuser("admin@sensitive-flag-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin_group.user_set.add(admin)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
    )
    processing = Processing.objects.create(name="Payroll", folder=domain)
    item = _sensitive_item(processing, contact_details)

    response = client.delete(f"/api/privacy/personal-data/{item.id}/")
    assert response.status_code == 204
    assert _flag(processing) is False


def test_migration_recomputes_existing_flags(domain, contact_details):
    stale = Processing.objects.create(name="Payroll", folder=domain)
    missing = Processing.objects.create(name="Hiring", folder=domain)
    _sensitive_item(missing, contact_details)
    Processing.objects.filter(pk=stale.pk).update(has_sensitive_personal_data=True)
    Processing.objects.filter(pk=missing.pk).update(has_sensitive_personal_data=False)

    recompute_sensitive_flag(apps, None)
    assert _flag(stale) is False
    assert _flag(missing) is True
