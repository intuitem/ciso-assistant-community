import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from core.models import AppliedControl, QuickFormResponse
from core.utils import build_answers_dict
from iam.models import Folder, Role, RoleAssignment, User
from privacy.pia_import import html_to_text
from privacy.test_dpia import (  # noqa: F401 (fixtures)
    admin_client,
    app_config,
    dpia_form,
    processing,
)

P = "urn:intuitem:risk:qf_page:dpia"

# A small export in the shape of the CNIL PIA software's (v4.1 exportData).
EXPORT = {
    "pia": {
        "name": "Loyalty",
        "dpo_status": 1,
        "dpos_names": "Jo DPO",
        "dpo_opinion": "<p>Fine with <strong>conditions</strong>.</p>",
        "concerned_people_searched_opinion": False,
        "concerned_people_searched_content": "Panel too costly.",
        "applied_adjustments": "Encrypt backups.",
        "status": 2,
    },
    "answers": [
        {"reference_to": 111, "data": {"text": "Points for purchases."}},
        {"reference_to": 112, "data": {"text": "Marketing owns it."}},
        {"reference_to": 213, "data": {"text": "<ul><li>email</li><li>age</li></ul>"}},
        {"reference_to": 321, "data": {"list": ["Phishing", "Spam"]}},
        {"reference_to": 324, "data": {"list": ["Encryption", "Unknown"]}},
        {"reference_to": 325, "data": {"text": "Moderate", "gauge": 2}},
        {"reference_to": 326, "data": {"text": "Easy", "gauge": 4}},
    ],
    "measures": [
        {"id": 7, "title": "Encryption", "content": "TLS everywhere"},
        {"id": 8, "title": "Pseudonymisation", "content": "already there"},
    ],
    "evaluations": [
        {
            "reference_to": "3.1.7",
            "action_plan_comment": "Use TLS 1.3",
            "estimated_implementation_date": "2027-01-15T00:00:00.000Z",
        },
        {
            "reference_to": "3.2",
            "gauges": {"x": 1, "y": 3},
            "action_plan_comment": "Audit",
        },
    ],
    "comments": [{"description": "a comment", "reference_to": "1.1"}],
}


def test_html_to_text():
    assert (
        html_to_text("<p>a&amp;b</p><ul><li>x</li><li>y</li></ul>")
        == "a&b\n\n- x\n\n- y"
    )


@pytest.mark.django_db
def test_import_pia_fills_a_draft_dpia(admin_client, processing, dpia_form):
    url = f"/api/privacy/processings/{processing.id}/import-pia/"
    res = admin_client.post(
        url, {"quick_form": str(dpia_form.id), "pia": EXPORT}, format="json"
    )
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["controls_created"] == 1 and body["controls_reused"] == 1
    # Pseudonymisation is the processing's own control: linked, its file content left out.
    assert body["skipped"] == [
        "piaComments",
        "reusedMeasureDetails",
        "unmatchedMeasures",
    ]

    response = QuickFormResponse.objects.get(id=body["redirect"].rsplit("/", 1)[-1])
    assert response.status == QuickFormResponse.Status.DRAFT
    answers = build_answers_dict(response.answers.select_related("question"))
    encryption = AppliedControl.objects.get(name="Encryption", folder=processing.folder)
    assert encryption.eta.isoformat() == "2027-01-15"
    assert encryption.observation == "Use TLS 1.3"

    assert answers[f"{P}:overview:question:processing"] == [str(processing.id)]
    assert answers[f"{P}:overview:question:benefits"] == (
        "Points for purchases.\n\nResponsibilities: Marketing owns it."
    )
    assert answers[f"{P}:proportionality:question:minimisation"] == "- email\n\n- age"
    a = f"{P}:illegitimate_access:question"
    assert answers[f"{a}:impacts"] == "Phishing, Spam"
    assert answers[f"{a}:measures"] == [str(encryption.id)]
    assert answers[f"{a}:severity"] == f"{a}:severity:choice:limited"
    assert answers[f"{a}:likelihood"].endswith(":choice:maximum")
    assert (
        answers[f"{a}:residual_severity"] == f"{a}:residual_severity:choice:negligible"
    )
    assert answers[f"{a}:severity_justification"] == "Moderate"
    v = f"{P}:validation:question"
    assert answers[f"{v}:dpo_opinion"] == "Jo DPO, favourable\n\nFine with conditions."
    assert answers[f"{v}:views_not_sought_reason"] == "Panel too costly."
    assert answers[f"{v}:conditions"] == (
        "Encrypt backups.\n\nRisks: illegitimate access to data — Audit"
    )
    assert answers[f"{v}:decision"] is None
    # Nothing written on the processing before the DPIA is accepted.
    assert not processing.associated_controls.filter(id=encryption.id).exists()

    # A second import never writes over the draft.
    again = admin_client.post(
        url, {"quick_form": str(dpia_form.id), "pia": EXPORT}, format="json"
    )
    assert again.status_code == 409 and again.json()["error"] == "dpiaDraftExists"


