"""Quick forms: library import and update, builder bridge, response
lifecycle, CEL outcomes and page visibility, XOR parent constraints."""

import pytest
from django.db import IntegrityError, transaction
from knox.models import AuthToken
from rest_framework.test import APIClient

import core.tasks as core_tasks
from core.apps import startup
from core.models import (
    Actor,
    Answer,
    LibraryDraft,
    LoadedLibrary,
    Question,
    QuickForm,
    QuickFormPage,
    QuickFormResponse,
    RequirementNode,
    StoredLibrary,
)
from iam.models import Folder, RoleAssignment, User, UserGroup
from tprm.models import Entity

FORM_URN = "urn:test:risk:quick_form:dpia-screening"
PAGE1 = f"urn:test:risk:qf_page:dpia-screening:profile"
PAGE2 = f"urn:test:risk:qf_page:dpia-screening:details"
Q_SENSITIVE = f"{PAGE1}:question:sensitive_data"
Q_HEADCOUNT = f"{PAGE1}:question:headcount"
Q_COMMENT = f"{PAGE1}:question:comment"
Q_SCALE = f"{PAGE2}:question:scale"
C_SMALL = f"{Q_SCALE}:choice:1"
C_LARGE = f"{Q_SCALE}:choice:2"

LIBRARY_V1 = f"""
urn: urn:test:risk:library:dpia-screening
locale: en
ref_id: dpia-screening
name: DPIA screening
description: Quick form test library
copyright: Test
version: 1
publication_date: 2026-09-07
provider: test-provider
packager: test
objects:
  quick_forms:
    - urn: {FORM_URN}
      ref_id: dpia-screening
      name: DPIA screening
      description: Is a DPIA required?
      scores_definition:
        min: 0
        max: 100
        aggregation: sum
      outcomes_definition:
        - ref_id: dpia_required
          label: DPIA required
          expression: 'answers["profile:question:sensitive_data"].value == true'
        - ref_id: large_scale
          label: Large scale processing
          expression: '"details:question:scale:choice:2" in answers["details:question:scale"].selected_choices'
      pages:
        - urn: {PAGE1}
          ref_id: profile
          name: Processing profile
          description: |
            # Intro
            Describe the processing.
          questions:
            {Q_SENSITIVE}:
              type: boolean
              text: Does the processing involve sensitive data?
            {Q_HEADCOUNT}:
              type: number
              text: How many data subjects?
            {Q_COMMENT}:
              type: text
              text: Anything else?
              required: false
        - urn: {PAGE2}
          ref_id: details
          name: Details
          visibility_expression: 'answers["profile:question:sensitive_data"].value == true'
          questions:
            {Q_SCALE}:
              type: unique_choice
              text: Scale of the processing
              choices:
                - urn: {C_SMALL}
                  value: Small
                  add_score: 10
                - urn: {C_LARGE}
                  value: Large
                  add_score: 80
""".lstrip()

