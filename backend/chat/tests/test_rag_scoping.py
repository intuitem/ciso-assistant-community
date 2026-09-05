"""Semantic search and graph expansion must honour view_<model>, not just
view_folder — a role can see a domain without being allowed to read what is
in it."""

import pytest
from qdrant_client.models import ValueVariants

from chat.scoping import ReadScope
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

pytestmark = pytest.mark.django_db


@pytest.fixture
def domain():
    from iam.models import Folder

    return Folder.objects.create(
        name="RAG Scoping Tests",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


def _user_with_role(email, role_name, domain):
    user = User.objects.create(email=email)
    group = UserGroup.objects.create(folder=domain, name=f"{email}-group")
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_name),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    assignment.perimeter_folders.add(domain)
    group.user_set.add(user)
    return user


@pytest.fixture
def reader(domain):
    return _user_with_role("rag-reader@test.local", "BI-RL-AUD", domain)


@pytest.fixture
def auditee(domain):
    """Holds view_appliedcontrol/view_asset(via default_role) but not view_riskscenario."""
    return _user_with_role("rag-auditee@test.local", "BI-RL-ADE", domain)


def scope_for(user: User) -> ReadScope:
    return ReadScope(user)


def _allowed_types(scope: ReadScope) -> set[ValueVariants]:
    import chat.rag as rag

    partition = rag._user_partition_filter(scope, None, None)
    if partition is None:
        return set()

    return {clause.must[0].match.value for clause in partition.must[0].should}


class TestUserPartitionFilter:
    def test_reader_may_search_risk_scenarios(self, reader, domain):
        assert "risk_scenario" in _allowed_types(ReadScope(reader))

    def test_auditee_may_not_search_risk_scenarios(self, auditee, domain):
        import chat.rag as rag

        from iam.models import Folder

        allowed = _allowed_types(ReadScope(auditee))
        assert "applied_control" in allowed
        assert "risk_scenario" not in allowed

        # The `"BI-RL-CAT"` `root_folder.default_role` grants any non-third-party user the `"view_asset"` `Role`` on the root folder.
        assert "asset" in allowed
        partition = rag._user_partition_filter(ReadScope(auditee), None, None)
        asset_folders = {
            fid
            for clause in partition.must[0].should
            if clause.must[0].match.value == "asset"
            for fid in clause.must[1].match.any
        }
        assert asset_folders == {str(Folder.get_root_folder().id)}
        assert str(domain.id) not in asset_folders

    def test_each_clause_carries_only_that_types_folders(self, auditee, domain):
        import chat.rag as rag

        from core.models import AppliedControl

        partition = rag._user_partition_filter(ReadScope(auditee), None, None)
        scope = ReadScope(auditee)
        for clause in partition.must[0].should:
            if clause.must[0].match.value == "applied_control":
                assert set(clause.must[1].match.any) == set(
                    scope.folder_ids_for(AppliedControl)
                )

    def test_object_type_argument_narrows_further(self, reader, domain):
        import chat.rag as rag

        partition = rag._user_partition_filter(ReadScope(reader), None, "asset")
        assert [c.must[0].match.value for c in partition.must[0].should] == ["asset"]

    def test_no_readable_type_yields_no_filter(self, domain):
        import chat.rag as rag

        from iam.models import User

        stranger = User.objects.create(email="rag-stranger@test.local")
        assert rag._user_partition_filter(ReadScope(stranger), None, None) is None


class TestSearchEndToEnd:
    """Drives the real filter through an in-memory Qdrant."""

    @pytest.fixture
    def indexed(self, monkeypatch, domain):
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            Distance,
            PointStruct,
            VectorParams,
        )

        import chat.rag as rag

        client = QdrantClient(":memory:")
        client.create_collection(
            rag.COLLECTION_NAME,
            vectors_config=VectorParams(size=2, distance=Distance.COSINE),
        )
        client.upsert(
            rag.COLLECTION_NAME,
            points=[
                PointStruct(
                    id=1,
                    vector=[1.0, 0.0],
                    payload={
                        "object_type": "risk_scenario",
                        "folder_id": str(domain.id),
                        "source_type": "model",
                        "text": "ransomware on the payment portal",
                        "name": "secret scenario",
                    },
                ),
                PointStruct(
                    id=2,
                    vector=[1.0, 0.0],
                    payload={
                        "object_type": "applied_control",
                        "folder_id": str(domain.id),
                        "source_type": "model",
                        "text": "offline backups",
                        "name": "backup control",
                    },
                ),
            ],
        )

        monkeypatch.setattr(rag, "get_qdrant_client", lambda: client)
        monkeypatch.setattr(rag, "_get_reranker", lambda: None)

        class _Embedder:
            def embed_query(self, _text):
                return [1.0, 0.0]

        import chat.providers as providers

        monkeypatch.setattr(providers, "get_embedder", lambda: _Embedder())
        return client

    def test_reader_retrieves_both(self, indexed, reader):
        import chat.rag as rag

        names = {
            r["name"] for r in rag.search("ransomware", reader, source_type="model")
        }
        assert names == {"secret scenario", "backup control"}

    def test_auditee_never_retrieves_the_risk_scenario(self, indexed, auditee):
        import chat.rag as rag

        names = {
            r["name"] for r in rag.search("ransomware", auditee, source_type="model")
        }
        assert names == {"backup control"}


class TestGraphExpandScoping:
    @pytest.fixture
    def scenario_with_control(self, domain):
        from iam.models import Folder

        from core.models import AppliedControl, RiskAssessment, RiskMatrix, RiskScenario

        matrix = RiskMatrix.objects.create(
            name="rag scoping matrix",
            folder=Folder.get_root_folder(),
            json_definition={
                "risk": [{"abbreviation": "L", "name": "Low"}],
                "probability": [],
                "impact": [],
                "grid": [],
            },
        )
        assessment = RiskAssessment.objects.create(
            name="rag scoping assessment", folder=domain, risk_matrix=matrix
        )
        scenario = RiskScenario.objects.create(
            name="rag scoping scenario", risk_assessment=assessment, folder=domain
        )
        control = AppliedControl.objects.create(
            name="rag scoping control", folder=domain
        )
        scenario.applied_controls.add(control)
        return scenario

    def test_expands_for_a_user_who_may_read_both_ends(
        self, scenario_with_control, reader
    ):
        import chat.rag as rag

        seeds = [
            {"object_type": "risk_scenario", "object_id": str(scenario_with_control.id)}
        ]
        assert [e["name"] for e in rag.graph_expand(seeds, ReadScope(reader))] == [
            "rag scoping control"
        ]

    def test_unreadable_seed_expands_to_nothing(self, scenario_with_control, auditee):
        """An auditee can read the control but not the scenario — walking from
        the scenario must not become a way to reach it."""
        import chat.rag as rag

        seeds = [
            {"object_type": "risk_scenario", "object_id": str(scenario_with_control.id)}
        ]
        assert rag.graph_expand(seeds, ReadScope(auditee)) == []
