"""
End-to-end coverage for the xlsx templates shipped with the data import
documentation (https://intuitem.gitbook.io/ciso-assistant/guide/data-import-wizard).

Each template under data_wizard/tests/templates/ is uploaded through the
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
from iam.models import Folder, User
from privacy.models import Processing
from resilience.models import BusinessImpactAnalysis
from tprm.models import Contract, Entity, Solution


URL = "/api/data-wizard/load-file/"
TEMPLATES_DIR = Path(__file__).parent / "templates"


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
    def test_sample_assets(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "sample_assets.xlsx", "Asset", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 4
        first = Asset.objects.get(ref_id="X.01")
        assert first.name == "alpha"
        assert first.type == Asset.Type.PRIMARY

    def test_applied_controls_sample(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "applied_controls_sample.xlsx",
            "AppliedControl",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 20
        firewall = AppliedControl.objects.get(ref_id="AC-001")
        assert firewall.name == "Firewall"
        assert firewall.csf_function == "protect"

    def test_sample_perimeters(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "sample_perimeters.xlsx", "Perimeter", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 3
        first = Perimeter.objects.get(ref_id="PRJ.01")
        assert first.name == "Secret project"
        assert first.lc_status == "eol"

    def test_sample_users(self, api_client, domain_folder, all_accessible):
        resp = _post_template(api_client, "sample_users.xlsx", "User", domain_folder.id)
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 2
        user = User.objects.get(email="john.doe@company.com")
        assert user.first_name == "john"
        assert user.last_name == "doe"

    def test_sample_elementary_actions(self, api_client, domain_folder, all_accessible):
        resp = _post_template(
            api_client,
            "sample_elementary_actions.xlsx",
            "ElementaryAction",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 4
        first = ElementaryAction.objects.get(name="step 05")
        assert first.attack_stage == ElementaryAction.AttackStage.KNOW
        assert first.icon == "server"

    def test_sample_reference_controls(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "sample_reference_controls.xlsx",
            "ReferenceControl",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 7
        first = ReferenceControl.objects.get(ref_id="RC-001")
        assert first.name == "Access Control Policy"
        assert first.csf_function == "govern"

    def test_sample_threats(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "sample_threats.xlsx", "Threat", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 7
        first = Threat.objects.get(ref_id="T-001")
        assert first.name == "Phishing Attack"

    def test_sample_folders(self, api_client, root_folder, all_accessible):
        resp = _post_template(
            api_client, "sample_folders.xlsx", "Folder", root_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 4
        acme = Folder.objects.get(name="ACME Corp", parent_folder=root_folder)
        it = Folder.objects.get(name="IT Department")
        assert it.parent_folder == acme

    def test_exceptions_template(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "exceptions_template.xlsx",
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

    @pytest.mark.xfail(
        reason=(
            "template_vulnerabilities.xlsx ships filtering_labels with newline "
            "separators (e.g. 'Web\\ncode injection'), but _resolve_filtering_labels "
            "only splits on '|' or ',' (data_wizard/views.py). The whole string is "
            "treated as a single label name and fails validation, so neither row is "
            "created. Either the template should use '|' or the parser should also "
            "split on newlines."
        ),
        strict=True,
    )
    def test_template_vulnerabilities(self, api_client, domain_folder, all_accessible):
        for asset_name in ("website", "Office", "Wifi"):
            Asset.objects.create(name=asset_name, folder=domain_folder)
        resp = _post_template(
            api_client,
            "template_vulnerabilities.xlsx",
            "Vulnerability",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 2
        first = Vulnerability.objects.get(ref_id="Vuln_05")
        assert first.name == "reflected XSS"
        assert first.assets.filter(name="website").exists()

    def test_sample_processings(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client, "sample-processings.xlsx", "Processing", domain_folder.id
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["created"] == 2
        proc = Processing.objects.get(ref_id="process 2")
        assert proc.name == "processing 2"


@pytest.mark.django_db
class TestMultiSheetTemplates:
    def test_third_parties_ecosystem(
        self, api_client, domain_folder, template_domains, all_accessible
    ):
        resp = _post_template(
            api_client,
            "third_parties_ecosystem_template.xlsx",
            "TPRM",
            domain_folder.id,
        )
        assert resp.status_code == 200, resp.json()
        results = resp.json()["results"]
        assert results["entities"]["successful"] == 3
        assert results["solutions"]["successful"] == 3
        assert results["contracts"]["successful"] == 3
        parent = Entity.objects.get(ref_id="ENT-001")
        assert parent.name == "ACME Corporation"
        europe = Entity.objects.get(ref_id="ENT-002")
        assert europe.parent_entity == parent
        sol = Solution.objects.get(ref_id="SOL-001")
        assert sol.provider_entity == Entity.objects.get(ref_id="ENT-003")
        contract = Contract.objects.get(ref_id="CON-001")
        assert sol in contract.solutions.all()


@pytest.mark.django_db
class TestAssessmentTemplates:
    def test_sample_findings(
        self,
        api_client,
        domain_folder,
        template_domains,
        template_perimeter,
        all_accessible,
    ):
        resp = _post_template(
            api_client,
            "sample_findings.xlsx",
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

    def test_sample_business_impact_analysis(
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
            "sample_business_impact_analysis.xlsx",
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
class TestUnsupportedTemplates:
    def test_task_templates_template_skipped(self):
        pytest.skip(
            "sample_task-templates.xlsx is exported by the TaskTemplate admin and "
            "is not consumed through the data wizard load-file endpoint."
        )
