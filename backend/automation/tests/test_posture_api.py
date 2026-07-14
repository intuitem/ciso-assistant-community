import pytest
from rest_framework.test import APIClient

from automation.models import PostureAssessment, PostureResult
from core.models import Asset, Finding, FindingsAssessment, Framework, RequirementNode
from iam.models import Folder, Role, RoleAssignment, User


@pytest.fixture
def setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root,
        name="Posture Domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    fw = Framework.objects.create(name="Test Benchmark", folder=root, is_published=True)
    section = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:posture:section:1",
        ref_id="1",
        name="Control Plane",
        assessable=False,
        folder=root,
        is_published=True,
    )
    nodes = {}
    for ref_id in ("1.1", "1.2", "1.3", "2.1"):
        nodes[ref_id] = RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:posture:req:{ref_id}",
            parent_urn=section.urn if ref_id.startswith("1.") else None,
            ref_id=ref_id,
            assessable=True,
            folder=root,
            is_published=True,
        )
    RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:posture:section:9",
        ref_id="9",
        assessable=False,
        folder=root,
        is_published=True,
    )
    asset1 = Asset.objects.create(name="vm-1", folder=domain)
    asset2 = Asset.objects.create(name="vm-2", folder=domain)
    pa = PostureAssessment.objects.create(
        name="Test posture", folder=domain, framework=fw, history_depth=2
    )
    pa.assets.set([asset1, asset2])

    admin = User.objects.create_superuser("posture-admin@tests.com")
    client = APIClient()
    client.force_authenticate(admin)

    return {
        "root": root,
        "domain": domain,
        "framework": fw,
        "nodes": nodes,
        "asset1": asset1,
        "asset2": asset2,
        "pa": pa,
        "client": client,
    }


def upload(client, pa, asset, results, run_id=None, tool=""):
    payload = {"asset": str(asset.id), "results": results}
    if run_id:
        payload["run_id"] = str(run_id)
    if tool:
        payload["tool"] = tool
    return client.post(
        f"/api/automation/posture-assessments/{pa.id}/upload-results/",
        payload,
        format="json",
    )


def get_posture(client, pa):
    return client.get(f"/api/automation/posture-assessments/{pa.id}/posture/").json()


