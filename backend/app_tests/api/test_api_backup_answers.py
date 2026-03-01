"""Tests for backup/restore round-trip of Answer objects with selected_choices."""

import io
import json
import uuid
import zipfile

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ciso_assistant.settings import SCHEMA_VERSION, VERSION
from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken


@pytest.fixture
def authenticated_client(app_config):
    admin = User.objects.create_superuser("backup_answers_admin@tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return client


@pytest.fixture
def framework_with_questions(app_config):
    """Create a published framework with questions and choices (simulates loaded library)."""
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Backup Test Framework",
        urn="urn:test:backup:fw",
        folder=folder,
        status=Framework.Status.PUBLISHED,
        is_published=True,
        min_score=0,
        max_score=100,
    )
    rn = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:backup:req:001",
        ref_id="BK-REQ",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    # Single-choice question
    q_sc = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:backup:q_sc",
        ref_id="BQSC",
        annotation="Pick one",
        type=Question.Type.SINGLE_CHOICE,
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q_sc,
        ref_id="AC1",
        annotation="Choice A",
        add_score=10,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q_sc,
        ref_id="AC2",
        annotation="Choice B",
        add_score=0,
        compute_result="false",
        order=1,
        folder=folder,
        is_published=True,
    )

    # Multiple-choice question
    q_mc = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:backup:q_mc",
        ref_id="BQMC",
        annotation="Select all",
        type=Question.Type.MULTIPLE_CHOICE,
        order=1,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q_mc,
        ref_id="MC1",
        annotation="Option 1",
        add_score=3,
        compute_result="true",
        order=0,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q_mc,
        ref_id="MC2",
        annotation="Option 2",
        add_score=2,
        compute_result="true",
        order=1,
        folder=folder,
        is_published=True,
    )
    QuestionChoice.objects.create(
        question=q_mc,
        ref_id="MC3",
        annotation="Option 3",
        add_score=1,
        compute_result="false",
        order=2,
        folder=folder,
        is_published=True,
    )

    # Text question
    q_text = Question.objects.create(
        requirement_node=rn,
        urn="urn:test:backup:q_text",
        ref_id="BQTXT",
        annotation="Describe",
        type=Question.Type.TEXT,
        order=2,
        folder=folder,
        is_published=True,
    )

    return {
        "framework": fw,
        "requirement_node": rn,
        "q_sc": q_sc,
        "q_mc": q_mc,
        "q_text": q_text,
    }


def create_domain_import_zip(objects):
    """Create a ZIP file in memory with data.json for domain import."""
    data = {
        "meta": {
            "media_version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "exported_at": "2026-01-01T00:00:00Z",
        },
        "objects": objects,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(data))
    buf.seek(0)
    return buf


def send_domain_import(client, zip_buf, domain_name="Test Import Domain"):
    """Send a domain import request."""
    zip_buf.seek(0)
    return client.post(
        reverse("folders-import-domain"),
        data=zip_buf.read(),
        content_type="application/octet-stream",
        HTTP_CONTENT_DISPOSITION='attachment; filename="test.zip"',
        HTTP_X_CISOASSISTANTDOMAINNAME=domain_name,
    )


