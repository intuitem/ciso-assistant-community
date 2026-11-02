"""Whatever a chat tool or retrieval step returns ends up in the LLM prompt, so
none of it may come from objects the user cannot read through the API. Every
object in the foreign domain carries CANARY in its name; it must never surface."""

from types import SimpleNamespace

import pytest
from django.apps import apps

from chat.orm_query import format_query_result
from chat.scoping import ReadScope
from chat.tools import MODEL_MAP, dispatch_tool_call
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

pytestmark = pytest.mark.django_db

CANARY = "zzcanary"


def _domain(name):
    return Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


def _grant(user, role_name, domain):
    group = UserGroup.objects.create(
        folder=domain, name=f"{user.email}-{role_name}", builtin=True
    )
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_name),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    assignment.perimeter_folders.add(domain)
    group.user_set.add(user)


@pytest.fixture
def own():
    return _domain("own domain")


@pytest.fixture
def foreign():
    return _domain(f"{CANARY} domain")


@pytest.fixture
def reader(own):
    user = User.objects.create(email="chat-reader@test.local")
    _grant(user, "BI-RL-AUD", own)
    return user


@pytest.fixture
def canaries(foreign):
    from core.models import (
        AppliedControl,
        Asset,
        ComplianceAssessment,
        Evidence,
        Finding,
        FindingsAssessment,
        Framework,
        Incident,
        Perimeter,
        RequirementNode,
        RiskAcceptance,
        RiskAssessment,
        RiskMatrix,
        RiskScenario,
        SecurityException,
        Threat,
        Vulnerability,
    )
    from ebios_rm.models import EbiosRMStudy, FearedEvent
    from tprm.models import Entity, Solution

    name = f"{CANARY} object"
    AppliedControl.objects.create(name=name, folder=foreign)
    Asset.objects.create(name=name, folder=foreign)
    Threat.objects.create(name=name, folder=foreign)
    Evidence.objects.create(name=name, folder=foreign)
    Vulnerability.objects.create(name=name, folder=foreign)
    SecurityException.objects.create(name=name, folder=foreign)
    Incident.objects.create(name=name, folder=foreign)
    RiskAcceptance.objects.create(name=name, folder=foreign)
    entity = Entity.objects.create(name=name, folder=foreign)
    Solution.objects.create(name=name, provider_entity=entity)
    matrix = RiskMatrix.objects.create(
        name=name,
        folder=foreign,
        is_enabled=True,
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    perimeter = Perimeter.objects.create(name=name, folder=foreign)
    ra = RiskAssessment.objects.create(
        name=name, folder=foreign, perimeter=perimeter, risk_matrix=matrix
    )
    RiskScenario.objects.create(name=name, risk_assessment=ra)
    fa = FindingsAssessment.objects.create(name=name, folder=foreign)
    Finding.objects.create(name=name, findings_assessment=fa, folder=foreign)
    framework = Framework.objects.create(
        name="neutral framework", folder=Folder.get_root_folder()
    )
    RequirementNode.objects.create(
        name=name,
        framework=framework,
        assessable=True,
        folder=Folder.get_root_folder(),
    )
    audit = ComplianceAssessment.objects.create(
        name=name, framework=framework, perimeter=perimeter, folder=foreign
    )
    audit.create_requirement_assessments()
    study = EbiosRMStudy.objects.create(name=name, folder=foreign, risk_matrix=matrix)
    FearedEvent.objects.create(name=name, ebios_rm_study=study)
    return SimpleNamespace(audit=audit, matrix=matrix, entity=entity)


def _text(result) -> str:
    return format_query_result(result).lower() if result else ""


def test_query_tools_never_return_foreign_objects(reader, canaries):
    scope = ReadScope(reader)
    for model_key, (app_label, model_name, *_) in MODEL_MAP.items():
        model = apps.get_model(app_label, model_name)
        searches = [{}]
        if any(f.name == "name" for f in model._meta.get_fields()):
            searches.append({"search": "object"})
        for action in ("list", "count", "summary"):
            for extra in searches:
                args = {"model": model_key, "action": action, **extra}
                result = dispatch_tool_call("query_objects", args, scope)
                assert CANARY not in _text(result), (model_key, action, extra)
        multi = dispatch_tool_call(
            "multi_query", {"queries": [{"model": model_key, "action": "list"}]}, scope
        )
        for sub in (multi or {}).get("results", []):
            assert CANARY not in _text(sub), model_key


def test_create_proposal_never_offers_a_foreign_risk_matrix(reader, canaries):
    proposal = dispatch_tool_call(
        "propose_create",
        {"model": "ebios_rm_study", "items": [{"name": "new study"}]},
        ReadScope(reader),
    )
    for item in (proposal or {}).get("items", []):
        assert item.get("risk_matrix") != str(canaries.matrix.id)


def test_control_suggestions_ignore_unreadable_controls_in_the_audit_domain(
    reader, foreign, canaries
):
    from chat.workflows.suggest_controls import SuggestControlsWorkflow

    found = SuggestControlsWorkflow()._search_controls(
        SimpleNamespace(scope=ReadScope(reader)),
        {"name": f"{CANARY} object", "description": "", "folder_id": str(foreign.id)},
    )
    assert not [c for c in found if CANARY in c["name"].lower()]


class TestRespondentWithAnotherRole:
    """Reader in one domain (so chat is available) and auditee in another:
    the audit side of the second domain stays out of chat, as in analytics."""

    @pytest.fixture
    def user(self, own, foreign, canaries):
        from core.models import Actor, RequirementAssessment, RequirementAssignment

        user = User.objects.create(email="chat-mixed@test.local")
        _grant(user, "BI-RL-AUD", own)
        _grant(user, "BI-RL-ADE", foreign)
        actor, _ = Actor.objects.get_or_create(user=user)
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=canaries.audit, folder=foreign
        )
        assignment.actor.add(actor)
        assignment.requirement_assessments.set(
            RequirementAssessment.objects.filter(compliance_assessment=canaries.audit)
        )
        return user

    def test_audit_models_are_not_readable_in_the_respondent_domain(
        self, user, foreign
    ):
        from core.models import (
            AppliedControl,
            ComplianceAssessment,
            RequirementAssessment,
            RequirementAssignment,
        )

        scope = ReadScope(user)
        for model in (
            ComplianceAssessment,
            RequirementAssessment,
            RequirementAssignment,
        ):
            assert not scope.queryset(model).filter(folder=foreign).exists(), model
            assert str(foreign.id) not in scope.folder_ids_for(model), model
        assert scope.queryset(AppliedControl).filter(folder=foreign).exists()

    def test_query_tools_hide_the_audit(self, user):
        scope = ReadScope(user)
        for model_key in ("compliance_assessment", "requirement_assessment"):
            result = dispatch_tool_call(
                "query_objects", {"model": model_key, "action": "list"}, scope
            )
            assert CANARY not in _text(result), model_key