# v2: a new question on page 1, the "Large" choice dropped.
LIBRARY_V2 = (
    LIBRARY_V1.replace("version: 1", "version: 2")
    .replace(
        f"""                - urn: {C_LARGE}
                  value: Large
                  add_score: 80
""",
        "",
    )
    .replace(
        f"""            {Q_COMMENT}:
              type: text
              text: Anything else?
              required: false
""",
        f"""            {Q_COMMENT}:
              type: text
              text: Anything else?
              required: false
            {PAGE1}:question:dpo:
              type: text
              text: Who is the DPO?
""",
    )
)


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _admin_client(email="qf-admin@test.local"):
    user = User.objects.create_user(email=email, is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return user, client


def _load(yaml_text):
    stored, error = StoredLibrary.store_library_content(yaml_text.encode("utf-8"))
    assert error is None, error
    if LoadedLibrary.objects.filter(urn=stored.urn).exists():
        assert LoadedLibrary.objects.get(urn=stored.urn).update() is None
    else:
        assert stored.load() is None
    return QuickForm.objects.get(urn=FORM_URN)


@pytest.mark.django_db
class TestQuickFormImport:
    def test_import_creates_form_pages_and_questions(self, app_config):
        form = _load(LIBRARY_V1)
        assert form.library is not None
        assert form.urn_namespace == "test"
        assert form.score_bounds == (0, 100)
        pages = list(form.pages.order_by("order"))
        assert [p.ref_id for p in pages] == ["profile", "details"]
        assert pages[1].visibility_expression.startswith("answers[")
        questions = Question.objects.filter(page__quick_form=form)
        assert questions.count() == 4
        comment = Question.objects.get(urn=Q_COMMENT)
        assert comment.required is False
        assert comment.requirement_node is None
        assert Question.objects.get(urn=Q_SENSITIVE).required is True
        assert form.is_deletable()

    def test_update_reconciles_responses(self, app_config):
        form = _load(LIBRARY_V1)
        response = QuickFormResponse.objects.create(
            name="Vendor X", quick_form=form, folder=Folder.get_root_folder()
        )
        response.seed_answers()
        large = Question.objects.get(urn=Q_SCALE).choices.get(urn=C_LARGE)
        answer = response.answers.get(question__urn=Q_SCALE)
        answer.selected_choices.set([large])
        assert response.answers.count() == 4

        _load(LIBRARY_V2)
        response.refresh_from_db()
        # New question seeded, dropped choice deselected, nothing else lost.
        assert response.answers.count() == 5
        assert response.answers.filter(question__urn=f"{PAGE1}:question:dpo").exists()
        assert response.answers.get(question__urn=Q_SCALE).selected_choices.count() == 0
        assert (
            not Question.objects.get(urn=Q_SCALE).choices.filter(urn=C_LARGE).exists()
        )


@pytest.mark.django_db
class TestParentConstraints:
    def test_question_needs_exactly_one_parent(self, app_config):
        form = _load(LIBRARY_V1)
        page = form.pages.first()
        node = RequirementNode.objects.create(
            urn="urn:test:risk:req_node:x:n1",
            folder=Folder.get_root_folder(),
            assessable=True,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Question.objects.create(
                    urn="urn:test:q:orphan", folder=Folder.get_root_folder()
                )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Question.objects.create(
                    urn="urn:test:q:both",
                    folder=Folder.get_root_folder(),
                    page=page,
                    requirement_node=node,
                )

    def test_answer_needs_exactly_one_parent(self, app_config):
        form = _load(LIBRARY_V1)
        question = Question.objects.get(urn=Q_HEADCOUNT)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Answer.objects.create(
                    question=question, folder=Folder.get_root_folder()
                )
        response = QuickFormResponse.objects.create(
            name="r", quick_form=form, folder=Folder.get_root_folder()
        )
        Answer.objects.create(
            question=question, response=response, folder=Folder.get_root_folder()
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Answer.objects.create(
                    question=question,
                    response=response,
                    folder=Folder.get_root_folder(),
                )

    def test_form_with_responses_is_protected(self, app_config):
        form = _load(LIBRARY_V1)
        QuickFormResponse.objects.create(
            name="r", quick_form=form, folder=Folder.get_root_folder()
        )
        assert not form.is_deletable()
        loaded = LoadedLibrary.objects.get(urn="urn:test:risk:library:dpia-screening")
        assert loaded.reference_count == 1


@pytest.mark.django_db
class TestResponseLifecycle:
    def _create_response(
        self, client, form, folder, respondents=(), start_now=False, name=None
    ):
        payload = {
            "name": name or f"Vendor screening {QuickFormResponse.objects.count() + 1}",
            "quick_form": str(form.id),
            "folder": str(folder.id),
            "respondents": [str(a.id) for a in respondents],
            "start_now": start_now,
        }
        res = client.post("/api/quick-form-responses/", payload, format="json")
        assert res.status_code == 201, res.json()
        return QuickFormResponse.objects.get(id=res.json()["id"])

    def test_create_seeds_answers_and_defaults_reviewers(self, app_config):
        user, client = _admin_client()
        form = _load(LIBRARY_V1)
        response = self._create_response(client, form, Folder.get_root_folder())
        assert response.answers.count() == 4
        assert response.status == QuickFormResponse.Status.DRAFT
        creator_actor = Actor.objects.filter(user=user).first()
        if creator_actor is not None:
            assert list(response.reviewers.all()) == [creator_actor]

    def test_start_now_notifies_respondents(
        self, app_config, monkeypatch, django_capture_on_commit_callbacks
    ):
        user, client = _admin_client()
        respondent = User.objects.create_user(
            email="resp@test.local", is_published=True
        )
        actor, _ = Actor.objects.get_or_create(user=respondent)
        form = _load(LIBRARY_V1)
        sent = []
        monkeypatch.setattr(
            core_tasks,
            "send_quick_form_started_notification",
            lambda pk: sent.append(pk),
        )
        with django_capture_on_commit_callbacks(execute=True):
            response = self._create_response(
                client, form, Folder.get_root_folder(), [actor], start_now=True
            )
        assert response.started_at is not None
        assert sent == [response.pk]

    def test_entity_actor_rejected(self, app_config):
        user, client = _admin_client()
        form = _load(LIBRARY_V1)
        entity = Entity.objects.create(name="ACME", folder=Folder.get_root_folder())
        actor, _ = Actor.objects.get_or_create(entity=entity)
        res = client.post(
            "/api/quick-form-responses/",
            {
                "name": "x",
                "quick_form": str(form.id),
                "folder": str(Folder.get_root_folder().id),
                "respondents": [str(actor.id)],
            },
            format="json",
        )
        assert res.status_code == 400
        assert "respondents" in res.json()

    def test_answers_visibility_outcomes_and_transitions(
        self, app_config, monkeypatch, django_capture_on_commit_callbacks
    ):
        user, client = _admin_client()
        form = _load(LIBRARY_V1)
        response = self._create_response(client, form, Folder.get_root_folder())
        url = f"/api/quick-form-responses/{response.id}/"

        # Page 2 hidden while sensitive_data is unanswered; optional comment
        # does not count against completion.
        content = client.get(f"{url}content/").json()
        assert content["hidden_pages"] == [PAGE2]
        assert content["progress"] == {
            "answered_count": 0,
            "total_count": 3,
            "complete": False,
        }
        assert [p["ref_id"] for p in content["pages"]] == ["profile", "details"]
        assert content["pages"][1]["hidden"] is True
        assert content["pages"][0]["questions"][Q_COMMENT]["required"] is False

        # Submitting an incomplete response is refused.
        res = client.post(f"{url}set-status/", {"status": "submitted"}, format="json")
        assert res.status_code == 400
        assert res.json()["error"] == "responseIncomplete"

        with django_capture_on_commit_callbacks(execute=True):
            res = client.patch(
                url,
                {"answers": {Q_SENSITIVE: True, Q_HEADCOUNT: 12000}},
                format="json",
            )
        assert res.status_code == 200, res.json()
        content = client.get(f"{url}content/").json()
        assert content["hidden_pages"] == []
        assert content["answers"][Q_SENSITIVE] is True
        assert content["progress"]["complete"] is False  # scale now required
        assert "dpia_required" in content["computed_outcome"]
        assert "large_scale" not in content["computed_outcome"]

        with django_capture_on_commit_callbacks(execute=True):
            res = client.patch(url, {"answers": {Q_SCALE: C_LARGE}}, format="json")
        assert res.status_code == 200
        response.refresh_from_db()
        assert response.score == 80
        assert set(response.computed_outcome) == {"dpia_required", "large_scale"}

        submitted = []
        monkeypatch.setattr(
            core_tasks,
            "send_quick_form_submitted_notification",
            lambda pk: submitted.append(pk),
        )
        with django_capture_on_commit_callbacks(execute=True):
            res = client.post(
                f"{url}set-status/", {"status": "submitted"}, format="json"
            )
        assert res.status_code == 200, res.json()
        response.refresh_from_db()
        assert response.status == QuickFormResponse.Status.SUBMITTED
        assert response.submitted_at is not None
        assert submitted == [response.pk]

        # Answers are frozen once submitted.
        res = client.patch(url, {"answers": {Q_HEADCOUNT: 1}}, format="json")
        assert res.status_code == 400

        # From here the reviewer acts, and it cannot be the same person: whoever
        # submitted a request is barred from deciding on it.
        assert (
            client.post(
                f"{url}set-status/",
                {"status": "closed", "resolution": "accepted"},
                format="json",
            ).status_code
            == 403
        )
        _, reviewer = _admin_client("qf-reviewer@test.local")

        # Request changes sends it back to the requester, keeping the observation.
        res = reviewer.post(
            f"{url}set-status/",
            {"status": "draft", "observation": "Please detail the scale"},
            format="json",
        )
        assert res.status_code == 200
        response.refresh_from_db()
        assert response.observation == "Please detail the scale"
        res = client.post(f"{url}set-status/", {"status": "submitted"}, format="json")
        assert res.status_code == 200

        # A reviewer may claim before deciding; claiming records the assignee.
        res = reviewer.post(f"{url}set-status/", {"status": "in_review"}, format="json")
        assert res.status_code == 200
        response.refresh_from_db()
        assert response.assignee is not None

        # Closing demands a resolution: status says where it is, resolution how it ended.
        res = reviewer.post(f"{url}set-status/", {"status": "closed"}, format="json")
        assert res.status_code == 400
        assert res.json()["error"] == "resolutionRequired"
        res = reviewer.post(
            f"{url}set-status/",
            {"status": "closed", "resolution": "accepted"},
            format="json",
        )
        assert res.status_code == 200
        response.refresh_from_db()
        assert response.resolution == QuickFormResponse.Resolution.ACCEPTED
        assert not response.is_deletable()

        # Closed is terminal.
        res = reviewer.post(f"{url}set-status/", {"status": "draft"}, format="json")
        assert res.status_code == 400
        assert res.json()["error"] == "invalidTransition"

    def test_mine_filter(self, app_config):
        user, client = _admin_client()
        actor, _ = Actor.objects.get_or_create(user=user)
        form = _load(LIBRARY_V1)
        mine = self._create_response(client, form, Folder.get_root_folder(), [actor])
        self._create_response(client, form, Folder.get_root_folder())
        res = client.get("/api/quick-form-responses/?mine=true")
        assert res.status_code == 200
        ids = {r["id"] for r in res.json()["results"]}
        assert ids == {str(mine.id)}


@pytest.mark.django_db
class TestBuilderBridge:
    def test_add_edit_publish_round_trip(self, app_config):
        user, client = _admin_client()
        res = client.post(
            "/api/library-drafts/",
            {
                "name": "Vendor intake",
                "ref_id": "vendor-intake",
                "packager": "acme",
                "locale": "en",
                "folder": str(Folder.get_root_folder().id),
            },
            format="json",
        )
        assert res.status_code == 201, res.json()
        draft_id = res.json()["id"]
        base = f"/api/library-drafts/{draft_id}/"

        res = client.post(f"{base}add-quick-form/", {}, format="json")
        assert res.status_code == 201, res.json()
        form_urn = res.json()["quick_form_urn"]
        assert form_urn == "urn:acme:risk:quick_form:vendor-intake"

        res = client.get(f"{base}quick-form-editor/")
        assert res.status_code == 200, res.json()
        doc = res.json()["editing_draft"]
        assert doc["kind"] == "quick_form"
        assert len(doc["nodes"]) == 1
        page_id = doc["nodes"][0]["id"]

        # Add a question with a choice on the page, and a second page.
        doc["nodes"].append(
            {"id": "tmp-page-2", "urn": None, "name": "Security", "ref_id": "security"}
        )
        doc["questions"].append(
            {
                "id": "tmp-q1",
                "urn": None,
                "ref_id": "headcount",
                "text": "What is your headcount?",
                "type": "number",
                "order": 0,
                "required": False,
                "requirement_node_id": page_id,
            }
        )
        doc["questions"].append(
            {
                "id": "tmp-q2",
                "urn": None,
                "ref_id": "iso",
                "text": "ISO 27001 certified?",
                "type": "unique_choice",
                "order": 0,
                "requirement_node_id": "tmp-page-2",
            }
        )
        doc["choices"].append(
            {"id": "tmp-c1", "question_id": "tmp-q2", "value": "Yes", "order": 0}
        )
        doc["choices"].append(
            {"id": "tmp-c2", "question_id": "tmp-q2", "value": "No", "order": 1}
        )
        doc["framework_meta"]["outcomes_definition"] = [
            {
                "ref_id": "big",
                "expression": 'answers["page-1:question:headcount"].value > 250',
            }
        ]
        res = client.put(
            f"{base}quick-form-editor/", {"editing_draft": doc}, format="json"
        )
        assert res.status_code == 200, res.json()

        draft = LibraryDraft.objects.get(id=draft_id)
        form = draft.content["quick_forms"][0]
        assert [p["ref_id"] for p in form["pages"]] == ["page-1", "security"]
        assert form["pages"][1]["urn"] == "urn:acme:risk:qf_page:vendor-intake:security"
        headcount = form["pages"][0]["questions"][
            "urn:acme:risk:qf_page:vendor-intake:page-1:question:headcount"
        ]
        assert headcount["required"] is False
        assert "assessable" not in form["pages"][0]
        iso = form["pages"][1]["questions"][
            "urn:acme:risk:qf_page:vendor-intake:security:question:iso"
        ]
        assert [c["urn"] for c in iso["choices"]] == [
            "urn:acme:risk:qf_page:vendor-intake:security:question:iso:choice:1",
            "urn:acme:risk:qf_page:vendor-intake:security:question:iso:choice:2",
        ]

        res = client.get(f"{base}validate/")
        assert res.status_code == 200, res.json()
        assert res.json()["errors"] == [], res.json()

        res = client.post(f"{base}publish/", {}, format="json")
        assert res.status_code in (200, 201), res.json()
        live = QuickForm.objects.get(urn=form_urn)
        assert live.pages.count() == 2
        assert Question.objects.filter(page__quick_form=live).count() == 2
        assert live.outcomes_definition[0]["ref_id"] == "big"
        assert (
            QuickFormPage.objects.get(
                urn="urn:acme:risk:qf_page:vendor-intake:security"
            )
            .questions.first()
            .choices.count()
            == 2
        )


def _role_client(email, role_code, folder):
    """A user holding one built-in role on `folder`, with an authenticated client."""
    from iam.models import Role, RoleAssignment

    user = User.objects.create_user(email=email, is_published=True)
    user.folder = Folder.get_root_folder()
    user.save()
    group = UserGroup.objects.create(name=f"grp-{email}", folder=folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_code),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    assignment.perimeter_folders.add(folder)
    token = AuthToken.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return user, client


@pytest.mark.django_db
def test_requester_cannot_decide_on_their_own_request(app_config):
    """Separation of duties: whoever submitted a request may not close it, whatever
    folder rights they hold — unless an admin turns on self-validation."""
    from global_settings.models import GlobalSettings

    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-sod", parent_folder=Folder.get_root_folder()
    )

    analyst, analyst_client = _role_client("qf-analyst@test.local", "BI-RL-ANA", folder)
    response = QuickFormResponse.objects.create(
        name="self-filed",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=analyst,
    )
    url = f"/api/quick-form-responses/{response.id}/set-status/"
    payload = {"status": "closed", "resolution": "accepted"}

    res = analyst_client.post(url, payload, format="json")
    assert res.status_code == 403, res.json()
    assert res.json()["error"] == "selfValidationNotAllowed"

    # A different analyst on the same domain is unaffected.
    _, other_client = _role_client("qf-other@test.local", "BI-RL-ANA", folder)
    assert other_client.post(url, payload, format="json").status_code == 200, (
        "a colleague must still be able to decide"
    )

    # And the requester's own view says so, rather than offering a doomed button.
    content = analyst_client.get(
        f"/api/quick-form-responses/{response.id}/content/"
    ).json()
    assert content["can_review"] is False


@pytest.mark.django_db
def test_self_validation_setting_reopens_the_door(app_config):
    """The instance-wide escape hatch, for organisations too small to separate."""
    from global_settings.models import GlobalSettings

    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-sod2", parent_folder=Folder.get_root_folder()
    )
    analyst, client = _role_client("qf-solo@test.local", "BI-RL-ANA", folder)
    response = QuickFormResponse.objects.create(
        name="solo",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=analyst,
    )
    gs, _ = GlobalSettings.objects.get_or_create(name="general", defaults={"value": {}})
    gs.value = {**(gs.value or {}), "allow_self_validation": True}
    gs.save()

    res = client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": "accepted"},
        format="json",
    )
    assert res.status_code == 200, res.json()


@pytest.mark.django_db
def test_deciding_needs_the_approve_permission(app_config):
    """Reader may look at a request but not act on it."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-sod3", parent_folder=Folder.get_root_folder()
    )
    author, _ = _role_client("qf-author@test.local", "BI-RL-ANA", folder)
    response = QuickFormResponse.objects.create(
        name="readable",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=author,
    )
    # BI-RL-AUD carries the reader permission list: view without approve.
    _, reader_client = _role_client("qf-reader@test.local", "BI-RL-AUD", folder)
    res = reader_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "closed", "resolution": "accepted"},
        format="json",
    )
    assert res.status_code in (403, 404), res.status_code


@pytest.mark.django_db
def test_only_the_requester_owns_the_content(app_config):
    """A reviewer sends a request back with a note; they do not answer it for you,
    and they do not resubmit it on your behalf — whatever folder rights they hold."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-content", parent_folder=Folder.get_root_folder()
    )
    requester, _ = _role_client("qf-asker@test.local", "BI-RL-ANA", folder)
    asker_actor = Actor.objects.filter(user=requester, entity__isnull=True).first()

    response = QuickFormResponse.objects.create(
        name="theirs",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.DRAFT,
        submitted_by=requester,
    )
    if asker_actor:
        response.respondents.add(asker_actor)

    # A global administrator, who is not the requester.
    _, admin = _admin_client("qf-content-admin@test.local")
    url = f"/api/quick-form-responses/{response.id}/"

    res = admin.patch(url, {"answers": {Q_HEADCOUNT: 42}}, format="json")
    assert res.status_code == 400, res.json()
    assert "answers" in res.json()

    res = admin.post(f"{url}set-status/", {"status": "submitted"}, format="json")
    assert res.status_code == 403, res.json()
    assert res.json()["error"] == "onlyRequesterCanSubmit"

    # And the admin's own view of the request says the content is not theirs to touch.
    content = admin.get(f"{url}content/").json()
    assert content["can_edit_answers"] is False


@pytest.mark.django_db
def test_release_does_not_make_the_reviewer_the_requester(app_config):
    """`in_review -> submitted` puts a claimed request back on the queue. It is not a
    submission: recording the reviewer as `submitted_by` would bar them from ever
    deciding it, because separation of duties reads exactly that field."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-release", parent_folder=Folder.get_root_folder()
    )
    requester, _ = _role_client("qf-rel-asker@test.local", "BI-RL-ANA", folder)
    reviewer, reviewer_client = _role_client(
        "qf-rel-rev@test.local", "BI-RL-ANA", folder
    )
    response = QuickFormResponse.objects.create(
        name="released",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=requester,
    )
    submitted_at = response.submitted_at
    url = f"/api/quick-form-responses/{response.id}/set-status/"

    assert (
        reviewer_client.post(url, {"status": "in_review"}, format="json").status_code
        == 200
    )
    assert (
        reviewer_client.post(url, {"status": "submitted"}, format="json").status_code
        == 200
    )

    response.refresh_from_db()
    assert response.submitted_by_id == requester.id, "release must not steal authorship"
    assert response.submitted_at == submitted_at, "release must not restamp submission"

    # And the reviewer can still decide the request they just released.
    res = reviewer_client.post(
        url, {"status": "closed", "resolution": "accepted"}, format="json"
    )
    assert res.status_code == 200, res.json()


@pytest.mark.django_db
def test_reviewer_cannot_drop_or_auto_close(app_config):
    """`drop` is the requester's word and `auto` means nobody decided."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-res", parent_folder=Folder.get_root_folder()
    )
    author, _ = _role_client("qf-res-asker@test.local", "BI-RL-ANA", folder)
    _, reviewer = _role_client("qf-res-rev@test.local", "BI-RL-ANA", folder)
    response = QuickFormResponse.objects.create(
        name="resolutions",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=author,
    )
    url = f"/api/quick-form-responses/{response.id}/set-status/"
    for refused in ("dropped", "auto"):
        res = reviewer.post(
            url, {"status": "closed", "resolution": refused}, format="json"
        )
        assert res.status_code == 400, f"{refused} should not be a reviewer's to set"
    assert (
        reviewer.post(
            url, {"status": "closed", "resolution": "rejected"}, format="json"
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_a_closed_request_cannot_gain_attachments(app_config):
    """Attaching re-scores the response, which moves the outcome the decision rested on."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-closed-att", parent_folder=Folder.get_root_folder()
    )
    author, _ = _role_client("qf-att-asker@test.local", "BI-RL-ANA", folder)
    _, reviewer = _role_client("qf-att-rev@test.local", "BI-RL-ANA", folder)
    response = QuickFormResponse.objects.create(
        name="decided",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.CLOSED,
        resolution=QuickFormResponse.Resolution.ACCEPTED,
        submitted_by=author,
    )
    res = reviewer.post(
        f"/api/quick-form-responses/{response.id}/attachments/",
        {"question": Q_COMMENT},
        format="multipart",
    )
    assert res.status_code == 400, res.json()
    assert res.json()["error"] == "responseClosed"


SCORING_LIBRARY = """
urn: urn:test:risk:library:score-parity
locale: en
ref_id: score-parity
name: Score parity
description: Mean scoring across scorable and non-scorable questions
copyright: Test
version: 1
publication_date: 2026-09-11
provider: test-provider
packager: test
objects:
  quick_forms:
    - urn: urn:test:risk:quick_form:score-parity
      ref_id: score-parity
      name: Score parity
      description: Two scorable questions and two that carry no score
      scores_definition:
        min: 0
        max: 100
        aggregation: mean
      pages:
        - urn: urn:test:risk:qf_page:score-parity:only
          ref_id: only
          name: Only page
          order: 1
          questions:
            urn:test:risk:qf_page:score-parity:only:question:a:
              type: unique_choice
              text: A
              order: 1
              choices:
                - urn: urn:test:risk:qf_page:score-parity:only:question:a:choice:1
                  value: five
                  add_score: 5
            urn:test:risk:qf_page:score-parity:only:question:b:
              type: unique_choice
              text: B
              order: 2
              choices:
                - urn: urn:test:risk:qf_page:score-parity:only:question:b:choice:1
                  value: five
                  add_score: 5
            urn:test:risk:qf_page:score-parity:only:question:c:
              type: text
              text: C
              order: 3
            urn:test:risk:qf_page:score-parity:only:question:d:
              type: text
              text: D
              order: 4
"""


@pytest.mark.django_db
def test_preview_score_matches_the_persisted_score(app_config):
    """The preview divided a mean by every visible question; the live path divides by
    the weight of the ones that actually scored. Two scorable questions worth 5 each,
    plus two text questions, must read 5 on both paths — not 3 on one of them."""
    from core.cel_service import evaluate_quick_form, evaluate_quick_form_document
    from core.utils import apply_answers_dict

    # Not `_load`: that helper returns the DPIA fixture's form by a fixed urn.
    stored, error = StoredLibrary.store_library_content(SCORING_LIBRARY.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    form = QuickForm.objects.get(urn="urn:test:risk:quick_form:score-parity")
    folder = Folder.objects.create(
        name="qf-score", parent_folder=Folder.get_root_folder()
    )
    response = QuickFormResponse.objects.create(
        name="scored", quick_form=form, folder=folder
    )
    base = "urn:test:risk:qf_page:score-parity:only:question"
    answers = {
        f"{base}:a": f"{base}:a:choice:1",
        f"{base}:b": f"{base}:b:choice:1",
        f"{base}:c": "free text",
        f"{base}:d": "more free text",
    }
    questions = {q.urn: q for q in Question.objects.filter(page__quick_form=form)}
    apply_answers_dict("response", response, questions, answers)

    live = evaluate_quick_form(response, persist=False)["score"]
    preview = evaluate_quick_form_document(
        {
            "urn": form.urn,
            "scores_definition": form.scores_definition,
            "pages": [
                {
                    "urn": p.urn,
                    "ref_id": p.ref_id,
                    "name": p.name,
                    "order": p.order,
                    "questions": p.get_questions_translated() or {},
                }
                for p in form.pages.all().order_by("order")
            ],
        },
        answers,
    )["score"]
    assert live == preview, f"preview {preview} disagrees with live {live}"
    assert live == 5, f"mean of two 5s is 5, got {live}"


@pytest.mark.parametrize(
    "filename,accept,expected",
    [
        ("photo.png", ".png", True),
        ("photo.png", "image/*", True),
        ("photo.png", "image/png", True),
        ("photo.png", "*/*", True),
        ("photo.png", "png", True),
        ("photo.png", ".pdf,image/*", True),
        ("photo.png", ".pdf", False),
        ("photo.png", "video/*", False),
        ("report.pdf", "application/pdf", True),
        ("archive.zzz", "image/*", False),
    ],
)
def test_accept_matches_every_shape_html_allows(filename, accept, expected):
    """`accept` carries extensions, exact MIME types and MIME wildcards. Only the first
    is a suffix of the filename, so a suffix test alone rejects every MIME form."""
    from core.answer_attachments import _accepts

    allowed = [a.strip().lower() for a in accept.split(",") if a.strip()]
    assert _accepts(filename.lower(), allowed) is expected


@pytest.mark.django_db
def test_answer_endpoint_honours_the_requester_rule(app_config):
    """The `/answers/` surface is the same content, reached by a different door:
    folder-level rights on Answer are not rights over someone else's request."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    question = Question.objects.get(urn=Q_HEADCOUNT)
    folder = Folder.objects.create(
        name="qf-answer-door", parent_folder=Folder.get_root_folder()
    )
    requester, requester_client = _role_client(
        "qf-door@test.local", "BI-RL-ANA", folder
    )
    response = QuickFormResponse.objects.create(
        name="theirs",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.DRAFT,
        submitted_by=requester,
    )
    payload = {
        "response": str(response.id),
        "question": str(question.id),
        "value": 42,
        "folder": str(folder.id),
    }

    _, admin = _admin_client("qf-door-admin@test.local")
    res = admin.post("/api/answers/", payload, format="json")
    assert res.status_code == 400, res.json()
    assert "Only the requester" in str(res.json())
    assert not Answer.objects.filter(response=response).exists()

    res = requester_client.post("/api/answers/", payload, format="json")
    assert res.status_code == 201, res.json()

    # And the same door stays shut on update.
    answer_id = res.json()["id"]
    res = admin.patch(f"/api/answers/{answer_id}/", {"value": 99}, format="json")
    assert res.status_code == 400, res.json()
    assert "Only the requester" in str(res.json())


@pytest.mark.django_db
def test_my_requests_pagination_is_stable_across_ties(app_config):
    """Offset pagination over a non-unique sort repeats or drops rows. Requests closed
    by one workflow run share `updated_at` to the microsecond, so the tie is real."""
    from datetime import datetime, timezone as dt_timezone

    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-paging", parent_folder=Folder.get_root_folder()
    )
    requester, client = _role_client("qf-paging@test.local", "BI-RL-ANA", folder)
    actor = Actor.objects.filter(user=requester, entity__isnull=True).first()

    made = []
    for i in range(7):
        r = QuickFormResponse.objects.create(
            name=f"req-{i}",
            quick_form=form,
            folder=folder,
            status=QuickFormResponse.Status.DRAFT,
            submitted_by=requester,
        )
        r.respondents.add(actor)
        made.append(r.id)

    # auto_now would defeat the point; .update() writes the column directly.
    tie = datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
    QuickFormResponse.objects.filter(id__in=made).update(updated_at=tie)

    seen = []
    for offset in range(0, 8, 2):
        page = client.get(f"/api/my-requests/?limit=2&offset={offset}").json()
        assert page["count"] == 7, page
        seen.extend(row["id"] for row in page["results"])

    assert len(seen) == len(set(seen)), "a row was served on two different pages"
    assert set(seen) == {str(i) for i in made}, "a row was never served"

    # The union being complete is necessary but not sufficient: SQLite happens to return
    # a consistent order for this query even without a tie-breaker, so assert the order
    # the tie-breaker *defines* instead. Insertion order is not UUID order.
    assert seen == [str(i) for i in sorted(made, key=lambda u: u.hex)], (
        "tied rows must fall back to a unique key"
    )


@pytest.mark.django_db
def test_supervised_run_seeds_the_real_requester_email(app_config):
    """The notification node addresses `{{requester_emails}}`. Unseeded, the workflow
    fell back to its declared default and mailed a placeholder domain."""
    from automation.workflows.supervised import SUPERVISED_TARGETS

    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-seed", parent_folder=Folder.get_root_folder()
    )
    requester, _ = _role_client("qf-seed@test.local", "BI-RL-ANA", folder)
    actor = Actor.objects.filter(user=requester, entity__isnull=True).first()

    response = QuickFormResponse.objects.create(
        name="needs-a-control",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=requester,
    )
    response.respondents.add(actor)

    variables = SUPERVISED_TARGETS["quick_form_response"]["variables"](response)
    assert variables["requester_emails"] == "qf-seed@test.local"
    assert "example.com" not in variables["requester_emails"]

    # A request nobody is on addresses nobody, rather than a placeholder.
    orphan = QuickFormResponse.objects.create(
        name="unclaimed", quick_form=form, folder=folder
    )
    orphan_vars = SUPERVISED_TARGETS["quick_form_response"]["variables"](orphan)
    assert orphan_vars["requester_emails"] == ""


@pytest.mark.django_db
def test_approver_role_can_decide_without_edit_rights(app_config):
    """BI-RL-APP is granted `approve` and deliberately not `change`. The DRF layer used
    to demand `change` on set-status, so the role could read a request and nothing else."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-approver", parent_folder=Folder.get_root_folder()
    )
    requester, _ = _role_client("qf-appr-asker@test.local", "BI-RL-ANA", folder)
    _approver, approver = _role_client("qf-appr@test.local", "BI-RL-APP", folder)

    response = QuickFormResponse.objects.create(
        name="decide-me",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=requester,
    )
    url = f"/api/quick-form-responses/{response.id}/"

    assert approver.get(f"{url}content/").status_code == 200
    res = approver.post(
        f"{url}set-status/",
        {"status": "closed", "resolution": "accepted"},
        format="json",
    )
    assert res.status_code == 200, res.json()
    response.refresh_from_db()
    assert response.status == QuickFormResponse.Status.CLOSED
    assert response.resolution == QuickFormResponse.Resolution.ACCEPTED

    # Deciding is not editing: the role still cannot rewrite the request itself.
    assert approver.patch(url, {"name": "renamed"}, format="json").status_code == 403


@pytest.mark.django_db
def test_viewing_a_request_is_not_deciding_it(app_config):
    """set-status now only requires `view` at the DRF layer, so the per-transition
    actor checks inside the action are the whole authorisation. They must hold."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-viewer", parent_folder=Folder.get_root_folder()
    )
    requester, _ = _role_client("qf-view-asker@test.local", "BI-RL-ANA", folder)
    # Reader holds every quick-form `view` permission and no `approve`.
    _reader, reader = _role_client("qf-reader@test.local", "BI-RL-AUD", folder)

    response = QuickFormResponse.objects.create(
        name="not-yours-to-close",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=requester,
    )
    url = f"/api/quick-form-responses/{response.id}/set-status/"

    assert (
        reader.get(f"/api/quick-form-responses/{response.id}/content/").status_code
        == 200
    )
    res = reader.post(
        url, {"status": "closed", "resolution": "accepted"}, format="json"
    )
    assert res.status_code == 403, res.json()
    assert res.json()["error"] == "approvalPermissionRequired"

    res = reader.post(url, {"status": "in_review"}, format="json")
    assert res.status_code == 403, res.json()
    response.refresh_from_db()
    assert response.status == QuickFormResponse.Status.SUBMITTED


