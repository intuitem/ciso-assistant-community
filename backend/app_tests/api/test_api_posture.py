import pytest
from rest_framework.test import APIClient

from automation.models import PostureAssessment, PostureResult, PostureRun
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
    def test_upload_rejects_malformed_asset_id(self, setup):
        s = setup
        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/upload-results/",
            {"asset": "not-a-uuid", "results": [{"ref_id": "1.1", "result": "pass"}]},
            format="json",
        )
        assert res.status_code == 400
        assert "UUID" in res.json()["error"]

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
        assert row.run.tool == "kube-bench 0.7"
        assert row.run.posture_assessment == s["pa"]
        assert row.source == PostureResult.Source.API
        assert row.imported_by is not None

    def test_run_object_reuse_and_scoping(self, setup):
        s = setup
        first = upload(
            s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        ).json()
        upload(
            s["client"],
            s["pa"],
            s["asset2"],
            [{"ref_id": "1.1", "result": "pass"}],
            run_id=first["run_id"],
        )
        assert PostureRun.objects.filter(posture_assessment=s["pa"]).count() == 1

        other = PostureAssessment.objects.create(
            name="Other", folder=s["domain"], framework=s["framework"]
        )
        other.assets.set([s["asset1"]])
        res = upload(
            s["client"],
            other,
            s["asset1"],
            [{"ref_id": "1.1", "result": "pass"}],
            run_id=first["run_id"],
        )
        assert res.status_code == 400
        assert "another assessment" in res.json()["error"]

    def test_pruning_garbage_collects_empty_runs(self, setup):
        s = setup
        for result in ("fail", "fail", "pass"):
            upload(
                s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": result}]
            )
        assert PostureRun.objects.filter(posture_assessment=s["pa"]).count() == 2

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
        assert (
            PostureResult.objects.filter(run__posture_assessment=s["pa"]).count() == 1
        )
        assert (
            PostureResult.objects.get(run__posture_assessment=s["pa"]).result == "pass"
        )

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

    def test_auto_enroll_existing_asset(self, setup):
        s = setup
        newcomer = Asset.objects.create(name="vm-new", folder=s["domain"])
        res = upload(
            s["client"], s["pa"], newcomer, [{"ref_id": "1.1", "result": "pass"}]
        )
        assert res.status_code == 200
        assert res.json()["enrolled_asset"] is True
        assert s["pa"].assets.filter(id=newcomer.id).exists()

        res2 = upload(
            s["client"], s["pa"], newcomer, [{"ref_id": "1.2", "result": "pass"}]
        )
        assert res2.json()["enrolled_asset"] is False

    def test_scope_removal_blocked_for_measured_assets(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])

        res = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"assets": [str(s["asset2"].id)]},
            format="json",
        )
        assert res.status_code == 400
        assert "vm-1" in str(res.json())

        res2 = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"assets": [str(s["asset1"].id)]},
            format="json",
        )
        assert res2.status_code == 200
        assert not s["pa"].assets.filter(id=s["asset2"].id).exists()

    def test_orphaned_results_do_not_block_scope_additions(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])
        s["pa"].assets.remove(s["asset1"])  # simulate pre-guard drift

        newcomer = Asset.objects.create(name="vm-3", folder=s["domain"])
        res = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"assets": [str(s["asset2"].id), str(newcomer.id)]},
            format="json",
        )
        assert res.status_code == 200

    def test_purge_asset(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}])
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])

        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/purge-asset/",
            {"asset": str(s["asset1"].id)},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["deleted_results"] == 1
        assert not s["pa"].assets.filter(id=s["asset1"].id).exists()
        assert not s["pa"].results.filter(asset=s["asset1"]).exists()
        assert PostureRun.objects.filter(posture_assessment=s["pa"]).count() == 1
        assert s["pa"].results.filter(asset=s["asset2"]).exists()

    def test_nonexistent_asset_rejected(self, setup):
        s = setup
        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/upload-results/",
            {
                "asset": "00000000-0000-0000-0000-000000000000",
                "results": [{"ref_id": "1.1", "result": "pass"}],
            },
            format="json",
        )
        assert res.status_code == 400
        assert (
            PostureResult.objects.filter(run__posture_assessment=s["pa"]).count() == 0
        )

    def test_invalid_result_vocabulary(self, setup):
        s = setup
        res = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "compliant"}],
        )
        assert res.status_code == 400
        assert (
            PostureResult.objects.filter(run__posture_assessment=s["pa"]).count() == 0
        )

    def test_pruning_per_asset_and_check(self, setup):
        s = setup
        for result in ("fail", "fail", "pass"):
            upload(
                s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": result}]
            )
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.2", "result": "fail"}])

        kept = PostureResult.objects.filter(
            run__posture_assessment=s["pa"], requirement=s["nodes"]["1.1"]
        )
        assert kept.count() == 2
        assert (
            PostureResult.objects.filter(
                run__posture_assessment=s["pa"], requirement=s["nodes"]["1.2"]
            ).count()
            == 1
        )
        # same check on the other asset is untouched by asset1's pruning
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])
        assert (
            PostureResult.objects.filter(
                run__posture_assessment=s["pa"],
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

    def test_trend_per_asset(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}])
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])

        base = f"/api/automation/posture-assessments/{s['pa'].id}/trend/"
        combined = s["client"].get(base).json()["points"]
        asset1_only = s["client"].get(f"{base}?asset={s['asset1'].id}").json()["points"]
        assert combined[-1]["score"] == 50.0
        assert [p["score"] for p in asset1_only] == [0.0]
        assert s["client"].get(f"{base}?asset=not-a-uuid").status_code == 400

    def test_runs_timeline(self, setup):
        s = setup
        r1 = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "pass"},
                {"ref_id": "1.2", "result": "fail"},
            ],
            tool="kube-bench 0.7",
        ).json()
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "fail"}],
            tool="kube-bench 0.8",
        )
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])

        base = f"/api/automation/posture-assessments/{s['pa'].id}/runs/"
        all_runs = s["client"].get(base).json()["runs"]
        assert len(all_runs) == 3
        first = next(r for r in all_runs if r["run_id"] == r1["run_id"])
        assert first["tool"] == "kube-bench 0.7"
        assert first["checks"] == 2
        assert first["passed"] == 1
        assert first["failed"] == 1
        assert first["assets"] == 1

        asset1_runs = s["client"].get(f"{base}?asset={s['asset1'].id}").json()["runs"]
        assert len(asset1_runs) == 2
        assert [r["tool"] for r in asset1_runs] == ["kube-bench 0.7", "kube-bench 0.8"]

    def test_posture_total_checks(self, setup):
        s = setup
        assert get_posture(s["client"], s["pa"])["total_checks"] == 4
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])
        assert get_posture(s["client"], s["pa"])["total_checks"] == 4

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
class TestRunDetail:
    def test_run_detail_multi_asset(self, setup):
        s = setup
        first = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "pass"},
                {"ref_id": "1.2", "result": "fail"},
            ],
            tool="kube-bench 0.7",
        ).json()
        upload(
            s["client"],
            s["pa"],
            s["asset2"],
            [
                {"ref_id": "1.1", "result": "pass"},
                {"ref_id": "1.3", "result": "error"},
            ],
            run_id=first["run_id"],
        )

        res = s["client"].get(
            f"/api/automation/posture-assessments/{s['pa'].id}/runs/{first['run_id']}/"
        )
        assert res.status_code == 200
        body = res.json()
        assert body["run"]["assets"] == 2
        assert body["run"]["checks"] == 4
        assert body["run"]["passed"] == 2
        assert body["run"]["failed"] == 1
        assert body["run"]["tool"] == "kube-bench 0.7"
        asset_ids = {row["asset"]["id"] for row in body["results"]}
        assert asset_ids == {str(s["asset1"].id), str(s["asset2"].id)}

    def test_run_detail_not_found(self, setup):
        s = setup
        res = s["client"].get(
            f"/api/automation/posture-assessments/{s['pa'].id}/runs/00000000-0000-0000-0000-000000000000/"
        )
        assert res.status_code == 404

        other = PostureAssessment.objects.create(
            name="Other", folder=s["domain"], framework=s["framework"]
        )
        other.assets.set([s["asset1"]])
        run = upload(
            s["client"], other, s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        ).json()["run_id"]
        res2 = s["client"].get(
            f"/api/automation/posture-assessments/{s['pa'].id}/runs/{run}/"
        )
        assert res2.status_code == 404

    def test_run_detail_reflects_patch(self, setup):
        s = setup
        run = upload(
            s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}]
        ).json()["run_id"]
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "pass"}],
            run_id=run,
        )
        body = (
            s["client"]
            .get(f"/api/automation/posture-assessments/{s['pa'].id}/runs/{run}/")
            .json()
        )
        assert body["results"][0]["result"] == "pass"
        assert body["run"]["checks"] == 1

    def test_runs_list_still_routes(self, setup):
        s = setup
        res = s["client"].get(f"/api/automation/posture-assessments/{s['pa'].id}/runs/")
        assert res.status_code == 200
        assert res.json() == {"runs": []}


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
        row = PostureResult.objects.get(run__posture_assessment=s["pa"])
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


