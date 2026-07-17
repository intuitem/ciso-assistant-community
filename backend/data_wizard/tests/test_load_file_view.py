"""
Integration tests for the LoadFileView HTTP endpoint.

Endpoint: POST /api/data-wizard/load-file/
Auth: force_authenticate
File: raw body with Content-Disposition header (FileUploadParser)

Key headers:
  X-Model-Type     model type string (required)
  X-Folder-Id      target folder UUID
  X-On-Conflict    stop | skip | update (default: stop)

Pattern mirrors tprm/test/test_views.py:
  - Real DRF request through the full view stack
  - Unit-layer classes: RBAC patched via all_accessible fixture
  - RBAC-layer classes: real knox token + startup(), no RBAC patch
"""

import pytest

from core.models import (
    AppliedControl,
    Asset,
    Incident,
    Perimeter,
    Policy,
    ReferenceControl,
    SecurityException,
    Threat,
    Vulnerability,
)
from ebios_rm.models import ElementaryAction
from iam.models import User
from privacy.models import Processing

from data_wizard.tests.conftest import make_excel_file

URL = "/api/data-wizard/load-file/"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _post(client, data: bytes, filename: str, model_type: str, folder_id=None, **extra):
    headers = {
        "HTTP_X_MODEL_TYPE": model_type,
        "HTTP_CONTENT_DISPOSITION": f"attachment; filename={filename}",
        "content_type": "application/octet-stream",
    }
    if folder_id:
        headers["HTTP_X_FOLDER_ID"] = str(folder_id)
    headers.update(extra)
    return client.post(URL, data=data, **headers)


def _csv(text: str) -> bytes:
    return text.encode()


def _assert_response_shape(body: dict):
    """Verify the standard response envelope is complete."""
    results = body.get("results", {})
    for key in ("created", "updated", "skipped", "failed", "stopped", "errors"):
        assert key in results, f"Missing key '{key}' in response results"


