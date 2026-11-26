"""Mapping-set editor of the library builder (library/mapping_editor.py + the
LibraryDraftViewSet mapping actions)."""

import copy

import pytest
import yaml
from django.urls import reverse
from rest_framework import status

from core.models import StoredLibrary
from library import mapping_editor as me
from library.builder import BuilderError
from library.tests.test_library_builder import (  # noqa: F401 (fixtures)
    _create_draft,
    admin_client,
    app_config,
)


def _framework(packager, ref, nodes, ref_id=None, name=None):
    base = f"urn:{packager}:risk:req_node:{ref}"
    return {
        "urn": f"urn:{packager}:risk:framework:{ref}",
        "ref_id": ref_id or ref,
        "name": name or ref,
        "requirement_nodes": [
            {"urn": f"{base}:ch", "ref_id": "CH", "assessable": False, "name": "Ch"}
        ]
        + [
            {
                "urn": f"{base}:{leaf}",
                "ref_id": node_ref,
                "name": node_name,
                "assessable": True,
                "parent_urn": f"{base}:ch",
            }
            for leaf, node_ref, node_name in nodes
        ],
    }


BUILTIN_NODES = [
    ("a.1", "A.1", "Information security policies are defined"),
    ("a.2", "A.2", "Roles and responsibilities are assigned"),
    ("a.3", "A.3", "Segregation of duties is enforced"),
]
BUILTIN = {
    "urn": "urn:acme:risk:library:iso-like",
    "locale": "en",
    "ref_id": "iso-like",
    "name": "ISO-like",
    "version": 1,
    "packager": "acme",
    "objects": {"framework": _framework("acme", "iso-like", BUILTIN_NODES, "ISO-LIKE")},
}


def _nodes(framework):
    return me.assessable_nodes(framework)


# --- pure helpers -----------------------------------------------------------


def test_suggestions_survive_rewording_via_urn_tail():
    original = BUILTIN["objects"]["framework"]
    clone = _framework(
        "me",
        "mylib",
        [
            ("a.1", "", "Our policy framework is written and approved by the board"),
            ("a.2", "A.2", "Roles and responsibilities are assigned"),
            ("a.3", "A.3", "Duties are split"),
        ],
    )
    suggestions = me.suggest_pairs(
        _nodes(clone),
        _nodes(original),
        set(),
        me.node_base(clone),
        me.node_base(original),
    )
    assert [(s["source"].rsplit(":", 1)[1], s["reason"]) for s in suggestions] == [
        ("a.1", "urn"),
        ("a.2", "urn"),
        ("a.3", "urn"),
    ]
    assert all(s["relationship"] == "equal" for s in suggestions)
    reworded = {s["source"].rsplit(":", 1)[1]: s["reworded"] for s in suggestions}
    assert reworded == {"a.1": True, "a.2": False, "a.3": True}
    assert me.clone_score(clone, original) == 1.0


def test_suggestions_fall_back_to_ref_id_then_name_one_to_one():
    target = _framework("acme", "t", [("x1", "A.1", "Alpha"), ("x2", "B", "Beta")])
    source = _framework(
        "me", "s", [("y1", "a.1", "zzz"), ("y2", "", "beta"), ("y3", "", "Alpha")]
    )
    suggestions = me.suggest_pairs(
        _nodes(source),
        _nodes(target),
        set(),
        me.node_base(source),
        me.node_base(target),
    )
    by_source = {s["source"].rsplit(":", 1)[1]: s for s in suggestions}
    assert by_source["y1"]["reason"] == "ref_id"
    assert by_source["y2"]["reason"] == "name"
    # x1 is already claimed by y1: no second suggestion for it
    assert "y3" not in by_source


