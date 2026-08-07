"""
End-to-end coverage for the xlsx templates shipped with the data import
documentation (https://intuitem.gitbook.io/ciso-assistant/guide/data-import-wizard).

Each template under data_wizard/import_templates/ is uploaded through the
LoadFileView endpoint with the model type it advertises in the docs, then
the response and a spot-checked record are asserted against the template
content.
"""

from pathlib import Path

import pytest

from core.models import (
    AppliedControl,
    Asset,
    Finding,
    FindingsAssessment,
    Incident,
    Perimeter,
    Policy,
    ReferenceControl,
    RiskAssessment,
    RiskMatrix,
    SecurityException,
    Threat,
    Vulnerability,
)
from ebios_rm.models import ElementaryAction
from iam.models import Folder, User, UserGroup
from privacy.models import Processing
from resilience.models import BusinessImpactAnalysis
from tprm.models import Contract, Entity, Representative, Solution


URL = "/api/data-wizard/load-file/"
TEMPLATES_DIR = Path(__file__).parent.parent / "import_templates"


def _read_template(filename: str) -> bytes:
    return (TEMPLATES_DIR / filename).read_bytes()


def _post_template(client, filename: str, model_type: str, folder_id, **extra_headers):
    headers = {
        "HTTP_X_MODEL_TYPE": model_type,
        "HTTP_CONTENT_DISPOSITION": f"attachment; filename={filename}",
        "content_type": "application/octet-stream",
    }
    if folder_id is not None:
        headers["HTTP_X_FOLDER_ID"] = str(folder_id)
    headers.update(extra_headers)
    return client.post(URL, data=_read_template(filename), **headers)


@pytest.fixture
def template_domains(root_folder):
    """Pre-create the domain folders referenced in the shipped templates."""
    names = [
        "Global",
        "Nebula",
        "DEMO",
        "DEMO2",
        "test-domain",
        "IT Security",
        "IT Operations",
        "Human Resources",
        "Facilities",
    ]
    domains = {}
    for name in names:
        folder, _ = Folder.objects.get_or_create(
            name=name,
            parent_folder=root_folder,
            defaults={"content_type": Folder.ContentType.DOMAIN},
        )
        domains[name] = folder
    return domains


@pytest.fixture
def ebios_4x4_matrix(root_folder):
    return RiskMatrix.objects.create(
        name="4x4 risk matrix from EBIOS-RM",
        ref_id="risk-matrix-4x4-ebios-rm",
        folder=root_folder,
        json_definition={
            "name": "4x4 risk matrix from EBIOS-RM",
            "probability": [
                {
                    "id": 0,
                    "abbreviation": "V1",
                    "name": "Unlikely",
                    "translations": {"fr": {"name": "Peu vraisemblable"}},
                },
                {
                    "id": 1,
                    "abbreviation": "V2",
                    "name": "Likely",
                    "translations": {"fr": {"name": "Vraisemblable"}},
                },
                {
                    "id": 2,
                    "abbreviation": "V3",
                    "name": "Very likely",
                    "translations": {"fr": {"name": "Très vraisemblable"}},
                },
                {
                    "id": 3,
                    "abbreviation": "V4",
                    "name": "Certain",
                    "translations": {"fr": {"name": "Certain"}},
                },
            ],
            "impact": [
                {
                    "id": 0,
                    "abbreviation": "G1",
                    "name": "Minor",
                    "translations": {"fr": {"name": "Mineur"}},
                },
                {
                    "id": 1,
                    "abbreviation": "G2",
                    "name": "Significant",
                    "translations": {"fr": {"name": "Significatif"}},
                },
                {
                    "id": 2,
                    "abbreviation": "G3",
                    "name": "Important",
                    "translations": {"fr": {"name": "Important"}},
                },
                {
                    "id": 3,
                    "abbreviation": "G4",
                    "name": "Critical",
                    "translations": {"fr": {"name": "Critique"}},
                },
            ],
            "risk": [
                {"id": 0, "abbreviation": "1", "name": "Low"},
                {"id": 1, "abbreviation": "2", "name": "Medium"},
                {"id": 2, "abbreviation": "3", "name": "High"},
            ],
            "grid": [
                [0, 0, 0, 1],
                [0, 0, 1, 1],
                [1, 1, 2, 2],
                [1, 2, 2, 2],
            ],
        },
    )


@pytest.fixture
def template_perimeter(domain_folder):
    return Perimeter.objects.create(
        name="Template Perimeter",
        ref_id="TPL-PRM-01",
        folder=domain_folder,
    )


