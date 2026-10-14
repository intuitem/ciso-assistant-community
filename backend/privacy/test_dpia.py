from pathlib import Path

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import (
    AppliedControl,
    Asset,
    QuickForm,
    QuickFormApplication,
    QuickFormResponse,
    StoredLibrary,
    Terminology,
)
from core.startup import startup
from iam.models import Folder, User, UserGroup
from privacy.models import (
    DpiaRequirementChange,
    PersonalData,
    Processing,
    Purpose,
)


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _admin_client(email):
    user = User.objects.create_user(email=email, is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def admin_client(app_config):
    return _admin_client("dpia-admin@test.local")


@pytest.fixture
def reviewer_client(app_config):
    """A second administrator: nobody reviews their own request."""
    return _admin_client("dpia-reviewer@test.local")


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


SCREENING = "urn:intuitem:risk:qf_page:pre-dpia-screening"
TARGET = "processing.dpia_required"


def _answers(page, criteria, exemption=None):
    question = f"{page}:criteria:question:criteria"
    answers = {
        f"{page}:identification:question:role": f"{page}:identification:question:role:choice:controller",
        f"{page}:identification:question:stage": f"{page}:identification:question:stage:choice:new",
        question: [f"{question}:choice:{c}" for c in criteria],
    }
    if exemption:
        question = f"{page}:exemption:question:exemption"
        answers[question] = f"{question}:choice:{exemption}"
    return answers


@pytest.fixture
def screening_form(app_config):
    stored = StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:pre-dpia-screening"
    )
    assert stored.load() is None
    return QuickForm.objects.get(urn="urn:intuitem:risk:quick_form:pre-dpia-screening")


