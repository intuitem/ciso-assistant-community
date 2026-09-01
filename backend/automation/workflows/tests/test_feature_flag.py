"""Flag off means off everywhere: the `workflows` feature flag must gate the
API, the webhook ingress, the scheduler and event dispatch — not just the
sidebar entry the frontend hides."""

import pytest
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import User
from automation.workflows.events import dispatch_internal_event
from automation.workflows.scheduling import run_due_schedules
from automation.workflows.tests.test_scheduling import (
    force_due,
    get_registration,
    make_workflow,
)


@pytest.fixture
def flag_off():
    ff_settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    ff_settings.value = {**(ff_settings.value or {}), "workflows": False}
    ff_settings.save()
    clear_feature_flags_cache()


@pytest.fixture
def admin_client():
    admin = User.objects.create_superuser(
        email="admin@wf-flag-tests.local", password="x"
    )
    client = APIClient()
    client.force_authenticate(admin)
    return client


@pytest.mark.django_db
class TestWorkflowsFeatureFlag:
    def test_the_api_is_gated(self, flag_off, admin_client):
        for endpoint in (
            "workflows",
            "workflow-versions",
            "workflow-instances",
            "workflow-secrets",
            "workflow-tokens",
            "workflow-triggers",
        ):
            resp = admin_client.get(f"/api/workflows/{endpoint}/")
            assert resp.status_code == 403, (endpoint, resp.status_code)

    def test_the_api_answers_with_the_flag_on(self, admin_client):
        resp = admin_client.get("/api/workflows/workflows/")
        assert resp.status_code == 200

    def test_the_webhook_ingress_is_gated(self, flag_off):
        workflow, _version = make_workflow()
        resp = APIClient().post(
            f"/api/workflows/hooks/{workflow.id}/entry/not-a-secret/",
            {},
            format="json",
        )
        assert resp.status_code == 404

    def test_the_scheduler_holds(self, flag_off):
        workflow, _version = make_workflow()
        registration = get_registration(workflow)
        force_due(registration)
        assert run_due_schedules() == []
        registration.refresh_from_db()
        assert not workflow.instances.exists()

    def test_event_dispatch_holds(self, flag_off):
        assert dispatch_internal_event("applied_control.updated", {}, None) == []
