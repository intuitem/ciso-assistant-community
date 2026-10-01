import uuid
from datetime import date

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    HistoricalMetric,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
)
from iam.models import Folder, User

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
        # Framework has no Meta ordering, so all()[0]/all()[1] are
        # nondeterministic on PostgreSQL — pin the import order explicitly.
        frameworks = list(Framework.objects.order_by("created_at", "pk"))

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Compliance Assessments",
            ComplianceAssessment,
            {
                "name": COMPLIANCE_ASSESSMENT_NAME,
                "description": COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION,
                "perimeter": perimeter,
                "framework": frameworks[0],
            },
            {
                "name": "new " + COMPLIANCE_ASSESSMENT_NAME,
                "description": "new " + COMPLIANCE_ASSESSMENT_DESCRIPTION,
                "version": COMPLIANCE_ASSESSMENT_VERSION + ".1",
                "perimeter": str(perimeter2.id),
                "framework": str(frameworks[1].id),
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
                    "id": str(frameworks[0].id),
                    "urn": frameworks[0].urn,
                    "str": str(frameworks[0]),
                    "implementation_groups_definition": None,
                    "outcomes_definition": [],
                    "reference_controls": [
                        {"id": str(rc["id"]), "str": rc["str"], "urn": rc["urn"]}
                        for rc in frameworks[0].reference_controls
                    ],
                    "min_score": frameworks[0].min_score,
                    "max_score": frameworks[0].max_score,
                    "ref_id": str(frameworks[0].ref_id),
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


# Progress modes: the status field's visibility is the mode switch. It is
# visible by default (DEFAULT_VISIBILITY), so a bare audit is STATUS MODE
# (only `done` counts). Hiding it switches to CONTENT MODE (questionnaire,
# else result when visible, else score above the resolved minimum).
_HIDDEN_PAIR = {"auditor": "hidden", "respondent": "hidden"}


def _content_mode(**extra_hidden_fields) -> dict:
    fv = {"status": dict(_HIDDEN_PAIR)}
    for field in extra_hidden_fields.get("hide", []):
        fv[field] = dict(_HIDDEN_PAIR)
    return fv


@pytest.mark.django_db
class TestComplianceAssessmentListProgress:
    """`/api/compliance-assessments/` list `progress` field is computed by
    `ComplianceAssessmentViewSet._get_optimized_object_data` (per-page,
    per-mode GROUP BY) and read from `optimized_data` by the list serializer.
    Pin the numeric output across the modes and branches so the path
    can't drift silently."""

    def test_progress_zero_when_all_not_assessed(self, authenticated_client):
        """Default RA state → 0 % in both modes (no done, no content)."""
        framework = _make_framework()
        for i in range(4):
            _make_requirement(framework, f"R{i}")
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()

        assert _list_progress(authenticated_client, audit.id) == 0

    def test_status_mode_only_done_counts(self, authenticated_client):
        """Status field visible (the default) → status mode: results are
        ignored, only `done` requirements count."""
        framework = _make_framework()
        for i in range(4):
            _make_requirement(framework, f"D{i}")
        audit = _make_audit(Folder.get_root_folder(), framework)
        audit.create_requirement_assessments()

        ras = list(audit.requirement_assessments.all())
        for ra in ras:  # content everywhere, must not count
            ra.result = RequirementAssessment.Result.COMPLIANT
            ra.save(update_fields=["result"])
        ras[0].status = RequirementAssessment.Status.DONE
        ras[0].save(update_fields=["status"])

        assert _list_progress(authenticated_client, audit.id) == 25

    def test_progress_partial_assessed(self, authenticated_client):
        """Content mode (status hidden): 1 of 4 RAs marked compliant → 25 %."""
        framework = _make_framework()
        for i in range(4):
            _make_requirement(framework, f"P{i}")
        audit = _make_audit(
            Folder.get_root_folder(), framework, field_visibility=_content_mode()
        )
        audit.create_requirement_assessments()

        ras = list(audit.requirement_assessments.all())
        ras[0].result = RequirementAssessment.Result.COMPLIANT
        ras[0].save(update_fields=["result"])

        assert _list_progress(authenticated_client, audit.id) == 25

    def test_score_alone_does_not_count_when_result_visible(self, authenticated_client):
        """Content mode with the result field visible: the result decides,
        a score alone (e.g. left by the scoring pre-fill) never counts."""
        framework = _make_framework()
        for i in range(2):
            _make_requirement(framework, f"S{i}")
        audit = _make_audit(
            Folder.get_root_folder(), framework, field_visibility=_content_mode()
        )
        audit.create_requirement_assessments()

        ras = list(audit.requirement_assessments.all())
        ras[0].score = 3  # leave result = NOT_ASSESSED on purpose
        ras[0].save(update_fields=["score"])

        assert _list_progress(authenticated_client, audit.id) == 0

    def test_score_only_audit_min_does_not_count(self, authenticated_client):
        """Score-only audit (status and result hidden): a score left at the
        scale minimum is indistinguishable from the pre-fill and does not
        count; a score strictly above the minimum does."""
        framework = _make_framework()  # min_score=0, max_score=4
        for i in range(2):
            _make_requirement(framework, f"SO{i}")
        audit = _make_audit(
            Folder.get_root_folder(),
            framework,
            field_visibility=_content_mode(hide=["result"]),
        )
        audit.create_requirement_assessments()

        ras = list(audit.requirement_assessments.all())
        ras[0].score = 0  # == resolved minimum: pre-fill value
        ras[0].save(update_fields=["score"])
        ras[1].score = 3  # deliberate scoring
        ras[1].save(update_fields=["score"])

        assert _list_progress(authenticated_client, audit.id) == 50

    def test_progress_all_assessed(self, authenticated_client):
        framework = _make_framework()
        for i in range(3):
            _make_requirement(framework, f"A{i}")
        audit = _make_audit(
            Folder.get_root_folder(), framework, field_visibility=_content_mode()
        )
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
        audit = _make_audit(
            Folder.get_root_folder(), framework, field_visibility=_content_mode()
        )
        audit.create_requirement_assessments()

        for ra in audit.requirement_assessments.all():
            if ra.requirement.ref_id == "AS-0":
                ra.result = RequirementAssessment.Result.COMPLIANT
                ra.save(update_fields=["result"])

        # 1 / 2 assessable assessed → 50 %, not 1/4 = 25 %.
        assert _list_progress(authenticated_client, audit.id) == 50

    def test_progress_with_implementation_groups(self, authenticated_client):
        """The implementation-groups branch (in-memory scalar loop) must
        compute the same cascade when only some RAs match the audit's IGs."""
        framework = _make_framework()
        for i in range(2):
            _make_requirement(framework, f"G1-{i}", implementation_groups=["G1"])
        for i in range(2):
            _make_requirement(framework, f"G2-{i}", implementation_groups=["G2"])
        audit = _make_audit(
            Folder.get_root_folder(),
            framework,
            selected_implementation_groups=["G1"],
            field_visibility=_content_mode(),
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


# ---------------------------------------------------------------------------
# Map-from-audit feature
# ---------------------------------------------------------------------------

R = RequirementAssessment.Result
S = RequirementAssessment.Status


@pytest.mark.django_db
class TestComplianceAssessmentMapFrom:
    """Integration tests for the map-from-audit feature: the merge strategy in
    core.mappings.merge.compute_map_from_merge plus the `map_from`
    (POST) and `map_from_preview` (GET) endpoints and their guards.

    Same-framework cases exercise the full-coverage merge path without needing
    a mapping library; cross-framework cases load a RequirementMappingSet into
    the engine to exercise partial coverage and mapping_inference.
    """

    # --- helpers -----------------------------------------------------------
    def _audit(self, framework, **kwargs):
        audit = _make_audit(Folder.get_root_folder(), framework, **kwargs)
        audit.create_requirement_assessments()
        return audit

    def _ra(self, audit, ref):
        return audit.requirement_assessments.get(requirement__ref_id=ref)

    def _map_from(self, client, target, source):
        return client.post(
            f"/api/compliance-assessments/{target.id}/map_from/",
            {"source_audit_id": str(source.id)},
            format="json",
        )

    def _preview(self, client, target, source_id):
        return client.get(
            f"/api/compliance-assessments/{target.id}/map_from_preview/",
            {"source_audit_id": str(source_id)},
        )

    def _load_mapping(self, source_fw, target_fw, mappings):
        """mappings: list of (source_ref_id, target_ref_id, relationship)."""
        rms = {
            "urn": f"urn:test:req_mapping_set:{uuid.uuid4().hex[:8]}",
            "name": "test mapping",
            "source_framework_urn": source_fw.urn,
            "target_framework_urn": target_fw.urn,
            "requirement_mappings": [
                {
                    "source_requirement_urn": f"{source_fw.urn}:req:{s}",
                    "target_requirement_urn": f"{target_fw.urn}:req:{t}",
                    "relationship": rel,
                }
                for (s, t, rel) in mappings
            ],
        }
        StoredLibrary.objects.create(
            name="test mapping lib",
            urn=f"urn:test:lib:{uuid.uuid4().hex[:8]}",
            ref_id=f"test-map-{uuid.uuid4().hex[:6]}",
            locale="en",
            version=1,
            hash_checksum=uuid.uuid4().hex,
            is_loaded=True,
            content={"requirement_mapping_sets": [rms]},
        )

    # --- same-framework merge strategy -------------------------------------
    def test_full_copy_into_empty_target(self, authenticated_client):
        """Same framework, empty target: source values are copied verbatim,
        M2M unioned; an untouched requirement stays at its default."""
        fw = _make_framework()
        for r in ("A", "B"):
            _make_requirement(fw, r)
        source = self._audit(fw)
        target = self._audit(fw)
        # Scoring is hidden by default; enable it on both audits so the
        # visibility intersection includes score/is_scored.
        source.scoring_enabled = True
        source.save()
        target.scoring_enabled = True
        target.save()

        ctrl = AppliedControl.objects.create(
            name="ctrl", folder=Folder.get_root_folder()
        )
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.status = S.DONE
        sa.score = 3
        sa.is_scored = True
        sa.observation = "src obs"
        sa.save()
        sa.applied_controls.add(ctrl)

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert resp.json()["updated_count"] == 1

        ta = self._ra(target, "A")
        assert ta.result == R.COMPLIANT
        assert ta.status == S.DONE
        assert ta.score == 3
        assert ta.is_scored is True
        assert ta.observation == "src obs"
        assert ctrl in ta.applied_controls.all()
        # mapping_inference is not recorded for a same-framework direct copy
        assert ta.mapping_inference in ({}, None)
        # untouched requirement keeps the default
        assert self._ra(target, "B").result == R.NOT_ASSESSED

    def test_source_default_does_not_overwrite_assessed_target(
        self, authenticated_client
    ):
        """Full coverage must NOT clobber a real target result with a source
        value that is merely the default (not_assessed). Regression guard."""
        fw = _make_framework()
        _make_requirement(fw, "A")
        _make_requirement(fw, "B")
        source = self._audit(fw)
        target = self._audit(fw)

        # source A is meaningful so the call maps something; source B stays default
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.save()
        # target B was manually assessed
        tb = self._ra(target, "B")
        tb.result = R.PARTIALLY_COMPLIANT
        tb.save()

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_200_OK, resp.content

        # source B (not_assessed) must not overwrite target B (partially_compliant)
        assert self._ra(target, "B").result == R.PARTIALLY_COMPLIANT

    def test_observation_concatenated_and_idempotent(self, authenticated_client):
        fw = _make_framework()
        _make_requirement(fw, "A")
        source = self._audit(fw)
        target = self._audit(fw)

        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.observation = "SRC"
        sa.save()
        ta = self._ra(target, "A")
        ta.observation = "TGT"
        ta.save()

        self._map_from(authenticated_client, target, source)
        ta = self._ra(target, "A")
        assert ta.observation == "TGT\n\n---\nSRC"

        # re-run map-from with the same source: no duplicate appended
        self._map_from(authenticated_client, target, source)
        assert self._ra(target, "A").observation == "TGT\n\n---\nSRC"

    def test_is_scored_not_leaked_when_scoring_disabled(self, authenticated_client):
        fw = _make_framework()
        _make_requirement(fw, "A")
        source = self._audit(fw)
        target = self._audit(fw)
        source.scoring_enabled = True
        source.save()
        target.scoring_enabled = False
        target.save()

        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.score = 3
        sa.is_scored = True
        sa.save()

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_200_OK, resp.content
        ta = self._ra(target, "A")
        assert ta.is_scored is False
        assert ta.score is None

    def test_preview_shape(self, authenticated_client):
        fw = _make_framework()
        _make_requirement(fw, "A")
        _make_requirement(fw, "B")
        source = self._audit(fw)
        target = self._audit(fw)
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.save()

        resp = self._preview(authenticated_client, target, source.id)
        assert resp.status_code == status.HTTP_200_OK, resp.content
        body = resp.json()
        assert body["updated_count"] == 1
        # IG-correct denominator: assessable RAs that actually exist
        assert body["assessable_requirements_count"] == 2
        assert "current_results" in body and "projected_results" in body
        diffs = body["differences"]
        assert len(diffs) == 1
        diff = diffs[0]
        assert diff["requirement"]["ref_id"] == "A"
        # source requirement surfaced in the preview
        assert diff["sources"] and diff["sources"][0]["ref_id"] == "A"

    # --- endpoint guards ---------------------------------------------------
    def test_locked_target_rejected(self, authenticated_client):
        fw = _make_framework()
        _make_requirement(fw, "A")
        source = self._audit(fw)
        target = self._audit(fw)
        target.is_locked = True
        target.save()

        assert (
            self._map_from(authenticated_client, target, source).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            self._preview(authenticated_client, target, source.id).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_unknown_source_rejected(self, authenticated_client):
        fw = _make_framework()
        _make_requirement(fw, "A")
        target = self._audit(fw)
        resp = authenticated_client.post(
            f"/api/compliance-assessments/{target.id}/map_from/",
            {"source_audit_id": str(uuid.uuid4())},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_preview_requires_source_param(self, authenticated_client):
        fw = _make_framework()
        _make_requirement(fw, "A")
        target = self._audit(fw)
        resp = authenticated_client.get(
            f"/api/compliance-assessments/{target.id}/map_from_preview/"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # --- cross-framework (mapping engine) ----------------------------------
    def test_cross_framework_full_equal_copies_and_sets_inference(
        self, authenticated_client
    ):
        src_fw = _make_framework()
        tgt_fw = _make_framework()
        _make_requirement(src_fw, "A")
        _make_requirement(tgt_fw, "X")
        self._load_mapping(src_fw, tgt_fw, [("A", "X", "equal")])

        source = self._audit(src_fw)
        target = self._audit(tgt_fw)
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.save()

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_200_OK, resp.content

        tx = self._ra(target, "X")
        assert tx.result == R.COMPLIANT
        # cross-framework records provenance
        srcs = (tx.mapping_inference or {}).get("source_requirement_assessments", {})
        assert any(f"{src_fw.urn}:req:A" == k for k in srcs)

    def test_cross_framework_intersect_only_fills_and_adds_controls(
        self, authenticated_client
    ):
        src_fw = _make_framework()
        tgt_fw = _make_framework()
        _make_requirement(src_fw, "A")
        _make_requirement(tgt_fw, "X")
        self._load_mapping(src_fw, tgt_fw, [("A", "X", "intersect")])

        source = self._audit(src_fw)
        target = self._audit(tgt_fw)
        ctrl = AppliedControl.objects.create(name="c", folder=Folder.get_root_folder())
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.save()
        sa.applied_controls.add(ctrl)
        # target X already assessed -> partial coverage must leave it alone
        tx = self._ra(target, "X")
        tx.result = R.PARTIALLY_COMPLIANT
        tx.save()

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_200_OK, resp.content

        tx = self._ra(target, "X")
        assert tx.result == R.PARTIALLY_COMPLIANT  # not overwritten
        assert ctrl in tx.applied_controls.all()  # but control added

    def test_cross_framework_no_mapping_path_rejected(self, authenticated_client):
        src_fw = _make_framework()
        tgt_fw = _make_framework()
        _make_requirement(src_fw, "A")
        _make_requirement(tgt_fw, "X")
        # no mapping library loaded for this pair

        source = self._audit(src_fw)
        target = self._audit(tgt_fw)
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.save()

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Object-level authorization on custom detail actions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestComplianceAssessmentDetailActionAuthorization:
    """The `frameworks` and `progress_ts` detail actions must fetch the audit
    through `get_object()` so folder scoping applies: a user without a role
    on the audit's folder gets the same 404 as the standard detail endpoint
    and cannot tell whether the object exists."""

    @pytest.fixture
    def audit(self, app_config):
        framework = _make_framework()
        _make_requirement(framework, "R0")
        domain = Folder.objects.create(
            name="idor-domain", parent_folder=Folder.get_root_folder()
        )
        audit = _make_audit(domain, framework)
        audit.create_requirement_assessments()
        HistoricalMetric.objects.create(
            model="ComplianceAssessment",
            object_id=audit.id,
            date=date(2026, 1, 1),
            data={"reqs": {"progress_perc": 42}},
        )
        return audit

    @pytest.fixture
    def outsider_client(self, app_config):
        """An authenticated user with no role assignment on any folder."""
        user = User.objects.create_user("outsider@tests.com")
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
        )
        return client

    def test_frameworks_requires_folder_access(
        self, authenticated_client, outsider_client, audit
    ):
        url = f"/api/compliance-assessments/{audit.id}/frameworks/"
        assert outsider_client.get(url).status_code == status.HTTP_404_NOT_FOUND
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert isinstance(resp.json(), list)

    def test_progress_ts_requires_folder_access(
        self, authenticated_client, outsider_client, audit
    ):
        url = f"/api/compliance-assessments/{audit.id}/progress_ts/"
        assert outsider_client.get(url).status_code == status.HTTP_404_NOT_FOUND
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK, resp.content
        # Snapshots are date-ordered; creating the audit auto-records one for
        # today, so only pin the synthetic (oldest) point.
        assert resp.json()["data"][0] == ["2026-01-01", 42]

    def test_unknown_audit_is_404(self, authenticated_client):
        """Nonexistent UUIDs must 404: `frameworks` used to raise a bare
        DoesNotExist (500) and `progress_ts` returned an empty 200."""
        missing = uuid.uuid4()
        for action in ("frameworks", "progress_ts"):
            resp = authenticated_client.get(
                f"/api/compliance-assessments/{missing}/{action}/"
            )
            assert resp.status_code == status.HTTP_404_NOT_FOUND, action


def _list_ordered_ids(
    client: APIClient, ordering: str, among: list | None
) -> list[str]:
    r = client.get(f"/api/compliance-assessments/?ordering={ordering}")
    assert r.status_code == status.HTTP_200_OK, r.content
    body = r.json()
    results = body["results"] if isinstance(body, dict) and "results" in body else body
    if among is None:
        return [item["id"] for item in results]
    wanted = {str(audit_id) for audit_id in among}
    return [item["id"] for item in results if item["id"] in wanted]


def _audit_at_progress(folder: Folder, done: int, total: int) -> ComplianceAssessment:
    framework = _make_framework()
    for i in range(total):
        _make_requirement(framework, f"O{i}")
    audit = _make_audit(folder, framework)
    audit.create_requirement_assessments()
    for ra in list(audit.requirement_assessments.all())[:done]:
        ra.status = RequirementAssessment.Status.DONE
        ra.save(update_fields=["status"])
    return audit


@pytest.mark.django_db
class TestComplianceAssessmentProgressOrdering:
    """`progress` has no column: it is derived in Python, so DRF used to drop
    `?ordering=progress` as an unknown field and the header click did nothing."""

    def _fixture(self, client: APIClient) -> dict[int, ComplianceAssessment]:
        root = Folder.get_root_folder()
        audits = {
            0: _audit_at_progress(root, 0, 4),
            50: _audit_at_progress(root, 2, 4),
            100: _audit_at_progress(root, 4, 4),
        }
        # Implementation-group audit: only the 3 selected requirements count,
        # one of them done. This is the branch no SQL annotation can express.
        framework = _make_framework()
        for i in range(3):
            _make_requirement(framework, f"G{i}", implementation_groups=["g1"])
        _make_requirement(framework, "G3", implementation_groups=["g2"])
        ig_audit = _make_audit(root, framework, selected_implementation_groups=["g1"])
        ig_audit.create_requirement_assessments()
        selected = ig_audit.requirement_assessments.filter(
            requirement__implementation_groups=["g1"]
        )
        first = selected.first()
        first.status = RequirementAssessment.Status.DONE
        first.save(update_fields=["status"])
        audits[33] = ig_audit

        for expected, audit in audits.items():
            assert _list_progress(client, audit.id) == expected
        return audits

    def test_ascending_orders_by_computed_progress(
        self, authenticated_client: APIClient
    ) -> None:
        audits = self._fixture(authenticated_client)
        ids = _list_ordered_ids(
            authenticated_client, "progress", [a.id for a in audits.values()]
        )
        assert ids == [str(audits[p].id) for p in (0, 33, 50, 100)]

    def test_descending_orders_by_computed_progress(
        self, authenticated_client: APIClient
    ) -> None:
        audits = self._fixture(authenticated_client)
        ids = _list_ordered_ids(
            authenticated_client, "-progress", [a.id for a in audits.values()]
        )
        assert ids == [str(audits[p].id) for p in (100, 50, 33, 0)]

    def test_first_page_holds_the_globally_highest(
        self, authenticated_client: APIClient
    ) -> None:
        """Ranking the page after slicing it would reorder the same rows
        instead of choosing them, so pin the slice against the full order."""
        self._fixture(authenticated_client)
        full = _list_ordered_ids(authenticated_client, "-progress", among=None)

        r = authenticated_client.get(
            "/api/compliance-assessments/?ordering=-progress&limit=2"
        )
        assert r.status_code == status.HTTP_200_OK, r.content
        assert [item["id"] for item in r.json()["results"]] == full[:2]