def _screen(client, quick_form, processing, answers):
    started = client.post(
        f"/api/quick-forms/{quick_form.id}/start/",
        {"subject": str(processing.id)},
        format="json",
    )
    assert started.status_code == 200, started.json()
    response_id = started.json()["redirect"].rsplit("/", 1)[-1]
    patched = client.patch(
        f"/api/quick-form-responses/{response_id}/",
        {"answers": answers},
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
    return QuickFormResponse.objects.get(id=response_id)


@pytest.mark.django_db
def test_screening_is_offered_and_bound_to_the_processing(
    admin_client, processing, screening_form
):
    options = admin_client.get(
        "/api/quick-forms/assess-options/",
        {"target": TARGET, "subject": str(processing.id)},
    )
    assert [o["id"] for o in options.json()] == [str(screening_form.id)]

    url = f"/api/quick-forms/{screening_form.id}/start/"
    first = admin_client.post(url, {"subject": str(processing.id)}, format="json")
    second = admin_client.post(url, {"subject": str(processing.id)}, format="json")
    assert second.json()["resumed"] is True
    assert first.json()["redirect"] == second.json()["redirect"]
    response = QuickFormResponse.objects.get(
        id=first.json()["redirect"].rsplit("/", 1)[-1]
    )
    assert response.subject_object_id == processing.id
    assert response.folder_id == processing.folder_id


@pytest.mark.django_db
def test_two_criteria_mark_the_dpia_required(admin_client, processing, screening_form):
    response = _screen(
        admin_client,
        screening_form,
        processing,
        _answers(SCREENING, ["evaluation_scoring", "large_scale"], exemption="none"),
    )
    assert response.status == QuickFormResponse.Status.CLOSED
    assert processing.dpia_required is True
    assert processing.dpia_screening_id == response.id
    application = QuickFormApplication.objects.get(response=response)
    assert (application.previous_value, application.new_value) == (False, True)


@pytest.mark.django_db
def test_no_criterion_clears_the_flag(admin_client, processing, screening_form):
    Processing.objects.filter(pk=processing.pk).update(dpia_required=True)
    _screen(admin_client, screening_form, processing, _answers(SCREENING, ["none"]))
    assert processing.dpia_required is False


@pytest.mark.django_db
def test_every_screening_applies_on_submit(admin_client, processing, screening_form):
    recommended = _screen(
        admin_client,
        screening_form,
        processing,
        _answers(SCREENING, ["large_scale"]),
    )
    assert recommended.status == QuickFormResponse.Status.CLOSED
    assert recommended.decided_by == recommended.submitted_by
    assert processing.dpia_required is True

    exempted = _screen(
        admin_client,
        screening_form,
        processing,
        _answers(SCREENING, ["evaluation_scoring", "large_scale"], exemption="list"),
    )
    assert exempted.status == QuickFormResponse.Status.CLOSED
    assert processing.dpia_required is False
    assert processing.dpia_required_source == "assessment"


def _exemptions_go_to_review(quick_form):
    """A form of your own that leaves exemptions to a reviewer."""
    config = quick_form.on_accept[0]["config"]
    config["mapping"] = [
        r for r in config["mapping"] if r["outcome"] != "exemption_claimed"
    ]
    config["review"] = ["exemption_claimed"]
    quick_form.save(update_fields=["on_accept"])


@pytest.mark.django_db
def test_nothing_offered_without_a_screening_form(admin_client, processing):
    options = admin_client.get(
        "/api/quick-forms/assess-options/",
        {"target": TARGET, "subject": str(processing.id)},
    )
    assert options.json() == []


@pytest.mark.django_db
def test_a_cloned_form_drives_the_screening(admin_client, processing):
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
    custom = QuickForm.objects.get(urn="urn:acme:risk:quick_form:pre-dpia-screening")

    response = _screen(
        admin_client,
        custom,
        processing,
        _answers(
            "urn:acme:risk:qf_page:pre-dpia-screening",
            ["large_scale", "prevents_rights"],
            exemption="none",
        ),
    )
    assert processing.dpia_required is True
    assert response.quick_form == custom


@pytest.mark.django_db
def test_an_applied_screening_is_dated_and_logged(
    admin_client, processing, screening_form
):
    response = _screen(
        admin_client,
        screening_form,
        processing,
        _answers(SCREENING, ["evaluation_scoring", "large_scale"], exemption="none"),
    )
    assert processing.dpia_required_source == "assessment"
    assert processing.dpia_required_set_at is not None
    change = DpiaRequirementChange.objects.get(processing=processing)
    assert (change.previous_dpia_required, change.dpia_required) == (False, True)
    assert (change.source, change.response_id) == ("assessment", response.id)
    assert change.folder_id == processing.folder_id


@pytest.mark.django_db
def test_a_manual_change_keeps_its_reason(admin_client, processing):
    url = f"/api/privacy/processings/{processing.id}/"
    changed = admin_client.patch(
        url,
        {"dpia_required": True, "dpia_required_note": "DPO call"},
        format="json",
    )
    assert changed.status_code == 200, changed.json()
    # Re-saving the same value, or other fields, writes no history.
    admin_client.patch(url, {"dpia_required": True}, format="json")
    admin_client.patch(url, {"description": "Edited"}, format="json")

    processing.refresh_from_db()
    assert processing.dpia_required_source == "manual"
    change = DpiaRequirementChange.objects.get(processing=processing)
    assert (change.source, change.note) == ("manual", "DPO call")
    history = admin_client.get(
        "/api/privacy/dpia-requirement-changes/", {"processing": str(processing.id)}
    )
    assert history.json()["count"] == 1


@pytest.mark.django_db
def test_a_reviewer_settles_an_exemption(
    admin_client, reviewer_client, processing, screening_form
):
    _exemptions_go_to_review(screening_form)
    response = _screen(
        admin_client,
        screening_form,
        processing,
        _answers(SCREENING, ["evaluation_scoring", "large_scale"], exemption="list"),
    )
    url = f"/api/quick-form-responses/{response.id}/set-status/"
    accept = {"status": "closed", "resolution": "accepted"}
    no_note = reviewer_client.post(
        url, {**accept, "overrides": {TARGET: {"value": False}}}, format="json"
    )
    assert no_note.status_code == 400

    accepted = reviewer_client.post(
        url,
        {**accept, "overrides": {TARGET: {"value": False, "note": "On the CNIL list"}}},
        format="json",
    )
    assert accepted.status_code == 200, accepted.json()
    processing.refresh_from_db()
    assert processing.dpia_required is False
    assert processing.dpia_required_source == "override"
    assert processing.dpia_screening_id == response.id
    change = DpiaRequirementChange.objects.get(processing=processing)
    assert (change.source, change.note) == ("override", "On the CNIL list")


@pytest.mark.django_db
def test_overview_counts_where_processings_stand(
    admin_client, processing, screening_form
):
    domain = processing.folder
    Processing.objects.create(name="Untouched", folder=domain)
    _screen(
        admin_client,
        screening_form,
        processing,
        _answers(SCREENING, ["evaluation_scoring", "large_scale"], exemption="none"),
    )
    _exemptions_go_to_review(screening_form)
    pending = Processing.objects.create(name="Pending", folder=domain)
    _screen(
        admin_client,
        screening_form,
        pending,
        _answers(SCREENING, ["evaluation_scoring", "large_scale"], exemption="list"),
    )

    overview = admin_client.get("/api/privacy/processings/dpia-overview/").json()
    assert overview["required_without_dpia"] >= 1
    assert overview["awaiting_review"] >= 1
    assert overview["not_assessed"] >= 2

    url = "/api/privacy/processings/dpia-overview/"
    (row,) = admin_client.get(f"{url}?state=awaiting_review&search=pend").json()["rows"]
    assert row["id"] == str(pending.id)
    assert row["pending_screening"]["status"] == "submitted"

    forms = admin_client.get("/api/privacy/processings/dpia-screening-forms/").json()
    assert [(f["id"], f["problems"]) for f in forms] == [(str(screening_form.id), [])]


DPIA = "urn:intuitem:risk:qf_page:dpia"


@pytest.fixture
def dpia_form(app_config):
    stored = StoredLibrary.objects.get(urn="urn:intuitem:risk:library:dpia")
    assert stored.load() is None
    return QuickForm.objects.get(urn="urn:intuitem:risk:quick_form:dpia")


def _start_dpia(client, quick_form, processing):
    options = client.get(
        "/api/quick-forms/assess-options/",
        {"target": "processing.dpia", "subject": str(processing.id)},
    ).json()
    assert [o["id"] for o in options] == [str(quick_form.id)]
    started = client.post(
        f"/api/quick-forms/{quick_form.id}/start/",
        {"subject": str(processing.id)},
        format="json",
    )
    assert started.status_code == 200, started.json()
    return QuickFormResponse.objects.get(
        id=started.json()["redirect"].rsplit("/", 1)[-1]
    )


@pytest.mark.django_db
def test_a_dpia_is_a_form_on_the_processing(admin_client, processing, dpia_form):
    response = _start_dpia(admin_client, dpia_form, processing)
    assert response.subject == processing
    assert response.ref_id.startswith("DPIA")
    measures = response.answers.get(question__urn=f"{DPIA}:measures:question:measures")
    assert measures.question.config == {
        "model": "applied_control",
        "multiple": True,
        "subject_field": "associated_controls",
    }

    listed = admin_client.get(
        "/api/quick-form-responses/", {"target": "processing.dpia"}
    ).json()
    assert [r["id"] for r in listed["results"]] == [str(response.id)]
    screenings = admin_client.get(
        "/api/quick-form-responses/", {"target": TARGET}
    ).json()
    assert screenings["count"] == 0


@pytest.mark.django_db
def test_an_accepted_dpia_is_the_processings_dpia(
    admin_client, reviewer_client, processing, dpia_form
):
    response = _start_dpia(admin_client, dpia_form, processing)
    response.status = QuickFormResponse.Status.SUBMITTED
    response.save(update_fields=["status"])
    accepted = reviewer_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": "accepted"},
        format="json",
    )
    assert accepted.status_code == 200, accepted.json()
    processing.refresh_from_db()
    assert processing.dpia == response

    Processing.objects.filter(pk=processing.pk).update(dpia_required=True)
    overview = admin_client.get("/api/privacy/processings/dpia-overview/").json()
    assert overview["required_dpia_done"] >= 1
    row = next(r for r in overview["rows"] if r["id"] == str(processing.id))
    assert row["state"] == "required_dpia_done"
    assert row["dpia"]["id"] == str(response.id)


