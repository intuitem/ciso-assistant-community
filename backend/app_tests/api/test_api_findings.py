import pytest
from rest_framework.test import APIClient

from core.models import Finding, FindingsAssessment, TaskTemplate
from iam.models import Folder, User


@pytest.fixture
def setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root,
        name="Findings Domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    other_domain = Folder.objects.create(
        parent_folder=root,
        name="Other Domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    binder = FindingsAssessment.objects.create(name="Pentest 2026", folder=domain)
    other_binder = FindingsAssessment.objects.create(
        name="Audit 2026", folder=other_domain
    )

    admin = User.objects.create_superuser("findings-admin@tests.com")
    client = APIClient()
    client.force_authenticate(admin)

    return {
        "domain": domain,
        "other_domain": other_domain,
        "binder": binder,
        "other_binder": other_binder,
        "client": client,
    }


def create_finding(client, **payload):
    return client.post("/api/findings/", payload, format="json")


def set_flag(enabled: bool):
    from global_settings.models import GlobalSettings
    from global_settings.utils import clear_feature_flags_cache

    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    gs.value = {**(gs.value or {}), "findings_from_requirements": enabled}
    gs.save()
    clear_feature_flags_cache()


class TestFindingsFromRequirements:
    """A finding raised from a requirement lands in the audit's own binder."""

    @pytest.fixture
    def audit(self, setup):
        from core.models import (
            ComplianceAssessment,
            Framework,
            RequirementAssessment,
            RequirementNode,
        )

        framework = Framework.objects.create(
            name="F", folder=Folder.get_root_folder(), is_published=True
        )
        node = RequirementNode.objects.create(
            framework=framework,
            urn="urn:test:req:1",
            ref_id="1",
            assessable=True,
            folder=Folder.get_root_folder(),
            is_published=True,
        )
        assessment = ComplianceAssessment.objects.create(
            name="ISO audit", folder=setup["domain"], framework=framework
        )
        # Requirement assessments are created by the audit's create flow, not by the
        # model's save, so make the one under test explicitly.
        return assessment, RequirementAssessment.objects.create(
            compliance_assessment=assessment,
            requirement=node,
            folder=setup["domain"],
        )

    def test_the_setting_gates_it(self, setup, audit):
        _, requirement_assessment = audit
        set_flag(False)
        res = setup["client"].post(
            f"/api/requirement-assessments/{requirement_assessment.id}/findings-binder/"
        )
        assert res.status_code == 403

    def test_the_binder_is_created_once_and_bound_to_the_audit(self, setup, audit):
        assessment, requirement_assessment = audit
        set_flag(True)
        endpoint = (
            f"/api/requirement-assessments/{requirement_assessment.id}/findings-binder/"
        )

        first = setup["client"].post(endpoint)
        assert first.status_code == 201, first.json()
        second = setup["client"].post(endpoint)
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]

        binder = FindingsAssessment.objects.get(id=first.json()["id"])
        assert binder.compliance_assessment == assessment
        assert binder.folder == assessment.folder
        assert binder.category == "audit"
        set_flag(False)

    def test_the_binder_name_distinguishes_it_from_the_audit(self, setup, audit):
        assessment, requirement_assessment = audit
        set_flag(True)
        binder_id = (
            setup["client"]
            .post(
                f"/api/requirement-assessments/{requirement_assessment.id}/findings-binder/"
            )
            .json()["id"]
        )
        binder = FindingsAssessment.objects.get(id=binder_id)
        assert binder.name != assessment.name
        assert "findings" in binder.name.lower()
        set_flag(False)

    def test_a_requirement_assessment_can_carry_several_findings(self, setup, audit):
        assessment, requirement_assessment = audit
        set_flag(True)
        binder_id = (
            setup["client"]
            .post(
                f"/api/requirement-assessments/{requirement_assessment.id}/findings-binder/"
            )
            .json()["id"]
        )

        for name in ("Major nonconformity", "Minor nonconformity"):
            res = setup["client"].post(
                "/api/findings/",
                {
                    "name": name,
                    "findings_assessment": binder_id,
                    "requirement_assessment": str(requirement_assessment.id),
                    "requirement_node": str(requirement_assessment.requirement_id),
                },
                format="json",
            )
            assert res.status_code == 201, res.json()

        listed = setup["client"].get(
            f"/api/findings/?requirement_assessment={requirement_assessment.id}"
        )
        assert {f["name"] for f in listed.json()["results"]} == {
            "Major nonconformity",
            "Minor nonconformity",
        }
        # And each one links back to what raised it.
        assert listed.json()["results"][0]["requirement_assessment"]["id"] == str(
            requirement_assessment.id
        )
        set_flag(False)

    def test_the_audit_lists_its_findings_through_the_binder(self, setup, audit):
        assessment, requirement_assessment = audit
        set_flag(True)
        binder_id = (
            setup["client"]
            .post(
                f"/api/requirement-assessments/{requirement_assessment.id}/findings-binder/"
            )
            .json()["id"]
        )

        res = setup["client"].post(
            "/api/findings/",
            {
                "name": "Nonconformity",
                "findings_assessment": binder_id,
                "requirement_node": str(requirement_assessment.requirement_id),
            },
            format="json",
        )
        assert res.status_code == 201, res.json()

        listed = setup["client"].get(
            f"/api/findings-assessments/?compliance_assessment={assessment.id}"
        )
        assert [b["id"] for b in listed.json()["results"]] == [binder_id]
        set_flag(False)