@pytest.fixture
def ig_setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root, name="IG Domain", content_type=Folder.ContentType.DOMAIN
    )
    fw = Framework.objects.create(
        name="IG Benchmark",
        folder=root,
        is_published=True,
        implementation_groups_definition=[
            {"ref_id": "A", "name": "Automatic"},
            {"ref_id": "B", "name": "Manual"},
        ],
    )
    section = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:ig:section:1",
        ref_id="1",
        assessable=False,
        folder=root,
        is_published=True,
    )
    groups = {"1.1": ["A"], "1.2": ["B"], "1.3": None, "2.1": ["A", "B"]}
    nodes = {}
    for ref_id, igs in groups.items():
        nodes[ref_id] = RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:ig:req:{ref_id}",
            parent_urn=section.urn if ref_id.startswith("1.") else None,
            ref_id=ref_id,
            assessable=True,
            implementation_groups=igs,
            folder=root,
            is_published=True,
        )
    asset = Asset.objects.create(name="ig-vm", folder=domain)
    pa = PostureAssessment.objects.create(
        name="IG posture", folder=domain, framework=fw
    )
    pa.assets.set([asset])
    admin = User.objects.create_superuser("ig-admin@tests.com")
    client = APIClient()
    client.force_authenticate(admin)
    upload(
        client,
        pa,
        asset,
        [
            {"ref_id": "1.1", "result": "pass"},
            {"ref_id": "1.2", "result": "fail"},
            {"ref_id": "1.3", "result": "fail"},
            {"ref_id": "2.1", "result": "fail"},
        ],
    )
    return {"pa": pa, "asset": asset, "client": client, "nodes": nodes}