@pytest.mark.django_db
def test_the_form_rating_rates_each_risk(admin_client, processing, dpia_form):
    response = _start_dpia(admin_client, dpia_form, processing)
    page = f"{DPIA}:illegitimate_access:question"
    answers = {
        f"{page}:severity": f"{page}:severity:choice:maximum",
        f"{page}:likelihood": f"{page}:likelihood:choice:negligible",
        f"{page}:residual_severity": f"{page}:residual_severity:choice:limited",
        f"{page}:residual_likelihood": f"{page}:residual_likelihood:choice:limited",
    }
    patched = admin_client.patch(
        f"/api/quick-form-responses/{response.id}/", {"answers": answers}, format="json"
    )
    assert patched.status_code == 200, patched.json()
    url = f"/api/quick-form-responses/{response.id}/content/"

    content = admin_client.get(url).json()
    (rating,) = content["ratings"]
    assert (rating["ref_id"], rating["dimensions"][0]["label"]) == (
        "privacy_risk",
        "Severity",
    )
    points = {p["stage"]: p["level"] for p in rating["points"]}
    # A maximum severity is never acceptable; limited × limited is to reduce.
    assert points == {"current": "unacceptable", "residual": "to_reduce"}
    assert content["computed_values"]["privacy_risk"] == 3.0
    assert "residual_risk_unacceptable" not in (content["computed_outcome"] or {})

    french = admin_client.get(url, HTTP_ACCEPT_LANGUAGE="fr").json()
    assert french["ratings"][0]["dimensions"][0]["label"] == "Gravité"
    severity = next(p for p in french["pages"] if f"{page}:severity" in p["questions"])
    labels = [c["value"] for c in severity["questions"][f"{page}:severity"]["choices"]]
    assert labels[0] == "Négligeable"

    answers[f"{page}:residual_severity"] = f"{page}:residual_severity:choice:maximum"
    admin_client.patch(
        f"/api/quick-form-responses/{response.id}/", {"answers": answers}, format="json"
    )
    content = admin_client.get(url).json()
    assert "residual_risk_unacceptable" in content["computed_outcome"]


