import io
from datetime import date

import openpyxl
import pytest

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    RiskAssessment,
    RiskScenario,
)
from ebios_rm.models import EbiosRMStudy
from iam.models import Folder


@pytest.mark.django_db
def test_export_xlsx_sanitizes_audit_sheet_name(
    admin_client, basic_ebios_rm_study_fixture
):
    study = basic_ebios_rm_study_fixture
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="FW export", urn="urn:test:fw-export", folder=folder
    )
    rn = RequirementNode.objects.create(
        urn="urn:test:rn-export", framework=fw, assessable=True, folder=folder
    )
    ca = ComplianceAssessment.objects.create(
        name="Socle ISO 27001:2022 [v1]/*?\\ – Nu",
        framework=fw,
        folder=folder,
        perimeter=Perimeter.objects.create(name="p-export", folder=folder),
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca, requirement=rn, folder=folder
    )
    study.compliance_assessments.add(ca)

    response = admin_client.get(f"/api/ebios-rm/studies/{study.id}/export-xlsx/")

    assert response.status_code == 200
    sheets = openpyxl.load_workbook(io.BytesIO(response.content)).sheetnames
    assert "1.4.1 Socle ISO 27001_2022 _v1_" in sheets


@pytest.mark.django_db
def test_export_import_round_trips_workshop_5(
    admin_client, basic_ebios_rm_study_fixture
):
    study = basic_ebios_rm_study_fixture
    root = Folder.get_root_folder()
    ra = RiskAssessment.objects.create(
        name="WS5 risk assessment",
        ref_id="RA.1",
        version="2",
        folder=root,
        risk_matrix=study.risk_matrix,
        ebios_rm_study=study,
    )
    measure = AppliedControl.objects.create(
        name="MFA rollout",
        ref_id="M.1",
        folder=root,
        status="in_progress",
        eta=date(2027, 3, 31),
    )
    existing = AppliedControl.objects.create(name="Firewall", folder=root)
    scenario = RiskScenario.objects.create(
        risk_assessment=ra,
        name="Ransomware via phishing",
        ref_id="R.1",
        current_proba=2,
        current_impact=3,
        residual_proba=0,
        residual_impact=1,
        treatment="mitigate",
        justification="MFA cuts the entry vector",
    )
    scenario.applied_controls.set([measure])
    scenario.existing_applied_controls.set([existing])

    export = admin_client.get(f"/api/ebios-rm/studies/{study.id}/export-xlsx/")
    assert export.status_code == 200

    target = Folder.objects.create(name="Imported", parent_folder=root)
    response = admin_client.post(
        "/api/data-wizard/load-file/",
        data=export.content,
        content_type="application/octet-stream",
        HTTP_X_MODEL_TYPE="EbiosRMStudyExcel",
        HTTP_X_FOLDER_ID=str(target.id),
        HTTP_X_MATRIX_ID=str(study.risk_matrix.id),
        HTTP_CONTENT_DISPOSITION="attachment; filename=study.xlsx",
    )
    assert response.status_code == 200, response.content
    results = response.json()["results"]
    assert results["successful"] == 1, results["errors"]

    imported = EbiosRMStudy.objects.get(folder=target)
    imported_ra = imported.last_risk_assessment
    assert (imported_ra.name, imported_ra.ref_id, imported_ra.version) == (
        "WS5 risk assessment",
        "RA.1",
        "2",
    )
    assert imported_ra.folder == target
    rs = imported_ra.risk_scenarios.get()
    assert (rs.name, rs.ref_id, rs.treatment, rs.justification) == (
        "Ransomware via phishing",
        "R.1",
        "mitigate",
        "MFA cuts the entry vector",
    )
    assert (rs.current_proba, rs.current_impact) == (2, 3)
    assert (rs.residual_proba, rs.residual_impact) == (0, 1)
    assert [c.name for c in rs.existing_applied_controls.all()] == ["Firewall"]
    imported_measure = rs.applied_controls.get()
    assert imported_measure.folder == target
    assert (imported_measure.ref_id, imported_measure.status) == ("M.1", "in_progress")
    assert imported_measure.eta == date(2027, 3, 31)