def make_objects_for_answer(
    framework_urn,
    requirement_urn,
    question_urn,
    *,
    answer_value=None,
    selected_choices_ref_ids=None,
    include_choices_field=True,
):
    """Build minimal backup objects: perimeter, CA, RA, answer."""
    perim_id = uuid.uuid4().hex[:12]
    ca_id = uuid.uuid4().hex[:12]
    ra_id = uuid.uuid4().hex[:12]
    ans_id = uuid.uuid4().hex[:12]

    objects = [
        {
            "model": "core.perimeter",
            "id": perim_id,
            "fields": {
                "name": "Imported Perimeter",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        },
        {
            "model": "core.complianceassessment",
            "id": ca_id,
            "fields": {
                "name": "Imported CA",
                "perimeter": perim_id,
                "framework": framework_urn,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        },
        {
            "model": "core.requirementassessment",
            "id": ra_id,
            "fields": {
                "compliance_assessment": ca_id,
                "requirement": requirement_urn,
                "status": "to_do",
                "result": "not_assessed",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        },
    ]

    answer_fields = {
        "requirement_assessment": ra_id,
        "question": question_urn,
        "value": answer_value,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    if include_choices_field and selected_choices_ref_ids is not None:
        answer_fields["selected_choices_ref_ids"] = selected_choices_ref_ids

    objects.append(
        {
            "model": "core.answer",
            "id": ans_id,
            "fields": answer_fields,
        }
    )

    return objects


@pytest.mark.django_db(transaction=True)
class TestBackupRestoreAnswers:
    def test_backup_restore_single_choice_answer(
        self, authenticated_client, framework_with_questions
    ):
        """selected_choices_ref_ids: ['AC1'] -> Answer with 1 selected choice."""
        fwq = framework_with_questions
        objects = make_objects_for_answer(
            fwq["framework"].urn,
            fwq["requirement_node"].urn,
            fwq["q_sc"].urn,
            selected_choices_ref_ids=["AC1"],
        )
        zip_buf = create_domain_import_zip(objects)
        resp = send_domain_import(authenticated_client, zip_buf)

        assert resp.status_code == status.HTTP_200_OK
        answer = Answer.objects.filter(question=fwq["q_sc"]).first()
        assert answer is not None
        choice_refs = list(answer.selected_choices.values_list("ref_id", flat=True))
        assert choice_refs == ["AC1"]

    def test_backup_restore_multiple_choice_answer(
        self, authenticated_client, framework_with_questions
    ):
        """selected_choices_ref_ids: ['MC1','MC3'] -> Answer with 2 selected choices."""
        fwq = framework_with_questions
        objects = make_objects_for_answer(
            fwq["framework"].urn,
            fwq["requirement_node"].urn,
            fwq["q_mc"].urn,
            selected_choices_ref_ids=["MC1", "MC3"],
        )
        zip_buf = create_domain_import_zip(objects)
        resp = send_domain_import(authenticated_client, zip_buf)

        assert resp.status_code == status.HTTP_200_OK
        answer = Answer.objects.filter(question=fwq["q_mc"]).first()
        assert answer is not None
        choice_refs = set(answer.selected_choices.values_list("ref_id", flat=True))
        assert choice_refs == {"MC1", "MC3"}

    def test_backup_restore_answer_with_empty_choices(
        self, authenticated_client, framework_with_questions
    ):
        """selected_choices_ref_ids: [] -> Answer with no choices."""
        fwq = framework_with_questions
        objects = make_objects_for_answer(
            fwq["framework"].urn,
            fwq["requirement_node"].urn,
            fwq["q_sc"].urn,
            selected_choices_ref_ids=[],
        )
        zip_buf = create_domain_import_zip(objects)
        resp = send_domain_import(authenticated_client, zip_buf)

        assert resp.status_code == status.HTTP_200_OK
        answer = Answer.objects.filter(question=fwq["q_sc"]).first()
        assert answer is not None
        assert answer.selected_choices.count() == 0

    def test_backup_restore_answer_no_choices_field(
        self, authenticated_client, framework_with_questions
    ):
        """No selected_choices_ref_ids key -> Answer created, empty M2M."""
        fwq = framework_with_questions
        objects = make_objects_for_answer(
            fwq["framework"].urn,
            fwq["requirement_node"].urn,
            fwq["q_sc"].urn,
            include_choices_field=False,
        )
        zip_buf = create_domain_import_zip(objects)
        resp = send_domain_import(authenticated_client, zip_buf)

        assert resp.status_code == status.HTTP_200_OK
        answer = Answer.objects.filter(question=fwq["q_sc"]).first()
        assert answer is not None
        assert answer.selected_choices.count() == 0

    def test_backup_restore_preserves_value_field(
        self, authenticated_client, framework_with_questions
    ):
        """Text-type answer with value: 'some text' -> restored correctly."""
        fwq = framework_with_questions
        objects = make_objects_for_answer(
            fwq["framework"].urn,
            fwq["requirement_node"].urn,
            fwq["q_text"].urn,
            answer_value="some text",
        )
        zip_buf = create_domain_import_zip(objects)
        resp = send_domain_import(authenticated_client, zip_buf)

        assert resp.status_code == status.HTTP_200_OK
        answer = Answer.objects.filter(question=fwq["q_text"]).first()
        assert answer is not None
        assert answer.value == "some text"