@pytest.mark.django_db
def test_the_published_preview_rates_each_risk(admin_client, dpia_form):
    page = f"{DPIA}:illegitimate_access:question"
    res = admin_client.post(
        f"/api/quick-forms/{dpia_form.id}/preview/",
        {
            "answers": {
                f"{page}:severity": f"{page}:severity:choice:maximum",
                f"{page}:likelihood": f"{page}:likelihood:choice:negligible",
            }
        },
        format="json",
    )
    assert res.status_code == 200, res.content[:300]
    assert res.json()["computed_values"]["privacy_risk"] == 3.0


def test_the_dpia_target_previews_without_a_response():
    from core.quick_form_apply import project

    (row,) = project([{"target": "processing.dpia", "config": {}}], {}, {})
    assert row["ok"], row


def _complete(client, response, extra=None):
    """Answer every required question still empty, then submit."""
    url = f"/api/quick-form-responses/{response.id}/"
    content = client.get(f"{url}content/").json()
    answers = dict(extra or {})
    for page in content["pages"]:
        for urn, question in page["questions"].items():
            if question.get("required") is False or content["answers"].get(urn):
                continue
            if question["type"] == "text":
                answers.setdefault(urn, "Noted")
            elif question["type"] == "unique_choice":
                answers.setdefault(urn, question["choices"][0]["urn"])
    patched = client.patch(url, {"answers": answers}, format="json")
    assert patched.status_code == 200, patched.json()
    submitted = client.post(f"{url}set-status/", {"status": "submitted"}, format="json")
    assert submitted.status_code == 200, submitted.json()
    response.refresh_from_db()


