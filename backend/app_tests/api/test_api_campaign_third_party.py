"""A third-party campaign builds its questionnaires by hand rather than through
EntityAssessmentWriteSerializer, so the access that serializer grants has to be
granted on this path too — otherwise the representatives are emailed a link to a
questionnaire they cannot open."""

import pytest
from rest_framework.test import APIClient

from core.models import Campaign, Framework, RequirementAssignment, RequirementNode
from iam.models import Folder, User, UserGroup
from tprm.models import Entity, EntityAssessment, Representative


@pytest.fixture
def setup(db):
    domain = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="Campaign Domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    entity = Entity.objects.create(name="Vendor Co", folder=domain)
    respondent = User.objects.create_user("campaign-rep@tests.com", is_third_party=True)
    Representative.objects.create(
        entity=entity, email=respondent.email, user=respondent
    )

    admin = APIClient()
    admin.force_authenticate(User.objects.create_superuser("campaign-admin@tests.com"))
    respondent_client = APIClient()
    respondent_client.force_authenticate(respondent)

    framework = Framework.objects.create(name="F", min_score=0, max_score=100)
    # An assignment covers the audit's requirement assessments, so the framework needs
    # at least one assessable node for the questionnaire to have anything to hold.
    RequirementNode.objects.create(
        framework=framework,
        folder=Folder.get_root_folder(),
        urn="urn:test:campaign:req:001",
        ref_id="REQ-001",
        assessable=True,
    )

    return {
        "domain": domain,
        "entity": entity,
        "respondent": respondent,
        "admin": admin,
        "respondent_client": respondent_client,
        "framework": framework,
    }


def launch(setup):
    response = setup["admin"].post(
        "/api/campaigns/",
        {
            "name": "Vendor round",
            "folder": str(setup["domain"].id),
            "kind": "third_party",
            "frameworks": [str(setup["framework"].id)],
            "entities": [str(setup["entity"].id)],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return Campaign.objects.get(id=response.json()["id"])


def test_launch_lets_the_representatives_into_the_workspace(setup):
    launch(setup)
    assessment = EntityAssessment.objects.get(entity=setup["entity"])
    enclave = assessment.compliance_assessment.folder

    assert assessment.representatives.count() == 1
    assert UserGroup.objects.filter(folder=enclave).exists()
    assert setup["respondent"].user_groups.filter(folder=enclave).exists()


def test_the_questionnaire_opens_for_the_representative_it_was_sent_to(setup):
    campaign = launch(setup)
    started = setup["admin"].post(f"/api/campaigns/{campaign.id}/start/", {}, "json")
    assert started.status_code == 200, started.data

    assessment = EntityAssessment.objects.get(entity=setup["entity"])
    audit = assessment.compliance_assessment
    assignment = RequirementAssignment.objects.filter(
        compliance_assessment=audit
    ).first()
    assert assignment is not None, "starting the campaign must wire an assignment"

    client = setup["respondent_client"]
    assert client.get(f"/api/compliance-assessments/{audit.id}/").status_code == 200
    assert (
        client.get(f"/api/requirement-assignments/{assignment.id}/").status_code == 200
    )
