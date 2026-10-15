from unittest.mock import patch

import pytest

from chat.knowledge_graph import DiGraph, _process_library
from core.models import Framework, RequirementNode
from iam.models import Folder, RoleAssignment


def framework_lib(key, refs):
    return {
        "urn": f"urn:test:library:{key}",
        "objects": {
            "framework": {
                "urn": f"urn:test:framework:{key}",
                "ref_id": key.upper(),
                "name": f"Framework {key}",
                "requirement_nodes": [
                    {
                        "urn": f"urn:test:req:{key}:{ref.lower()}",
                        "ref_id": ref,
                        "name": f"{key} {ref} {name}",
                        "assessable": True,
                    }
                    for ref, name in refs
                ],
            }
        },
    }


def mapping(s, t, rel):
    return {
        "source_requirement_urn": f"urn:test:req:{s}",
        "target_requirement_urn": f"urn:test:req:{t}",
        "relationship": rel,
    }


@pytest.fixture
def graph():
    G = DiGraph()
    _process_library(
        G, framework_lib("a", [("A.1", "multi-factor login"), ("A.2", "backups")])
    )
    _process_library(
        G, framework_lib("b", [("B.1", "authentication"), ("B.2", "restore")])
    )
    _process_library(G, framework_lib("c", [("C.1", "strong auth")]))
    # unloaded and reusing b's references, like CyFun reuses NIST CSF's
    _process_library(G, framework_lib("d", [("B.2", "restore copy")]))
    # the plural form most mapping libraries use
    _process_library(
        G,
        {
            "objects": {
                "requirement_mapping_sets": [
                    {
                        "source_framework_urn": "urn:test:framework:a",
                        "target_framework_urn": "urn:test:framework:b",
                        "requirement_mappings": [
                            mapping("a:a.1", "b:b.1", "equal"),
                            mapping("a:a.1", "b:b.2", "not_related"),
                        ],
                    },
                    {
                        "source_framework_urn": "urn:test:framework:a",
                        "target_framework_urn": "urn:test:framework:c",
                        "requirement_mappings": [
                            mapping("a:a.1", "c:c.1", "subset"),
                            # target of a framework that is not shipped
                            mapping("a:a.1", "zz:z.1", "equal"),
                        ],
                    },
                ]
            }
        },
    )
    with patch("library.knowledge.get_graph", return_value=G):
        yield G


@pytest.fixture
def loaded(db):
    """Frameworks a and b are loaded; c is shipped but not loaded."""
    root = Folder.get_root_folder()
    out = {}
    for key, refs in (("a", ("A.1", "A.2")), ("b", ("B.1", "B.2"))):
        fw = Framework.objects.create(
            name=f"Framework {key}",
            urn=f"urn:test:framework:{key}",
            ref_id=key,
            folder=root,
        )
        for ref in refs:
            out[ref] = RequirementNode.objects.create(
                framework=fw,
                urn=f"urn:test:req:{key}:{ref.lower()}",
                ref_id=ref,
                assessable=True,
                folder=root,
            )
    return out


def get(client, path, **params):
    return client.get(f"/api/library-knowledge/{path}/", params)


@pytest.mark.django_db
def test_lookup_by_ref_id_returns_loaded_id(authenticated_client, graph, loaded):
    res = get(
        authenticated_client, "requirements", framework="framework a", ref_id="a.1"
    )
    rows = res.json()["requirements"]
    assert [(r["ref_id"], r["id"], r["loaded"]) for r in rows] == [
        ("A.1", str(loaded["A.1"].id), True)
    ]


@pytest.mark.django_db
def test_unloaded_framework_is_answerable_without_id(
    authenticated_client, graph, loaded
):
    rows = get(authenticated_client, "requirements", ref_id="C.1").json()[
        "requirements"
    ]
    assert [(r["ref_id"], r["id"], r["loaded"]) for r in rows] == [("C.1", None, False)]


@pytest.mark.django_db
def test_ref_id_looked_up_in_wrong_framework_falls_back(
    authenticated_client, graph, loaded
):
    data = get(
        authenticated_client,
        "requirements",
        framework="framework a",
        search="map to B.2",
    ).json()
    # loaded framework first
    assert [r["framework_ref_id"] for r in data["requirements"]] == ["B", "D"]
    assert "B.2" in data["note"]


