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
    url = lambda name: reverse(f"library-drafts-{name}", args=[draft["id"]])

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
    assert accepted.data == {"status": "ok", "count": 3, "issues": []}

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


# --- suggestions from stored mapping sets ------------------------------------


def test_compose_relationship_and_pairs():
    assert me.compose_relationship("equal", "subset") == "subset"
    assert me.compose_relationship("subset", "equal") == "subset"
    assert me.compose_relationship("subset", "subset") == "subset"
    assert me.compose_relationship("subset", "superset") is None
    assert me.compose_relationship("intersect", "intersect") is None
    assert me.compose_relationship("equal", "intersect") == "intersect"
    assert me.compose_relationship("equal", "not_related") is None
    composed = me.compose_pairs(
        [("a1", "p1", "equal"), ("a1", "p2", "subset"), ("a2", "p3", "equal")],
        [("p1", "b1", "equal"), ("p2", "b1", "equal"), ("p3", "b2", "not_related")],
    )
    # two pivots disagree on (a1, b1): intersect; a2's only chain is not_related
    assert composed == {("a1", "b1"): "intersect"}


def test_oriented_pairs_turns_a_reverse_set_around():
    sets = [
        {
            "source_framework_urn": "urn:x:risk:framework:p",
            "target_framework_urn": "urn:x:risk:framework:a",
            "requirement_mappings": [
                {
                    "source_requirement_urn": "p1",
                    "target_requirement_urn": "a1",
                    "relationship": "subset",
                }
            ],
        }
    ]
    assert me.oriented_pairs(
        sets, "urn:x:risk:framework:a", "urn:x:risk:framework:p"
    ) == [("a1", "p1", "superset")]
    assert (
        me.oriented_pairs(sets, "urn:x:risk:framework:a", "urn:x:risk:framework:z")
        == []
    )


def _store(objects, ref):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(
            {
                "urn": f"urn:acme:risk:library:{ref}",
                "locale": "en",
                "ref_id": ref,
                "name": ref,
                "version": 1,
                "packager": "acme",
                "objects": objects,
            }
        ).encode(),
        builtin=True,
    )
    assert error is None, error
    return stored


def _mapping(ref, source, target, links):
    node = lambda fw, leaf: f"urn:acme:risk:req_node:{fw}:{leaf}"
    return {
        "urn": f"urn:acme:risk:req_mapping_set:{ref}",
        "ref_id": ref,
        "name": ref,
        "source_framework_urn": f"urn:acme:risk:framework:{source}",
        "target_framework_urn": f"urn:acme:risk:framework:{target}",
        "requirement_mappings": [
            {
                "source_requirement_urn": node(source, s),
                "target_requirement_urn": node(target, t),
                "relationship": rel,
            }
            for s, t, rel in links
        ],
    }