def test_apply_pair_ops_is_atomic_and_validated():
    mapping_set = {"requirement_mappings": []}
    sources, targets = {"s:1", "s:2"}, {"t:1"}
    pairs = me.apply_pair_ops(
        mapping_set,
        [
            {"op": "add", "source": "S:1", "target": "t:1"},
            {"op": "add", "source": "s:2", "target": "t:1", "relationship": "subset"},
            {"op": "update", "source": "s:1", "target": "t:1", "relationship": "equal"},
        ],
        sources,
        targets,
    )
    assert [(p["source_requirement_urn"], p["relationship"]) for p in pairs] == [
        ("s:1", "equal"),
        ("s:2", "subset"),
    ]
    mapping_set["requirement_mappings"] = pairs
    # remove is idempotent, add upserts
    pairs = me.apply_pair_ops(
        mapping_set,
        [
            {"op": "remove", "source": "s:2", "target": "t:1"},
            {"op": "remove", "source": "s:2", "target": "t:1"},
            {"op": "add", "source": "s:1", "target": "t:1", "annotation": "note"},
        ],
        sources,
        targets,
    )
    assert pairs == [
        {
            "source_requirement_urn": "s:1",
            "target_requirement_urn": "t:1",
            "relationship": "equal",
            "annotation": "note",
        }
    ]
    mapping_set["requirement_mappings"] = pairs
    for bad in (
        {"op": "add", "source": "s:9", "target": "t:1"},
        {"op": "add", "source": "s:1", "target": "t:1", "relationship": "same"},
        {"op": "add", "source": "s:1", "target": "t:1", "rationale": "because"},
        {
            "op": "add",
            "source": "s:1",
            "target": "t:1",
            "strength_of_relationship": "9",
        },
        {"op": "update", "source": "s:2", "target": "t:1"},
        {"op": "rename"},
    ):
        before = copy.deepcopy(mapping_set)
        with pytest.raises(BuilderError):
            me.apply_pair_ops(
                mapping_set,
                [{"op": "remove", "source": "s:1", "target": "t:1"}, bad],
                sources,
                targets,
            )
        assert mapping_set == before


def test_reverse_swaps_sides_and_direction():
    reversed_pairs = me.reverse_mappings(
        {
            "requirement_mappings": [
                {
                    "source_requirement_urn": "a",
                    "target_requirement_urn": "b",
                    "relationship": "subset",
                    "rationale": "semantic",
                },
                {
                    "source_requirement_urn": "c",
                    "target_requirement_urn": "d",
                    "relationship": "intersect",
                },
            ]
        }
    )
    assert reversed_pairs == [
        {
            "source_requirement_urn": "b",
            "target_requirement_urn": "a",
            "relationship": "superset",
            "rationale": "semantic",
        },
        {
            "source_requirement_urn": "d",
            "target_requirement_urn": "c",
            "relationship": "intersect",
        },
    ]


# --- API: the clone round-trip ------------------------------------------------


