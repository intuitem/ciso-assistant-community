"""The subject of a quick form response: which object it is about, read from
the form's `subject_question_urn` (a single-object reference question)."""

import copy

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.cel_service import evaluate_quick_form, validate_quick_form_expressions
from core.models import (
    Question,
    QuickForm,
    QuickFormPublication,
    QuickFormResponse,
    StoredLibrary,
    User,
)
from core.object_references import ReferenceError_, subject_question_error
from core.utils import apply_answers_dict
from core.views import start_quick_form_response
from iam.models import Folder, UserGroup
from library.quick_form_editor import (
    editor_doc_to_quick_form_object,
    quick_form_to_editor_doc,
)
from tprm.models import Entity

FORM = "urn:test:risk:quick_form:vendor-subject"
PAGE = "urn:test:risk:qf_page:vendor-subject:vendor"
Q_VENDOR = f"{PAGE}:question:vendor"
Q_OTHERS = f"{PAGE}:question:others"
Q_NOTE = f"{PAGE}:question:note"

FORM_DICT = {
    "urn": FORM,
    "ref_id": "vendor-subject",
    "name": "Vendor subject",
    "subject_question_urn": Q_VENDOR,
    "pages": [
        {
            "urn": PAGE,
            "ref_id": "vendor",
            "name": "Vendor",
            "questions": {
                Q_VENDOR: {
                    "type": "object_reference",
                    "text": "Which vendor?",
                    "config": {"model": "entity"},
                },
                Q_OTHERS: {
                    "type": "object_reference",
                    "text": "Related vendors",
                    "config": {"model": "entity", "multiple": True},
                },
                Q_NOTE: {"type": "text", "text": "Note", "required": False},
            },
        }
    ],
}

LIBRARY_YAML = f"""
urn: urn:test:risk:library:vendor-subject
locale: en
ref_id: vendor-subject
name: Vendor subject
description: test
copyright: test
version: 1
provider: test
packager: test
objects:
  quick_forms:
    - urn: {FORM}
      ref_id: vendor-subject
      name: Vendor subject
      subject_question_urn: {Q_VENDOR}
      pages:
        - urn: {PAGE}
          ref_id: vendor
          name: Vendor
          questions:
            {Q_VENDOR}:
              type: object_reference
              text: Which vendor?
              config:
                model: entity
            {Q_NOTE}:
              type: text
              text: Note
              required: false
"""


def _form_with(**changes):
    form = copy.deepcopy(FORM_DICT)
    form.update(changes)
    return form


class TestSubjectQuestionCheck:
    def test_valid(self):
        assert subject_question_error(FORM_DICT) is None

    def test_none_declared(self):
        assert subject_question_error(_form_with(subject_question_urn="")) is None

    @pytest.mark.parametrize(
        "urn,message",
        [
            (Q_NOTE, "object reference"),
            (Q_OTHERS, "single-object"),
            (f"{PAGE}:question:missing", "does not match"),
        ],
    )
    def test_invalid(self, urn, message):
        error = subject_question_error(_form_with(subject_question_urn=urn))
        assert message in error

    def test_reported_by_the_builder_save_check(self):
        errors = validate_quick_form_expressions(
            _form_with(subject_question_urn=Q_NOTE)
        )
        assert [e["where"] for e in errors] == ["subject_question"]


