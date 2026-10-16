"""Collection frequencies are named by their period: `realtime`, which always
meant fifteen minutes, is `15min`. The old name is still accepted where a
client writes or filters a frequency, as a deprecated alias."""

import datetime
import importlib
import uuid

import pytest
from django.apps import apps
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, User
from metrology.models import (
    STALENESS_THRESHOLDS,
    CustomMetricSample,
    MetricDefinition,
    MetricInstance,
)
from metrology.serializers import MetricInstanceWriteSerializer
from metrology.views import MetricInstanceViewSet


def make_domain():
    return Folder.objects.create(
        name=f"Domain {uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def make_definition():
    return MetricDefinition.objects.create(
        name=f"Metric {uuid.uuid4().hex[:6]}", folder=Folder.get_root_folder()
    )


def test_realtime_is_no_longer_offered():
    assert "realtime" not in MetricInstance.Frequency.values
    assert MetricInstance.Frequency.EVERY_15_MINUTES == "15min"
    assert STALENESS_THRESHOLDS["15min"] == datetime.timedelta(minutes=15)


@pytest.mark.django_db
def test_writing_realtime_stores_15min():
    serializer = MetricInstanceWriteSerializer(
        data={
            "folder": str(make_domain().id),
            "metric_definition": str(make_definition().id),
            "name": "Old script",
            "status": "active",
            "collection_frequency": "realtime",
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.save().collection_frequency == "15min"


@pytest.mark.django_db
def test_filtering_on_realtime_finds_15min_instances():
    domain = make_domain()
    fast = MetricInstance.objects.create(
        name="Fast",
        folder=domain,
        metric_definition=make_definition(),
        collection_frequency="15min",
    )
    MetricInstance.objects.create(
        name="Slow",
        folder=domain,
        metric_definition=make_definition(),
        collection_frequency="daily",
    )
    request = APIRequestFactory().get(
        "/metrology/metric-instances/",
        {"collection_frequency": "realtime", "folder": str(domain.id)},
    )
    force_authenticate(
        request,
        user=User.objects.create_superuser(
            email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
        ),
    )
    response = MetricInstanceViewSet.as_view({"get": "list"})(request)
    assert response.status_code == 200, response.data
    assert [row["id"] for row in response.data["results"]] == [str(fast.id)]


@pytest.mark.django_db
def test_the_migration_renames_stored_instances_only():
    migration = importlib.import_module("metrology.migrations.0007_derived_metrics")
    domain = make_domain()
    old = MetricInstance.objects.create(
        name="Old", folder=domain, metric_definition=make_definition()
    )
    # Written as before the rename, around the model's choices.
    MetricInstance.objects.filter(id=old.id).update(collection_frequency="realtime")
    hourly = MetricInstance.objects.create(
        name="Hourly",
        folder=domain,
        metric_definition=make_definition(),
        collection_frequency="hourly",
    )
    migration.rename_frequency("realtime", "15min")(apps, None)
    old.refresh_from_db()
    hourly.refresh_from_db()
    assert (old.collection_frequency, hourly.collection_frequency) == (
        "15min",
        "hourly",
    )


@pytest.mark.django_db
def test_a_15min_metric_turns_stale_after_fifteen_minutes(monkeypatch):
    now = datetime.datetime(2026, 5, 18, 12, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: now)
    instance = MetricInstance.objects.create(
        name="Fast",
        folder=make_domain(),
        metric_definition=make_definition(),
        collection_frequency="15min",
        status="active",
    )
    CustomMetricSample.objects.create(
        metric_instance=instance,
        folder=instance.folder,
        timestamp=now - datetime.timedelta(minutes=14),
        value={"result": 1},
    )
    assert not instance.is_stale()
    monkeypatch.setattr(timezone, "now", lambda: now + datetime.timedelta(minutes=2))
    assert instance.is_stale()