@pytest.mark.django_db
class TestImplementationGroups:
    def select(self, s, groups):
        s["pa"].selected_implementation_groups = groups
        s["pa"].save(update_fields=["selected_implementation_groups"])

    def test_posture_filtered_by_selection(self, ig_setup):
        s = ig_setup
        self.select(s, ["A"])
        body = get_posture(s["client"], s["pa"])
        refs = sorted(r["requirement"]["ref_id"] for r in body["results"])
        assert refs == ["1.1", "2.1"]
        assert body["total_checks"] == 2
        assert body["score"] == 50.0  # 1 pass / (1 pass + 1 fail)

    def test_no_ig_node_excluded_when_selection_active(self, ig_setup):
        s = ig_setup
        self.select(s, ["A"])
        refs = {
            r["requirement"]["ref_id"]
            for r in get_posture(s["client"], s["pa"])["results"]
        }
        assert "1.3" not in refs

    @pytest.mark.parametrize("selection", [[], None])
    def test_empty_selection_means_no_filtering(self, ig_setup, selection):
        s = ig_setup
        self.select(s, selection)
        body = get_posture(s["client"], s["pa"])
        assert len(body["results"]) == 4
        assert body["total_checks"] == 4

    def test_tree_pruned(self, ig_setup):
        s = ig_setup
        self.select(s, ["B"])
        tree = (
            s["client"]
            .get(f"/api/automation/posture-assessments/{s['pa'].id}/tree/")
            .json()["tree"]
        )
        top_refs = [n["ref_id"] for n in tree]
        assert top_refs == ["1", "2.1"]
        section = tree[0]
        assert [c["ref_id"] for c in section["children"]] == ["1.2"]
        assert section["counts"] == {"fail": 1}

    def test_trend_filtered(self, ig_setup):
        s = ig_setup
        self.select(s, ["A"])
        points = (
            s["client"]
            .get(f"/api/automation/posture-assessments/{s['pa'].id}/trend/")
            .json()["points"]
        )
        assert points[-1]["counts"] == {"pass": 1, "fail": 1}

    def test_runs_stay_unfiltered(self, ig_setup):
        s = ig_setup
        self.select(s, ["A"])
        runs = (
            s["client"]
            .get(f"/api/automation/posture-assessments/{s['pa'].id}/runs/")
            .json()["runs"]
        )
        assert runs[0]["checks"] == 4

    def test_upload_outside_selection_stored_but_hidden(self, ig_setup):
        s = ig_setup
        self.select(s, ["A"])
        res = upload(
            s["client"], s["pa"], s["asset"], [{"ref_id": "1.2", "result": "pass"}]
        )
        assert res.status_code == 200
        assert (
            PostureResult.objects.filter(
                run__posture_assessment=s["pa"], requirement=s["nodes"]["1.2"]
            ).count()
            == 2
        )
        refs = {
            r["requirement"]["ref_id"]
            for r in get_posture(s["client"], s["pa"])["results"]
        }
        assert "1.2" not in refs


@pytest.mark.django_db
class TestImportResults:
    def import_file(self, s, name, content, content_type="text/plain"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/import-results/",
            {
                "asset": str(s["asset1"].id),
                "file": SimpleUploadedFile(name, content, content_type=content_type),
            },
            format="multipart",
        )

    def test_csv_import(self, setup):
        s = setup
        csv_content = (
            b"ref_id,result,actual,message\n"
            b"1.1,pass,mode 0644,\n"
            b"1.2,fail,mode 0666,bad perms\n"
            b"bogus,,\n"
        )
        res = self.import_file(s, "scan.csv", csv_content)
        assert res.status_code == 200
        body = res.json()
        assert body["created"] == 2
        assert len(body["parse_errors"]) == 1
        row = PostureResult.objects.get(requirement=s["nodes"]["1.2"])
        assert row.source == "import"
        assert row.run.tool == "scan.csv"
        assert row.message == "bad perms"

    def test_xlsx_import(self, setup):
        s = setup
        import io

        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["ref_id", "result"])
        ws.append(["1.1", "pass"])
        ws.append(["2.1", "not_applicable"])
        buffer = io.BytesIO()
        wb.save(buffer)
        res = self.import_file(s, "scan.xlsx", buffer.getvalue())
        assert res.status_code == 200
        assert res.json()["created"] == 2

    def test_ocsf_import(self, setup):
        s = setup
        import json

        events = [
            {
                "class_uid": 2003,
                "metadata": {"product": {"name": "prowler", "version": "4.2"}},
                "compliance": {
                    "status": "Pass",
                    "requirements": ["1.1"],
                },
            },
            {
                "class_uid": 2003,
                "compliance": {
                    "status": "Fail",
                    "status_detail": "port open",
                    "requirements": ["CIS-1.2"],
                },
            },
            {
                "class_uid": 2003,
                "compliance": {"status": "Warning", "requirements": ["1.3"]},
            },
            {
                "class_uid": 2003,
                "status": "Suppressed",
                "compliance": {"status": "Fail", "requirements": ["2.1"]},
            },
            {"class_uid": 2002, "compliance": {"status": "Fail"}},
        ]
        res = self.import_file(
            s, "findings.json", json.dumps(events).encode(), "application/json"
        )
        assert res.status_code == 200
        body = res.json()
        assert body["created"] == 3
        assert body["skipped_suppressed"] == 1
        assert body["skipped_other_class"] == 1
        assert body["unknown_ref_ids"] == []

        assert PostureResult.objects.get(requirement=s["nodes"]["1.1"]).result == "pass"
        prefixed = PostureResult.objects.get(requirement=s["nodes"]["1.2"])
        assert prefixed.result == "fail"
        assert prefixed.message == "port open"
        assert prefixed.run.tool == "prowler 4.2"
        assert (
            PostureResult.objects.get(requirement=s["nodes"]["1.3"]).result
            == "not_checked"
        )

    def test_unsupported_extension(self, setup):
        s = setup
        res = self.import_file(s, "scan.pdf", b"whatever")
        assert res.status_code == 400

    def test_malformed_json(self, setup):
        s = setup
        res = self.import_file(s, "scan.json", b"{not json", "application/json")
        assert res.status_code == 400

    def test_import_auto_enrolls(self, setup):
        s = setup
        from django.core.files.uploadedfile import SimpleUploadedFile

        newcomer = Asset.objects.create(name="vm-import", folder=s["domain"])
        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/import-results/",
            {
                "asset": str(newcomer.id),
                "file": SimpleUploadedFile("scan.csv", b"ref_id,result\n1.1,pass\n"),
            },
            format="multipart",
        )
        assert res.status_code == 200
        assert res.json()["enrolled_asset"] is True
        assert s["pa"].assets.filter(id=newcomer.id).exists()