@pytest.mark.django_db
def test_clone_reword_map_to_original_round_trip(admin_client):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(BUILTIN).encode(), builtin=True
    )
    assert error is None, error
    draft = _create_draft(admin_client, content={})
    url = lambda name: reverse(f"library-drafts-{name}", args=[draft["id"]])  # noqa: E731

    cloned = admin_client.post(
        url("import-objects"),
        {"source": str(stored.id), "object_types": ["frameworks"]},
        format="json",
    )
    assert cloned.status_code == status.HTTP_200_OK, cloned.content
    clone = cloned.data["draft"]["content"]["frameworks"][0]
    clone_urn = clone["urn"]

    # reword every item through the framework editor path's storage
    content = copy.deepcopy(cloned.data["draft"]["content"])
    # Real-world clone: renamed, framework ref_id dropped.
    content["frameworks"][0]["name"] = "ISO-like (copy)"
    content["frameworks"][0].pop("ref_id", None)
    for node in content["frameworks"][0]["requirement_nodes"]:
        node["name"] = f"Reworded {node['name'][::-1]}"
    response = admin_client.patch(
        reverse("library-drafts-detail", args=[draft["id"]]),
        {"content": content},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content

    original = admin_client.get(url("mapping-original"), {"framework_urn": clone_urn})
    assert original.status_code == status.HTTP_200_OK, original.content
    assert original.data["original"]["urn"] == "urn:acme:risk:framework:iso-like"
    assert original.data["original"]["library_urn"] == BUILTIN["urn"]

    pickable = admin_client.get(url("mapping-frameworks")).data["frameworks"]
    assert pickable[0] == {
        "urn": clone_urn,
        "name": "ISO-like (copy)",
        "library_urn": "urn:me:risk:library:mylib",
        "kind": "draft",
    }
    assert "urn:acme:risk:framework:iso-like" in {f["urn"] for f in pickable}

    created = admin_client.post(
        url("add-mapping-set"),
        {
            "source_framework_urn": clone_urn,
            "target_framework_urn": "urn:acme:risk:framework:iso-like",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED, created.content
    set_urn = created.data["urn"]
    detail = admin_client.get(reverse("library-drafts-detail", args=[draft["id"]]))
    assert BUILTIN["urn"] in detail.data["dependencies"]

    again = admin_client.post(
        url("add-mapping-set"),
        {
            "source_framework_urn": clone_urn,
            "target_framework_urn": "urn:acme:risk:framework:iso-like",
        },
        format="json",
    )
    assert again.status_code == status.HTTP_409_CONFLICT

    editor = admin_client.get(url("mapping-editor"), {"set_urn": set_urn}).data
    assert len(editor["source"]["nodes"]) == 3
    assert editor["reverse"] is None
    suggestions = editor["suggestions"]
    assert {s["reason"] for s in suggestions} == {"urn"}
    assert all(s["reworded"] for s in suggestions)

    accepted = admin_client.post(
        url("edit-mapping-pairs"),
        {
            "set_urn": set_urn,
            "ops": [
                {
                    "op": "add",
                    "source": s["source"],
                    "target": s["target"],
                    "relationship": s["relationship"],
                }
                for s in suggestions
            ],
        },
        format="json",
    )
    assert accepted.status_code == status.HTTP_200_OK, accepted.content
    assert accepted.data == {"status": "ok", "count": 3}

    bad = admin_client.post(
        url("edit-mapping-pairs"),
        {
            "set_urn": set_urn,
            "ops": [{"op": "add", "source": clone_urn, "target": "x"}],
        },
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST
    assert bad.data == {"error": "pairNodeNotAssessable"}

    reverse_set = admin_client.post(
        url("generate-reverse-set"), {"set_urn": set_urn}, format="json"
    )
    assert reverse_set.status_code == status.HTTP_200_OK, reverse_set.content
    assert reverse_set.data["count"] == 3

    editor = admin_client.get(url("mapping-editor"), {"set_urn": set_urn}).data
    assert editor["suggestions"] == []
    assert all(p["reworded"] for p in editor["pairs"])
    assert editor["reverse"] == {"urn": reverse_set.data["urn"], "in_sync": True}

    validation = admin_client.get(url("validate"))
    assert validation.status_code == status.HTTP_200_OK
    assert validation.data["errors"] == [], validation.data

    exported = admin_client.get(url("export"))
    assert exported.status_code == status.HTTP_200_OK
    library = yaml.safe_load(exported.content)
    sets = library["objects"]["requirement_mapping_sets"]
    assert len(sets) == 2
    assert {len(s["requirement_mappings"]) for s in sets} == {3}
    assert "reworded" not in sets[0]["requirement_mappings"][0]


@pytest.mark.django_db
def test_add_mapping_set_refuses_unknown_and_identical_frameworks(admin_client):
    draft = _create_draft(
        admin_client,
        content={"frameworks": [_framework("me", "mylib", [("a", "A", "A")])]},
    )
    url = reverse("library-drafts-add-mapping-set", args=[draft["id"]])
    same = admin_client.post(
        url,
        {
            "source_framework_urn": "urn:me:risk:framework:mylib",
            "target_framework_urn": "urn:me:risk:framework:mylib",
        },
        format="json",
    )
    assert same.status_code == status.HTTP_400_BAD_REQUEST
    missing = admin_client.post(
        url,
        {
            "source_framework_urn": "urn:me:risk:framework:mylib",
            "target_framework_urn": "urn:nobody:risk:framework:nothing",
        },
        format="json",
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND
