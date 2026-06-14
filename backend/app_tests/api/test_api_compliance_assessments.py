import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
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


# ---------------------------------------------------------------------------
# Map-from-audit feature
# ---------------------------------------------------------------------------

R = RequirementAssessment.Result
S = RequirementAssessment.Status


@pytest.mark.django_db
class TestComplianceAssessmentMapFrom:
    """Integration tests for the map-from-audit feature: the merge strategy in
    ComplianceAssessmentViewSet._compute_map_from_merge plus the `map_from`
    (POST) and `map_from_preview` (GET) endpoints and their guards.

    Same-framework cases exercise the full-coverage merge path without needing
    a mapping library; cross-framework cases load a RequirementMappingSet into
    the engine to exercise partial coverage and mapping_inference.
    """

    @pytest.fixture(autouse=True)
    def _reset_engine_cache(self):
        # After each test the django_db transaction rolls back; reload the
        # global engine so any mapping libraries we created don't leak into
        # other tests via the in-memory cache.
        yield
        from core.mappings.engine import engine

        engine.reload_cache()

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
        from core.mappings.engine import engine

        engine.reload_cache()

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
        from core.mappings.engine import engine

        engine.reload_cache()

        source = self._audit(src_fw)
        target = self._audit(tgt_fw)
        sa = self._ra(source, "A")
        sa.result = R.COMPLIANT
        sa.save()

        resp = self._map_from(authenticated_client, target, source)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