@pytest.mark.django_db
def test_clone_gets_suggestions_from_shipped_and_chained_mappings(admin_client):
    nodes = [("x1", "X1", "First"), ("x2", "X2", "Second")]
    a = _store({"framework": _framework("acme", "a", nodes, "A", "Alpha")}, "a")
    for ref in ("b", "c", "p"):
        _store({"framework": _framework("acme", ref, nodes, ref.upper())}, ref)
    _store(
        {
            "requirement_mapping_sets": [
                _mapping("a-to-b", "a", "b", [("x1", "x2", "subset")])
            ]
        },
        "map-a-b",
    )
    # A→P only exists as P→A: it must be turned around
    _store(
        {
            "requirement_mapping_sets": [
                _mapping(
                    "p-to-a",
                    "p",
                    "a",
                    [("x1", "x1", "equal"), ("x2", "x2", "superset")],
                )
            ]
        },
        "map-p-a",
    )
    _store(
        {
            "requirement_mapping_sets": [
                _mapping(
                    "p-to-c",
                    "p",
                    "c",
                    [("x1", "x2", "equal"), ("x2", "x1", "subset")],
                )
            ]
        },
        "map-p-c",
    )
    draft = _create_draft(admin_client, content={})
    url = lambda name: reverse(f"library-drafts-{name}", args=[draft["id"]])
    cloned = admin_client.post(
        url("import-objects"),
        {"source": str(a.id), "object_types": ["frameworks"]},
        format="json",
    )
    assert cloned.status_code == status.HTTP_200_OK, cloned.content
    clone = cloned.data["draft"]["content"]["frameworks"][0]
    clone_node = {n["ref_id"]: n["urn"] for n in clone["requirement_nodes"]}

    def suggestions_to(target):
        created = admin_client.post(
            url("add-mapping-set"),
            {
                "source_framework_urn": clone["urn"],
                "target_framework_urn": f"urn:acme:risk:framework:{target}",
            },
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, created.content
        editor = admin_client.get(
            url("mapping-editor"), {"set_urn": created.data["urn"]}
        )
        return {
            (s["source"], s["target"].rsplit(":", 1)[1]): (
                s["relationship"],
                s["reason"],
                s["via"],
            )
            for s in editor.data["suggestions"]
            # the fixtures share item ids, so the structural arms fire too
            if s["reason"] in ("mapping", "via")
        }

    # direct: the shipped A→B set, rebased onto the clone's nodes
    assert suggestions_to("b") == {
        (clone_node["X1"], "x2"): ("subset", "mapping", "map-a-b")
    }
    # chained: clone→A (tails) →P (reversed) →C
    assert suggestions_to("c") == {
        (clone_node["X1"], "x2"): ("equal", "via", "p"),
        (clone_node["X2"], "x1"): ("subset", "via", "p"),
    }


# --- wording hints and consistency checks ------------------------------------


def _node(urn, name, description=""):
    return {"urn": urn, "ref_id": "", "name": name, "description": description}


def test_wording_hints_rank_shared_rare_words_and_drop_noise():
    sources = [
        _node("s:backup", "Backups are tested and restorable"),
        _node("s:crypto", "Cryptographic keys are rotated"),
        _node("s:fr", "Les sauvegardes sont testées"),
    ]
    targets = [
        _node("t:keys", "Key management", "Cryptographic keys have a lifecycle"),
        _node("t:backup", "Information backup", "Backup copies are tested"),
        _node("t:hr", "Screening", "Candidates are screened before hiring"),
    ]
    hints = me.wording_hints(sources, targets)
    assert hints["s:backup"][0][0] == "t:backup"
    assert hints["s:crypto"][0][0] == "t:keys"
    # nothing in common: no hint rather than noise
    assert "s:fr" not in hints
    assert all(score >= me.HINT_MIN_SCORE for h in hints.values() for _, score in h)


def test_mapping_issues_flags_each_inconsistency():
    def pair(s, t, rel):
        return {
            "source_requirement_urn": s,
            "target_requirement_urn": t,
            "relationship": rel,
        }

    mapping_set = {
        "requirement_mappings": [
            pair("a", "x", "equal"),
            pair("a", "x", "subset"),
            pair("b", "y", "intersect"),
            pair("b", "y", "intersect"),
            pair("c", "y", "equal"),
            pair("c", "z", "equal"),
            pair("gone", "z", "intersect"),
        ]
    }
    reverse_set = {"requirement_mappings": [pair("y", "b", "subset")]}
    issues = me.mapping_issues(
        mapping_set, {"a", "b", "c"}, {"x", "y", "z"}, reverse_set
    )
    found = {(i["code"], i["source"], i["target"]): i["detail"] for i in issues}
    assert found == {
        ("pairConflict", "a", "x"): ["equal", "subset"],
        ("pairDuplicate", "b", "y"): ["intersect"],
        ("pairNodeMissing", "gone", "z"): ["source"],
        ("equalFanOut", "c", None): ["y", "z"],
        # reverse says y⊂b, i.e. b⊃y, while this set says b∩y
        ("reverseConflict", "b", "y"): ["intersect", "superset"],
    }
    assert me.mapping_issues({"requirement_mappings": []}) == []


@pytest.mark.django_db
def test_editor_and_validate_report_conflicting_pairs(admin_client):
    framework = _framework("me", "mylib", [("a", "A", "Alpha"), ("b", "B", "Beta")])
    target = _framework("me", "other", [("x", "X", "Alpha"), ("y", "Y", "Gamma")])
    node = lambda fw, leaf: f"urn:me:risk:req_node:{fw}:{leaf}"
    mapping_set = {
        "urn": "urn:me:risk:req_mapping_set:mylib:m",
        "ref_id": "m",
        "name": "m",
        "source_framework_urn": framework["urn"],
        "target_framework_urn": target["urn"],
        "requirement_mappings": [
            {
                "source_requirement_urn": node("mylib", "a"),
                "target_requirement_urn": node("other", "x"),
                "relationship": rel,
            }
            for rel in ("equal", "subset")
        ],
    }
    draft = _create_draft(
        admin_client,
        content={
            "frameworks": [framework, target],
            "requirement_mapping_sets": [mapping_set],
        },
    )
    url = lambda name: reverse(f"library-drafts-{name}", args=[draft["id"]])

    validation = admin_client.get(url("validate")).data
    assert any(
        "conflicting relationships (equal, subset)" in e for e in validation["errors"]
    )

    editor = admin_client.get(
        url("mapping-editor"), {"set_urn": mapping_set["urn"]}
    ).data
    assert [i["code"] for i in editor["issues"]] == ["pairConflict"]
    # B "Beta" shares no word with any target; A "Alpha" matches X "Alpha"
    assert editor["hints"] == {node("mylib", "a"): [[node("other", "x"), 1.0]]}

    # choosing the relationship resolves the conflict
    fixed = admin_client.post(
        url("edit-mapping-pairs"),
        {
            "set_urn": mapping_set["urn"],
            "ops": [
                {
                    "op": "update",
                    "source": node("mylib", "a"),
                    "target": node("other", "x"),
                    "relationship": "equal",
                }
            ],
        },
        format="json",
    )
    assert fixed.status_code == status.HTTP_200_OK, fixed.content
    assert fixed.data["issues"] == [] and fixed.data["count"] == 1

    # a contradiction between both directions is reported once
    regenerated = admin_client.post(
        url("generate-reverse-set"), {"set_urn": mapping_set["urn"]}, format="json"
    )
    assert regenerated.status_code == status.HTTP_200_OK, regenerated.content
    admin_client.post(
        url("edit-mapping-pairs"),
        {
            "set_urn": mapping_set["urn"],
            "ops": [
                {
                    "op": "update",
                    "source": node("mylib", "a"),
                    "target": node("other", "x"),
                    "relationship": "intersect",
                }
            ],
        },
        format="json",
    )
    errors = admin_client.get(url("validate")).data["errors"]
    assert sum("reverse set says" in e for e in errors) == 1, errors


def test_pair_error_code_never_echoes_the_exception():
    assert me.pair_error_code(BuilderError("pairNotFound")) == "pairNotFound"
    assert me.pair_error_code(BuilderError("urn:x leaked detail")) == "invalidPairOps"


def test_edits_keep_conflicts_on_untouched_pairs():
    def pair(s, t, rel):
        return {
            "source_requirement_urn": s,
            "target_requirement_urn": t,
            "relationship": rel,
        }

    mapping_set = {
        "requirement_mappings": [
            pair("a", "x", "equal"),
            pair("a", "x", "subset"),
            pair("b", "y", "intersect"),
        ]
    }
    # editing b→y leaves the a→x conflict exactly as recorded
    pairs = me.apply_pair_ops(
        mapping_set,
        [{"op": "update", "source": "b", "target": "y", "relationship": "equal"}],
        {"a", "b"},
        {"x", "y"},
    )
    assert [(p["source_requirement_urn"], p["relationship"]) for p in pairs] == [
        ("a", "equal"),
        ("a", "subset"),
        ("b", "equal"),
    ]
    # addressing a→x collapses it to the chosen relationship
    mapping_set["requirement_mappings"] = pairs
    pairs = me.apply_pair_ops(
        mapping_set,
        [{"op": "update", "source": "a", "target": "x", "relationship": "subset"}],
        {"a", "b"},
        {"x", "y"},
    )
    assert [(p["source_requirement_urn"], p["relationship"]) for p in pairs] == [
        ("a", "subset"),
        ("b", "equal"),
    ]


def test_splash_nodes_and_malformed_relationships():
    framework = _framework("me", "f", [("a", "A", "Alpha"), ("b", "B", "Beta")])
    framework["requirement_nodes"][1]["display_mode"] = "splash"
    assert [n["ref_id"] for n in me.assessable_nodes(framework)] == ["B"]
    broken = {
        "requirement_mappings": [
            {
                "source_requirement_urn": "a",
                "target_requirement_urn": "b",
                "relationship": [],
            }
        ]
    }
    assert me.reverse_mappings(broken)[0]["relationship"] == []
    assert me.mapping_issues(broken, reverse_set=broken) is not None
    assert me.compose_relationship([], "equal") is None