class TestStandaloneFinding:
    def test_create_without_assessment_requires_a_folder(self, setup):
        res = create_finding(setup["client"], name="Orphan")
        assert res.status_code == 400
        assert "folder" in res.json()

    def test_create_without_assessment(self, setup):
        res = create_finding(
            setup["client"], name="Orphan", folder=str(setup["domain"].id)
        )
        assert res.status_code == 201
        finding = Finding.objects.get(id=res.json()["id"])
        assert finding.findings_assessment is None
        assert finding.folder == setup["domain"]

    def test_create_with_assessment_inherits_its_folder(self, setup):
        res = create_finding(
            setup["client"],
            name="Bound",
            findings_assessment=str(setup["binder"].id),
            folder=str(setup["other_domain"].id),
        )
        assert res.status_code == 201
        finding = Finding.objects.get(id=res.json()["id"])
        assert finding.folder == setup["domain"]

    def test_read_serializer_tolerates_a_missing_assessment(self, setup):
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        res = setup["client"].get(f"/api/findings/{finding.id}/")
        assert res.status_code == 200
        body = res.json()
        assert body["findings_assessment"] is None
        assert body["perimeter"] is None

    def test_deleting_the_assessment_still_cascades_to_its_findings(self, setup):
        finding = Finding.objects.create(
            name="Bound", folder=setup["domain"], findings_assessment=setup["binder"]
        )
        standalone = Finding.objects.create(name="Orphan", folder=setup["domain"])
        setup["binder"].delete()
        assert not Finding.objects.filter(id=finding.id).exists()
        assert Finding.objects.filter(id=standalone.id).exists()


class TestExtraFields:
    def test_finding_recommendation_round_trip(self, setup):
        res = create_finding(
            setup["client"],
            name="Orphan",
            folder=str(setup["domain"].id),
            recommendation="Rotate the key and **document** it",
        )
        assert res.status_code == 201, res.json()
        finding = Finding.objects.get(id=res.json()["id"])
        assert finding.recommendation == "Rotate the key and **document** it"

        res = setup["client"].get(f"/api/findings/{finding.id}/")
        assert res.json()["recommendation"] == "Rotate the key and **document** it"

    def test_findings_assessment_extra_fields_round_trip(self, setup):
        payload = {
            "name": "Pentest 2027",
            "folder": str(setup["domain"].id),
            "objectives": "Cover the **external** perimeter",
            "budget": "25000.00",
            "expenses": "1250.50",
            "reference_link": "https://example.com/report",
            "start_date": "2026-09-01",
        }
        res = setup["client"].post("/api/findings-assessments/", payload, format="json")
        assert res.status_code == 201, res.json()

        binder = FindingsAssessment.objects.get(id=res.json()["id"])
        assert binder.objectives == "Cover the **external** perimeter"
        assert str(binder.budget) == "25000.00"
        assert str(binder.expenses) == "1250.50"
        assert binder.reference_link == "https://example.com/report"
        assert str(binder.start_date) == "2026-09-01"

        body = setup["client"].get(f"/api/findings-assessments/{binder.id}/").json()
        assert body["budget"] == "25000.00"
        assert body["expenses"] == "1250.50"
        assert body["start_date"] == "2026-09-01"

    def test_negative_budget_is_rejected(self, setup):
        res = setup["client"].post(
            "/api/findings-assessments/",
            {"name": "Bad", "folder": str(setup["domain"].id), "budget": "-1"},
            format="json",
        )
        assert res.status_code == 400
        assert "budget" in res.json()