class TestBuilderRoundTrip:
    def test_kept_set_and_cleared(self):
        doc = quick_form_to_editor_doc(FORM_DICT)
        assert doc["framework_meta"]["subject_question_urn"] == Q_VENDOR
        assert (
            editor_doc_to_quick_form_object(doc, existing=FORM_DICT)[
                "subject_question_urn"
            ]
            == Q_VENDOR
        )

        doc["framework_meta"]["subject_question_urn"] = None
        cleared = editor_doc_to_quick_form_object(doc, existing=FORM_DICT)
        assert "subject_question_urn" not in cleared

        doc["framework_meta"].pop("subject_question_urn")
        kept = editor_doc_to_quick_form_object(doc, existing=FORM_DICT)
        assert kept["subject_question_urn"] == Q_VENDOR

    def test_a_question_added_in_the_editor_can_be_the_subject(self):
        doc = quick_form_to_editor_doc(FORM_DICT)
        editor_urn = "urn:test:risk:question:vendor-subject:vendor-q9"
        added = copy.deepcopy(doc["questions"][0])
        added.update(id="tmp-id", urn=editor_urn, ref_id="vendor-q9", order=900)
        doc["questions"].append(added)
        doc["framework_meta"]["subject_question_urn"] = editor_urn

        urn_map = {}
        saved = editor_doc_to_quick_form_object(
            doc, existing=FORM_DICT, urn_map_out=urn_map
        )
        canonical = urn_map[editor_urn]
        assert canonical == f"{PAGE}:question:vendor-q9"
        assert saved["subject_question_urn"] == canonical
        assert validate_quick_form_expressions(saved) == []

        # The editor adopts the returned URNs; saving again changes nothing.
        added["urn"] = canonical
        doc["framework_meta"]["subject_question_urn"] = canonical
        again_map = {}
        again = editor_doc_to_quick_form_object(
            doc, existing=saved, urn_map_out=again_map
        )
        assert set(again["pages"][0]["questions"]) == set(
            saved["pages"][0]["questions"]
        )
        assert again_map["tmp-id"] == canonical

    def test_rules_written_before_the_first_save_follow_the_ids(self):
        """A page and question added and renamed in the editor are stored under
        ids derived from their ref_id: rules naming the editor's ids follow."""
        doc = quick_form_to_editor_doc(FORM_DICT)
        page = copy.deepcopy(doc["nodes"][0])
        page.update(
            id="tmp-page",
            urn="urn:test:risk:qf_page:vendor-subject:2",
            ref_id="scoring",
            name="Scoring",
            order_id=2,
        )
        doc["nodes"].append(page)
        question = copy.deepcopy(doc["questions"][0])
        question.update(
            id="tmp-q",
            urn="urn:test:risk:question:vendor-subject:2-q1",
            ref_id="2-q1",
            requirement_node_id="tmp-page",
            type="unique_choice",
            config=None,
        )
        doc["questions"].append(question)
        doc["choices"].append(
            {
                "id": "tmp-c",
                "urn": "urn:test:risk:question_choice:vendor-subject:2-q1-c1",
                "question_id": "tmp-q",
                "value": "Yes",
                "add_score": 1,
                "order": 0,
            }
        )
        doc["framework_meta"]["outcomes_definition"] = [
            {"ref_id": "score", "kind": "number", "expression": 'pages["2"].score'},
            {
                "ref_id": "yes",
                "expression": '"2-q1-c1" in answers["2-q1"].selected_choices',
            },
            {"ref_id": "literal", "expression": 'answers["2-q1"].value == "2"'},
        ]

        urn_map = {}
        saved = editor_doc_to_quick_form_object(
            doc, existing=FORM_DICT, urn_map_out=urn_map
        )
        rules = {r["ref_id"]: r["expression"] for r in saved["outcomes_definition"]}
        assert rules["score"] == 'pages["scoring"].score'
        assert rules["yes"] == (
            '"scoring:question:2-q1:choice:1" in '
            'answers["scoring:question:2-q1"].selected_choices'
        )
        # A plain value that happens to equal an old id is left alone.
        assert rules["literal"] == 'answers["scoring:question:2-q1"].value == "2"'
        assert validate_quick_form_expressions(saved) == []

    def test_saving_twice_with_editor_urns_mints_twice(self):
        """Why the editor must adopt the returned URNs: the server cannot tell a
        re-sent editor URN from new content, so it mints again."""
        doc = quick_form_to_editor_doc(FORM_DICT)
        added = copy.deepcopy(doc["questions"][0])
        added.update(
            id="tmp-id",
            urn="urn:test:risk:question:vendor-subject:vendor-q9",
            ref_id="vendor-q9",
            order=900,
        )
        doc["questions"].append(added)
        saved = editor_doc_to_quick_form_object(doc, existing=FORM_DICT)
        again = editor_doc_to_quick_form_object(doc, existing=saved)
        assert f"{PAGE}:question:vendor-q9-2" in again["pages"][0]["questions"]