@pytest.fixture
def qdrant(monkeypatch):
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    import chat.providers as providers
    import chat.rag as rag

    client = QdrantClient(":memory:")
    client.create_collection(
        rag.COLLECTION_NAME,
        vectors_config=VectorParams(size=2, distance=Distance.COSINE),
    )
    monkeypatch.setattr(rag, "get_qdrant_client", lambda: client)
    monkeypatch.setattr(rag, "_get_reranker", lambda: None)
    monkeypatch.setattr(
        providers,
        "get_embedder",
        lambda: SimpleNamespace(embed_query=lambda _text: [1.0, 0.0]),
    )
    return client


def _index(client, folder, points):
    from qdrant_client.models import PointStruct

    import chat.rag as rag

    client.upsert(
        rag.COLLECTION_NAME,
        points=[
            PointStruct(
                id=i,
                vector=[1.0, 0.0],
                payload={
                    "object_type": object_type,
                    "folder_id": str(folder.id),
                    "source_type": "model",
                    "text": name,
                    "name": name,
                },
            )
            for i, (object_type, name) in enumerate(points, start=1)
        ],
    )


def test_questionnaire_evidence_search_honours_the_owner_read_rights(qdrant, own):
    from chat.questionnaire import _search_folder_evidence

    owner = User.objects.create(email="chat-auditee@test.local")
    _grant(owner, "BI-RL-ADE", own)
    _index(
        qdrant,
        own,
        [("risk_scenario", f"{CANARY} scenario"), ("applied_control", "backups")],
    )

    names = {r["name"] for r in _search_folder_evidence("q", own.id, owner)}
    assert names == {"backups"}


def test_rag_search_hides_audits_from_a_respondent_with_another_role(
    qdrant, own, foreign
):
    import chat.rag as rag

    user = User.objects.create(email="chat-rag-mixed@test.local")
    _grant(user, "BI-RL-AUD", own)
    _grant(user, "BI-RL-ADE", foreign)
    _index(
        qdrant,
        foreign,
        [("compliance_assessment", f"{CANARY} audit"), ("applied_control", "backups")],
    )

    names = {r["name"] for r in rag.search("q", user, source_type="model")}
    assert names == {"backups"}