class TestTaskTemplates:
    def test_create_with_task_templates(self, setup):
        task = TaskTemplate.objects.create(name="Remediate", folder=setup["domain"])
        res = create_finding(
            setup["client"],
            name="Orphan",
            folder=str(setup["domain"].id),
            task_templates=[str(task.id)],
        )
        assert res.status_code == 201, res.json()
        finding = Finding.objects.get(id=res.json()["id"])
        assert list(finding.task_templates.all()) == [task]

    def test_update_replaces_task_templates(self, setup):
        first = TaskTemplate.objects.create(name="First", folder=setup["domain"])
        second = TaskTemplate.objects.create(name="Second", folder=setup["domain"])
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        finding.task_templates.set([first])

        res = setup["client"].patch(
            f"/api/findings/{finding.id}/",
            {"task_templates": [str(second.id)]},
            format="json",
        )
        assert res.status_code == 200, res.json()
        assert list(finding.task_templates.all()) == [second]

    def test_list_exposes_task_templates(self, setup):
        task = TaskTemplate.objects.create(name="Remediate", folder=setup["domain"])
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        finding.task_templates.set([task])

        res = setup["client"].get("/api/findings/")
        assert res.status_code == 200
        row = next(r for r in res.json()["results"] if r["id"] == str(finding.id))
        assert [t["id"] for t in row["task_templates"]] == [str(task.id)]

    def test_object_endpoint_exposes_task_templates(self, setup):
        # The "select existing" modal seeds itself from /object/ and PATCHes the whole
        # list back: if the field were missing there, picking one would wipe the rest.
        first = TaskTemplate.objects.create(name="First", folder=setup["domain"])
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        finding.task_templates.set([first])

        res = setup["client"].get(f"/api/findings/{finding.id}/object/")
        assert res.status_code == 200
        assert res.json()["task_templates"] == [str(first.id)]

    def test_read_serializer_exposes_task_templates(self, setup):
        task = TaskTemplate.objects.create(name="Remediate", folder=setup["domain"])
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        finding.task_templates.set([task])

        res = setup["client"].get(f"/api/findings/{finding.id}/")
        assert res.status_code == 200
        assert [t["id"] for t in res.json()["task_templates"]] == [str(task.id)]


class TestBinderFilter:
    @pytest.fixture
    def findings(self, setup):
        return {
            "unfiled": Finding.objects.create(name="Orphan", folder=setup["domain"]),
            "here": Finding.objects.create(
                name="Bound",
                folder=setup["domain"],
                findings_assessment=setup["binder"],
            ),
            "elsewhere": Finding.objects.create(
                name="Other",
                folder=setup["other_domain"],
                findings_assessment=setup["other_binder"],
            ),
        }

    def ids(self, res):
        assert res.status_code == 200, res.json()
        return {r["id"] for r in res.json()["results"]}

    def test_double_dash_selects_the_unfiled(self, setup, findings):
        res = setup["client"].get("/api/findings/?findings_assessment=--")
        assert self.ids(res) == {str(findings["unfiled"].id)}

    def test_a_binder_selects_its_own(self, setup, findings):
        res = setup["client"].get(
            f"/api/findings/?findings_assessment={setup['binder'].id}"
        )
        assert self.ids(res) == {str(findings["here"].id)}

    def test_double_dash_combines_with_a_binder(self, setup, findings):
        res = setup["client"].get(
            f"/api/findings/?findings_assessment=--&findings_assessment={setup['binder'].id}"
        )
        assert self.ids(res) == {
            str(findings["unfiled"].id),
            str(findings["here"].id),
        }

    def test_no_filter_returns_everything(self, setup, findings):
        res = setup["client"].get("/api/findings/")
        assert self.ids(res) == {str(f.id) for f in findings.values()}