SCANNER_CSV = (
    b"PROVIDER;REQUIREMENTS_ID;STATUS;STATUSEXTENDED;RESOURCENAME\n"
    b"kubernetes;1.1;PASS;pod a ok;pod-a\n"
    b"kubernetes;1.1;FAIL;pod b has caps;pod-b\n"
    b"kubernetes;1.2;PASS;ok;pod-a\n"
    b"kubernetes;1.3;MANUAL;check by hand;cluster\n"
    b"kubernetes;2.1;MUTED;waived;pod-a\n"
)

SCANNER_MAPPING = {
    "delimiter": ";",
    "columns": {
        "ref_id": "REQUIREMENTS_ID",
        "result": "STATUS",
        "message": "STATUSEXTENDED",
    },
    "values": {
        "PASS": "pass",
        "FAIL": "fail",
        "MANUAL": "not_checked",
        "MUTED": "ignore",
    },
    "aggregation": "worst_case",
}


@pytest.mark.django_db
class TestCreateFollowUpAssessment:
    def create(self, s, **extra):
        payload = {
            "name": "posture with follow-up",
            "folder": str(s["domain"].id),
            "framework": str(s["framework"].id),
            **extra,
        }
        return s["client"].post(
            "/api/automation/posture-assessments/", payload, format="json"
        )

    def test_flag_creates_linked_findings_assessment(self, setup):
        s = setup
        res = self.create(s, create_follow_up_assessment=True)
        assert res.status_code == 201
        pa = PostureAssessment.objects.get(id=res.json()["id"])
        follow_up = pa.follow_up_assessment
        assert follow_up is not None
        assert follow_up.name == "posture with follow-up — follow-up"
        assert follow_up.folder == s["domain"]
        assert follow_up.category == FindingsAssessment.Category.POSTURE

    def test_flag_off_creates_nothing(self, setup):
        s = setup
        res = self.create(s, create_follow_up_assessment=False)
        assert res.status_code == 201
        pa = PostureAssessment.objects.get(id=res.json()["id"])
        assert pa.follow_up_assessment is None
        assert FindingsAssessment.objects.count() == 0

    def test_explicit_follow_up_wins_over_flag(self, setup):
        s = setup
        existing = FindingsAssessment.objects.create(
            name="existing", folder=s["domain"]
        )
        res = self.create(
            s,
            create_follow_up_assessment=True,
            follow_up_assessment=str(existing.id),
        )
        assert res.status_code == 201
        pa = PostureAssessment.objects.get(id=res.json()["id"])
        assert pa.follow_up_assessment == existing
        assert FindingsAssessment.objects.count() == 1

    def test_flag_ignored_on_update(self, setup):
        s = setup
        res = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"create_follow_up_assessment": True},
            format="json",
        )
        assert res.status_code == 200
        s["pa"].refresh_from_db()
        assert s["pa"].follow_up_assessment is None
        assert FindingsAssessment.objects.count() == 0


@pytest.mark.django_db
class TestAnalyzeImport:
    def analyze(self, s, content, name="scan.csv"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/analyze-import/",
            {"file": SimpleUploadedFile(name, content)},
            format="multipart",
        )

    def test_analyze_sniffs_delimiter_and_profiles_columns(self, setup):
        res = self.analyze(setup, SCANNER_CSV)
        assert res.status_code == 200
        body = res.json()
        assert body["delimiter"] == ";"
        assert body["headers"][1] == "REQUIREMENTS_ID"
        assert body["row_count"] == 5
        assert body["columns"]["STATUS"]["values"] == [
            "FAIL",
            "MANUAL",
            "MUTED",
            "PASS",
        ]
        assert len(body["sample_rows"]) == 5

    def test_analyze_caps_distinct_values(self, setup):
        content = b"ref;status\n" + b"".join(b"check-%d;PASS\n" % i for i in range(30))
        body = self.analyze(setup, content).json()
        assert body["columns"]["ref"]["values"] is None
        assert body["columns"]["ref"]["distinct"] == "20+"
        assert body["columns"]["status"]["values"] == ["PASS"]

    def test_analyze_rejects_non_csv(self, setup):
        res = self.analyze(setup, b"{}", name="scan.json")
        assert res.status_code == 400


