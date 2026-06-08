import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def donut_setup():
    """One folder, one assessment, one assessable requirement marked compliant."""
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root_folder, name="donut folder")
    perimeter = Perimeter.objects.create(name="donut perimeter", folder=folder)

    framework = Framework.objects.create(
        name="Donut Test Framework",
        urn="urn:test:donut-framework",
        min_score=0,
        max_score=100,
        folder=root_folder,
    )

    assessable_node = RequirementNode.objects.create(
        name="Assessable",
        urn="urn:test:donut-assessable",
        ref_id="P.1",
        framework=framework,
        assessable=True,
        folder=root_folder,
    )

    ca = ComplianceAssessment.objects.create(
        name="Donut Test Assessment",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=100,
    )

    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=assessable_node,
        folder=folder,
        result=RequirementAssessment.Result.COMPLIANT,
        status=RequirementAssessment.Status.DONE,
    )

    return {"ca": ca, "assessable_node": assessable_node}


@pytest.mark.django_db
class TestGetDonutData:
    def test_labels_match_enum_order(self, donut_setup):
        """Slice order is fixed by enum value order, not by which requirements are iterated first."""
        ca = donut_setup["ca"]

        donut = ca.get_donut_data()

        assert donut["result"]["labels"] == list(RequirementAssessment.Result.values)
        assert donut["status"]["labels"] == list(RequirementAssessment.Status.values)

    def test_emits_zero_entries_for_unused_buckets(self, donut_setup):
        ca = donut_setup["ca"]

        donut = ca.get_donut_data()

        result_to_value = {v["name"]: v["value"] for v in donut["result"]["values"]}
        assert result_to_value["compliant"] == 1
        assert result_to_value["non_compliant"] == 0
        assert result_to_value["not_assessed"] == 0

    def test_prefetched_requirements_path_matches_unprefetched(self, donut_setup):
        """The prefetched shortcut must return the same payload as the default DB-fetching path."""
        ca = donut_setup["ca"]
        prefetched = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=ca, requirement__assessable=True
            ).select_related("requirement")
        )

        assert ca.get_donut_data(prefetched) == ca.get_donut_data()
