"""`?fields=` sparse fieldsets (core.views.SparseFieldsMixin).

The parameter exists so bulk read clients (Power BI bridge tables, exports)
can ask for two columns out of a wide row. It must only ever *remove*
columns: these tests pin that it cannot reach a field the serializer
withholds, and that it does not run ahead of per-role redaction.
"""

import pytest


@pytest.fixture
def sparse_dataset(db):
    from core.models import AppliedControl, ComplianceAssessment, Framework
    from core.models import LoadedLibrary, RequirementAssessment, RequirementNode
    from iam.models import Folder

    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="Sparse Domain",
        parent_folder=root,
        content_type=Folder.ContentType.DOMAIN,
    )
    library = LoadedLibrary.objects.create(
        name="Sparse Library",
        urn="urn:test:risk:library:sparse-fields",
        locale="en",
        default_locale=True,
        version=1,
        objects_meta={},
        folder=root,
    )
    framework = Framework.objects.create(
        name="Sparse Framework",
        urn="urn:test:risk:framework:sparse-fields",
        ref_id="SPARSE",
        provider="test",
        library=library,
        folder=root,
    )
    requirement = RequirementNode.objects.create(
        name="Sparse Requirement",
        urn="urn:test:req_node:sparse-fields:1",
        ref_id="R.1",
        framework=framework,
        folder=root,
        assessable=True,
        order_id=1,
    )
    # No field_visibility override: score is hidden by default
    # (core.utils.DEFAULT_VISIBILITY).
    compliance_assessment = ComplianceAssessment.objects.create(
        name="Sparse Audit", framework=framework, folder=domain
    )
    requirement_assessment = RequirementAssessment.objects.create(
        compliance_assessment=compliance_assessment,
        requirement=requirement,
        folder=domain,
        is_scored=True,
        score=3,
    )
    applied_control = AppliedControl.objects.create(
        name="Sparse Control", folder=domain, ref_id="AC-1"
    )
    return {
        "domain": domain,
        "applied_control": applied_control,
        "requirement_assessment": requirement_assessment,
    }


@pytest.mark.django_db
def test_returns_only_the_requested_columns(authenticated_client, sparse_dataset):
    response = authenticated_client.get(
        "/api/applied-controls/", {"fields": "id,name,status"}
    )

    assert response.status_code == 200
    rows = response.json()["results"]
    assert rows
    for row in rows:
        assert set(row) == {"id", "name", "status"}


@pytest.mark.django_db
def test_id_is_kept_even_when_not_requested(authenticated_client, sparse_dataset):
    response = authenticated_client.get("/api/applied-controls/", {"fields": "name"})

    assert response.status_code == 200
    assert set(response.json()["results"][0]) == {"id", "name"}


@pytest.mark.django_db
def test_unknown_field_is_rejected(authenticated_client, sparse_dataset):
    response = authenticated_client.get(
        "/api/applied-controls/", {"fields": "id,nonexistent"}
    )

    assert response.status_code == 400
    assert "nonexistent" in str(response.json())


@pytest.mark.django_db
def test_cannot_reach_a_field_the_serializer_withholds(
    authenticated_client, sparse_dataset
):
    """`fields` is subtractive: a model column outside the serializer stays out."""
    response = authenticated_client.get("/api/users/", {"fields": "id,password"})

    assert response.status_code == 400

    full = authenticated_client.get("/api/users/")
    assert full.status_code == 200
    for row in full.json()["results"]:
        assert "password" not in row


@pytest.mark.django_db
def test_does_not_bypass_per_role_redaction(authenticated_client, sparse_dataset):
    """Redaction runs in to_representation, after this trimming."""
    response = authenticated_client.get(
        "/api/requirement-assessments/", {"fields": "id,score"}
    )

    assert response.status_code == 200
    rows = response.json()["results"]
    assert rows
    for row in rows:
        assert "score" not in row, "hidden field resurfaced through ?fields="


@pytest.mark.django_db
def test_m2m_only_projection(authenticated_client, sparse_dataset):
    """The shape the Power BI connector's bridge tables ask for."""
    response = authenticated_client.get(
        "/api/applied-controls/", {"fields": "id,filtering_labels"}
    )

    assert response.status_code == 200
    for row in response.json()["results"]:
        assert set(row) == {"id", "filtering_labels"}


@pytest.mark.django_db
def test_applies_to_retrieve(authenticated_client, sparse_dataset):
    control_id = sparse_dataset["applied_control"].id
    response = authenticated_client.get(
        f"/api/applied-controls/{control_id}/", {"fields": "id,name"}
    )

    assert response.status_code == 200
    assert set(response.json()) == {"id", "name"}


@pytest.mark.django_db
def test_absent_parameter_returns_the_full_row(authenticated_client, sparse_dataset):
    """Trimming is per-request: it must not narrow the next caller's response.

    `get_serializer` builds a new serializer every call and `serializer.fields`
    is a per-instance copy of `_declared_fields`, so popping from it cannot
    reach the class. This runs after the narrowing tests in the same process,
    which is what makes it a check on that and not just on the default path.
    """
    response = authenticated_client.get("/api/applied-controls/")

    assert response.status_code == 200
    assert len(response.json()["results"][0]) > 3
