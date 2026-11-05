"""The recompute job: one queued at a time whatever the burst of marks, one
running at a time, and the sweep and the refresh going through it."""

import datetime
import time
import uuid

import pytest
from django.core.cache import cache
from django.utils import timezone
from huey import MemoryHuey
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, User
from metrology import recompute, tasks
from metrology.derived import compute_sample
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from metrology.recompute import request_recompute as real_request_recompute
from metrology.series import FULL
from metrology.views import MetricInstanceViewSet

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 5, 18, 12, 0, tzinfo=UTC)


class _Job:
    """Stands in for the queued task: records when it was asked to run."""

    def __init__(self):
        self.delays = []

    def schedule(self, delay=None, **kwargs):
        self.delays.append(delay)


@pytest.fixture
def queue(monkeypatch):
    """The real request_recompute, on an in-memory task queue."""
    huey = MemoryHuey()
    job = _Job()
    monkeypatch.setattr(recompute, "HUEY", huey)
    monkeypatch.setattr(recompute, "request_recompute", real_request_recompute)
    monkeypatch.setattr(tasks, "recompute_marked_formulas", job)
    cache.delete(recompute.RUNNING_KEY)
    yield huey, job
    cache.delete(recompute.RUNNING_KEY)


def test_a_burst_of_requests_queues_one_job(queue):
    _huey, job = queue
    for _ in range(50):
        recompute.request_recompute()
    assert job.delays == [recompute.RECOMPUTE_DELAY_SECONDS]


@pytest.mark.django_db
def test_a_running_job_lets_the_next_request_queue_another(queue):
    """The job lets go of the pending flag first: a mark made while it runs
    queues the next job instead of being lost."""
    _huey, job = queue
    recompute.request_recompute()
    recompute.run_job()
    recompute.request_recompute()
    assert len(job.delays) == 2


def test_a_flag_nobody_released_is_taken_over(queue):
    """A job queued and then lost (a worker killed with it) must not block
    every later request."""
    huey, job = queue
    huey.put(recompute.PENDING_KEY, time.time() - recompute.PENDING_STALE_SECONDS - 1)
    recompute.request_recompute()
    assert job.delays == [recompute.RECOMPUTE_DELAY_SECONDS]


def test_a_job_finding_another_running_comes_back_later(queue, monkeypatch):
    _huey, job = queue

    def must_not_run():
        raise AssertionError("two jobs ran at once")

    monkeypatch.setattr(recompute, "compute_marked_formulas", must_not_run)
    cache.add(recompute.RUNNING_KEY, "1", 60)
    recompute.run_job()
    assert job.delays == [recompute.RECOMPUTE_DELAY_SECONDS]


# ---------- what asks for a job ----------


def make_domain():
    return Folder.objects.create(
        name=f"Domain {uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def make_definition(**extra):
    return MetricDefinition.objects.create(
        name=f"Metric {uuid.uuid4().hex[:6]}", folder=Folder.get_root_folder(), **extra
    )


@pytest.fixture
def series(monkeypatch):
    """A monthly formula over one input, computed once at NOW."""
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    cache.clear()
    domain = make_domain()
    base = make_definition()
    source = MetricInstance.objects.create(
        name="Source", folder=domain, metric_definition=base, status="active"
    )
    CustomMetricSample.objects.create(
        metric_instance=source,
        folder=domain,
        timestamp=NOW - datetime.timedelta(days=2),
        value={"result": 3},
    )
    out = MetricInstance.objects.create(
        name="Out",
        folder=domain,
        metric_definition=make_definition(
            inputs=[{"key": "x", "definition": str(base.id), "combine": "one"}],
            expression="x * 3",
        ),
        collection_frequency="monthly",
        status="active",
    )
    compute_sample(out)
    out.refresh_from_db()
    assert out.recompute_from is None
    return out


@pytest.mark.django_db
def test_the_sweep_marks_a_formula_past_its_interval(
    series, monkeypatch, recompute_requests
):
    """From the period its last run reached: what the run would have
    recomputed had the sweep computed it itself."""
    computed_at = series.last_computed_at
    later = NOW + datetime.timedelta(days=31)
    monkeypatch.setattr(timezone, "now", lambda: later)
    tasks.compute_due_derived_metrics.call_local()
    series.refresh_from_db()
    assert series.recompute_from == computed_at
    assert recompute_requests


@pytest.mark.django_db
def test_the_sweep_leaves_a_formula_inside_its_interval(series, recompute_requests):
    tasks.compute_due_derived_metrics.call_local()
    series.refresh_from_db()
    assert series.recompute_from is None
    assert not recompute_requests


@pytest.mark.django_db
def test_a_refresh_recomputes_the_whole_series_in_the_job(series, recompute_requests):
    request = APIRequestFactory().post(
        f"/metrology/metric-instances/{series.id}/refresh/", {}, format="json"
    )
    force_authenticate(
        request,
        user=User.objects.create_superuser(
            email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
        ),
    )
    response = MetricInstanceViewSet.as_view({"post": "refresh"})(
        request, pk=str(series.id)
    )
    assert response.status_code == 202
    series.refresh_from_db()
    assert series.recompute_from == FULL
    assert recompute_requests