@pytest.mark.django_db
def test_import_pia_rejects_bad_files(admin_client, processing, dpia_form):
    url = f"/api/privacy/processings/{processing.id}/import-pia/"
    for pia, code in (
        ({"answers": []}, "piaInvalidFile"),
        ({"pia": {"structure_id": 3}}, "piaCustomStructure"),
        (
            {"pia": {}, "answers": [{"reference_to": 111, "data": "x"}]},
            "piaInvalidFile",
        ),
        ({"pia": {}, "answers": [{"data": {"list": "abc"}}]}, "piaInvalidFile"),
        ({"pia": {}, "evaluations": [{"gauges": "x"}]}, "piaInvalidFile"),
    ):
        res = admin_client.post(
            url, {"quick_form": str(dpia_form.id), "pia": pia}, format="json"
        )
        assert res.status_code == 400 and res.json()["error"] == code
    for labels in ("Responsibilities:", {"legalBasis": 3}, {"favourable": "x" * 101}):
        res = admin_client.post(
            url,
            {"quick_form": str(dpia_form.id), "pia": EXPORT, "labels": labels},
            format="json",
        )
        assert res.status_code == 400 and res.json()["error"] == "invalidRequest"
    assert not QuickFormResponse.objects.filter(quick_form=dpia_form).exists()


@pytest.mark.django_db
def test_import_pia_reuses_a_control_whatever_its_case(
    admin_client, processing, dpia_form
):
    # Names are unique per domain regardless of case: creating "Encryption" would fail.
    existing = AppliedControl.objects.create(
        folder=processing.folder, name="encryption"
    )
    url = f"/api/privacy/processings/{processing.id}/import-pia/"
    res = admin_client.post(
        url, {"quick_form": str(dpia_form.id), "pia": EXPORT}, format="json"
    )
    assert res.status_code == 201, res.json()
    body = res.json()
    assert body["controls_created"] == 0 and body["controls_reused"] == 2
    assert "reusedMeasureDetails" in body["skipped"]
    assert (
        AppliedControl.objects.filter(
            folder=processing.folder, name__iexact="encryption"
        ).count()
        == 1
    )
    response = QuickFormResponse.objects.get(id=body["redirect"].rsplit("/", 1)[-1])
    answers = build_answers_dict(response.answers.select_related("question"))
    assert answers[f"{P}:illegitimate_access:question:measures"] == [str(existing.id)]


@pytest.mark.django_db
def test_import_pia_writes_the_callers_labels(admin_client, processing, dpia_form):
    url = f"/api/privacy/processings/{processing.id}/import-pia/"
    export = {
        **EXPORT,
        "answers": [a for a in EXPORT["answers"] if a["reference_to"] != 111],
    }
    labels = {"responsibilities": "Responsabilités :", "favourable": "favorable"}
    res = admin_client.post(
        url,
        {"quick_form": str(dpia_form.id), "pia": export, "labels": labels},
        format="json",
    )
    assert res.status_code == 201, res.json()
    response = QuickFormResponse.objects.get(
        id=res.json()["redirect"].rsplit("/", 1)[-1]
    )
    answers = build_answers_dict(response.answers.select_related("question"))
    # Not what the question asks: labelled, even with nothing before it.
    assert answers[f"{P}:overview:question:benefits"] == (
        "Responsabilités : Marketing owns it."
    )
    assert answers[f"{P}:validation:question:dpo_opinion"] == (
        "Jo DPO, favorable\n\nFine with conditions."
    )