# ─────────────────────────────────────────────────────────────────────────────
# Request-level validation (no model needed, no RBAC patch needed)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRequestValidation:
    def test_no_data_returns_400(self, api_client):
        resp = api_client.post(URL, data=None, content_type="application/octet-stream")
        assert resp.status_code == 400
        assert "error" in resp.json()

    def test_unsupported_file_format_returns_400(self, api_client, domain_folder):
        resp = _post(api_client, b"garbage", "data.txt", "Asset", domain_folder.id)
        assert resp.status_code == 400
        assert resp.json()["error"] == "unsupportedFileFormat"

    def test_unknown_model_type_returns_400(self, api_client, domain_folder):
        resp = _post(
            api_client, _csv("name\nTest"), "data.csv", "NoSuchModel", domain_folder.id
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "UnknownModelType"

    def test_unauthenticated_returns_401_or_403(self, domain_folder):
        from rest_framework.test import APIClient

        anon = APIClient()
        resp = _post(anon, _csv("name\nX"), "data.csv", "Asset", domain_folder.id)
        assert resp.status_code in (401, 403)

    def test_response_envelope_shape(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nShapeTest,SHP-001\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        assert resp.status_code == 200
        _assert_response_shape(resp.json())


# ─────────────────────────────────────────────────────────────────────────────
# Conflict modes — tested on Asset as the representative model
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConflictModes:
    def test_stop_mode_halts_on_duplicate(
        self, api_client, domain_folder, all_accessible
    ):
        Asset.objects.create(name="Web App", ref_id="AST-STOP", folder=domain_folder)
        resp = _post(
            api_client,
            _csv("name,ref_id\nWeb App,AST-STOP\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        body = resp.json()
        assert body["results"]["stopped"] is True
        assert body["results"]["failed"] == 1

    def test_skip_mode_ignores_duplicate(
        self, api_client, domain_folder, all_accessible
    ):
        Asset.objects.create(name="Web App", ref_id="AST-SKIP", folder=domain_folder)
        resp = _post(
            api_client,
            _csv("name,ref_id\nWeb App,AST-SKIP\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="skip",
        )
        body = resp.json()
        assert body["results"]["skipped"] == 1
        assert body["results"]["created"] == 0
        assert body["results"]["stopped"] is False

    def test_update_mode_patches_existing_record(
        self, api_client, domain_folder, all_accessible
    ):
        Asset.objects.create(
            name="Web App", ref_id="AST-UPD", folder=domain_folder, description="old"
        )
        resp = _post(
            api_client,
            _csv("name,ref_id,description\nWeb App,AST-UPD,new description\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="update",
        )
        assert resp.json()["results"]["updated"] == 1
        assert Asset.objects.get(ref_id="AST-UPD").description == "new description"

    def test_update_mode_deduplicates_by_ref_id_not_name(
        self, api_client, domain_folder, all_accessible
    ):
        """ref_id match must win even when the CSV name differs from the stored name."""
        asset = Asset.objects.create(
            name="Old Name", ref_id="AST-REF", folder=domain_folder
        )
        resp = _post(
            api_client,
            _csv("name,ref_id,description\nNew Name,AST-REF,updated\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="update",
        )
        assert resp.json()["results"]["updated"] == 1
        asset.refresh_from_db()
        assert asset.description == "updated"


# ─────────────────────────────────────────────────────────────────────────────
# CSV vs XLSX file detection
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFileFormatDetection:
    def test_csv_accepted(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nCSV Asset,CSV-001\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1

    def test_xlsx_accepted(self, api_client, domain_folder, all_accessible):
        excel = make_excel_file(
            {"Sheet1": [{"name": "Excel Asset", "ref_id": "XLS-001"}]}
        )
        resp = _post(api_client, excel.read(), "a.xlsx", "Asset", domain_folder.id)
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1

    def test_csv_and_xlsx_produce_same_result(
        self, api_client, domain_folder, all_accessible
    ):
        resp_csv = _post(
            api_client,
            _csv("name,ref_id\nSame,SAME-001\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        Asset.objects.filter(ref_id="SAME-001").delete()

        excel = make_excel_file({"Sheet1": [{"name": "Same", "ref_id": "SAME-001"}]})
        resp_excel = _post(
            api_client, excel.read(), "a.xlsx", "Asset", domain_folder.id
        )

        assert resp_csv.json()["results"]["created"] == 1
        assert resp_excel.json()["results"]["created"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Per-model smoke tests — one create + response shape per model type
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAssetEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id,type\nWeb App,AST-001,primary\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Asset.objects.filter(ref_id="AST-001", folder=domain_folder).exists()

    def test_missing_name_fails(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client, _csv("ref_id\nAST-X\n"), "a.csv", "Asset", domain_folder.id
        )
        assert resp.json()["results"]["failed"] == 1

    def test_xlsx_create(self, api_client, domain_folder, all_accessible):
        excel = make_excel_file(
            {"Sheet1": [{"name": "Excel Asset", "ref_id": "AST-XLS"}]}
        )
        resp = _post(api_client, excel.read(), "a.xlsx", "Asset", domain_folder.id)
        assert resp.json()["results"]["created"] == 1


@pytest.mark.django_db
class TestAppliedControlEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nPatch Mgmt,AC-001\n"),
            "a.csv",
            "AppliedControl",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert AppliedControl.objects.filter(ref_id="AC-001").exists()

    def test_ref_id_deduplication_on_skip(
        self, api_client, domain_folder, all_accessible
    ):
        AppliedControl.objects.create(
            name="Original", ref_id="AC-DUP", folder=domain_folder
        )
        resp = _post(
            api_client,
            _csv("name,ref_id\nDifferent,AC-DUP\n"),
            "a.csv",
            "AppliedControl",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="skip",
        )
        assert resp.json()["results"]["skipped"] == 1
        assert AppliedControl.objects.get(ref_id="AC-DUP").name == "Original"


@pytest.mark.django_db
class TestVulnerabilityEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id,severity\nLog4Shell,CVE-2021-44228,critical\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Vulnerability.objects.filter(ref_id="CVE-2021-44228").exists()

    def test_deduplication_by_ref_id(self, api_client, domain_folder, all_accessible):
        Vulnerability.objects.create(
            name="Log4Shell", ref_id="CVE-SKIP", folder=domain_folder
        )
        resp = _post(
            api_client,
            _csv("name,ref_id\nDifferent,CVE-SKIP\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="skip",
        )
        assert resp.json()["results"]["skipped"] == 1


@pytest.mark.django_db
class TestPerimeterEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nMain Scope,PRM-001\n"),
            "a.csv",
            "Perimeter",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Perimeter.objects.filter(ref_id="PRM-001").exists()


@pytest.mark.django_db
class TestThreatEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nPhishing,THR-001\n"),
            "a.csv",
            "Threat",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Threat.objects.filter(ref_id="THR-001").exists()


@pytest.mark.django_db
class TestReferenceControlEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nMFA Enforcement,RC-001\n"),
            "a.csv",
            "ReferenceControl",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert ReferenceControl.objects.filter(ref_id="RC-001").exists()


@pytest.mark.django_db
class TestPolicyEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nData Classification,POL-001\n"),
            "a.csv",
            "Policy",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Policy.objects.filter(ref_id="POL-001").exists()


@pytest.mark.django_db
class TestSecurityExceptionEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nLegacy System,SE-001\n"),
            "a.csv",
            "SecurityException",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert SecurityException.objects.filter(ref_id="SE-001").exists()

    def test_ref_id_deduplication_on_skip(
        self, api_client, domain_folder, all_accessible
    ):
        SecurityException.objects.create(
            name="Original", ref_id="SE-DUP", folder=domain_folder
        )
        resp = _post(
            api_client,
            _csv("name,ref_id\nDifferent,SE-DUP\n"),
            "a.csv",
            "SecurityException",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="skip",
        )
        assert resp.json()["results"]["skipped"] == 1


@pytest.mark.django_db
class TestUserEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("email,first_name,last_name\nnewuser@test.com,New,User\n"),
            "a.csv",
            "User",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert User.objects.filter(email="newuser@test.com").exists()

    def test_missing_email_fails(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client, _csv("first_name\nAlice\n"), "a.csv", "User", domain_folder.id
        )
        assert resp.json()["results"]["failed"] == 1


@pytest.mark.django_db
class TestElementaryActionEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id,attack_stage\nPhishing Email,EA-001,know\n"),
            "a.csv",
            "ElementaryAction",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert ElementaryAction.objects.filter(
            ref_id="EA-001", folder=domain_folder
        ).exists()

    def test_ref_id_deduplication_on_skip(
        self, api_client, domain_folder, all_accessible
    ):
        ElementaryAction.objects.create(
            name="Original", ref_id="EA-DUP", folder=domain_folder
        )
        resp = _post(
            api_client,
            _csv("name,ref_id\nDifferent,EA-DUP\n"),
            "a.csv",
            "ElementaryAction",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="skip",
        )
        assert resp.json()["results"]["skipped"] == 1

    def test_xlsx_create(self, api_client, domain_folder, all_accessible):
        excel = make_excel_file(
            {"Sheet1": [{"name": "XLSX Action", "ref_id": "EA-XLS"}]}
        )
        resp = _post(
            api_client, excel.read(), "a.xlsx", "ElementaryAction", domain_folder.id
        )
        assert resp.json()["results"]["created"] == 1


@pytest.mark.django_db
class TestProcessingEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nHR Payroll,PRC-001\n"),
            "a.csv",
            "Processing",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Processing.objects.filter(
            ref_id="PRC-001", folder=domain_folder
        ).exists()

    def test_ref_id_deduplication_on_skip(
        self, api_client, domain_folder, all_accessible
    ):
        Processing.objects.create(
            name="Original", ref_id="PRC-DUP", folder=domain_folder
        )
        resp = _post(
            api_client,
            _csv("name,ref_id\nDifferent,PRC-DUP\n"),
            "a.csv",
            "Processing",
            domain_folder.id,
            HTTP_X_ON_CONFLICT="skip",
        )
        assert resp.json()["results"]["skipped"] == 1

    def test_xlsx_create(self, api_client, domain_folder, all_accessible):
        excel = make_excel_file(
            {"Sheet1": [{"name": "XLSX Processing", "ref_id": "PRC-XLS"}]}
        )
        resp = _post(api_client, excel.read(), "a.xlsx", "Processing", domain_folder.id)
        assert resp.json()["results"]["created"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Field-contract tests — prove each supported field round-trips correctly
# through a real file upload, not just a unit-layer consumer call.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAssetFieldContracts:
    def test_type_primary_alias_stored_as_pr(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,type\nApp Server,AST-FC-01,primary\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        assert Asset.objects.get(ref_id="AST-FC-01").type == "PR"

    def test_link_column_alias_stored_as_reference_link(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,link\nDB Server,AST-FC-02,https://wiki.example.com\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        assert (
            Asset.objects.get(ref_id="AST-FC-02").reference_link
            == "https://wiki.example.com"
        )

    def test_domain_column_resolves_to_correct_folder(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv(f"name,ref_id,domain\nStorage,AST-FC-03,{domain_folder.name}\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        assert Asset.objects.get(ref_id="AST-FC-03").folder == domain_folder

    def test_parent_asset_ref_id_linked_in_same_upload(
        self, api_client, domain_folder, all_accessible
    ):
        # Both parent and child are in the same CSV — proves the second-pass
        # batch linking in views.py (not just update-mode relation attachment).
        csv = (
            "name,ref_id,type,parent_asset_ref_id\n"
            "Parent Server,AST-PAR-01,primary,\n"
            "Child App,AST-CHD-01,primary,AST-PAR-01\n"
        )
        resp = _post(api_client, _csv(csv), "a.csv", "Asset", domain_folder.id)
        assert resp.json()["results"]["created"] == 2
        parent = Asset.objects.get(ref_id="AST-PAR-01")
        child = Asset.objects.get(ref_id="AST-CHD-01")
        assert parent in child.parent_assets.all()


@pytest.mark.django_db
class TestAppliedControlFieldContracts:
    def test_effort_alias_extra_small_stored_as_xs(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,effort\nPatch Cycle,AC-FC-01,extra small\n"),
            "a.csv",
            "AppliedControl",
            domain_folder.id,
        )
        assert AppliedControl.objects.get(ref_id="AC-FC-01").effort == "XS"

    def test_impact_text_alias_high_stored_as_4(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,impact\nFirewall,AC-FC-02,high\n"),
            "a.csv",
            "AppliedControl",
            domain_folder.id,
        )
        assert AppliedControl.objects.get(ref_id="AC-FC-02").control_impact == 4

    def test_reference_control_linked_by_ref_id(
        self, api_client, domain_folder, all_accessible
    ):
        rc = ReferenceControl.objects.create(
            name="MFA Policy", ref_id="RC-LINK-01", folder=domain_folder
        )
        _post(
            api_client,
            _csv("name,ref_id,reference_control\nMFA Impl,AC-FC-03,RC-LINK-01\n"),
            "a.csv",
            "AppliedControl",
            domain_folder.id,
        )
        assert AppliedControl.objects.get(ref_id="AC-FC-03").reference_control == rc

    def test_csf_function_uppercase_lowercased_on_import(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,csf_function\nFirewall Policy,AC-FC-04,PROTECT\n"),
            "a.csv",
            "AppliedControl",
            domain_folder.id,
        )
        assert AppliedControl.objects.get(ref_id="AC-FC-04").csf_function == "protect"


@pytest.mark.django_db
class TestPerimeterFieldContracts:
    def test_status_alias_stored_as_lc_status(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,status\nERP,PRM-FC-01,in_prod\n"),
            "a.csv",
            "Perimeter",
            domain_folder.id,
        )
        assert Perimeter.objects.get(ref_id="PRM-FC-01").lc_status == "in_prod"


@pytest.mark.django_db
class TestReferenceControlFieldContracts:
    def test_function_alias_maps_to_csf_function(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,function\nAccess Control,RC-FC-01,protect\n"),
            "a.csv",
            "ReferenceControl",
            domain_folder.id,
        )
        assert ReferenceControl.objects.get(ref_id="RC-FC-01").csf_function == "protect"

    def test_governance_alias_normalised_to_govern(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,function\nPolicy Doc,RC-FC-02,governance\n"),
            "a.csv",
            "ReferenceControl",
            domain_folder.id,
        )
        assert ReferenceControl.objects.get(ref_id="RC-FC-02").csf_function == "govern"


@pytest.mark.django_db
class TestSecurityExceptionFieldContracts:
    def test_severity_high_stored_as_3(self, api_client, domain_folder, all_accessible):
        _post(
            api_client,
            _csv("name,ref_id,severity\nRisk Accepted,SE-FC-01,high\n"),
            "a.csv",
            "SecurityException",
            domain_folder.id,
        )
        assert SecurityException.objects.get(ref_id="SE-FC-01").severity == 3

    def test_status_in_review_alias_stored_correctly(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,status\nLegacy App,SE-FC-02,in review\n"),
            "a.csv",
            "SecurityException",
            domain_folder.id,
        )
        assert SecurityException.objects.get(ref_id="SE-FC-02").status == "in_review"


@pytest.mark.django_db
class TestIncidentEndpoint:
    def test_create(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,ref_id\nData Breach,INC-001\n"),
            "a.csv",
            "Incident",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        assert Incident.objects.filter(ref_id="INC-001").exists()

    def test_severity_alias_major_stored_as_2(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,severity\nOutage,INC-FC-01,major\n"),
            "a.csv",
            "Incident",
            domain_folder.id,
        )
        assert Incident.objects.get(ref_id="INC-FC-01").severity == 2

    def test_status_alias_in_progress_stored_as_ongoing(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,status\nRansomware,INC-FC-02,in progress\n"),
            "a.csv",
            "Incident",
            domain_folder.id,
        )
        assert Incident.objects.get(ref_id="INC-FC-02").status == "ongoing"

    def test_detection_alias_internal_stored_as_internally_detected(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,detection\nPhishing,INC-FC-03,internal\n"),
            "a.csv",
            "Incident",
            domain_folder.id,
        )
        assert (
            Incident.objects.get(ref_id="INC-FC-03").detection == "internally_detected"
        )

    def test_bad_security_objectives_on_asset_yields_warning_not_error(
        self, api_client, domain_folder, all_accessible
    ):
        resp = _post(
            api_client,
            _csv("name,ref_id,security_objectives\nBadObj,AST-FC-WARN-01,bad_format\n"),
            "a.csv",
            "Asset",
            domain_folder.id,
        )
        body = resp.json()["results"]
        assert body["created"] == 1
        assert Asset.objects.filter(ref_id="AST-FC-WARN-01").exists()
        assert "warnings" in body


@pytest.mark.django_db
class TestVulnerabilityFieldContracts:
    def test_status_exploitable_stored_correctly(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,status\nLog4Shell,CVE-FC-01,exploitable\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        assert Vulnerability.objects.get(ref_id="CVE-FC-01").status == "exploitable"

    def test_status_not_exploitable_alias_stored_correctly(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,status\nLog4j,CVE-FC-03,not exploitable\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        assert Vulnerability.objects.get(ref_id="CVE-FC-03").status == "not_exploitable"

    def test_severity_critical_stored_correctly(
        self, api_client, domain_folder, all_accessible
    ):
        _post(
            api_client,
            _csv("name,ref_id,severity\nShellShock,CVE-FC-02,critical\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        assert Vulnerability.objects.get(ref_id="CVE-FC-02").severity == 4

    def test_applied_controls_linked_by_ref_id(
        self, api_client, domain_folder, all_accessible
    ):
        AppliedControl.objects.create(
            name="Patch Policy", ref_id="AC-VUL-01", folder=domain_folder
        )
        _post(
            api_client,
            _csv("name,ref_id,applied_controls\nHeartbleed,CVE-FC-04,AC-VUL-01\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        vuln = Vulnerability.objects.get(ref_id="CVE-FC-04")
        assert (
            AppliedControl.objects.get(ref_id="AC-VUL-01")
            in vuln.applied_controls.all()
        )

    def test_assets_linked_by_ref_id(self, api_client, domain_folder, all_accessible):
        Asset.objects.create(
            name="Web Server", ref_id="AST-VUL-01", folder=domain_folder
        )
        _post(
            api_client,
            _csv("name,ref_id,assets\nSpectre,CVE-FC-05,AST-VUL-01\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        vuln = Vulnerability.objects.get(ref_id="CVE-FC-05")
        assert Asset.objects.get(ref_id="AST-VUL-01") in vuln.assets.all()

    def test_security_exceptions_linked_by_ref_id(
        self, api_client, domain_folder, all_accessible
    ):
        SecurityException.objects.create(
            name="Risk Accepted", ref_id="SE-VUL-01", folder=domain_folder
        )
        _post(
            api_client,
            _csv("name,ref_id,security_exceptions\nMeltdown,CVE-FC-06,SE-VUL-01\n"),
            "a.csv",
            "Vulnerability",
            domain_folder.id,
        )
        vuln = Vulnerability.objects.get(ref_id="CVE-FC-06")
        assert (
            SecurityException.objects.get(ref_id="SE-VUL-01")
            in vuln.security_exceptions.all()
        )


@pytest.mark.django_db
class TestFolderEndpoint:
    def test_create_folder_in_domain(self, api_client, domain_folder, all_accessible):
        resp = _post(
            api_client,
            _csv("name,domain\nNew Sub-Folder,Test Domain\n"),
            "folders.csv",
            "Folder",
            domain_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        from iam.models import Folder

        created = Folder.objects.get(name="New Sub-Folder")
        assert created.parent_folder == domain_folder

    def test_create_folder_without_domain_uses_root(
        self, api_client, root_folder, all_accessible
    ):
        resp = _post(
            api_client,
            _csv("name\nOrphan Folder\n"),
            "folders.csv",
            "Folder",
            root_folder.id,
        )
        assert resp.status_code == 200
        assert resp.json()["results"]["created"] == 1
        from iam.models import Folder

        created = Folder.objects.get(name="Orphan Folder")
        assert created.parent_folder == root_folder


# ─────────────────────────────────────────────────────────────────────────────
# Real auth + RBAC — no force_authenticate, no RBAC patching
# Uses startup() to initialize roles/groups exactly as production does.
# Mirrors app_tests/conftest.py authenticated_client pattern.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRealAuthAndRBAC:
    """
    Proves the full auth stack works end-to-end:
      knox middleware → user resolution → IsAuthenticated → view → RBAC
    No mocks or patches anywhere in this class.
    """

    def test_no_token_returns_401(self, app_ready, domain_folder):
        """Missing Authorization header must be rejected before the view runs."""
        from rest_framework.test import APIClient

        anon = APIClient()
        resp = _post(anon, _csv("name\nX\n"), "a.csv", "Asset", domain_folder.id)
        assert resp.status_code in (401, 403)

    def test_invalid_token_returns_401(self, app_ready, domain_folder):
        from rest_framework.test import APIClient

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token totally-invalid-token")
        resp = _post(client, _csv("name\nX\n"), "a.csv", "Asset", domain_folder.id)
        assert resp.status_code in (401, 403)

    def test_admin_can_create_asset_with_knox_token(self, knox_admin_client, app_ready):
        """
        Real admin token (BI-UG-ADM group) can create an asset through the
        real RBAC path without any patching.
        """
        folder = app_ready  # root folder returned by app_ready
        resp = _post(
            knox_admin_client,
            _csv("name,ref_id\nKnox Asset,KNOX-001\n"),
            "a.csv",
            "Asset",
            folder.id,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"]["created"] == 1
        assert Asset.objects.filter(ref_id="KNOX-001").exists()

    def test_admin_update_mode_sees_existing_record(self, knox_admin_client, app_ready):
        """
        With real RBAC, the admin's get_accessible_object_ids() returns the
        existing record so UPDATE mode can find and patch it.
        """
        folder = app_ready
        Asset.objects.create(
            name="Existing", ref_id="KNOX-UPD", folder=folder, description="old"
        )
        resp = _post(
            knox_admin_client,
            _csv("name,ref_id,description\nExisting,KNOX-UPD,new\n"),
            "a.csv",
            "Asset",
            folder.id,
            HTTP_X_ON_CONFLICT="update",
        )
        assert resp.json()["results"]["updated"] == 1
        assert Asset.objects.get(ref_id="KNOX-UPD").description == "new"

    def test_restricted_user_cannot_update_hidden_record(
        self, knox_restricted_client, app_ready
    ):
        """
        find_existing() locates the record regardless of RBAC (it searches by
        ref_id/name, not by viewable_ids).  The update is blocked one layer
        deeper: BaseModelSerializer.update() calls _check_object_perm("change"),
        which calls RoleAssignment.is_access_allowed() with the real request
        user.  A user with no role assignments has no "change_asset" permission
        on any folder, so PermissionDenied is raised → failed == 1, updated == 0,
        and the record on disk is unchanged.

        This test proves get_accessible_object_ids() / is_access_allowed() are
        called with the real user and return real results — not a patched shortcut.
        """
        folder = app_ready
        asset = Asset.objects.create(
            name="Hidden Asset", ref_id="RBAC-001", folder=folder
        )
        resp = _post(
            knox_restricted_client,
            _csv("name,ref_id,description\nHidden Asset,RBAC-001,attempted update\n"),
            "a.csv",
            "Asset",
            folder.id,
            HTTP_X_ON_CONFLICT="update",
        )
        body = resp.json()
        assert body["results"]["updated"] == 0
        assert body["results"]["failed"] == 1
        asset.refresh_from_db()
        assert asset.description is None
