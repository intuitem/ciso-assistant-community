import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


def _build_audit(framework, requirement, root_folder, folder_name, audit_name, result):
    folder = Folder.objects.create(parent_folder=root_folder, name=folder_name)
    perimeter = Perimeter.objects.create(name=f"{folder_name} perimeter", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name=audit_name,
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=100,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=requirement,
        folder=folder,
        result=result,
    )
    return ca


@pytest.mark.django_db
class TestComplianceAssessmentsRecapAction:
    URL = "/api/compliance-assessments/recap/"

    def test_recap_payload_shape_and_ordering(self, authenticated_client):
        root_folder = Folder.get_root_folder()
        framework = Framework.objects.create(
            name="Recap Test Framework",
            urn="urn:test:recap-framework",
            min_score=0,
            max_score=100,
            folder=root_folder,
        )
        assessable_node = RequirementNode.objects.create(
            name="Assessable",
            urn="urn:test:recap-assessable",
            ref_id="P.1",
            framework=framework,
            assessable=True,
            folder=root_folder,
        )

        # Folder names chosen so case-insensitive ordering ("alpha" < "Bravo")
        # differs from case-sensitive ordering ("Bravo" < "alpha").
        _build_audit(
            framework,
            assessable_node,
            root_folder,
            folder_name="Bravo",
            audit_name="a-audit",
            result=RequirementAssessment.Result.NON_COMPLIANT,
        )
        _build_audit(
            framework,
            assessable_node,
            root_folder,
            folder_name="alpha",
            audit_name="z-audit",
            result=RequirementAssessment.Result.COMPLIANT,
        )

        response = authenticated_client.get(self.URL)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Folder ordering is case-insensitive ("alpha" < "Bravo"),
        # so the audit under "alpha" must come first.
        assert [entry["folder"]["name"] for entry in data] == ["alpha", "Bravo"]
        assert [entry["name"] for entry in data] == ["z-audit", "a-audit"]

        first = data[0]
        assert set(first.keys()) >= {
            "id",
            "name",
            "folder",
            "framework",
            "donut",
            "global_score",
        }
        assert first["donut"]["result"]["labels"] == list(
            RequirementAssessment.Result.values
        )