@pytest.mark.django_db
def test_pages_show_the_processing_record_frozen_on_submit(
    admin_client, reviewer_client, processing, dpia_form
):
    response = _start_dpia(admin_client, dpia_form, processing)
    url = f"/api/quick-form-responses/{response.id}/content/"
    content = admin_client.get(url).json()
    data_page = next(p for p in content["pages"] if p["ref_id"] == "data")
    assert data_page["facts"] == [
        "processing.personal_data",
        "processing.data_subjects",
        "processing.recipients",
    ]
    purposes = content["facts"]["processing.purposes"]
    assert purposes["columns"] == ["name", "legalBasis", "article9Condition"]
    assert purposes["rows"] == [["Profiling", "privacy_consent", None]]
    (row,) = content["facts"]["processing.personal_data"]["rows"]
    assert row[-1] == "CRM"
    assert content["facts"]["processing.controls"]["rows"] == [
        ["Pseudonymisation", "in_progress", None]
    ]

    _complete(admin_client, response)
    assert response.facts_snapshot["processing.purposes"] == purposes
    Purpose.objects.create(
        processing=processing, name="Marketing", legal_basis="privacy_consent"
    )
    # Submitted: the record assessed, not the processing as it is now.
    frozen = admin_client.get(url).json()["facts"]["processing.purposes"]
    assert [r[0] for r in frozen["rows"]] == ["Profiling"]

    # Its submitter could accept, so it closed at once: reopen it for review.
    QuickFormResponse.objects.filter(pk=response.pk).update(
        status=QuickFormResponse.Status.SUBMITTED, resolution=""
    )
    sent_back = reviewer_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "draft"},
        format="json",
    )
    assert sent_back.status_code == 200, sent_back.json()
    live = admin_client.get(url).json()["facts"]["processing.purposes"]
    assert sorted(r[0] for r in live["rows"]) == ["Marketing", "Profiling"]


@pytest.mark.django_db
def test_the_processings_measures_are_offered_first(
    admin_client, processing, dpia_form
):
    response = _start_dpia(admin_client, dpia_form, processing)
    AppliedControl.objects.create(name="Access review", folder=processing.folder)
    options = admin_client.get(
        f"/api/quick-form-responses/{response.id}/reference-options/",
        {"question": f"{DPIA}:illegitimate_access:question:measures"},
    ).json()["results"]
    names = [o["label"] for o in options]
    assert names.index("Pseudonymisation") < names.index("Access review")
    assert options[0]["on_subject"] is True
    assert "on_subject" not in options[names.index("Access review")]


@pytest.mark.django_db
def test_accepting_adds_the_picked_measures_to_the_processing(
    admin_client, processing, dpia_form
):
    response = _start_dpia(admin_client, dpia_form, processing)
    review = AppliedControl.objects.create(
        name="Access review", folder=processing.folder
    )
    kept = processing.associated_controls.get()
    _complete(
        admin_client,
        response,
        {f"{DPIA}:illegitimate_access:question:measures": [str(review.id)]},
    )
    # Its submitter may change the processing: accepted on submit.
    assert response.resolution == QuickFormResponse.Resolution.ACCEPTED
    assert set(processing.associated_controls.all()) == {kept, review}
    log = QuickFormApplication.objects.get(
        response=response, target="processing.controls"
    )
    assert log.new_value == [str(review.id)]
    assert log.previous_display == "Pseudonymisation"


def test_a_page_naming_an_unknown_fact_is_refused():
    from core.quick_form_facts import facts_error

    assert facts_error([{"urn": "p", "facts": ["processing.purposes"]}]) is None
    assert "processing.nope" in facts_error(
        [{"urn": "p", "facts": ["processing.nope"]}]
    )


@pytest.mark.django_db
def test_always_review_sends_the_dpia_to_validation(
    admin_client, reviewer_client, processing, dpia_form
):
    switched = admin_client.post(
        f"/api/quick-forms/{dpia_form.id}/always-review/",
        {"always_review": True},
        format="json",
    )
    assert switched.status_code == 200, switched.json()
    response = _start_dpia(admin_client, dpia_form, processing)
    _complete(admin_client, response)
    # Not applied on submit, although its submitter could change the processing.
    assert response.status == QuickFormResponse.Status.SUBMITTED
    processing.refresh_from_db()
    assert processing.dpia is None

    accepted = reviewer_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": "accepted"},
        format="json",
    )
    assert accepted.status_code == 200, accepted.json()
    processing.refresh_from_db()
    assert processing.dpia == response