@pytest.mark.django_db
class TestSimpleTemplates:
    def test_assets_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "assets_template.xlsx", "Asset", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 4
        first = Asset.objects.get(ref_id="X.01")
        assert first.name == "alpha"
        assert first.type == Asset.Type.PRIMARY

    def test_applied_controls_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "applied_controls_template.xlsx",
            "AppliedControl",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 20
        firewall = AppliedControl.objects.get(ref_id="AC-001")
        assert firewall.name == "Firewall"
        assert firewall.csf_function == "protect"

    def test_perimeters_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "perimeters_template.xlsx", "Perimeter", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 3
        first = Perimeter.objects.get(ref_id="PRJ.01")
        assert first.name == "Secret project"
        assert first.lc_status == "eol"

    def test_users_template(self, api_client, domain_folder, all_accessible):
        resp = _post_template(
            api_client, "users_template.xlsx", "User", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 2
        user = User.objects.get(email="john.doe@company.com")
        assert user.first_name == "john"
        assert user.last_name == "doe"

    def test_elementary_actions_template(
        self, api_client, domain_folder, all_accessible
    ):
        resp = _post_template(
            api_client,
            "elementary_actions_template.xlsx",
            "ElementaryAction",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 4
        first = ElementaryAction.objects.get(name="step 05")
        assert first.attack_stage == ElementaryAction.AttackStage.KNOW
        assert first.icon == "server"

    def test_reference_controls_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "reference_controls_template.xlsx",
            "ReferenceControl",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 7
        first = ReferenceControl.objects.get(ref_id="RC-001")
        assert first.name == "Access Control Policy"
        assert first.csf_function == "govern"

    def test_threats_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "threats_template.xlsx", "Threat", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 7
        first = Threat.objects.get(ref_id="T-001")
        assert first.name == "Phishing Attack"

    def test_domains_template(self, api_client, root_folder, all_accessible):
        resp = _post_template(
            api_client, "domains_template.xlsx", "Folder", root_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 4
        acme = Folder.objects.get(name="ACME Corp", parent_folder=root_folder)
        it = Folder.objects.get(name="IT Department")
        assert it.parent_folder == acme
        assert acme.create_iam_groups is True
        assert it.create_iam_groups is False
        assert UserGroup.objects.filter(folder=acme).exists()
        assert not UserGroup.objects.filter(folder=it).exists()

    def test_security_exceptions_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "security_exceptions_template.xlsx",
            "SecurityException",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 1
        first = SecurityException.objects.get(ref_id="DE.01")
        assert first.name == "Exception 01"
        assert first.status == "approved"

    def test_incidents_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "incidents_template.xlsx", "Incident", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 1
        first = Incident.objects.get(ref_id="IN.01")
        assert first.name == "Incident 01"
        assert first.detection == Incident.Detection.INTERNAL

    def test_policies_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "policies_template.xlsx", "Policy", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 1
        first = Policy.objects.get(ref_id="POL.01")
        assert first.name == "Policy 1"
        assert first.status == "active"

    def test_vulnerabilities_template(self, api_client, domain_folder, all_accessible):
        for asset_name in ("website", "Office", "Wifi"):
            Asset.objects.create(name=asset_name, folder=domain_folder)
        resp = _post_template(
            api_client,
            "vulnerabilities_template.xlsx",
            "Vulnerability",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 2
        first = Vulnerability.objects.get(ref_id="Vuln_05")
        assert first.name == "reflected XSS"
        assert first.assets.filter(name="website").exists()
        # The template separates multi-values with newlines (alt+enter in Excel).
        assert set(first.filtering_labels.values_list("label", flat=True)) == {
            "Web",
            "code-injection",
        }
        second = Vulnerability.objects.get(ref_id="Vuln_06")
        assert set(second.assets.values_list("name", flat=True)) == {"Office", "Wifi"}

    def test_processings_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "processings_template.xlsx", "Processing", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 2
        proc = Processing.objects.get(ref_id="process 2")
        assert proc.name == "processing 2"


@pytest.mark.django_db
class TestMultiSheetTemplates:
    def test_third_parties_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "third_parties_template.xlsx",
            "TPRM",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["entities"]["successful"] == 3
        assert results["solutions"]["successful"] == 3
        assert results["contracts"]["successful"] == 3
        assert results["representatives"]["successful"] == 3
        parent = Entity.objects.get(ref_id="ENT-001")
        assert parent.name == "ACME Corporation"
        europe = Entity.objects.get(ref_id="ENT-002")
        assert europe.parent_entity == parent
        sol = Solution.objects.get(ref_id="SOL-001")
        assert sol.provider_entity == Entity.objects.get(ref_id="ENT-003")
        contract = Contract.objects.get(ref_id="CON-001")
        assert sol in contract.solutions.all()
        marie = Representative.objects.get(email="marie.durand@techvendor.com")
        assert marie.first_name == "Marie"
        assert marie.entity == Entity.objects.get(ref_id="ENT-003")
        alexandre = Representative.objects.get(email="alexandre.morel@acmecorp.com")
        assert alexandre.role == "Security Coordinator"
        assert alexandre.entity == parent


@pytest.mark.django_db
class TestAssessmentTemplates:
    def test_findings_assessment_template(
        self,
        api_client,
        domain_folder,
        template_domains,
        template_perimeter,
        all_accessible,
    ):
        resp = _post_template(
            api_client,
            "findings_assessment_template.xlsx",
            "FindingsAssessment",
            domain_folder.id,
            HTTP_X_PERIMETER_ID=str(template_perimeter.id),
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 3
        assert (
            FindingsAssessment.objects.filter(perimeter=template_perimeter).count() == 1
        )
        first = Finding.objects.get(ref_id="tls.001")
        assert first.name == "weak ciphers detected"
        assert first.status == "dismissed"
        assert first.asset.name == "web frontend"
        assert first.asset.folder == domain_folder
        assert first.asset.type == Asset.Type.SUPPORT
        assert results["details"]["assets_created"] == 3

    def test_risk_assessment_template(
        self,
        api_client,
        domain_folder,
        template_perimeter,
        ebios_4x4_matrix,
        all_accessible,
    ):
        resp = _post_template(
            api_client,
            "risk_assessment_template.xlsx",
            "RiskAssessment",
            domain_folder.id,
            HTTP_X_PERIMETER_ID=str(template_perimeter.id),
            HTTP_X_MATRIX_ID=str(ebios_4x4_matrix.id),
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["successful"] == 4
        ra = RiskAssessment.objects.get(perimeter=template_perimeter)
        scenarios = ra.risk_scenarios.order_by("ref_id")
        assert [s.ref_id for s in scenarios] == ["R01", "R02", "R03", "R04"]
        assert scenarios.get(ref_id="R01").treatment == "avoid"
        assert set(
            scenarios.get(ref_id="R01").assets.values_list("name", flat=True)
        ) == {"erp", "database server"}
        assert list(
            scenarios.get(ref_id="R02").assets.values_list("name", flat=True)
        ) == ["erp"]
        assert not scenarios.get(ref_id="R03").assets.exists()
        assert results["details"]["assets_created"] == 3

    def test_business_impact_analysis_template(
        self,
        api_client,
        domain_folder,
        template_domains,
        template_perimeter,
        ebios_4x4_matrix,
        all_accessible,
    ):
        Asset.objects.create(name="hypervisor", folder=template_domains["DEMO"])
        resp = _post_template(
            api_client,
            "business_impact_analysis_template.xlsx",
            "BusinessImpactAnalysis",
            template_domains["DEMO"].id,
            HTTP_X_PERIMETER_ID=str(template_perimeter.id),
            HTTP_X_MATRIX_ID=str(ebios_4x4_matrix.id),
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["bia"]["successful"] == 1
        bia = BusinessImpactAnalysis.objects.get(name="bia")
        assert bia.version == "1.0"


@pytest.mark.django_db
class TestTaskTemplateTemplates:
    def test_tasks_template(self, api_client, domain_folder, all_accessible):
        # Warnings are expected: the sample cross-references demo objects
        # (users, assets, audits) that don't exist on a blank instance.
        resp = _post_template(
            api_client,
            "tasks_template.xlsx",
            "TaskTemplate",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["templates"]["created"] == 8
        assert results["templates"]["failed"] == 0
        assert results["task_nodes"]["failed"] == 0


@pytest.mark.django_db
class TestImportTemplateDownload:
    def test_every_declared_template_downloads(self, api_client):
        from data_wizard.views import IMPORT_TEMPLATES, IMPORT_TEMPLATES_DIR

        for model_type, filename in IMPORT_TEMPLATES.items():
            assert (IMPORT_TEMPLATES_DIR / filename).is_file(), filename
            resp = api_client.get(f"/api/data-wizard/templates/{model_type.value}/")
            assert resp.status_code == 200, model_type
            assert filename in resp["Content-Disposition"]

    def test_unknown_or_templateless_model_is_404(self, api_client):
        for model_type in ("ComplianceAssessment", "NotAModel"):
            resp = api_client.get(f"/api/data-wizard/templates/{model_type}/")
            assert resp.status_code == 404