@pytest.mark.django_db
def test_unknown_framework_lists_choices(authenticated_client, graph, loaded):
    data = get(
        authenticated_client, "requirements", framework="zzz", ref_id="A.1"
    ).json()
    assert data["unknown_framework"] == "zzz" and "A" in data["frameworks"]


@pytest.mark.django_db
def test_mappings_skip_not_related_and_filter_target(
    authenticated_client, graph, loaded
):
    data = get(
        authenticated_client, "mappings", requirement=str(loaded["A.1"].id)
    ).json()
    assert {(r["ref_id"], r["relationship"]) for r in data["mappings"]} == {
        ("B.1", "equal"),
        ("C.1", "subset"),
    }
    data = get(
        authenticated_client,
        "mappings",
        requirement="urn:test:req:a:a.1",
        framework="C",
    ).json()
    assert [r["ref_id"] for r in data["mappings"]] == ["C.1"]


@pytest.mark.django_db
def test_mappings_wrong_target_reports_elsewhere(authenticated_client, graph, loaded):
    data = get(
        authenticated_client,
        "mappings",
        requirement="urn:test:req:a:a.1",
        framework="framework a",
    ).json()
    assert data["mappings"] == [] and data["elsewhere"] == {
        "Framework b": 1,
        "Framework c": 1,
    }


@pytest.mark.django_db
def test_mappings_unknown_requirement_404(authenticated_client, graph, loaded):
    assert (
        get(authenticated_client, "mappings", requirement="urn:nope").status_code == 404
    )


def patched_permissions(denied=(), hidden_framework=None):
    real_has = RoleAssignment.has_permission_anywhere
    real_ids = RoleAssignment.get_viewable_object_ids

    def has(user, codename):
        return codename not in denied and real_has(user, codename)

    def ids(user, model, folder=None):
        got = real_ids(user, model, folder)
        if model is Framework and hidden_framework:
            return [i for i in got if i != hidden_framework]
        return got

    return (
        patch.object(RoleAssignment, "has_permission_anywhere", side_effect=has),
        patch.object(RoleAssignment, "get_viewable_object_ids", side_effect=ids),
    )


@pytest.mark.django_db
def test_unloaded_frameworks_need_view_storedlibrary(
    authenticated_client, graph, loaded
):
    p1, p2 = patched_permissions(denied={"view_storedlibrary"})
    with p1, p2:
        assert (
            get(authenticated_client, "requirements", ref_id="C.1").json()[
                "requirements"
            ]
            == []
        )
        data = get(
            authenticated_client, "mappings", requirement="urn:test:req:a:a.1"
        ).json()
    assert [r["ref_id"] for r in data["mappings"]] == ["B.1"]


@pytest.mark.django_db
def test_loaded_framework_not_viewable_is_hidden(authenticated_client, graph, loaded):
    p1, p2 = patched_permissions(hidden_framework=loaded["B.1"].framework_id)
    with p1, p2:
        assert (
            get(authenticated_client, "requirements", ref_id="B.1").json()[
                "requirements"
            ]
            == []
        )
        data = get(
            authenticated_client, "mappings", requirement="urn:test:req:a:a.1"
        ).json()
    assert [r["ref_id"] for r in data["mappings"]] == ["C.1"]


@pytest.mark.django_db
def test_permission_type_gates_access(authenticated_client, graph, loaded):
    p1, p2 = patched_permissions(
        denied={"view_requirementnode", "view_requirementmappingset"}
    )
    with p1, p2:
        assert (
            get(authenticated_client, "requirements", ref_id="A.1").status_code == 403
        )
        assert (
            get(
                authenticated_client, "mappings", requirement="urn:test:req:a:a.1"
            ).status_code
            == 403
        )


@pytest.mark.django_db
def test_chat_requirement_mappings_not_hijacked_by_compare(
    authenticated_client, graph, loaded
):
    from chat.tools import _dispatch_search_library
    from iam.models import User

    admin = User.objects.get(email="admin@tests.com")  # from authenticated_client
    out = _dispatch_search_library(
        {
            "action": "requirement_mappings",
            "requirement": "urn:test:req:a:a.1",
            "framework_b": "C",
        },
        user_message="Which Framework c requirements map to Framework a A.1?",
        user=admin,
    )
    assert "C.1" in out["text"] and "B.1" not in out["text"]
    # one line per mapping, no identifiers for the answer model to wade through
    assert "- C C.1: c C.1 strong auth (subset)" in out["text"]
    assert "urn:" not in out["text"]


