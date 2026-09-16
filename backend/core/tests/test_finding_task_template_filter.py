"""Findings raised from a task are reachable from that task.

The task detail view lists them through `/findings/?task_templates=<id>`;
an unknown filter is dropped silently, so without it the tab would show every
finding in the instance rather than the ones attached to the task.
"""

import pytest
from django.urls import reverse
from rest_framework import status as http

from core.models import Finding, FindingsAssessment, TaskTemplate
from core.tests.test_audit_word_export import (  # noqa: F401
    admin_client,
    app_config,
)
from iam.models import Folder


@pytest.fixture
def findings(app_config):  # noqa: F811
    folder = Folder.objects.create(
        name="Task findings domain", content_type=Folder.ContentType.DOMAIN
    )
    assessment = FindingsAssessment.objects.create(name="Q3 review", folder=folder)
    attached = Finding.objects.create(
        name="Raised by the task", findings_assessment=assessment, folder=folder
    )
    unrelated = Finding.objects.create(
        name="Raised elsewhere", findings_assessment=assessment, folder=folder
    )
    task = TaskTemplate.objects.create(name="Monthly review", folder=folder)
    task.findings.add(attached)
    other_task = TaskTemplate.objects.create(name="Yearly review", folder=folder)
    return {
        "task": task,
        "other_task": other_task,
        "attached": attached,
        "unrelated": unrelated,
    }


@pytest.mark.django_db
def test_findings_filtered_by_task_template(admin_client, findings):  # noqa: F811
    response = admin_client.get(
        reverse("findings-list"), {"task_templates": str(findings["task"].id)}
    )
    assert response.status_code == http.HTTP_200_OK
    names = [f["name"] for f in response.json()["results"]]
    assert names == [findings["attached"].name]


@pytest.mark.django_db
def test_task_without_findings_lists_none(admin_client, findings):  # noqa: F811
    """The empty case is the one a dropped filter hides: it answers with every
    finding in the instance instead of none."""
    response = admin_client.get(
        reverse("findings-list"), {"task_templates": str(findings["other_task"].id)}
    )
    assert response.json()["results"] == []
