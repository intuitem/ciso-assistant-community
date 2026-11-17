"""
Filters integrations rely on to target one object. django-filter silently drops an
unknown query param, so a missing filter returns everything instead of failing.
"""

import pytest
from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    RequirementNode,
    TaskNode,
    TaskTemplate,
)
from iam.models import Folder


def _ids(client, url):
    response = client.get(url)
    assert response.status_code == 200, response.content
    return {row["id"] for row in response.json()["results"]}


@pytest.mark.django_db
def test_requirement_assessments_filter_by_requirement_ref_id(authenticated_client):
    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="F", folder=root)
    audit = ComplianceAssessment.objects.create(
        name="Audit", folder=root, framework=framework
    )
    by_ref = {}
    for ref_id in ("A.5.1", "A.5.2"):
        node = RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:lookup:{ref_id}",
            ref_id=ref_id,
            assessable=True,
            folder=root,
        )
        by_ref[ref_id] = RequirementAssessment.objects.create(
            compliance_assessment=audit, requirement=node, folder=root
        )

    ids = _ids(
        authenticated_client,
        f"/api/requirement-assessments/?compliance_assessment={audit.id}"
        "&requirement__ref_id=A.5.2",
    )
    assert ids == {str(by_ref["A.5.2"].id)}


@pytest.mark.django_db
def test_task_nodes_filter_by_folder(authenticated_client):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="Lookup domain", parent_folder=root, content_type=Folder.ContentType.DOMAIN
    )
    nodes = {}
    for folder in (root, domain):
        task = TaskTemplate.objects.create(
            name=f"task {folder.name}", folder=folder, is_recurrent=False
        )
        nodes[folder] = TaskNode.objects.create(task_template=task, folder=folder)

    ids = _ids(authenticated_client, f"/api/task-nodes/?folder={domain.id}")
    assert ids == {str(nodes[domain].id)}