class TestReparenting:
    def test_attach_moves_the_finding_to_the_assessment_folder(self, setup):
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        res = setup["client"].patch(
            f"/api/findings/{finding.id}/",
            {"findings_assessment": str(setup["other_binder"].id)},
            format="json",
        )
        assert res.status_code == 200
        finding.refresh_from_db()
        assert finding.findings_assessment == setup["other_binder"]
        assert finding.folder == setup["other_domain"]

    def test_detach_keeps_the_folder(self, setup):
        finding = Finding.objects.create(
            name="Bound", folder=setup["domain"], findings_assessment=setup["binder"]
        )
        res = setup["client"].patch(
            f"/api/findings/{finding.id}/",
            {"findings_assessment": None},
            format="json",
        )
        assert res.status_code == 200
        finding.refresh_from_db()
        assert finding.findings_assessment is None
        assert finding.folder == setup["domain"]

    def test_moving_a_bound_finding_is_rejected(self, setup):
        finding = Finding.objects.create(
            name="Bound", folder=setup["domain"], findings_assessment=setup["binder"]
        )
        res = setup["client"].patch(
            f"/api/findings/{finding.id}/",
            {"folder": str(setup["other_domain"].id)},
            format="json",
        )
        assert res.status_code == 400
        assert "folder" in res.json()

    def test_moving_a_standalone_finding_is_allowed(self, setup):
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        res = setup["client"].patch(
            f"/api/findings/{finding.id}/",
            {"folder": str(setup["other_domain"].id)},
            format="json",
        )
        assert res.status_code == 200
        finding.refresh_from_db()
        assert finding.folder == setup["other_domain"]

    def test_attaching_to_a_locked_assessment_is_rejected(self, setup):
        setup["binder"].is_locked = True
        setup["binder"].save()
        finding = Finding.objects.create(name="Orphan", folder=setup["domain"])
        res = setup["client"].patch(
            f"/api/findings/{finding.id}/",
            {"findings_assessment": str(setup["binder"].id)},
            format="json",
        )
        assert res.status_code == 400


class TestBatchAction:
    def test_batch_change_findings_assessment(self, setup):
        findings = [
            Finding.objects.create(name=f"Orphan {i}", folder=setup["domain"])
            for i in range(3)
        ]
        res = setup["client"].post(
            "/api/findings/batch-action/",
            {
                "action": "change_field",
                "ids": [str(f.id) for f in findings],
                "field": "findings_assessment",
                "value": str(setup["binder"].id),
            },
            format="json",
        )
        assert res.status_code == 200, res.json()
        for finding in findings:
            finding.refresh_from_db()
            assert finding.findings_assessment == setup["binder"]

    def test_batch_detach(self, setup):
        findings = [
            Finding.objects.create(
                name=f"Bound {i}",
                folder=setup["domain"],
                findings_assessment=setup["binder"],
            )
            for i in range(3)
        ]
        res = setup["client"].post(
            "/api/findings/batch-action/",
            {
                "action": "change_field",
                "ids": [str(f.id) for f in findings],
                "field": "findings_assessment",
                "value": None,
            },
            format="json",
        )
        assert res.status_code == 200, res.json()
        for finding in findings:
            finding.refresh_from_db()
            assert finding.findings_assessment is None
            assert finding.folder == setup["domain"]

    def test_batch_change_folder_on_standalone_findings(self, setup):
        findings = [
            Finding.objects.create(name=f"Orphan {i}", folder=setup["domain"])
            for i in range(2)
        ]
        res = setup["client"].post(
            "/api/findings/batch-action/",
            {
                "action": "change_folder",
                "ids": [str(f.id) for f in findings],
                "value": str(setup["other_domain"].id),
            },
            format="json",
        )
        assert res.status_code == 200, res.json()
        for finding in findings:
            finding.refresh_from_db()
            assert finding.folder == setup["other_domain"]
