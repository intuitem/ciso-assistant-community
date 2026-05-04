import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic compliance assessment data for tests
COMPLIANCE_ASSESSMENT_NAME = "Test Compliance Assessment"
COMPLIANCE_ASSESSMENT_DESCRIPTION = "Test Description"
COMPLIANCE_ASSESSMENT_VERSION = "1.0"


@pytest.mark.django_db
class TestComplianceAssessmentsUnauthenticated:
    """Perform tests on ComplianceAssessments API endpoint without authentication"""

    client = APIClient()

    def test_get_compliance_assessments(self, authenticated_client):
        """test to get compliance assessments from the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.get_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "framework": Framework.objects.all()[0],
            },
        )

    def test_create_compliance_assessments(self):
        """test to create compliance assessments with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ).id,
            },
        )

    def test_update_compliance_assessments(self, authenticated_client):
        """test to update compliance assessments with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.update_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "framework": Framework.objects.all()[0],
            },
            {
                "name": "new " + COMPLIANCE_ASSESSMENT_NAME,
                "description": "new " + COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "perimeter": Perimeter.objects.create(
                    name="test2", folder=Folder.objects.create(name="test2")
                ).id,
            },
        )

    def test_delete_compliance_assessments(self, authenticated_client):
        """test to delete compliance assessments with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.delete_object(
            self.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "perimeter": Perimeter.objects.create(
                    name="test", folder=Folder.objects.create(name="test")
                ),
                "framework": Framework.objects.all()[0],
            },
        )


@pytest.mark.django_db
class TestComplianceAssessmentsAuthenticated:
    """Perform tests on ComplianceAssessments API endpoint with authentication"""

    def test_get_compliance_assessments(self, test):
        """test to get compliance assessments from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                },
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "str": str(Framework.objects.all()[0]),
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_compliance_assessments(self, test):
        """test to create compliance assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": str(perimeter.id),
                "framework": str(Framework.objects.all()[0].id),
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                },
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "str": str(Framework.objects.all()[0]),
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_compliance_assessments(self, test):
        """test to update compliance assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Documents")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework2")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)
        perimeter2 = Perimeter.objects.create(
            name="test2", folder=Folder.objects.create(name="test2")
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
            },
            {
                "name": "new " + COMPLIANCE_ASSESSMENT_NAME,
                "description": "new " + COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION + ".1",
                "perimeter": str(perimeter2.id),
                "framework": str(Framework.objects.all()[1].id),
            },
            {
                "perimeter": {
                    "id": str(perimeter.id),
                    "str": perimeter.folder.name + "/" + perimeter.name,
                    "folder": {
                        "id": str(perimeter.folder.id),
                        "str": perimeter.folder.name,
                    },
                },
                "framework": {
                    "id": str(Framework.objects.all()[0].id),
                    "urn": Framework.objects.all()[0].urn,
                    "str": str(Framework.objects.all()[0]),
                    "implementation_groups_definition": None,
                    "outcomes_definition": [],
                    "reference_controls": [
                        {"id": str(rc["id"]), "str": rc["str"], "urn": rc["urn"]}
                        for rc in Framework.objects.all()[0].reference_controls
                    ],
                    "min_score": Framework.objects.all()[0].min_score,
                    "max_score": Framework.objects.all()[0].max_score,
                    "ref_id": str(Framework.objects.all()[0].ref_id),
                    "has_update": False,
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_delete_compliance_assessments(self, test):
        """test to delete compliance assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        perimeter = Perimeter.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "perimeter": perimeter,
                "framework": Framework.objects.all()[0],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )


# ---------------------------------------------------------------------------
# Helpers for the list-progress tests below. Kept module-local: they assemble
# a synthetic framework + audit + RAs without going through the library
# loader, which the parametrised tests above already exercise.
# ---------------------------------------------------------------------------


def _make_framework(name: str | None = None) -> Framework:
    name = name or f"perf-test-fw-{uuid.uuid4().hex[:6]}"
    return Framework.objects.create(
        folder=Folder.get_root_folder(),
        name=name,
        provider="test",
        urn=f"urn:test:framework:{uuid.uuid4().hex[:12]}",
        ref_id=name,
        min_score=0,
        max_score=4,
    )


def _make_requirement(framework: Framework, ref_id: str, **kwargs) -> RequirementNode:
    kwargs.setdefault("assessable", True)
    return RequirementNode.objects.create(
        folder=framework.folder,
        framework=framework,
        urn=f"{framework.urn}:req:{ref_id}",
        ref_id=ref_id,
        name=f"requirement {ref_id}",
        **kwargs,
    )


def _make_audit(folder: Folder, framework: Framework, **kwargs) -> ComplianceAssessment:
    name = kwargs.pop("name", f"audit-{uuid.uuid4().hex[:6]}")
    return ComplianceAssessment.objects.create(
        folder=folder,
        framework=framework,
        name=name,
        ref_id=kwargs.pop("ref_id", name),
        **kwargs,
    )


