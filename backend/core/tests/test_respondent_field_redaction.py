"""Respondents must not receive the fields their audit's field_visibility hides from them.

`RequirementAssessmentReadSerializer` strips fields by viewer role, but only callers that
passed a `viewer_role` got the stripping: the requirement-assessment endpoints and
`inspect_requirement` served every viewer as an auditor.
"""

from pathlib import Path

import pytest
from rest_framework.test import APIClient

from core.models import (
    Actor,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    StoredLibrary,
)
from core.startup import startup
from core.utils import UserGroupCodename
from iam.models import Folder, User, UserGroup

FIXTURE = Path(__file__).parent / "fixtures" / "test-splash-assessable.yaml"

# Hidden from respondents by DEFAULT_VISIBILITY.
RESPONDENT_HIDDEN = {"status", "extended_result", "findings", "score"}


@pytest.fixture
def audit():
    startup(sender=None)
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored.load() is None
    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:splash-assessable"
    )
    domain = Folder.objects.create(
        name="RedactionDomain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(domain)
    perimeter = Perimeter.objects.create(name="P1", folder=domain)
    ca = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, perimeter=perimeter, folder=domain
    )
    ca.create_requirement_assessments()
    assigned = RequirementAssessment.objects.get(
        compliance_assessment=ca, requirement__assessable=True
    )
    unassigned = (
        RequirementAssessment.objects.filter(compliance_assessment=ca)
        .exclude(id=assigned.id)
        .first()
    )
    assert unassigned is not None

    respondent = User.objects.create_user("respondent@redaction-tests.com")
    UserGroup.objects.get(
        name=str(UserGroupCodename.AUDITEE), folder=domain
    ).user_set.add(respondent)
    actor, _ = Actor.objects.get_or_create(user=respondent)
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=ca, folder=domain, status="in_progress"
    )
    assignment.actor.add(actor)
    assignment.requirement_assessments.set([assigned])

    auditor = User.objects.create_user("auditor@redaction-tests.com")
    UserGroup.objects.get(
        name=str(UserGroupCodename.ANALYST), folder=domain
    ).user_set.add(auditor)

    return ca, assigned, unassigned, respondent, auditor


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_detail_hides_fields_from_respondent(audit):
    _, assigned, _, respondent, _ = audit
    response = _client(respondent).get(f"/api/requirement-assessments/{assigned.id}/")
    assert response.status_code == 200
    assert RESPONDENT_HIDDEN & response.json().keys() == set()


@pytest.mark.django_db
def test_list_hides_fields_from_respondent(audit):
    ca, assigned, _, respondent, _ = audit
    response = _client(respondent).get(
        f"/api/requirement-assessments/?compliance_assessment={ca.id}"
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [ra["id"] for ra in results] == [str(assigned.id)]
    assert RESPONDENT_HIDDEN & results[0].keys() == set()


@pytest.mark.django_db
def test_inspect_requirement_scopes_and_hides_for_respondent(audit):
    _, assigned, unassigned, respondent, _ = audit
    client = _client(respondent)

    response = client.get(
        f"/api/requirement-nodes/{assigned.requirement_id}/inspect_requirement/"
    )
    assert response.status_code == 200
    ras = response.json()["requirement_assessments"]
    assert [ra["id"] for ra in ras] == [str(assigned.id)]
    assert RESPONDENT_HIDDEN & ras[0].keys() == set()

    response = client.get(
        f"/api/requirement-nodes/{unassigned.requirement_id}/inspect_requirement/"
    )
    assert response.status_code == 200
    assert response.json()["requirement_assessments"] == []


@pytest.mark.django_db
def test_auditor_keeps_the_fields(audit):
    ca, assigned, _, _, auditor = audit
    client = _client(auditor)

    detail = client.get(f"/api/requirement-assessments/{assigned.id}/").json()
    assert {"status", "extended_result", "findings"} <= detail.keys()

    edit = client.get(f"/api/requirement-assessments/{assigned.id}/object/").json()
    assert {"status", "extended_result", "findings", "score"} <= edit.keys()

    ras = client.get(
        f"/api/requirement-nodes/{assigned.requirement_id}/inspect_requirement/"
    ).json()["requirement_assessments"]
    assert {"status", "extended_result", "findings"} <= ras[0].keys()


@pytest.mark.django_db
def test_object_endpoint_hides_fields_from_respondent(audit):
    _, assigned, _, respondent, _ = audit
    response = _client(respondent).get(
        f"/api/requirement-assessments/{assigned.id}/object/"
    )
    assert response.status_code == 200
    assert RESPONDENT_HIDDEN & response.json().keys() == set()


@pytest.mark.django_db
def test_audit_and_requirement_send_defaults_for_missing_visibility_keys(audit):
    # A stored map from before `findings` joined DEFAULT_VISIBILITY.
    ca, assigned, _, _, auditor = audit
    ca.field_visibility = {"result": {"auditor": "edit", "respondent": "edit"}}
    ca.save(update_fields=["field_visibility"])
    client = _client(auditor)

    audit_fv = client.get(f"/api/compliance-assessments/{ca.id}/").json()[
        "field_visibility"
    ]
    nested_fv = client.get(f"/api/requirement-assessments/{assigned.id}/").json()[
        "compliance_assessment"
    ]["field_visibility"]

    expected = {"auditor": "edit", "respondent": "hidden"}
    assert audit_fv["findings"] == expected
    assert nested_fv["findings"] == expected