@pytest.mark.django_db
class TestPostureIngestion:
    def test_upload_and_unknown_refs(self, setup):
        s = setup
        res = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "pass"},
                {
                    "ref_id": "1.2",
                    "result": "fail",
                    "actual": "0666",
                    "expected": "0644",
                },
                {"ref_id": "9", "result": "pass"},
                {"ref_id": "404.1", "result": "pass"},
            ],
            tool="kube-bench 0.7",
        )
        assert res.status_code == 200
        body = res.json()
        assert body["created"] == 2
        assert sorted(body["unknown_ref_ids"]) == ["404.1", "9"]

        row = PostureResult.objects.get(requirement=s["nodes"]["1.2"])
        assert row.actual == "0666"
        assert row.expected == "0644"
        assert row.tool == "kube-bench 0.7"
        assert row.source == PostureResult.Source.API
        assert row.imported_by is not None

    def test_run_id_patch_upsert(self, setup):
        s = setup
        first = upload(
            s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}]
        ).json()
        res = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "pass"}],
            run_id=first["run_id"],
        )
        body = res.json()
        assert body["run_id"] == first["run_id"]
        assert body["created"] == 0
        assert body["updated"] == 1
        assert PostureResult.objects.filter(posture_assessment=s["pa"]).count() == 1
        assert PostureResult.objects.get(posture_assessment=s["pa"]).result == "pass"

    def test_invalid_run_id(self, setup):
        s = setup
        res = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "pass"}],
            run_id="not-a-uuid",
        )
        assert res.status_code == 400

    def test_scope_enforcement(self, setup):
        s = setup
        rogue = Asset.objects.create(name="rogue", folder=s["domain"])
        res = upload(s["client"], s["pa"], rogue, [{"ref_id": "1.1", "result": "pass"}])
        assert res.status_code == 400
        assert PostureResult.objects.filter(posture_assessment=s["pa"]).count() == 0

    def test_invalid_result_vocabulary(self, setup):
        s = setup
        res = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "compliant"}],
        )
        assert res.status_code == 400
        assert PostureResult.objects.filter(posture_assessment=s["pa"]).count() == 0

    def test_pruning_per_asset_and_check(self, setup):
        s = setup
        for result in ("fail", "fail", "pass"):
            upload(
                s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": result}]
            )
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.2", "result": "fail"}])

        kept = PostureResult.objects.filter(
            posture_assessment=s["pa"], requirement=s["nodes"]["1.1"]
        )
        assert kept.count() == 2
        assert (
            PostureResult.objects.filter(
                posture_assessment=s["pa"], requirement=s["nodes"]["1.2"]
            ).count()
            == 1
        )
        # same check on the other asset is untouched by asset1's pruning
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])
        assert (
            PostureResult.objects.filter(
                posture_assessment=s["pa"],
                requirement=s["nodes"]["1.1"],
                asset=s["asset2"],
            ).count()
            == 1
        )

    def test_partial_run_fallback(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "fail"},
                {"ref_id": "1.2", "result": "pass"},
                {"ref_id": "1.3", "result": "pass"},
            ],
        )
        partial = upload(
            s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        ).json()

        posture = get_posture(s["client"], s["pa"])
        by_ref = {r["requirement"]["ref_id"]: r for r in posture["results"]}
        assert len(by_ref) == 3
        assert by_ref["1.1"]["result"] == "pass"
        assert by_ref["1.1"]["run_id"] == partial["run_id"]
        assert by_ref["1.2"]["run_id"] != partial["run_id"]

    def test_score_pass_rate_of_applicable(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "pass"},
                {"ref_id": "1.2", "result": "fail"},
                {"ref_id": "1.3", "result": "not_applicable"},
                {"ref_id": "2.1", "result": "error"},
            ],
        )
        assert get_posture(s["client"], s["pa"])["score"] == 50.0

    def test_trend_series_over_runs(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "fail"},
                {"ref_id": "1.2", "result": "fail"},
            ],
        )
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.2", "result": "pass"}])

        points = (
            s["client"]
            .get(f"/api/automation/posture-assessments/{s['pa'].id}/trend/")
            .json()["points"]
        )
        assert [p["score"] for p in points] == [0.0, 50.0, 100.0]
        assert points[0]["counts"] == {"fail": 2}
        assert points[2]["counts"] == {"pass": 2}

    def test_score_none_when_nothing_applicable(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "not_applicable"}],
        )
        assert get_posture(s["client"], s["pa"])["score"] is None


@pytest.mark.django_db
class TestTree:
    def get_tree(self, s, asset=None):
        url = f"/api/automation/posture-assessments/{s['pa'].id}/tree/"
        if asset:
            url += f"?asset={asset.id}"
        return s["client"].get(url).json()

    def test_structure_and_rollup(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "pass"},
                {"ref_id": "1.2", "result": "fail"},
            ],
        )
        body = self.get_tree(s)
        top_refs = [n["ref_id"] for n in body["tree"]]
        assert top_refs == ["1", "2.1", "9"]
        section = body["tree"][0]
        assert [c["ref_id"] for c in section["children"]] == ["1.1", "1.2", "1.3"]
        assert section["counts"] == {"pass": 1, "fail": 1}
        assert not section["assessable"]
        assert len(body["assets"]) == 2

    def test_per_asset_current(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}])
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])

        body = self.get_tree(s, asset=s["asset1"])
        leaf = body["tree"][0]["children"][0]
        assert leaf["current"]["result"] == "fail"
        assert leaf["counts"] == {"fail": 1}
        assert "current" not in body["tree"][0]["children"][1]

    def test_manual_source(self, setup):
        s = setup
        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/upload-results/",
            {
                "asset": str(s["asset1"].id),
                "source": "manual",
                "results": [{"ref_id": "1.1", "result": "pass"}],
            },
            format="json",
        )
        assert res.status_code == 200
        row = PostureResult.objects.get(posture_assessment=s["pa"])
        assert row.source == "manual"

        bad = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/upload-results/",
            {
                "asset": str(s["asset1"].id),
                "source": "telepathy",
                "results": [{"ref_id": "1.1", "result": "pass"}],
            },
            format="json",
        )
        assert bad.status_code == 400