@pytest.mark.django_db
def test_chat_overview_action_with_ref_id_is_rerouted(
    authenticated_client, graph, loaded
):
    from chat.tools import _dispatch_search_library
    from iam.models import User

    admin = User.objects.get(email="admin@tests.com")
    lookup = _dispatch_search_library(
        {"action": "get_framework_detail", "framework": "Framework a", "ref_id": "A.2"},
        user=admin,
    )
    assert "a A.2 backups" in lookup["text"]
    mapped = _dispatch_search_library(
        {
            "action": "find_mappings",
            "framework": "Framework a",
            "ref_id": "A.1",
            "framework_b": "Framework c",
        },
        user=admin,
    )
    assert "C.1" in mapped["text"] and "B.1" not in mapped["text"]


@pytest.mark.django_db
def test_chat_falls_back_to_reference_in_question(authenticated_client, graph, loaded):
    from chat.tools import _dispatch_search_library
    from iam.models import User

    admin = User.objects.get(email="admin@tests.com")
    # no ref_id at all: the reference is only in the question
    lookup = _dispatch_search_library(
        {"action": "get_framework_detail", "framework": "Framework a"},
        user_message="What is requirement A.2 in Framework a?",
        user=admin,
    )
    assert "a A.2 backups" in lookup["text"]
    # a made-up ref_id: the question's reference wins
    mapped = _dispatch_search_library(
        {
            "action": "find_mappings",
            "framework": "Framework a",
            "ref_id": "A.9.9.9",
            "framework_b": "Framework c",
        },
        user_message="Which Framework c requirements map to Framework a A.1?",
        user=admin,
    )
    assert "C.1" in mapped["text"]
    # numbers that are not references of the named framework keep the overview
    overview = _dispatch_search_library(
        {"action": "get_framework_detail", "framework": "Framework b"},
        user_message="Summarise Framework b, version 2024, C.1",
        user=admin,
    )
    assert "b B.1" not in overview["text"] and "C.1 strong" not in overview["text"]


@pytest.mark.django_db
def test_mappings_by_source_framework_and_ref_id(authenticated_client, graph, loaded):
    data = get(
        authenticated_client,
        "mappings",
        source_framework="Framework A",
        ref_id="a.1",
        framework="b",
    ).json()
    assert [r["ref_id"] for r in data["mappings"]] == ["B.1"]
    # loaded framework wins over an unloaded one reusing the reference
    data = get(authenticated_client, "mappings", ref_id="B.2").json()
    assert data["source"]["framework_ref_id"] == "B"
    # two unloaded frameworks: the caller has to choose
    _process_library(graph, framework_lib("e", [("C.1", "other")]))
    ambiguous = get(authenticated_client, "mappings", ref_id="C.1").json()["ambiguous"]
    assert {r["framework_ref_id"] for r in ambiguous} == {"C", "E"}
    # not in the named framework: the one framework that has it, with a note
    fallback = get(
        authenticated_client, "mappings", source_framework="c", ref_id="A.1"
    ).json()
    assert fallback["source"]["ref_id"] == "A.1" and fallback["note"]
    assert (
        get(
            authenticated_client, "mappings", source_framework="c", ref_id="Z.9"
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_mappings_swapped_frameworks_are_corrected(authenticated_client, graph, loaded):
    # "which Framework a requirements map to Framework b B.1?" asked the wrong way round
    data = get(
        authenticated_client,
        "mappings",
        source_framework="framework c",
        ref_id="A.1",
        framework="framework a",
    ).json()
    assert data["source"]["ref_id"] == "A.1" and data["note"]
    assert {r["ref_id"] for r in data["mappings"]} == {"C.1"}


@pytest.mark.django_db
def test_exact_framework_name_beats_longer_one(authenticated_client, graph, loaded):
    from library.knowledge import _pick

    G = graph
    G.add_node(
        "urn:test:framework:a-journey",
        node_type="framework",
        name="Framework a journey",
    )
    assert _pick(
        G, ["urn:test:framework:a", "urn:test:framework:a-journey"], "Framework A"
    ) == ["urn:test:framework:a"]
