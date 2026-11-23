"""Audits through the mapped import: requirement rows from any layout, an audit
created and named by the import, nested applied controls, and a third-party
assessment linked to that audit in the same run."""

import io
import json
from pathlib import Path

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    RequirementNode,
)
from tprm.models import EntityAssessment

SAMPLES = Path(__file__).parent / "samples"
IMPORT_URL = "/api/data-wizard/mapping/import/"
AUDIT_REFS = ["A.5.1", "A.5.2", "A.5.3", "A.5.7", "A.5.15", "A.5.30", "A.8.24"]


@pytest.fixture
def framework(root_folder):
    fw = Framework.objects.create(name="ISO 27001 (test)", folder=root_folder)
    for ref_id in AUDIT_REFS:
        RequirementNode.objects.create(
            framework=fw,
            urn=f"urn:test:iso27001:req:{ref_id.lower()}",
            ref_id=ref_id,
            assessable=True,
            folder=root_folder,
        )
    return fw


def _import(client, filename, steps, options, dry_run=False):
    return client.post(
        IMPORT_URL,
        {
            "file": SimpleUploadedFile(filename, (SAMPLES / filename).read_bytes()),
            "mapping": json.dumps({"steps": steps}),
            "options": json.dumps(options),
            "dry_run": str(dry_run).lower(),
        },
        format="multipart",
    )


AUDIT_STEP = {
    "model_type": "ComplianceAssessment",
    "sheets": [
        {
            "source": "SoA review",
            "target": "Requirements",
            "header_row": 4,
            "columns": {
                "Control": "ref_id",
                "Assessment": "compliance_result",
                "Progress": "requirement_progress",
                "Score": "score",
                "Auditor notes": "observations",
                "Existing measures": "applied_controls",
            },
            "values": {
                "Assessment": {
                    "Compliant": "compliant",
                    "Partially compliant": "partially_compliant",
                    "Non compliant": "non_compliant",
                    "Not applicable": "not_applicable",
                },
                "Progress": {
                    "Done": "done",
                    "In review": "in_review",
                    "To do": "to_do",
                    "In progress": "in_progress",
                },
            },
        }
    ],
}