@pytest.mark.django_db
def test_a_rejected_dpia_leaves_the_processing_to_do(
    admin_client, reviewer_client, processing, dpia_form
):
    Processing.objects.filter(pk=processing.pk).update(dpia_required=True)
    url = "/api/privacy/processings/dpia-overview/"
    response = _start_dpia(admin_client, dpia_form, processing)
    overview = admin_client.get(url).json()
    assert overview["required_dpia_in_progress"] == 1
    gaps = admin_client.get(f"{url}?state=required_without_dpia").json()["rows"]
    assert str(processing.id) not in [g["id"] for g in gaps]
    (row,) = admin_client.get(f"{url}?state=required_dpia_in_progress").json()["rows"]
    assert row["dpia"]["status"] == "draft"

    response.status = QuickFormResponse.Status.SUBMITTED
    response.save(update_fields=["status"])
    rejected = reviewer_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": "rejected"},
        format="json",
    )
    assert rejected.status_code == 200, rejected.json()
    overview = admin_client.get(url).json()
    assert overview["required_dpia_in_progress"] == 0
    assert overview["required_dpia_done"] == 0
    gaps = admin_client.get(f"{url}?state=required_without_dpia").json()["rows"]
    assert str(processing.id) in [g["id"] for g in gaps]
    assert gaps[0]["dpia"] is None


@pytest.mark.django_db
def test_the_snapshot_is_not_writable_nor_listed(admin_client, processing, dpia_form):
    response = _start_dpia(admin_client, dpia_form, processing)
    _complete(admin_client, response)
    frozen = response.facts_snapshot
    patched = admin_client.patch(
        f"/api/quick-form-responses/{response.id}/",
        {"facts_snapshot": {"processing.purposes": {"rows": [["Invented"]]}}},
        format="json",
    )
    assert patched.status_code in (200, 400), patched.json()
    response.refresh_from_db()
    assert response.facts_snapshot == frozen
    # Only the content endpoint shows facts, to who may view the processing.
    listed = admin_client.get(f"/api/quick-form-responses/{response.id}/").json()
    assert "facts_snapshot" not in listed


@pytest.mark.django_db
def test_measures_from_another_domain_are_not_added(
    admin_client, processing, dpia_form
):
    other = Folder.objects.create(
        name="OtherDomain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    elsewhere = AppliedControl.objects.create(name="Elsewhere", folder=other)
    here = AppliedControl.objects.create(name="Here", folder=processing.folder)
    response = _start_dpia(admin_client, dpia_form, processing)
    question = f"{DPIA}:illegitimate_access:question:measures"
    # Written as an earlier version of the form could have: not through the picker.
    answer = response.answers.get(question__urn=question)
    answer.value = [str(elsewhere.id), str(here.id)]
    answer.save()
    from privacy.dpia import ProcessingControlsTarget

    proposal = ProcessingControlsTarget().resolve(response, {})
    assert proposal.value == [str(here.id)]

    answer.value = str(here.id)
    answer.save()
    assert ProcessingControlsTarget().resolve(response, {}).value == [str(here.id)]
    answer.value = ["not-a-uuid", str(here.id)]
    answer.save()
    assert ProcessingControlsTarget().resolve(response, {}).value == [str(here.id)]


@pytest.mark.django_db
def test_requirement_history_moves_with_the_processing(admin_client, processing):
    changed = admin_client.patch(
        f"/api/privacy/processings/{processing.id}/",
        {"dpia_required": True, "dpia_required_note": "Large-scale profiling"},
        format="json",
    )
    assert changed.status_code == 200, changed.json()
    target = Folder.objects.create(
        name="NewHome",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    moved = admin_client.patch(
        f"/api/privacy/processings/{processing.id}/",
        {"folder": str(target.id)},
        format="json",
    )
    assert moved.status_code == 200, moved.json()
    assert set(
        DpiaRequirementChange.objects.filter(processing=processing).values_list(
            "folder", flat=True
        )
    ) == {target.id}


def test_the_dpia_is_translated_in_french():
    import yaml

    source = Path(__file__).resolve().parents[1] / (
        "library/libraries/quick-form-dpia.yaml"
    )
    form = yaml.safe_load(source.read_text())["objects"]["quick_forms"][0]
    assert form["translations"]["fr"]["name"] == "AIPD"
    for page in form["pages"]:
        assert page["translations"]["fr"]["name"], page["urn"]
        for urn, question in page["questions"].items():
            assert question["translations"]["fr"]["text"], urn