@pytest.mark.django_db
def test_baseline_role_sees_the_form_but_not_the_requests(app_config):
    """Ambient on the root folder: the catalog is fair game, people's requests are not."""
    from iam.models import Role

    _load(LIBRARY_V1)
    baseline = set(
        Role.objects.get(name="BI-RL-BSL").permissions.values_list(
            "codename", flat=True
        )
    )
    assert {"view_quickform", "view_quickformpage"} <= baseline
    assert not (
        {"view_quickformresponse", "view_answer", "view_quickformpublication"}
        & baseline
    )


@pytest.mark.django_db
def test_a_low_privilege_requester_can_still_submit(app_config):
    """`set_status` serves both sides. Gating it on `approve` would fix the reviewer and
    break the requester: filing your own request is not an approval."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-lowpriv", parent_folder=Folder.get_root_folder()
    )
    # Reader holds view on responses and neither `change` nor `approve`.
    reader, reader_client = _role_client("qf-lowpriv@test.local", "BI-RL-AUD", folder)
    actor = Actor.objects.filter(user=reader, entity__isnull=True).first()

    response = QuickFormResponse.objects.create(
        name="mine",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.DRAFT,
    )
    response.respondents.add(actor)

    res = reader_client.post(
        f"/api/quick-form-responses/{response.id}/set-status/",
        {"status": "submitted"},
        format="json",
    )
    # Reaching the completion check proves the permission layer let the requester in;
    # under an `approve` gate this is a flat 403.
    assert res.status_code != 403, "the requester was refused by the permission layer"
    assert res.json()["error"] == "responseIncomplete", res.json()


@pytest.mark.django_db
def test_preview_survives_non_choice_answers(app_config):
    """A boolean or number answer used to reach `extract_node_id` as a raw value, so
    previewing any form with one 500ed as soon as it was answered truthy."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    _user, client = _admin_client("qf-preview-bool@test.local")

    res = client.post(
        f"/api/quick-forms/{form.id}/preview/",
        {"answers": {Q_SENSITIVE: True, Q_HEADCOUNT: 12}},
        format="json",
    )
    assert res.status_code == 200, res.content[:300]
    body = res.json()

    # The boolean did not merely survive: it drove the rule that reads it.
    assert "dpia_required" in (body["computed_outcome"] or {}), body["computed_outcome"]
    assert body["progress"]["answered_count"] == 2, body["progress"]


