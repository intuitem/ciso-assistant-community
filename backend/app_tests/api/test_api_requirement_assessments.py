import pytest
from rest_framework.status import HTTP_403_FORBIDDEN
from rest_framework.test import APIClient
from core.models import (
    ComplianceAssessment,
    RequirementNode,
    RequirementAssessment,
    Framework,
)
from core.models import Perimeter, AppliedControl
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic requirement assessment data for tests
REQUIREMENT_ASSESSMENT_STATUS = "to_do"
REQUIREMENT_ASSESSMENT_STATUS2 = "in_progress"
REQUIREMENT_ASSESSMENT_OBSERVATION = "Test observation"


@pytest.mark.django_db
class TestRequirementAssessmentsUnauthenticated:
    """Perform tests on Requirement Assessments API endpoint without authentication"""

    client = APIClient()

    def test_get_requirement_assessments(self, authenticated_client):
        """test to get requirement assessments from the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.get_object(
            self.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "folder": folder,
                "compliance_assessment": ComplianceAssessment.objects.create(
                    name="test",
                    perimeter=Perimeter.objects.create(name="test", folder=folder),
                    framework=Framework.objects.all()[0],
                ),
                "requirement": RequirementNode.objects.create(
                    name="test", folder=folder, assessable=False
                ),
                "score": None,
            },
        )

    def test_create_requirement_assessments(self):
        """test to create requirement assessments with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_requirement_assessments(self, authenticated_client):
        """test to update requirement assessments with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.update_object(
            self.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "folder": folder,
                "compliance_assessment": ComplianceAssessment.objects.create(
                    name="test",
                    perimeter=Perimeter.objects.create(name="test", folder=folder),
                    framework=Framework.objects.all()[0],
                ),
                "requirement": RequirementNode.objects.create(
                    name="test", folder=folder, assessable=False
                ),
                "score": None,
            },
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS2,
                "folder": Folder.objects.create(name="test2").id,
            },
        )


@pytest.mark.django_db
class TestRequirementAssessmentsAuthenticated:
    """Perform tests on Requirement Assessments API endpoint with authentication"""

    def test_get_requirement_assessments(self, test):
        """test to get requirement assessments from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            perimeter=Perimeter.objects.create(name="test", folder=test.folder),
            framework=Framework.objects.all()[0],
        )

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": test.folder,
                "compliance_assessment": compliance_assessment,
                "requirement": RequirementNode.objects.all()[0],
                # `score` intentionally omitted: the CA is created via
                # .objects.create() without seeding field_visibility, so the
                # cascade resolves score → DEFAULT_VISIBILITY (HIDDEN) and
                # the API correctly strips score from the response.
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                    "is_locked": False,
                    "min_score": compliance_assessment.min_score,
                    "max_score": compliance_assessment.max_score,
                    "extended_result_enabled": compliance_assessment.extended_result_enabled,
                    "progress_status_enabled": compliance_assessment.progress_status_enabled,
                    "field_visibility": compliance_assessment.field_visibility,
                    "name": compliance_assessment.name,
                    "framework": {
                        "implementation_groups_definition": compliance_assessment.framework.implementation_groups_definition,
                        "field_visibility": compliance_assessment.framework.field_visibility,
                        "str": str(compliance_assessment.framework),
                    },
                },
                "requirement": {
                    "id": str(RequirementNode.objects.all()[0].id),
                    "urn": RequirementNode.objects.all()[0].urn,
                    "annotation": RequirementNode.objects.all()[0].annotation,
                    "name": RequirementNode.objects.all()[0].name,
                    "questions": None,
                    "description": RequirementNode.objects.all()[0].description,
                    "typical_evidence": RequirementNode.objects.all()[
                        0
                    ].typical_evidence,
                    "ref_id": RequirementNode.objects.all()[0].ref_id,
                    "associated_reference_controls": RequirementNode.objects.all()[
                        0
                    ].associated_reference_controls,
                    "associated_threats": RequirementNode.objects.all()[
                        0
                    ].associated_threats,
                    "implementation_groups": RequirementNode.objects.all()[
                        0
                    ].implementation_groups,
                    "display_mode": RequirementNode.objects.all()[0].display_mode,
                    "parent_requirement": {
                        "str": RequirementNode.objects.all()[0].parent_requirement.get(
                            "str"
                        ),
                        "urn": RequirementNode.objects.all()[0].parent_requirement.get(
                            "urn"
                        ),
                        "id": str(
                            RequirementNode.objects.all()[0].parent_requirement.get(
                                "id"
                            )
                        ),
                        "ref_id": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("ref_id"),
                        "name": RequirementNode.objects.all()[0].parent_requirement.get(
                            "name"
                        ),
                        "description": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("description"),
                    }
                    if RequirementNode.objects.all()[0].parent_requirement
                    else None,
                },
            },
            base_count=-1,
            user_group=test.user_group,
        )

    def test_create_requirement_assessments(self, test):
        """test to create requirement assessments with the API with authentication"""
        """nobody has permission to do that, so it will fail"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            perimeter=Perimeter.objects.create(name="test", folder=test.folder),
            framework=Framework.objects.all()[0],
        )
        applied_control = AppliedControl.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": str(test.folder.id),
                "compliance_assessment": str(compliance_assessment.id),
                "requirement": str(RequirementNode.objects.all()[0].id),
                "applied_controls": [str(applied_control.id)],
                "score": None,
            },
            {
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                    "is_locked": False,
                    "min_score": compliance_assessment.min_score,
                    "max_score": compliance_assessment.max_score,
                    "extended_result_enabled": compliance_assessment.extended_result_enabled,
                    "progress_status_enabled": compliance_assessment.progress_status_enabled,
                    "field_visibility": compliance_assessment.field_visibility,
                    "name": compliance_assessment.name,
                    "framework": {
                        "implementation_groups_definition": compliance_assessment.framework.implementation_groups_definition,
                        "field_visibility": compliance_assessment.framework.field_visibility,
                        "str": str(compliance_assessment.framework),
                    },
                }
            },
            base_count=-1,
            fails=True,
            expected_status=HTTP_403_FORBIDDEN,
        )

    def test_update_requirement_assessments(self, test):
        """test to update requirement assessments with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        folder = Folder.objects.create(name="test2")
        # Seed both CAs with score visible to the auditor so the score field
        # round-trips through the read serializer's cascade strip.
        score_auditor_only = {
            "score": {"auditor": "edit", "respondent": "hidden"},
            "is_scored": {"auditor": "edit", "respondent": "hidden"},
        }
        compliance_assessment = ComplianceAssessment.objects.create(
            name="test",
            perimeter=Perimeter.objects.create(name="test", folder=test.folder),
            framework=Framework.objects.all()[0],
            field_visibility=score_auditor_only,
        )
        compliance_assessment2 = ComplianceAssessment.objects.create(
            name="test2",
            perimeter=Perimeter.objects.create(name="test2", folder=folder),
            framework=Framework.objects.all()[0],
            field_visibility=score_auditor_only,
        )
        applied_control = AppliedControl.objects.create(name="test", folder=folder)

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Requirement Assessments",
            RequirementAssessment,
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS,
                "observation": REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": test.folder,
                "compliance_assessment": compliance_assessment,
                "requirement": RequirementNode.objects.all()[0],
                "score": None,
            },
            {
                "status": REQUIREMENT_ASSESSMENT_STATUS2,
                "observation": "new " + REQUIREMENT_ASSESSMENT_OBSERVATION,
                "folder": str(folder.id),
                "compliance_assessment": str(compliance_assessment2.id),
                "applied_controls": [str(applied_control.id)],
                "score": 3,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "compliance_assessment": {
                    "id": str(compliance_assessment.id),
                    "str": compliance_assessment.name,
                    "is_locked": False,
                    "min_score": compliance_assessment.min_score,
                    "max_score": compliance_assessment.max_score,
                    "extended_result_enabled": compliance_assessment.extended_result_enabled,
                    "progress_status_enabled": compliance_assessment.progress_status_enabled,
                    "field_visibility": compliance_assessment.field_visibility,
                    "name": compliance_assessment.name,
                    "framework": {
                        "implementation_groups_definition": compliance_assessment.framework.implementation_groups_definition,
                        "field_visibility": compliance_assessment.framework.field_visibility,
                        "str": str(compliance_assessment.framework),
                    },
                },
                "requirement": {
                    "id": str(RequirementNode.objects.all()[0].id),
                    "urn": RequirementNode.objects.all()[0].urn,
                    "annotation": RequirementNode.objects.all()[0].annotation,
                    "name": RequirementNode.objects.all()[0].name,
                    "questions": None,
                    "description": RequirementNode.objects.all()[0].description,
                    "typical_evidence": RequirementNode.objects.all()[
                        0
                    ].typical_evidence,
                    "ref_id": RequirementNode.objects.all()[0].ref_id,
                    "associated_reference_controls": RequirementNode.objects.all()[
                        0
                    ].associated_reference_controls,
                    "associated_threats": RequirementNode.objects.all()[
                        0
                    ].associated_threats,
                    "implementation_groups": RequirementNode.objects.all()[
                        0
                    ].implementation_groups,
                    "display_mode": RequirementNode.objects.all()[0].display_mode,
                    "parent_requirement": {
                        "str": RequirementNode.objects.all()[0].parent_requirement.get(
                            "str"
                        ),
                        "urn": RequirementNode.objects.all()[0].parent_requirement.get(
                            "urn"
                        ),
                        "id": str(
                            RequirementNode.objects.all()[0].parent_requirement.get(
                                "id"
                            )
                        ),
                        "ref_id": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("ref_id"),
                        "name": RequirementNode.objects.all()[0].parent_requirement.get(
                            "name"
                        ),
                        "description": RequirementNode.objects.all()[
                            0
                        ].parent_requirement.get("description"),
                    }
                    if RequirementNode.objects.all()[0].parent_requirement
                    else None,
                },
            },
            {
                "requirement": str(RequirementNode.objects.all()[0].id),
            },
            user_group=test.user_group,
        )

    def test_get_status_choices(self, test):
        """test to get requirement assessments status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Requirement Assessments",
            "status",
            RequirementAssessment.Status.choices,
            user_group=test.user_group,
        )


# ---------------------------------------------------------------------------
# Bulk parent-requirement lookup on /api/requirement-assessments/ list.
#
# `RequirementNode.parent_requirement` falls back to
# `RequirementNode.objects.filter(urn=self.parent_urn).first()` when its
# `_parent_requirement_obj` cache isn't populated — one query per row, so
# the RA list paid an N+1 across every requirement that had a parent.
#
# `RequirementAssessmentViewSet._get_optimized_object_data` now bulk-fetches
# all parent nodes for the page (`urn__in=<parent_urns>`) and seeds the
# `_parent_requirement_obj` cache. The tests below pin:
#   - output: parent_requirement field is populated correctly,
#   - perf: query count for parent lookups is bounded by 1 per page.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRequirementAssessmentListParentBulkLoad:
    @staticmethod
    def _build_audit_with_parent_child_requirements(n_pairs=5):
        """Create a framework with `n_pairs` parent/child requirement pairs,
        plus an audit and one RA per child requirement. Returns the audit."""
        import uuid

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name=f"parent-bulk-fw-{uuid.uuid4().hex[:6]}",
            folder=folder,
            urn=f"urn:test:parent-bulk:{uuid.uuid4().hex[:12]}",
            is_published=True,
        )
        # Create parents (assessable=False is OK; the property only
        # cares about parent_urn matching).
        parent_urns = []
        for i in range(n_pairs):
            parent_urn = f"{fw.urn}:parent:{i}"
            RequirementNode.objects.create(
                framework=fw,
                urn=parent_urn,
                ref_id=f"P{i}",
                name=f"Parent {i}",
                assessable=False,
                folder=folder,
            )
            parent_urns.append(parent_urn)
        # Create child requirements pointing at those parents.
        for i in range(n_pairs):
            RequirementNode.objects.create(
                framework=fw,
                urn=f"{fw.urn}:child:{i}",
                ref_id=f"C{i}",
                parent_urn=parent_urns[i],
                name=f"Child {i}",
                assessable=True,
                folder=folder,
            )
        audit = ComplianceAssessment.objects.create(
            folder=folder,
            framework=fw,
            name=f"parent-bulk-audit-{uuid.uuid4().hex[:6]}",
        )
        audit.create_requirement_assessments()
        return audit

    def test_response_includes_parent_requirement(self, authenticated_client):
        audit = self._build_audit_with_parent_child_requirements(n_pairs=3)
        r = authenticated_client.get(
            "/api/requirement-assessments/",
            {
                "compliance_assessment": str(audit.id),
                "requirement__assessable": "true",
                "limit": 10,
            },
        )
        assert r.status_code == 200, r.content
        body = r.json()
        results = body["results"] if isinstance(body, dict) else body
        # Only assessable children are in scope here; the non-assessable
        # parent rows have no parent_requirement of their own and are
        # filtered out above.
        assert len(results) > 0
        for item in results:
            req = item.get("requirement") or {}
            parent = req.get("parent_requirement")
            assert parent is not None, (
                f"parent_requirement not populated for {req.get('ref_id')!r}"
            )
            # Child ref_id is e.g. "C2"; matching parent urn ends with
            # ":parent:2".
            child_idx = req["ref_id"][1:]
            assert parent["urn"].endswith(f":parent:{child_idx}"), (
                f"wrong parent for child {req['ref_id']!r}: {parent}"
            )

    def test_query_count_is_bounded_by_page_not_by_rows(self, authenticated_client):
        """For N RAs whose requirements all have parent_urn, the bulk
        loader should issue ONE query for parents (not N)."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        audit = self._build_audit_with_parent_child_requirements(n_pairs=10)

        with CaptureQueriesContext(connection) as ctx:
            r = authenticated_client.get(
                "/api/requirement-assessments/",
                {
                    "compliance_assessment": str(audit.id),
                    "requirement__assessable": "true",
                    "limit": 10,
                },
            )
        assert r.status_code == 200, r.content

        # Count queries that look like a per-row parent lookup:
        #   SELECT ... FROM core_requirementnode WHERE urn = ? LIMIT 1
        per_row_parent_lookups = sum(
            1
            for q in ctx.captured_queries
            if 'from "core_requirementnode"' in q["sql"].lower()
            and '"urn" =' in q["sql"].lower()
            and "limit 1" in q["sql"].lower()
        )
        assert per_row_parent_lookups == 0, (
            f"per-row parent lookups detected ({per_row_parent_lookups}); "
            f"expected the bulk loader in _get_optimized_object_data to "
            f"replace them with a single urn__in query"
        )

        # Also: a single bulk parent load — `WHERE urn IN (...)`.
        bulk_parent_loads = sum(
            1
            for q in ctx.captured_queries
            if 'from "core_requirementnode"' in q["sql"].lower()
            and '"urn" in (' in q["sql"].lower()
        )
        assert bulk_parent_loads == 1, (
            f"expected exactly one bulk parent load via urn__in, got {bulk_parent_loads}"
        )

    def test_response_correct_when_no_requirements_have_parents(
        self, authenticated_client
    ):
        """Bulk loader must not emit a query when the page has no
        parent_urns to look up."""
        import uuid
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        folder = Folder.get_root_folder()
        fw = Framework.objects.create(
            name=f"no-parent-fw-{uuid.uuid4().hex[:6]}",
            folder=folder,
            urn=f"urn:test:no-parent:{uuid.uuid4().hex[:12]}",
            is_published=True,
        )
        for i in range(3):
            RequirementNode.objects.create(
                framework=fw,
                urn=f"{fw.urn}:r:{i}",
                ref_id=f"R{i}",
                assessable=True,
                folder=folder,
                # parent_urn intentionally None
            )
        audit = ComplianceAssessment.objects.create(
            folder=folder, framework=fw, name=f"no-parent-{uuid.uuid4().hex[:6]}"
        )
        audit.create_requirement_assessments()

        with CaptureQueriesContext(connection) as ctx:
            r = authenticated_client.get(
                "/api/requirement-assessments/",
                {"compliance_assessment": str(audit.id), "limit": 10},
            )
        assert r.status_code == 200, r.content

        # No urn__in lookup should fire when there are no parent_urns.
        bulk_parent_loads = sum(
            1
            for q in ctx.captured_queries
            if 'from "core_requirementnode"' in q["sql"].lower()
            and '"urn" in (' in q["sql"].lower()
        )
        assert bulk_parent_loads == 0, (
            "bulk loader emitted a query despite no parent_urns on the page"
        )