@pytest.mark.django_db
def test_import_pia_needs_a_cnil_shaped_form(admin_client, processing, dpia_form):
    url = f"/api/privacy/processings/{processing.id}/import-pia/"
    payload = {"quick_form": str(dpia_form.id), "pia": EXPORT}
    measures = dpia_form.pages.get(urn=f"{P}:measures")
    dpia_form.pages.filter(pk=measures.pk).update(urn=None)
    res = admin_client.post(url, payload, format="json")
    assert res.status_code == 400 and res.json()["error"] == "piaFormMismatch"
    assert not QuickFormResponse.objects.filter(quick_form=dpia_form).exists()
    assert not AppliedControl.objects.filter(name="Encryption").exists()

    dpia_form.pages.filter(pk=measures.pk).update(urn=f"{P}:measures")
    dpia_form.pages.filter(urn=f"{P}:overview").update(urn=None)
    bad_date = {
        **EXPORT,
        "evaluations": [
            {"reference_to": "3.1.7", "estimated_implementation_date": "2027-02-30"}
        ],
    }
    res = admin_client.post(
        url, {"quick_form": str(dpia_form.id), "pia": bad_date}, format="json"
    )
    assert res.status_code == 201, res.json()
    assert "unmappedAnswers" in res.json()["skipped"]
    assert AppliedControl.objects.get(name="Encryption").eta is None


def _domain_user(domain, codenames):
    user = User.objects.create_user(email="pia-analyst@test.local", is_published=True)
    role = Role.objects.create(name="pia-importer")
    role.permissions.set(Permission.objects.filter(codename__in=codenames))
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
    )
    assignment.perimeter_folders.add(domain)
    reader = Role.objects.create(name="pia-form-reader")
    reader.permissions.set(Permission.objects.filter(codename="view_quickform"))
    RoleAssignment.objects.create(
        user=user, role=reader, folder=Folder.get_root_folder()
    ).perimeter_folders.add(Folder.get_root_folder())
    client = APIClient()
    client.force_authenticate(user=user)
    return client


IMPORTER = [
    "view_folder",
    "view_processing",
    "view_quickform",
    "view_quickformresponse",
    "add_quickformresponse",
    "change_quickformresponse",
    "view_appliedcontrol",
    "add_appliedcontrol",
]


@pytest.mark.django_db
def test_import_pia_needs_rights_on_the_processing_domain(processing, dpia_form):
    url = f"/api/privacy/processings/{processing.id}/import-pia/"
    payload = {"quick_form": str(dpia_form.id), "pia": EXPORT}

    no_controls = [c for c in IMPORTER if c != "add_appliedcontrol"]
    res = _domain_user(processing.folder, no_controls).post(url, payload, format="json")
    assert res.status_code == 403 and res.json()["error"] == "permissionDenied"
    User.objects.filter(email="pia-analyst@test.local").delete()
    Role.objects.filter(name__startswith="pia-").delete()

    elsewhere = Folder.objects.create(
        name="Elsewhere",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    res = _domain_user(elsewhere, IMPORTER).post(url, payload, format="json")
    assert res.status_code == 404
    User.objects.filter(email="pia-analyst@test.local").delete()
    Role.objects.filter(name__startswith="pia-").delete()

    res = _domain_user(processing.folder, IMPORTER).post(url, payload, format="json")
    assert res.status_code == 201, res.json()
    assert AppliedControl.objects.filter(
        name="Encryption", folder=processing.folder
    ).exists()