@pytest.mark.django_db
def test_respondent_role_can_answer_and_submit(app_config):
    """BI-RL-ADE ("Respondent") holds no quick-form permission at all, and does not need
    one: `/my-requests` authorises on respondent membership, not folder RBAC."""
    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-respondent", parent_folder=Folder.get_root_folder()
    )
    user, client = _role_client("qf-respondent@test.local", "BI-RL-ADE", folder)
    actor = Actor.objects.filter(user=user, entity__isnull=True).first()

    response = QuickFormResponse.objects.create(
        name="theirs",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.DRAFT,
    )
    response.respondents.add(actor)
    base = f"/api/my-requests/{response.id}/"

    assert client.get("/api/my-requests/").status_code == 200
    assert client.get(f"{base}content/").status_code == 200

    res = client.patch(
        f"{base}answers/",
        {"answers": {Q_SENSITIVE: False, Q_HEADCOUNT: 5}},
        format="json",
    )
    assert res.status_code == 200, res.json()

    res = client.post(f"{base}submit/", {}, format="json")
    assert res.status_code == 200, res.json()
    response.refresh_from_db()
    assert response.status == QuickFormResponse.Status.SUBMITTED
    assert response.submitted_by_id == user.id

    # And the reviewer surface stays shut: answering is not reviewing. 404 rather than
    # 403 — folder scoping hides the row, so it does not leak that it exists.
    assert (
        client.get(f"/api/quick-form-responses/{response.id}/content/").status_code
        == 404
    )


@pytest.mark.django_db
def test_respondent_may_start_a_request_but_sees_only_their_own(app_config):
    """`add_quickformresponse` on BI-RL-ADE is what an inline portal tile checks. It is
    create-only on purpose: reading needs `view_quickformresponse`, which the role has
    not got, so a respondent never sees a request they are not on."""
    from django.contrib.auth.models import Permission

    _load(LIBRARY_V1)
    form = QuickForm.objects.get(urn=FORM_URN)
    folder = Folder.objects.create(
        name="qf-ade-grant", parent_folder=Folder.get_root_folder()
    )
    respondent, client = _role_client("qf-ade@test.local", "BI-RL-ADE", folder)
    other, _ = _role_client("qf-ade-other@test.local", "BI-RL-ANA", folder)

    # The gate the inline tile checks (portals/views.py).
    assert RoleAssignment.is_access_allowed(
        user=respondent,
        perm=Permission.objects.get(codename="add_quickformresponse"),
        folder=folder,
    )

    someone_elses = QuickFormResponse.objects.create(
        name="not yours",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.SUBMITTED,
        submitted_by=other,
    )

    # Create-only: the reviewer surface stays empty and closed.
    listing = client.get("/api/quick-form-responses/")
    assert listing.status_code == 200
    assert listing.json()["results"] == [], listing.json()
    assert (
        client.get(f"/api/quick-form-responses/{someone_elses.id}/content/").status_code
        == 404
    )

    # Their own request is reachable, answerable and submittable.
    mine = QuickFormResponse.objects.create(
        name="mine",
        quick_form=form,
        folder=folder,
        status=QuickFormResponse.Status.DRAFT,
    )
    mine.respondents.add(
        Actor.objects.filter(user=respondent, entity__isnull=True).first()
    )
    base = f"/api/my-requests/{mine.id}/"
    assert [r["id"] for r in client.get("/api/my-requests/").json()["results"]] == [
        str(mine.id)
    ]
    assert (
        client.patch(
            f"{base}answers/",
            {"answers": {Q_SENSITIVE: False, Q_HEADCOUNT: 3}},
            format="json",
        ).status_code
        == 200
    )
    assert client.post(f"{base}submit/", {}, format="json").status_code == 200