@pytest.mark.django_db
class TestInternalAudit:
    def _run(self, client, folder, framework, dry_run=False, **options):
        step = {**AUDIT_STEP, "options": {"framework_id": str(framework.id), **options}}
        return _import(
            client,
            "09_iso27001_internal_audit.xlsx",
            [step],
            {"folder_id": str(folder.id), "on_conflict": "skip"},
            dry_run,
        )

    def test_creates_a_named_audit_from_the_rows(
        self, api_client, domain_folder, framework, all_accessible
    ):
        resp = self._run(
            api_client, domain_folder, framework, container_name="ISMS audit 2026"
        )
        assert resp.status_code == 200, resp.json()
        audit = ComplianceAssessment.objects.get(name="ISMS audit 2026")
        assert audit.framework == framework
        by_ref = {
            ra.requirement.ref_id: ra
            for ra in RequirementAssessment.objects.filter(compliance_assessment=audit)
        }
        assert by_ref["A.5.1"].result == "compliant"
        assert by_ref["A.5.2"].status == "in_review"
        assert by_ref["A.5.3"].observation == "Admins approve their own changes"
        assert by_ref["A.5.15"].score == 3

    def test_existing_measures_become_linked_applied_controls(
        self, api_client, domain_folder, framework, all_accessible
    ):
        self._run(api_client, domain_folder, framework, container_name="Audit")
        audit = ComplianceAssessment.objects.get(name="Audit")
        ra = RequirementAssessment.objects.get(
            compliance_assessment=audit, requirement__ref_id="A.5.15"
        )
        assert sorted(c.name for c in ra.applied_controls.all()) == [
            "MFA for remote access",
            "Quarterly access review",
        ]

    def test_unknown_requirement_is_reported(
        self, api_client, domain_folder, framework, all_accessible
    ):
        resp = self._run(api_client, domain_folder, framework, container_name="Audit")
        errors = json.dumps(resp.json()["steps"][0]["results"]["errors"])
        assert "A.99.9" in errors

    def test_dry_run_creates_nothing(
        self, api_client, domain_folder, framework, all_accessible
    ):
        resp = self._run(
            api_client, domain_folder, framework, dry_run=True, container_name="Dry"
        )
        assert resp.status_code == 200
        assert not ComplianceAssessment.objects.filter(name="Dry").exists()
        assert not AppliedControl.objects.filter(name="MFA for remote access").exists()

    def test_updates_an_existing_audit(
        self, api_client, domain_folder, framework, all_accessible
    ):
        audit = ComplianceAssessment.objects.create(
            name="Existing", framework=framework, folder=domain_folder
        )
        audit.create_requirement_assessments()
        self._run(api_client, domain_folder, framework, target_id=str(audit.id))
        assert ComplianceAssessment.objects.filter(framework=framework).count() == 1
        ra = RequirementAssessment.objects.get(
            compliance_assessment=audit, requirement__ref_id="A.5.1"
        )
        assert ra.result == "compliant"

    def test_reimport_keeps_controls_linked_from_another_domain(
        self, api_client, root_folder, domain_folder, framework, all_accessible
    ):
        audit = ComplianceAssessment.objects.create(
            name="Existing", framework=framework, folder=domain_folder
        )
        audit.create_requirement_assessments()
        ra = RequirementAssessment.objects.get(
            compliance_assessment=audit, requirement__ref_id="A.5.15"
        )
        linked = AppliedControl.objects.create(
            name="Quarterly access review", folder=root_folder
        )
        ra.applied_controls.add(linked)
        self._run(api_client, domain_folder, framework, target_id=str(audit.id))
        assert (
            AppliedControl.objects.filter(name="Quarterly access review").count() == 1
        )
        assert linked in ra.applied_controls.all()


def test_audit_rows_carry_answers_and_score_override():
    from data_wizard.mapping import template_schema
    from data_wizard.views import ModelType

    (sheet,) = template_schema(ModelType.COMPLIANCE_ASSESSMENT)["sheets"]
    keys = {c["key"] for c in sheet["columns"]}
    assert {"answers", "is_score_overridden"} <= keys


@pytest.mark.django_db
def test_vendor_assessment_links_the_audit_created_in_the_same_run(
    api_client, domain_folder, framework, all_accessible
):
    audit_step = {
        "model_type": "ComplianceAssessment",
        "options": {
            "framework_id": str(framework.id),
            "container_name": "Northwind questionnaire 2026",
        },
        "sheets": [
            {
                "source": "Answers",
                "target": "Requirements",
                "columns": {
                    "Requirement": "ref_id",
                    "Answer": "compliance_result",
                    "Comment": "observations",
                },
                "values": {
                    "Answer": {
                        "Compliant": "compliant",
                        "Partially compliant": "partially_compliant",
                        "Non compliant": "non_compliant",
                    }
                },
            }
        ],
    }
    vendor_step = {
        "model_type": "TPRM",
        "sheets": [
            {
                "source": "Vendor",
                "target": "Entities",
                "columns": {
                    "Vendor ID": "ref_id",
                    "Vendor": "name",
                    "What they do": "description",
                    "Domain": "domain",
                },
            },
            {
                "source": "Assessment",
                "target": "EntityAssessments",
                "columns": {
                    "Vendor ID": "entity_ref_id",
                    "Assessment": "name",
                    "Description": "description",
                    "Criticality": "criticality",
                    "Due date": "due_date",
                    "Domain": "domain",
                    "Audit name": "audit_name",
                },
            },
        ],
    }
    resp = _import(
        api_client,
        "10_vendor_due_diligence.xlsx",
        [audit_step, vendor_step],
        {"folder_id": str(domain_folder.id), "on_conflict": "skip"},
    )
    assert resp.status_code == 200, resp.json()
    audit = ComplianceAssessment.objects.get(name="Northwind questionnaire 2026")
    assessment = EntityAssessment.objects.get(name="Northwind onboarding review")
    assert assessment.compliance_assessment == audit
    assert (
        RequirementAssessment.objects.get(
            compliance_assessment=audit, requirement__ref_id="A.5.30"
        ).result
        == "non_compliant"
    )


def _scored_audit(framework, folder, documentation_score=True):
    audit = ComplianceAssessment.objects.create(
        name="Scored", framework=framework, folder=folder, min_score=1, max_score=5
    )
    audit.create_requirement_assessments()
    audit.scoring_enabled = True
    audit.show_documentation_score = documentation_score
    audit.save()
    return audit


def _import_into(client, folder, audit, workbook):
    buffer = io.BytesIO()
    workbook.save(buffer)
    header = [cell.value for cell in workbook.active[1]]
    imported = {"ref_id", "implementation_score", "documentation_score", "score"}
    step = {
        "model_type": "ComplianceAssessment",
        "options": {"target_id": str(audit.id)},
        "sheets": [
            {
                "source": workbook.active.title,
                "target": "Requirements",
                "header_row": 1,
                "columns": {name: name for name in header if name in imported},
            }
        ],
    }
    return client.post(
        IMPORT_URL,
        {
            "file": SimpleUploadedFile("audit.xlsx", buffer.getvalue()),
            "mapping": json.dumps({"steps": [step]}),
            "options": json.dumps({"folder_id": str(folder.id)}),
        },
        format="multipart",
    )


def _scores(audit):
    return {
        ra.requirement.ref_id: (ra.score, ra.documentation_score, ra.is_scored)
        for ra in RequirementAssessment.objects.filter(compliance_assessment=audit)
    }


@pytest.mark.django_db
class TestScoreColumns:
    def test_exported_audit_reimports_either_score_alone(
        self, knox_admin_client, domain_folder, framework
    ):
        audit = _scored_audit(framework, domain_folder)
        RequirementAssessment.objects.filter(
            compliance_assessment=audit, requirement__ref_id="A.5.7"
        ).update(score=2, documentation_score=3, is_scored=True)

        resp = knox_admin_client.get(f"/api/compliance-assessments/{audit.id}/xlsx/")
        assert resp.status_code == 200
        workbook = openpyxl.load_workbook(io.BytesIO(resp.content))
        sheet = workbook.active
        column = {cell.value: cell.column for cell in sheet[1]}
        row = {
            sheet.cell(r, column["ref_id"]).value: r
            for r in range(2, sheet.max_row + 1)
        }
        edits = {
            "A.5.1": {"implementation_score": 4},
            "A.5.2": {"implementation_score": 3, "documentation_score": 2},
            "A.5.3": {"documentation_score": 5},
            "A.5.7": {"implementation_score": 4},
        }
        for ref_id, cells in edits.items():
            for name, value in cells.items():
                sheet.cell(row[ref_id], column[name]).value = value

        resp = _import_into(knox_admin_client, domain_folder, audit, workbook)
        assert resp.status_code == 200, resp.json()
        results = resp.json()["steps"][0]["results"]
        assert results["failed"] == 0, results["errors"]

        scores = _scores(audit)
        assert scores["A.5.1"] == (4, None, True)
        assert scores["A.5.2"] == (3, 2, True)
        # A documentation score alone does not make the requirement scored.
        assert scores["A.5.3"] == (None, 5, False)
        assert scores["A.5.7"] == (4, 3, True)

    def test_documentation_score_alone_turns_it_on(
        self, knox_admin_client, domain_folder, framework
    ):
        audit = _scored_audit(framework, domain_folder, documentation_score=False)
        workbook = openpyxl.Workbook()
        workbook.active.append(["ref_id", "documentation_score"])
        workbook.active.append(["A.5.1", 4])

        resp = _import_into(knox_admin_client, domain_folder, audit, workbook)
        assert resp.status_code == 200, resp.json()

        audit.refresh_from_db()
        assert audit.show_documentation_score
        assert _scores(audit)["A.5.1"] == (None, 4, False)