@pytest.mark.django_db
class TestMappedImport:
    def import_mapped(self, s, mapping, content=SCANNER_CSV, asset=None):
        import json as json_

        from django.core.files.uploadedfile import SimpleUploadedFile

        payload = {
            "file": SimpleUploadedFile("prowler.csv", content),
            "mapping": json_.dumps(mapping),
        }
        if asset is not False:
            payload["asset"] = str((asset or s["asset1"]).id)
        return s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/import-results/",
            payload,
            format="multipart",
        )

    def test_worst_case_aggregation(self, setup):
        s = setup
        res = self.import_mapped(s, SCANNER_MAPPING)
        assert res.status_code == 200
        body = res.json()
        assert body["created"] == 3
        assert body["skipped_ignored"] == 1
        row = PostureResult.objects.get(requirement=s["nodes"]["1.1"])
        assert row.result == "fail"
        assert row.actual == "1/2 rows fail"
        assert row.message == "pod b has caps"
        assert PostureResult.objects.get(requirement=s["nodes"]["1.3"]).result == (
            "not_checked"
        )

    def test_best_case_aggregation(self, setup):
        s = setup
        res = self.import_mapped(s, {**SCANNER_MAPPING, "aggregation": "best_case"})
        assert res.status_code == 200
        assert PostureResult.objects.get(requirement=s["nodes"]["1.1"]).result == (
            "pass"
        )

    def test_last_row_aggregation(self, setup):
        s = setup
        res = self.import_mapped(s, {**SCANNER_MAPPING, "aggregation": "last_row"})
        assert res.status_code == 200
        assert PostureResult.objects.get(requirement=s["nodes"]["1.1"]).result == (
            "fail"
        )

    def test_strict_aggregation_rejects_collision(self, setup):
        res = self.import_mapped(setup, {**SCANNER_MAPPING, "aggregation": "strict"})
        assert res.status_code == 400
        assert "1.1" in res.json()["error"]

    def test_unmapped_value_counted_not_fatal(self, setup):
        s = setup
        mapping = {**SCANNER_MAPPING, "values": {"PASS": "pass", "FAIL": "fail"}}
        res = self.import_mapped(s, mapping)
        assert res.status_code == 200
        body = res.json()
        assert body["skipped_unmapped"] == 2
        assert body["created"] == 2

    def test_mapping_validation_errors(self, setup):
        res = self.import_mapped(setup, {**SCANNER_MAPPING, "columns": {}})
        assert res.status_code == 400
        res = self.import_mapped(
            setup,
            {
                **SCANNER_MAPPING,
                "columns": {"ref_id": "NOPE", "result": "STATUS"},
            },
        )
        assert res.status_code == 400
        res = self.import_mapped(setup, {**SCANNER_MAPPING, "aggregation": "median"})
        assert res.status_code == 400

    def test_asset_column_multi_asset_shared_run(self, setup):
        s = setup
        content = (
            b"REQUIREMENTS_ID;STATUS;NAMESPACE\n"
            b"1.1;PASS;vm-1\n"
            b"1.2;FAIL;vm-1\n"
            b"1.1;PASS;vm-2\n"
            b"1.1;PASS;ghost\n"
        )
        mapping = {
            **SCANNER_MAPPING,
            "columns": {
                "ref_id": "REQUIREMENTS_ID",
                "result": "STATUS",
                "asset": "NAMESPACE",
            },
        }
        res = self.import_mapped(s, mapping, content=content, asset=False)
        assert res.status_code == 200
        body = res.json()
        assert body["assets_imported"] == 2
        assert body["created"] == 3
        assert body["skipped_assets"] == ["ghost"]
        run_ids = set(
            PostureResult.objects.filter(source="import").values_list(
                "run_id", flat=True
            )
        )
        assert len(run_ids) == 1
        assert body["enrolled_assets"] == []  # vm-1/vm-2 already scoped in fixture

    def test_explicit_multi_asset_targets_shared_run(self, setup):
        s = setup
        import json as json_

        from django.core.files.uploadedfile import SimpleUploadedFile

        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/import-results/",
            {
                "file": SimpleUploadedFile("prowler.csv", SCANNER_CSV),
                "mapping": json_.dumps(SCANNER_MAPPING),
                "assets": json_.dumps([str(s["asset1"].id), str(s["asset2"].id)]),
            },
            format="multipart",
        )
        assert res.status_code == 200
        body = res.json()
        assert body["assets_imported"] == 2
        assert body["created"] == 6  # 3 aggregated cells x 2 assets
        run_ids = set(
            PostureResult.objects.filter(source="import").values_list(
                "run_id", flat=True
            )
        )
        assert len(run_ids) == 1
        for asset in (s["asset1"], s["asset2"]):
            assert (
                PostureResult.objects.get(
                    asset=asset, requirement=s["nodes"]["1.1"]
                ).result
                == "fail"
            )

    def test_canonical_csv_multi_asset_targets(self, setup):
        s = setup
        import json as json_

        from django.core.files.uploadedfile import SimpleUploadedFile

        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/import-results/",
            {
                "file": SimpleUploadedFile("scan.csv", b"ref_id,result\n1.1,pass\n"),
                "assets": json_.dumps([str(s["asset1"].id), str(s["asset2"].id)]),
            },
            format="multipart",
        )
        assert res.status_code == 200
        body = res.json()
        assert body["assets_imported"] == 2
        assert body["created"] == 2
        assert PostureRun.objects.filter(posture_assessment=s["pa"]).count() == 1

    def test_invalid_assets_param_400(self, setup):
        s = setup
        from django.core.files.uploadedfile import SimpleUploadedFile

        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/import-results/",
            {
                "file": SimpleUploadedFile("scan.csv", b"ref_id,result\n1.1,pass\n"),
                "assets": "not-json",
            },
            format="multipart",
        )
        assert res.status_code == 400

    def test_asset_column_no_match_400(self, setup):
        content = b"REQUIREMENTS_ID;STATUS;NAMESPACE\n1.1;PASS;ghost\n"
        mapping = {
            **SCANNER_MAPPING,
            "columns": {
                "ref_id": "REQUIREMENTS_ID",
                "result": "STATUS",
                "asset": "NAMESPACE",
            },
        }
        res = self.import_mapped(setup, mapping, content=content, asset=False)
        assert res.status_code == 400
        assert res.json()["skipped_assets"] == ["ghost"]


