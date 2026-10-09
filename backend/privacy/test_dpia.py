from pathlib import Path

import pytest
from core.models import (
    AppliedControl,
    Asset,
    QuickForm,
    QuickFormResponse,
    RiskMatrix,
    StoredLibrary,
    Terminology,
)
from core.startup import startup
from global_settings.models import GlobalSettings
from global_settings.serializers import validate_dpia_screening_form_value
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from privacy.models import Dpia, PersonalData, Processing, Purpose
from privacy.screening import screening_reasons


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def admin_client(app_config):
    user = User.objects.create_user(email="dpia-admin@test.local", is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def privacy_matrix(app_config):
    stored = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:risk-matrix-4x4-privacy"
    )
    assert stored.load() is None
    return RiskMatrix.objects.get(
        urn="urn:intuitem:risk:matrix:risk-matrix-4x4-privacy"
    )


@pytest.fixture
def processing(app_config):
    domain = Folder.objects.create(
        name="DpiaDomain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    processing = Processing.objects.create(name="Loyalty programme", folder=domain)
    Purpose.objects.create(
        processing=processing, name="Profiling", legal_basis="privacy_consent"
    )
    crm = Asset.objects.create(name="CRM", folder=domain)
    category = Terminology.objects.filter(
        field_path=Terminology.FieldPath.PERSONAL_DATA_CATEGORY
    ).first()
    personal_data = PersonalData.objects.create(
        processing=processing, name="Purchase history", category=category
    )
    personal_data.assets.add(crm)
    control = AppliedControl.objects.create(
        name="Pseudonymisation", folder=domain, status="in_progress"
    )
    processing.associated_controls.add(control)
    return processing


@pytest.mark.django_db
def test_create_seeds_both_risk_registers(admin_client, processing, privacy_matrix):
    response = admin_client.post(
        "/api/privacy/dpias/",
        {
            "name": "DPIA loyalty",
            "processing": str(processing.id),
            "reasons": ["evaluation_scoring", "large_scale"],
            "risk_matrix": str(privacy_matrix.id),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()

    dpia = Dpia.objects.get(id=response.json()["id"])
    assert dpia.folder == processing.folder
    assert dpia.design_risk_assessment.risk_scenarios.count() == 0
    incident = dpia.incident_risk_assessment.risk_scenarios.all()
    assert incident.count() == 3
    assert all(s.assets.filter(name="CRM").exists() for s in incident)


@pytest.mark.django_db
def test_report_projects_the_processing(admin_client, processing, privacy_matrix):
    dpia = Dpia.objects.create(name="DPIA", processing=processing)
    response = admin_client.get(f"/api/privacy/dpias/{dpia.id}/report/")
    assert response.status_code == 200
    report = response.json()

    assert report["overview"]["processing"]["name"] == "Loyalty programme"
    assert report["description"]["purposes"][0]["name"] == "Profiling"
    assert report["description"]["supporting_assets"][0]["name"] == "CRM"
    assert report["measures"][0]["edpb_status"] == "partially_implemented"
    assert "incident_risk_assessment" in report["missing"]
    assert "decision" in report["missing"]


@pytest.mark.django_db
def test_risk_registers_action_is_idempotent(admin_client, processing, privacy_matrix):
    dpia = Dpia.objects.create(name="DPIA", processing=processing)
    url = f"/api/privacy/dpias/{dpia.id}/risk-registers/"
    first = admin_client.post(
        url, {"risk_matrix": str(privacy_matrix.id)}, format="json"
    )
    second = admin_client.post(
        url, {"risk_matrix": str(privacy_matrix.id)}, format="json"
    )
    assert first.status_code == 200
    assert first.json() == second.json()
    dpia.refresh_from_db()
    assert dpia.incident_risk_assessment.risk_scenarios.count() == 3


@pytest.mark.django_db
def test_unknown_reason_is_rejected(admin_client, processing):
    response = admin_client.post(
        "/api/privacy/dpias/",
        {"name": "DPIA", "processing": str(processing.id), "reasons": ["gut_feeling"]},
        format="json",
    )
    assert response.status_code == 400
    assert "reasons" in response.json()


SCREENING = "urn:intuitem:risk:qf_page:pre-dpia-screening"
CRITERIA = f"{SCREENING}:criteria:question:criteria"
EXEMPTION = f"{SCREENING}:exemption:question:exemption"
BASE_ANSWERS = {
    f"{SCREENING}:identification:question:role": f"{SCREENING}:identification:question:role:choice:controller",
    f"{SCREENING}:identification:question:stage": f"{SCREENING}:identification:question:stage:choice:new",
}


@pytest.fixture
def screening_form(app_config):
    stored = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:pre-dpia-screening"
    )
    assert stored.load() is None


def _screen(client, processing, answers):
    started = client.post(f"/api/privacy/processings/{processing.id}/dpia-screening/")
    assert started.status_code == 201, started.json()
    response_id = started.json()["id"]
    patched = client.patch(
        f"/api/quick-form-responses/{response_id}/",
        {"answers": {**BASE_ANSWERS, **answers}},
        format="json",
    )
    assert patched.status_code == 200, patched.json()
    submitted = client.post(
        f"/api/quick-form-responses/{response_id}/set-status/",
        {"status": "submitted"},
        format="json",
    )
    assert submitted.status_code == 200, submitted.json()
    processing.refresh_from_db()
    return response_id


@pytest.mark.django_db
def test_screening_is_prefilled_and_resumed(admin_client, processing, screening_form):
    url = f"/api/privacy/processings/{processing.id}/dpia-screening/"
    first = admin_client.post(url)
    assert first.status_code == 201
    second = admin_client.post(url)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    processing.refresh_from_db()
    assert str(processing.dpia_screening_id) == first.json()["id"]
    content = admin_client.get(
        f"/api/quick-form-responses/{first.json()['id']}/content/"
    )
    answers = content.json()["answers"]
    assert answers[f"{SCREENING}:identification:question:name"] == "Loyalty programme"
    assert answers[f"{SCREENING}:identification:question:purpose"] == "Profiling"


@pytest.mark.django_db
def test_two_criteria_mark_the_dpia_required(admin_client, processing, screening_form):
    _screen(
        admin_client,
        processing,
        {
            CRITERIA: [
                f"{CRITERIA}:choice:evaluation_scoring",
                f"{CRITERIA}:choice:large_scale",
            ],
            EXEMPTION: f"{EXEMPTION}:choice:none",
        },
    )
    assert processing.dpia_required is True


@pytest.mark.django_db
def test_no_criterion_clears_the_flag(admin_client, processing, screening_form):
    Processing.objects.filter(pk=processing.pk).update(dpia_required=True)
    _screen(admin_client, processing, {CRITERIA: [f"{CRITERIA}:choice:none"]})
    assert processing.dpia_required is False


@pytest.mark.django_db
def test_claimed_exemption_leaves_the_flag_alone(
    admin_client, processing, screening_form
):
    _screen(
        admin_client,
        processing,
        {
            CRITERIA: [
                f"{CRITERIA}:choice:evaluation_scoring",
                f"{CRITERIA}:choice:large_scale",
            ],
            EXEMPTION: f"{EXEMPTION}:choice:list",
        },
    )
    assert processing.dpia_required is False


@pytest.mark.django_db
def test_dpia_inherits_the_screening(admin_client, processing, screening_form):
    response_id = _screen(
        admin_client,
        processing,
        {
            CRITERIA: [
                f"{CRITERIA}:choice:sensitive_data",
                f"{CRITERIA}:choice:vulnerable_subjects",
            ],
            EXEMPTION: f"{EXEMPTION}:choice:none",
        },
    )
    created = admin_client.post(
        "/api/privacy/dpias/",
        {"name": "DPIA", "processing": str(processing.id)},
        format="json",
    )
    assert created.status_code == 201, created.json()
    dpia = Dpia.objects.get(id=created.json()["id"])
    assert str(dpia.screening_id) == response_id
    assert dpia.reasons == ["sensitive_data", "vulnerable_subjects"]


@pytest.mark.django_db
def test_screening_needs_the_library(admin_client, processing):
    response = admin_client.post(
        f"/api/privacy/processings/{processing.id}/dpia-screening/"
    )
    assert response.status_code == 400


def _load_custom_screening():
    source = Path(__file__).resolve().parent.parent / (
        "library/libraries/quick-form-pre-dpia-screening.yaml"
    )
    content = (
        source.read_text()
        .replace("urn:intuitem:risk:", "urn:acme:risk:")
        .replace("ref_id: pre-dpia-screening", "ref_id: acme-dpia-screening")
        .replace("name: Pre-DPIA screening", "name: ACME screening")
        .replace("provider: intuitem", "provider: acme")
    )
    stored, error = StoredLibrary.store_library_content(content.encode())
    assert error is None, error
    assert stored.load() is None
    return QuickForm.objects.get(urn="urn:acme:risk:quick_form:pre-dpia-screening")


@pytest.mark.django_db
def test_configured_custom_form_drives_the_screening(admin_client, processing):
    custom = _load_custom_screening()
    GlobalSettings.objects.update_or_create(
        name="general", defaults={"value": {"dpia_screening_form": str(custom.id)}}
    )
    acme = "urn:acme:risk:qf_page:pre-dpia-screening"
    started = admin_client.post(
        f"/api/privacy/processings/{processing.id}/dpia-screening/"
    )
    assert started.status_code == 201
    response = QuickFormResponse.objects.get(id=started.json()["id"])
    assert response.quick_form_id == custom.id

    criteria = f"{acme}:criteria:question:criteria"
    exemption = f"{acme}:exemption:question:exemption"
    admin_client.patch(
        f"/api/quick-form-responses/{response.id}/",
        {
            "answers": {
                f"{acme}:identification:question:role": f"{acme}:identification:question:role:choice:controller",
                f"{acme}:identification:question:stage": f"{acme}:identification:question:stage:choice:new",
                criteria: [
                    f"{criteria}:choice:large_scale",
                    f"{criteria}:choice:prevents_rights",
                ],
                exemption: f"{exemption}:choice:none",
            }
        },
        format="json",
    )
    submitted = admin_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "submitted"},
        format="json",
    )
    assert submitted.status_code == 200, submitted.json()
    processing.refresh_from_db()
    assert processing.dpia_required is True
    assert screening_reasons(response) == ["large_scale", "prevents_rights"]
    content = admin_client.get(f"/api/quick-form-responses/{response.id}/content/")
    assert (
        content.json()["answers"][f"{acme}:identification:question:name"]
        == "Loyalty programme"
    )


@pytest.mark.django_db
def test_setting_rejects_a_form_without_the_required_outcome(app_config):
    stored = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:derogation-request"
    )
    assert stored.load() is None
    derogation = QuickForm.objects.get(
        urn="urn:intuitem:risk:quick_form:derogation-request"
    )
    with pytest.raises(ValidationError):
        validate_dpia_screening_form_value(str(derogation.id))