@pytest.fixture
def setup():
    startup(sender=None, **{})
    stored, error = StoredLibrary.store_library_content(LIBRARY_YAML.encode("utf-8"))
    assert error is None, error
    assert stored.load() is None
    form = QuickForm.objects.get(urn=FORM)
    domain = Folder.objects.create(
        name="vendors",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    acme = Entity.objects.create(name="Acme", folder=domain)
    globex = Entity.objects.create(name="Globex", folder=domain)
    elsewhere = Folder.objects.create(
        name="elsewhere",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    hidden = Entity.objects.create(name="Hidden", folder=elsewhere)
    return {
        "form": form,
        "domain": domain,
        "acme": acme,
        "globex": globex,
        "hidden": hidden,
    }


def _admin():
    user = User.objects.create_user(email="qf-subject@test.local", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return user, client


def _answer(response, value):
    questions = {
        q.urn: q for q in Question.objects.filter(page__quick_form=response.quick_form)
    }
    apply_answers_dict("response", response, questions, {Q_VENDOR: value})
    evaluate_quick_form(response, persist=True)
    response.refresh_from_db()


@pytest.mark.django_db
class TestSubjectFromAnswers:
    def _response(self, setup):
        response = QuickFormResponse.objects.create(
            name="r", quick_form=setup["form"], folder=setup["domain"]
        )
        response.seed_answers()
        return response

    def test_library_load_stores_the_subject_question(self, setup):
        assert setup["form"].subject_question_urn == Q_VENDOR

    def test_answer_sets_changes_and_clears_the_subject(self, setup):
        response = self._response(setup)
        assert response.subject is None

        _answer(response, [str(setup["acme"].id)])
        assert response.subject == setup["acme"]
        assert response.subject_content_type.model == "entity"

        _answer(response, [str(setup["globex"].id)])
        assert response.subject == setup["globex"]

        _answer(response, [])
        assert response.subject is None

    def test_question_urn_case_does_not_matter(self, setup):
        # Question URNs are stored as authored; the form's subject URN lowercased.
        Question.objects.filter(urn=Q_VENDOR).update(
            urn=Q_VENDOR.replace("vendor", "Vendor")
        )
        response = self._response(setup)
        questions = {
            q.urn: q for q in Question.objects.filter(page__quick_form=setup["form"])
        }
        apply_answers_dict(
            "response",
            response,
            questions,
            {Q_VENDOR.replace("vendor", "Vendor"): [str(setup["acme"].id)]},
        )
        evaluate_quick_form(response, persist=True)
        response.refresh_from_db()
        assert response.subject == setup["acme"]

    def test_unreachable_object_never_becomes_the_subject(self, setup):
        response = self._response(setup)
        _answer(response, [str(setup["hidden"].id)])
        assert response.subject is None

    def test_locked_once_closed(self, setup):
        response = self._response(setup)
        _answer(response, [str(setup["acme"].id)])
        QuickFormResponse.objects.filter(pk=response.pk).update(
            status=QuickFormResponse.Status.CLOSED
        )
        response.refresh_from_db()
        _answer(response, [str(setup["globex"].id)])
        assert response.subject == setup["acme"]

    def test_api_exposes_and_filters_by_subject(self, setup):
        _user, client = _admin()
        about_acme = self._response(setup)
        _answer(about_acme, [str(setup["acme"].id)])
        about_globex = self._response(setup)
        _answer(about_globex, [str(setup["globex"].id)])

        detail = client.get(f"/api/quick-form-responses/{about_acme.id}/").json()
        assert detail["subject"] == {
            "id": str(setup["acme"].id),
            "model": "entity",
            "str": "Acme",
        }

        listed = client.get(
            f"/api/quick-form-responses/?subject_object_id={setup['acme'].id}"
        ).json()
        assert [r["id"] for r in listed["results"]] == [str(about_acme.id)]

    def test_subject_cannot_be_written_directly(self, setup):
        _user, client = _admin()
        response = self._response(setup)
        client.patch(
            f"/api/quick-form-responses/{response.id}/",
            {"subject_object_id": str(setup["acme"].id)},
            format="json",
        )
        response.refresh_from_db()
        assert response.subject_object_id is None

    def test_label_hidden_from_a_user_who_cannot_see_the_object(self, setup):
        response = self._response(setup)
        _answer(response, [str(setup["acme"].id)])
        stranger = User.objects.create_user(email="stranger@test.local")
        summary = response.subject_summary(stranger)
        assert summary["id"] == str(setup["acme"].id)
        assert summary["str"] is None


@pytest.mark.django_db
class TestStartWithSubject:
    def _publication(self, setup, **extra):
        return QuickFormPublication.objects.create(
            name="Assess vendor",
            quick_form=setup["form"],
            folder=setup["domain"],
            **extra,
        )

    def test_subject_is_prefilled(self, setup):
        user, _client = _admin()
        response, resumed = start_quick_form_response(
            user, self._publication(setup), subject_id=str(setup["acme"].id)
        )
        assert not resumed
        response.refresh_from_db()
        assert response.subject == setup["acme"]
        answer = response.answers.get(question__urn=Q_VENDOR)
        assert answer.value == [str(setup["acme"].id)]

    def test_only_a_draft_about_the_same_subject_is_resumed(self, setup):
        user, _client = _admin()
        publication = self._publication(setup)
        first, _ = start_quick_form_response(
            user, publication, subject_id=str(setup["acme"].id)
        )
        again, resumed = start_quick_form_response(
            user, publication, subject_id=str(setup["acme"].id)
        )
        assert resumed and again.pk == first.pk
        other, resumed = start_quick_form_response(
            user, publication, subject_id=str(setup["globex"].id)
        )
        assert not resumed and other.pk != first.pk

    def test_unreachable_subject_is_refused(self, setup):
        user, _client = _admin()
        with pytest.raises(ReferenceError_):
            start_quick_form_response(
                user, self._publication(setup), subject_id=str(setup["hidden"].id)
            )

    def test_form_without_subject_question_is_refused(self, setup):
        user, _client = _admin()
        QuickForm.objects.filter(pk=setup["form"].pk).update(subject_question_urn="")
        setup["form"].refresh_from_db()
        with pytest.raises(ReferenceError_) as raised:
            start_quick_form_response(
                user, self._publication(setup), subject_id=str(setup["acme"].id)
            )
        assert raised.value.code == "formHasNoSubjectQuestion"

    def test_start_endpoint(self, setup):
        _user, client = _admin()
        publication = self._publication(setup)
        ok = client.post(
            f"/api/quick-form-publications/{publication.id}/start/",
            {"subject": str(setup["acme"].id)},
            format="json",
        )
        assert ok.status_code == 200, ok.json()
        refused = client.post(
            f"/api/quick-form-publications/{publication.id}/start/",
            {"subject": str(setup["hidden"].id)},
            format="json",
        )
        assert refused.status_code == 400
        assert refused.json() == {"error": "unreachableObjectReference"}
