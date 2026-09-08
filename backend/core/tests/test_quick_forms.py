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
from iam.models import Folder, User, UserGroup
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
        assert response.status == QuickFormResponse.Status.IN_PROGRESS
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

        # Reopen keeps the observation, closing is terminal.
        res = client.post(
            f"{url}set-status/",
            {"status": "in_progress", "observation": "Please detail the scale"},
            format="json",
        )
        assert res.status_code == 200
        response.refresh_from_db()
        assert response.observation == "Please detail the scale"
        res = client.post(f"{url}set-status/", {"status": "submitted"}, format="json")
        assert res.status_code == 200
        res = client.post(f"{url}set-status/", {"status": "closed"}, format="json")
        assert res.status_code == 200
        res = client.post(f"{url}set-status/", {"status": "in_progress"}, format="json")
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