@pytest.mark.django_db
class TestActionPlan:
    def action_plan(self, s):
        return (
            s["client"]
            .get(f"/api/automation/posture-assessments/{s['pa'].id}/action-plan/")
            .json()
        )

    def create_finding(self, s, requirement, asset):
        return s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/create-finding/",
            {"requirement": str(requirement.id), "asset": str(asset.id)},
            format="json",
        )

    def test_fails_listed_unplanned(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "fail"},
                {"ref_id": "1.2", "result": "pass"},
            ],
        )
        plan = self.action_plan(s)
        assert plan["total_fails"] == 1
        assert plan["planned"] == 0
        assert plan["results"][0]["requirement"]["ref_id"] == "1.1"
        assert plan["results"][0]["finding"] is None

    def test_create_finding_lazy_register_and_rejoin(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "fail", "actual": "0666", "expected": "0644"}],
        )
        assert s["pa"].follow_up_assessment is None

        res = self.create_finding(s, s["nodes"]["1.1"], s["asset1"])
        assert res.status_code == 201
        assert res.json()["created"] is True

        s["pa"].refresh_from_db()
        register = s["pa"].follow_up_assessment
        assert register is not None
        assert register.category == FindingsAssessment.Category.POSTURE
        assert register.folder == s["pa"].folder

        finding = Finding.objects.get(id=res.json()["finding"])
        assert finding.requirement_node == s["nodes"]["1.1"]
        assert finding.asset == s["asset1"]
        assert "0666" in finding.description
        assert finding.status == Finding.Status.IDENTIFIED

        again = self.create_finding(s, s["nodes"]["1.1"], s["asset1"])
        assert again.status_code == 200
        assert again.json() == {"finding": str(finding.id), "created": False}
        assert Finding.objects.filter(findings_assessment=register).count() == 1

        plan = self.action_plan(s)
        assert plan["planned"] == 1
        assert plan["results"][0]["finding"]["status"] == "identified"

    def test_create_finding_rejects_foreign_objects(self, setup):
        s = setup
        outside = Asset.objects.create(name="outside", folder=s["domain"])
        res = self.create_finding(s, s["nodes"]["1.1"], outside)
        assert res.status_code == 400


@pytest.mark.django_db
class TestPosturePermissions:
    def make_user(self, email, role_name, domain):
        user = User.objects.create_user(email)
        ra = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=role_name),
            folder=Folder.get_root_folder(),
            is_recursive=True,
        )
        ra.perimeter_folders.add(domain)
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_technical_tester_scoped_to_posture(self, setup):
        s = setup
        tester = self.make_user("tester@tests.com", "BI-RL-TST", s["domain"])

        listed = tester.get("/api/automation/posture-assessments/").json()
        assert listed["count"] == 1

        res = upload(
            tester, s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        )
        assert res.status_code == 200

        audits = tester.get("/api/compliance-assessments/").json()
        assert audits["count"] == 0

    def test_reader_cannot_upload(self, setup):
        s = setup
        reader = self.make_user("reader@tests.com", "BI-RL-AUD", s["domain"])

        listed = reader.get("/api/automation/posture-assessments/").json()
        assert listed["count"] == 1

        res = upload(
            reader, s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        )
        assert res.status_code == 403
        assert PostureResult.objects.filter(posture_assessment=s["pa"]).count() == 0