@pytest.mark.django_db
class TestExportResults:
    def test_csv_export_all_and_per_asset(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "pass", "actual": "0644"},
                {"ref_id": "1.2", "result": "fail"},
            ],
        )
        upload(s["client"], s["pa"], s["asset2"], [{"ref_id": "1.1", "result": "pass"}])

        base = f"/api/automation/posture-assessments/{s['pa'].id}/export-results/"
        res = s["client"].get(base)
        assert res.status_code == 200
        assert res["Content-Type"].startswith("text/csv")
        lines = res.content.decode().strip().splitlines()
        assert lines[0].startswith("asset,ref_id,requirement,result")
        assert len(lines) == 4  # header + 3 current rows

        per_asset = s["client"].get(f"{base}?asset={s['asset1'].id}")
        asset_lines = per_asset.content.decode().strip().splitlines()
        assert len(asset_lines) == 3
        assert all("vm-1" in line for line in asset_lines[1:])

    def test_xlsx_export(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])
        res = s["client"].get(
            f"/api/automation/posture-assessments/{s['pa'].id}/export-results/?file_format=xlsx"
        )
        assert res.status_code == 200
        assert "spreadsheetml" in res["Content-Type"]
        assert res.content[:2] == b"PK"

    def test_export_respects_implementation_groups(self, ig_setup):
        s = ig_setup
        s["pa"].selected_implementation_groups = ["A"]
        s["pa"].save(update_fields=["selected_implementation_groups"])
        res = s["client"].get(
            f"/api/automation/posture-assessments/{s['pa'].id}/export-results/"
        )
        lines = res.content.decode().strip().splitlines()
        assert len(lines) == 3  # header + 1.1 + 2.1


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

    def test_non_pass_listed_unplanned(self, setup):
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
        assert plan["total"] == 1
        assert plan["by_result"] == {"fail": 1}
        assert plan["planned"] == 0
        assert plan["results"][0]["requirement"]["ref_id"] == "1.1"
        assert plan["results"][0]["result"] == "fail"
        assert plan["results"][0]["finding"] is None

    def test_ordered_by_severity(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [
                {"ref_id": "1.1", "result": "not_checked"},
                {"ref_id": "1.2", "result": "error"},
                {"ref_id": "2.1", "result": "fail"},
                {"ref_id": "1.3", "result": "pass"},
            ],
        )
        plan = self.action_plan(s)
        assert plan["total"] == 3
        assert plan["by_result"] == {"fail": 1, "error": 1, "not_checked": 1}
        assert [r["result"] for r in plan["results"]] == [
            "fail",
            "error",
            "not_checked",
        ]

    def test_create_finding_requires_attached_follow_up(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}])
        assert s["pa"].follow_up_assessment is None
        res = self.create_finding(s, s["nodes"]["1.1"], s["asset1"])
        assert res.status_code == 400
        assert "follow-up" in res.json()["error"]
        assert FindingsAssessment.objects.count() == 0

    def test_create_finding_and_rejoin(self, setup):
        s = setup
        upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "fail", "actual": "0666", "expected": "0644"}],
        )
        register = FindingsAssessment.objects.create(
            name="follow-up",
            folder=s["pa"].folder,
            category=FindingsAssessment.Category.POSTURE,
        )
        s["pa"].follow_up_assessment = register
        s["pa"].save(update_fields=["follow_up_assessment"])

        res = self.create_finding(s, s["nodes"]["1.1"], s["asset1"])
        assert res.status_code == 201
        assert res.json()["created"] is True

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
class TestBatchAssetMutation:
    def batch(self, s, action, asset):
        return s["client"].post(
            "/api/automation/posture-assessments/batch-action/",
            {
                "action": action,
                "ids": [str(s["pa"].id)],
                "field": "assets",
                "value": [str(asset.id)],
            },
            format="json",
        )

    def test_add_and_remove_asset(self, setup):
        s = setup
        newcomer = Asset.objects.create(name="vm-3", folder=s["domain"])
        res = self.batch(s, "add_m2m", newcomer)
        assert res.status_code == 200
        assert res.json()["failed"] == []
        assert s["pa"].assets.filter(id=newcomer.id).exists()

        res = self.batch(s, "remove_m2m", newcomer)
        assert res.status_code == 200
        assert res.json()["failed"] == []
        assert not s["pa"].assets.filter(id=newcomer.id).exists()
        assert s["pa"].assets.count() == 2

    def test_remove_measured_asset_blocked(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])
        res = self.batch(s, "remove_m2m", s["asset1"])
        assert res.status_code == 200
        assert "recorded results" in str(res.json()["failed"][0]["error"])
        assert s["pa"].assets.filter(id=s["asset1"].id).exists()

    def test_locked_blocks_batch_mutation(self, setup):
        s = setup
        s["pa"].is_locked = True
        s["pa"].save(update_fields=["is_locked"])
        newcomer = Asset.objects.create(name="vm-3", folder=s["domain"])
        res = self.batch(s, "add_m2m", newcomer)
        assert "cannot modify a locked assessment" in str(
            res.json()["failed"][0]["error"]
        )
        assert not s["pa"].assets.filter(id=newcomer.id).exists()


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
        assert (
            PostureResult.objects.filter(run__posture_assessment=s["pa"]).count() == 0
        )

    def test_outsider_sees_nothing(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        outsider = self.make_user("outsider@tests.com", "BI-RL-ANA", other)

        listed = outsider.get("/api/automation/posture-assessments/").json()
        assert listed["count"] == 0

        base = f"/api/automation/posture-assessments/{s['pa'].id}"
        assert outsider.get(f"{base}/").status_code == 404
        assert outsider.get(f"{base}/posture/").status_code == 404
        assert outsider.get(f"{base}/tree/").status_code == 404
        res = upload(
            outsider, s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        )
        assert res.status_code == 404

    def test_unauthenticated_rejected(self, setup):
        s = setup
        anonymous = APIClient()
        res = anonymous.get("/api/automation/posture-assessments/")
        assert res.status_code in (401, 403)
        res = anonymous.get(
            f"/api/automation/posture-assessments/{s['pa'].id}/posture/"
        )
        assert res.status_code in (401, 403)

    def test_results_scoped_to_viewable_assets(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden_asset = Asset.objects.create(name="hidden-vm", folder=other)
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}])
        upload(
            s["client"], s["pa"], hidden_asset, [{"ref_id": "1.1", "result": "fail"}]
        )

        reader = self.make_user("scoped-reader@tests.com", "BI-RL-AUD", s["domain"])
        body = reader.get(
            f"/api/automation/posture-assessments/{s['pa'].id}/posture/"
        ).json()
        asset_ids = {row["asset"]["id"] for row in body["results"]}
        assert str(s["asset1"].id) in asset_ids
        assert str(hidden_asset.id) not in asset_ids
        assert body["score"] == 100.0

        tree = reader.get(
            f"/api/automation/posture-assessments/{s['pa'].id}/tree/"
        ).json()
        assert str(hidden_asset.id) not in {a["id"] for a in tree["assets"]}

        admin_body = get_posture(s["client"], s["pa"])
        assert str(hidden_asset.id) in {
            row["asset"]["id"] for row in admin_body["results"]
        }

    def test_batch_add_invisible_asset_blocked(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        tester = self.make_user("batch-tester@tests.com", "BI-RL-TST", s["domain"])
        res = tester.post(
            "/api/automation/posture-assessments/batch-action/",
            {
                "action": "add_m2m",
                "ids": [str(s["pa"].id)],
                "field": "assets",
                "value": [str(hidden.id)],
            },
            format="json",
        )
        assert "permission denied to add this asset" in str(
            res.json()["failed"][0]["error"]
        )
        assert not s["pa"].assets.filter(id=hidden.id).exists()

    def test_hidden_assets_filtered_from_read(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        s["pa"].assets.add(hidden)

        reader = self.make_user("asset-reader@tests.com", "BI-RL-AUD", s["domain"])
        body = reader.get(f"/api/automation/posture-assessments/{s['pa'].id}/").json()
        ids = {a["id"] for a in body["assets"]}
        assert str(hidden.id) not in ids
        assert {str(s["asset1"].id), str(s["asset2"].id)} <= ids

        admin_body = (
            s["client"].get(f"/api/automation/posture-assessments/{s['pa'].id}/").json()
        )
        assert str(hidden.id) in {a["id"] for a in admin_body["assets"]}

    def test_patch_add_invisible_asset_blocked(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        tester = self.make_user("patcher@tests.com", "BI-RL-TST", s["domain"])
        res = tester.patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {
                "assets": [
                    str(s["asset1"].id),
                    str(s["asset2"].id),
                    str(hidden.id),
                ]
            },
            format="json",
        )
        assert res.status_code == 400
        assert "permission denied" in str(res.json())
        assert not s["pa"].assets.filter(id=hidden.id).exists()

    def test_removal_errors_hide_invisible_asset_names(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        upload(s["client"], s["pa"], hidden, [{"ref_id": "1.1", "result": "fail"}])

        tester = self.make_user("remover@tests.com", "BI-RL-TST", s["domain"])
        res = tester.post(
            "/api/automation/posture-assessments/batch-action/",
            {
                "action": "remove_m2m",
                "ids": [str(s["pa"].id)],
                "field": "assets",
                "value": [str(hidden.id)],
            },
            format="json",
        )
        assert res.json()["failed"] == []
        assert "hidden-vm" not in str(res.json())
        assert s["pa"].assets.filter(id=hidden.id).exists()

        res = tester.patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"assets": [str(s["asset1"].id), str(s["asset2"].id)]},
            format="json",
        )
        assert res.status_code == 200
        assert "hidden-vm" not in str(res.json())
        assert s["pa"].assets.filter(id=hidden.id).exists()
        assert s["pa"].assets.count() == 3

    def test_batch_remove_invisible_asset_kept(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        s["pa"].assets.add(hidden)

        tester = self.make_user("batch-remover@tests.com", "BI-RL-TST", s["domain"])
        res = tester.post(
            "/api/automation/posture-assessments/batch-action/",
            {
                "action": "remove_m2m",
                "ids": [str(s["pa"].id)],
                "field": "assets",
                "value": [str(hidden.id)],
            },
            format="json",
        )
        assert res.json()["failed"] == []
        assert "hidden-vm" not in str(res.json())
        assert s["pa"].assets.filter(id=hidden.id).exists()

    def test_batch_mutate_visible_asset_while_hidden_linked(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        s["pa"].assets.add(hidden)
        newcomer = Asset.objects.create(name="vm-new", folder=s["domain"])

        tester = self.make_user("mixed@tests.com", "BI-RL-TST", s["domain"])
        res = tester.post(
            "/api/automation/posture-assessments/batch-action/",
            {
                "action": "add_m2m",
                "ids": [str(s["pa"].id)],
                "field": "assets",
                "value": [str(newcomer.id)],
            },
            format="json",
        )
        assert res.json()["failed"] == []
        assert s["pa"].assets.filter(id=newcomer.id).exists()

        res = tester.post(
            "/api/automation/posture-assessments/batch-action/",
            {
                "action": "remove_m2m",
                "ids": [str(s["pa"].id)],
                "field": "assets",
                "value": [str(newcomer.id)],
            },
            format="json",
        )
        assert res.json()["failed"] == []
        assert not s["pa"].assets.filter(id=newcomer.id).exists()
        assert s["pa"].assets.filter(id=hidden.id).exists()

    def test_patch_keeps_invisible_unmeasured_asset(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        s["pa"].assets.add(hidden)

        tester = self.make_user("keeper@tests.com", "BI-RL-TST", s["domain"])
        res = tester.patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"assets": [str(s["asset1"].id)]},
            format="json",
        )
        assert res.status_code == 200
        remaining = set(s["pa"].assets.values_list("id", flat=True))
        assert remaining == {s["asset1"].id, hidden.id}

    def test_create_finding_invisible_asset_rejected(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        hidden = Asset.objects.create(name="hidden-vm", folder=other)
        s["pa"].assets.add(hidden)
        register = FindingsAssessment.objects.create(
            name="follow-up",
            folder=s["pa"].folder,
            category=FindingsAssessment.Category.POSTURE,
        )
        s["pa"].follow_up_assessment = register
        s["pa"].save(update_fields=["follow_up_assessment"])

        tester = self.make_user("finder@tests.com", "BI-RL-TST", s["domain"])
        res = tester.post(
            f"/api/automation/posture-assessments/{s['pa'].id}/create-finding/",
            {"requirement": str(s["nodes"]["1.1"].id), "asset": str(hidden.id)},
            format="json",
        )
        assert res.status_code == 400
        assert Finding.objects.count() == 0

    def test_cross_domain_follow_up_link_rejected(self, setup):
        s = setup
        other = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name="Other Domain",
            content_type=Folder.ContentType.DOMAIN,
        )
        foreign = FindingsAssessment.objects.create(
            name="foreign register",
            folder=other,
            category=FindingsAssessment.Category.POSTURE,
        )
        tester = self.make_user("linker@tests.com", "BI-RL-TST", s["domain"])
        res = tester.patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"follow_up_assessment": str(foreign.id)},
            format="json",
        )
        assert res.status_code == 400
        s["pa"].refresh_from_db()
        assert s["pa"].follow_up_assessment is None


@pytest.mark.django_db
class TestLockedAssessment:
    def test_locked_blocks_mutations(self, setup):
        s = setup
        upload(s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "fail"}])
        s["pa"].is_locked = True
        s["pa"].save(update_fields=["is_locked"])

        res = upload(
            s["client"], s["pa"], s["asset1"], [{"ref_id": "1.1", "result": "pass"}]
        )
        assert res.status_code == 400
        assert "locked" in res.json()["error"]

        res = s["client"].post(
            f"/api/automation/posture-assessments/{s['pa'].id}/purge-asset/",
            {"asset": str(s["asset1"].id)},
            format="json",
        )
        assert res.status_code == 400

        res = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"name": "renamed"},
            format="json",
        )
        assert res.status_code == 400

        res = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"is_locked": False},
            format="json",
        )
        assert res.status_code == 200
        s["pa"].refresh_from_db()
        assert s["pa"].is_locked is False


@pytest.mark.django_db
class TestIngestionValidation:
    def test_non_dict_entries_rejected(self, setup):
        s = setup
        res = upload(s["client"], s["pa"], s["asset1"], ["1.1", "1.2"])
        assert res.status_code == 400
        assert "objects" in res.json()["error"]

    def test_long_values_truncated(self, setup):
        s = setup
        res = upload(
            s["client"],
            s["pa"],
            s["asset1"],
            [{"ref_id": "1.1", "result": "fail", "actual": "x" * 600}],
        )
        assert res.status_code == 200
        row = PostureResult.objects.get(run__posture_assessment=s["pa"])
        assert len(row.actual) == 255

    def test_history_depth_zero_rejected(self, setup):
        s = setup
        res = s["client"].patch(
            f"/api/automation/posture-assessments/{s['pa'].id}/",
            {"history_depth": 0},
            format="json",
        )
        assert res.status_code == 400