def _list_progress(client: APIClient, audit_id) -> int:
    r = client.get("/api/compliance-assessments/")
    assert r.status_code == status.HTTP_200_OK, r.content
    body = r.json()
    results = body["results"] if isinstance(body, dict) and "results" in body else body
    target = str(audit_id)
    for item in results:
        if item.get("id") == target:
            return item["progress"]
    raise AssertionError(f"audit {target} not in {len(results)} list results")


@pytest.mark.django_db
class TestComplianceAssessmentListProgress:
    """`/api/compliance-assessments/` list `progress` field is computed by
    `ComplianceAssessmentViewSet._get_optimized_object_data` (per-page
    GROUP BY) and read from `optimized_data` by the list serializer.
    Pin the numeric output across the relevant branches so the path
    can't drift silently."""

    def test_progress_zero_when_all_not_assessed(self, authenticated_client):
        """Default RA state is NOT_ASSESSED with no score → 0 / N → 0 %."""
        framework = _make_framework()
        for i in range(4):
            _make_requirement(framework, f"R{i}")
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()

        assert _list_progress(authenticated_client, audit.id) == 0

    def test_progress_partial_assessed(self, authenticated_client):
        """1 of 4 RAs marked compliant → 25 %."""
        framework = _make_framework()
        for i in range(4):
            _make_requirement(framework, f"P{i}")
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()

        ras = list(audit.requirement_assessments.all())
        ras[0].result = RequirementAssessment.Result.COMPLIANT
        ras[0].save(update_fields=["result"])

        assert _list_progress(authenticated_client, audit.id) == 25

    def test_score_alone_counts_as_assessed(self, authenticated_client):
        """A score set with `result == NOT_ASSESSED` still counts as
        assessed — matches the OR-clause shared by the dropped
        `Count(distinct=True)` annotation and the new GROUP BY:
        `~Q(result=NA) | Q(score__isnull=False)`."""
        framework = _make_framework()
        for i in range(2):
            _make_requirement(framework, f"S{i}")
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()

        ras = list(audit.requirement_assessments.all())
        ras[0].score = 3  # leave result = NOT_ASSESSED on purpose
        ras[0].save(update_fields=["score"])

        assert _list_progress(authenticated_client, audit.id) == 50

    def test_progress_all_assessed(self, authenticated_client):
        framework = _make_framework()
        for i in range(3):
            _make_requirement(framework, f"A{i}")
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()
        for ra in audit.requirement_assessments.all():
            ra.result = RequirementAssessment.Result.COMPLIANT
            ra.save(update_fields=["result"])

        assert _list_progress(authenticated_client, audit.id) == 100

    def test_non_assessable_requirements_excluded(self, authenticated_client):
        """The `requirement__assessable=True` filter must apply to both
        numerator and denominator: a non-assessable requirement neither
        adds to the total nor prevents reaching 100 %."""
        framework = _make_framework()
        _make_requirement(framework, "AS-0")
        _make_requirement(framework, "AS-1")
        _make_requirement(framework, "NA-0", assessable=False)
        _make_requirement(framework, "NA-1", assessable=False)
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()

        for ra in audit.requirement_assessments.all():
            if ra.requirement.ref_id == "AS-0":
                ra.result = RequirementAssessment.Result.COMPLIANT
                ra.save(update_fields=["result"])

        # 1 / 2 assessable assessed → 50 %, not 1/4 = 25 %.
        assert _list_progress(authenticated_client, audit.id) == 50

    def test_progress_with_implementation_groups(self, authenticated_client):
        """`get_progress`'s implementation-groups branch was uncovered
        before this PR. Verify it still computes the right number when
        only some RAs match the audit's selected IGs."""
        framework = _make_framework()
        for i in range(2):
            _make_requirement(framework, f"G1-{i}", implementation_groups=["G1"])
        for i in range(2):
            _make_requirement(framework, f"G2-{i}", implementation_groups=["G2"])
        audit = _make_audit(
            Folder.get_root_folder(),
            framework,
            selected_implementation_groups=["G1"],
        )
        audit.create_requirement_assessments()

        ras_by_ref = {
            ra.requirement.ref_id: ra for ra in audit.requirement_assessments.all()
        }
        ras_by_ref["G1-0"].result = RequirementAssessment.Result.COMPLIANT
        ras_by_ref["G1-0"].save(update_fields=["result"])
        ras_by_ref["G2-0"].result = RequirementAssessment.Result.COMPLIANT
        ras_by_ref["G2-0"].save(update_fields=["result"])

        # Denominator = 2 G1 RAs, numerator = 1 → 50 %.
        assert _list_progress(authenticated_client, audit.id) == 50

    def test_progress_with_implementation_groups_no_match(self, authenticated_client):
        """Audit selects an IG with no matching requirements → total = 0 →
        the `if total else 0` guard returns 0 %."""
        framework = _make_framework()
        _make_requirement(framework, "ONLY", implementation_groups=["G1"])
        audit = _make_audit(
            Folder.get_root_folder(),
            framework,
            selected_implementation_groups=["NONEXISTENT"],
        )
        audit.create_requirement_assessments()

        assert _list_progress(authenticated_client, audit.id) == 0
