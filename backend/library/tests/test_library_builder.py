"""
Tests for the library builder (LibraryDraft + library/builder.py).

Covered:
- document helpers: normalization, URN minting/rebasing (incl. question dict
  keys and parent_urn links), selective extraction policies (strip/pull/
  reference), merge collisions
- round-trip parity: shipped library YAML → draft (adopt) → exported YAML
- API lifecycle: create → edit (identity rename rebases the document) →
  publish (= load through the existing stored-library path) → identity
  frozen → re-publish (update-by-URN with version bump)
- adopt vs clone gating (builtin libraries cannot be adopted)
"""

from pathlib import Path

import pytest
import yaml
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    Framework,
    LibraryDraft,
    LoadedLibrary,
    ReferenceControl,
    RequirementNode,
    RiskMatrix,
    StoredLibrary,
    Threat,
)
from iam.models import Folder, Permission, Role, RoleAssignment, User, UserGroup
from library import builder

LIBRARIES_DIR = Path(__file__).resolve().parent.parent / "libraries"

SOURCE_LIBRARY = {
    "urn": "urn:acme:risk:library:source-lib",
    "locale": "en",
    "ref_id": "source-lib",
    "name": "Source library",
    "description": "Fixture library for extraction tests",
    "version": 3,
    "publication_date": "2025-01-01",
    "provider": "ACME",
    "packager": "acme",
    "objects": {
        "threats": [
            {
                "urn": "urn:acme:risk:threat:source-lib:t1",
                "ref_id": "T1",
                "name": "Threat 1",
            },
            {
                "urn": "urn:acme:risk:threat:source-lib:t2",
                "ref_id": "T2",
                "name": "Threat 2",
            },
        ],
        "reference_controls": [
            {
                "urn": "urn:acme:risk:reference_control:source-lib:c1",
                "ref_id": "C1",
                "name": "Control 1",
                "category": "technical",
            },
        ],
        "framework": {
            "urn": "urn:acme:risk:framework:source-lib",
            "ref_id": "SRC",
            "name": "Source framework",
            "requirement_nodes": [
                {
                    "urn": "urn:acme:risk:req_node:source-lib:a",
                    "ref_id": "A",
                    "assessable": False,
                    "depth": 1,
                    "name": "Chapter A",
                },
                {
                    "urn": "urn:acme:risk:req_node:source-lib:a.1",
                    "ref_id": "A.1",
                    "assessable": True,
                    "depth": 2,
                    "parent_urn": "urn:acme:risk:req_node:source-lib:a",
                    "name": "Requirement A.1",
                    "threats": ["urn:acme:risk:threat:source-lib:t1"],
                    "reference_controls": [
                        "urn:acme:risk:reference_control:source-lib:c1",
                        "urn:other:risk:reference_control:ext-lib:x1",
                    ],
                    "questions": {
                        "urn:acme:risk:req_node:source-lib:a.1:question:1": {
                            "type": "unique_choice",
                            "text": "Is it done?",
                            "choices": [
                                {
                                    "urn": "urn:acme:risk:req_node:source-lib:a.1:question:1:choice:1",
                                    "value": "Yes",
                                },
                            ],
                        }
                    },
                },
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Document helpers (no DB)
# ---------------------------------------------------------------------------


def test_normalize_objects_canonicalizes_deprecated_fields():
    objects = builder.normalize_objects(SOURCE_LIBRARY["objects"])
    assert "framework" not in objects
    assert isinstance(objects["frameworks"], list)
    assert objects["frameworks"][0]["ref_id"] == "SRC"
    # untouched fields survive
    assert len(objects["threats"]) == 2


def test_rebase_document_regenerates_the_whole_urn_family():
    rebased = builder.rebase_document(SOURCE_LIBRARY["objects"], "me", "newlib")
    framework = rebased["frameworks"][0]
    assert framework["urn"] == "urn:me:risk:framework:newlib"
    nodes = {node["ref_id"]: node for node in framework["requirement_nodes"]}
    assert nodes["A"]["urn"] == "urn:me:risk:req_node:newlib:a"
    assert nodes["A.1"]["urn"] == "urn:me:risk:req_node:newlib:a.1"
    assert nodes["A.1"]["parent_urn"] == "urn:me:risk:req_node:newlib:a"
    # references to rebased objects follow
    assert nodes["A.1"]["threats"] == ["urn:me:risk:threat:newlib:t1"]
    # external references are preserved
    assert (
        "urn:other:risk:reference_control:ext-lib:x1"
        in nodes["A.1"]["reference_controls"]
    )
    # question dict keys and choice URNs follow the node rebase
    question_urn = "urn:me:risk:req_node:newlib:a.1:question:1"
    assert question_urn in nodes["A.1"]["questions"]
    choice = nodes["A.1"]["questions"][question_urn]["choices"][0]
    assert choice["urn"] == f"{question_urn}:choice:1"


def test_extract_strip_policy_drops_unselected_internal_references():
    result = builder.extract_objects(
        source_content=SOURCE_LIBRARY["objects"],
        source_library_urn=SOURCE_LIBRARY["urn"],
        source_dependencies=["urn:other:risk:library:ext-lib"],
        target_packager="me",
        target_ref_id="fork",
        selected_types=["frameworks"],
        resolve_owner=lambda urn: None,
    )
    node = result["objects"]["frameworks"][0]["requirement_nodes"][1]
    assert node["threats"] == []
    # the external reference is kept, unresolved → source dependencies carried
    assert node["reference_controls"] == ["urn:other:risk:reference_control:ext-lib:x1"]
    assert result["dependencies"] == ["urn:other:risk:library:ext-lib"]
    assert {"threats", "reference_controls"} & set(result["objects"]) == set()
    stripped_refs = {entry["ref"] for entry in result["report"]["stripped"]}
    assert stripped_refs == {
        "urn:acme:risk:threat:source-lib:t1",
        "urn:acme:risk:reference_control:source-lib:c1",
    }


def test_extract_pull_policy_extracts_the_closure():
    result = builder.extract_objects(
        source_content=SOURCE_LIBRARY["objects"],
        source_library_urn=SOURCE_LIBRARY["urn"],
        source_dependencies=[],
        target_packager="me",
        target_ref_id="fork",
        selected_types=["frameworks"],
        default_policy=builder.POLICY_PULL,
        resolve_owner=lambda urn: "urn:other:risk:library:ext-lib",
    )
    node = result["objects"]["frameworks"][0]["requirement_nodes"][1]
    assert node["threats"] == ["urn:me:risk:threat:fork:t1"]
    assert node["reference_controls"] == [
        "urn:me:risk:reference_control:fork:c1",
        "urn:other:risk:reference_control:ext-lib:x1",
    ]
    # only the referenced threat is pulled, not the whole list
    assert [t["urn"] for t in result["objects"]["threats"]] == [
        "urn:me:risk:threat:fork:t1"
    ]
    assert result["dependencies"] == ["urn:other:risk:library:ext-lib"]


def test_extract_reference_policy_keeps_urn_and_adds_source_dependency():
    result = builder.extract_objects(
        source_content=SOURCE_LIBRARY["objects"],
        source_library_urn=SOURCE_LIBRARY["urn"],
        source_dependencies=[],
        target_packager="me",
        target_ref_id="fork",
        selected_types=["frameworks"],
        default_policy=builder.POLICY_REFERENCE,
        resolve_owner=lambda urn: "urn:other:risk:library:ext-lib",
    )
    node = result["objects"]["frameworks"][0]["requirement_nodes"][1]
    assert node["threats"] == ["urn:acme:risk:threat:source-lib:t1"]
    assert "urn:acme:risk:library:source-lib" in result["dependencies"]


def test_extract_rejects_non_dict_reference_policies():
    """`policies` comes straight from the request body: a list or scalar must
    raise BuilderError (→ 400), not AttributeError on .items() (→ 500)."""
    with pytest.raises(builder.BuilderError):
        builder.extract_objects(
            source_content=SOURCE_LIBRARY["objects"],
            source_library_urn=SOURCE_LIBRARY["urn"],
            source_dependencies=[],
            target_packager="me",
            target_ref_id="fork",
            selected_types=["frameworks"],
            per_urn_policies=["strip"],
            resolve_owner=lambda urn: None,
        )


@pytest.mark.django_db
def test_validation_rejects_cross_framework_parent_urn():
    """parent_urn must stay inside its own framework's tree. A multi-framework
    document (reachable through import-yaml or adopt) used to pass because the
    check ran against the document-wide node set."""
    draft = LibraryDraft(
        name="multi",
        packager="me",
        ref_id="multi",
        version=1,
        urn="urn:me:risk:library:multi",
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:multi-a",
                    "ref_id": "A",
                    "name": "A",
                    "requirement_nodes": [
                        {
                            "urn": "urn:me:risk:req_node:multi-a:root",
                            "assessable": False,
                        }
                    ],
                },
                {
                    "urn": "urn:me:risk:framework:multi-b",
                    "ref_id": "B",
                    "name": "B",
                    "requirement_nodes": [
                        {
                            "urn": "urn:me:risk:req_node:multi-b:child",
                            "assessable": True,
                            # Crosses into framework A's tree: must be rejected.
                            "parent_urn": "urn:me:risk:req_node:multi-a:root",
                        }
                    ],
                },
            ]
        },
    )
    validation = builder.validate_draft_document(draft)
    assert any(
        "parent_urn" in error and "multi-a:root" in error
        for error in validation["errors"]
    ), validation["errors"]


def test_extract_individual_selection_of_leaf_objects_is_clean():
    result = builder.extract_objects(
        source_content=SOURCE_LIBRARY["objects"],
        source_library_urn=SOURCE_LIBRARY["urn"],
        source_dependencies=[],
        target_packager="me",
        target_ref_id="fork",
        selected_urns=["urn:acme:risk:threat:source-lib:t2"],
        resolve_owner=lambda urn: None,
    )
    assert result["objects"] == {
        "threats": [
            {
                "urn": "urn:me:risk:threat:fork:t2",
                "ref_id": "T2",
                "name": "Threat 2",
            }
        ]
    }
    assert result["dependencies"] == []


def test_check_document_shape_reports_structural_garbage():
    # a well-formed document (incl. questions/choices/mappings) passes
    assert (
        builder.check_document_shape(
            builder.normalize_objects(SOURCE_LIBRARY["objects"])
        )
        == []
    )

    errors = builder.check_document_shape(
        {
            "threats": "hello",
            "reference_controls": [42],
            "preset": [],
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:x",
                    "requirement_nodes": [
                        {
                            "urn": {"nested": True},
                            "threats": [{"not": "a string"}],
                            "questions": ["not-a-dict"],
                        }
                    ],
                }
            ],
            "requirement_mapping_sets": [
                {"source_framework_urn": 7, "requirement_mappings": "nope"}
            ],
            "someone_elses_extension_field": "left alone",
        }
    )
    assert "content.threats: must be a list of objects" in errors
    assert "content.reference_controls[0]: must be an object" in errors
    assert "content.preset: must be an object" in errors
    assert any("requirement_nodes[0].urn" in error for error in errors)
    assert any("requirement_nodes[0].threats[0]" in error for error in errors)
    assert any("requirement_nodes[0].questions" in error for error in errors)
    assert any("source_framework_urn" in error for error in errors)
    assert any("requirement_mappings" in error for error in errors)
    # unknown fields are tolerated (round-trip)
    assert not any("extension_field" in error for error in errors)


def test_merge_objects_reports_collisions():
    content = {"threats": [{"urn": "urn:me:risk:threat:fork:t2", "ref_id": "T2"}]}
    incoming = {"threats": [{"urn": "urn:me:risk:threat:fork:t2", "ref_id": "T2"}]}
    with pytest.raises(builder.BuilderError):
        builder.merge_objects(content, incoming)
    merged = builder.merge_objects(content, incoming, overwrite=True)
    assert len(merged["threats"]) == 1


# ---------------------------------------------------------------------------
# Round-trip parity: YAML → draft → YAML
# ---------------------------------------------------------------------------


@pytest.mark.django_db  # instantiating LibraryDraft resolves the folder default
@pytest.mark.parametrize(
    "library_file",
    [
        "adobe-ccf-v5.yaml",
        "critical_risk_matrix_5x5.yaml",
        "key-reference-controls.yaml",
    ],
)
def test_round_trip_parity_with_shipped_libraries(library_file):
    """Adopting a library YAML then exporting it must lose nothing.

    Field spellings are canonicalized (framework → frameworks); the parity
    check therefore compares normalized objects and the library metadata.
    """
    library = yaml.safe_load((LIBRARIES_DIR / library_file).read_bytes())
    draft = LibraryDraft(
        name=library["name"],
        description=library.get("description"),
        packager=library.get("packager"),
        ref_id=library.get("ref_id"),
        locale=library.get("locale", "en"),
        version=library["version"],
        provider=library.get("provider"),
        copyright=library.get("copyright"),
        publication_date=library.get("publication_date"),
        annotation=library.get("annotation"),
        translations=library.get("translations", {}),
        dependencies=library.get("dependencies", []),
        labels=library.get("labels", []),
        content=builder.normalize_objects(library["objects"]),
        urn=library["urn"],
    )
    exported = draft.to_library_dict()
    for field in (
        "urn",
        "locale",
        "ref_id",
        "name",
        "description",
        "copyright",
        "version",
        "provider",
        "packager",
    ):
        if library.get(field) is not None:
            assert exported[field] == library[field], field
    assert exported.get("dependencies", []) == library.get("dependencies", [])
    assert exported["objects"] == builder.normalize_objects(library["objects"])
    # the export must still be a storable library
    yaml.safe_dump(exported, sort_keys=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# API lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture
def app_config(db):
    startup(sender=None, **{})


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser("admin@builder-tests.com", is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return client


def _create_draft(admin_client, **overrides) -> dict:
    payload = {
        "name": "My library",
        "packager": "me",
        "ref_id": "mylib",
        "content": {
            "threats": [
                {
                    "urn": "urn:me:risk:threat:mylib:t1",
                    "ref_id": "T1",
                    "name": "My threat",
                }
            ]
        },
        **overrides,
    }
    response = admin_client.post(reverse("library-drafts-list"), payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return admin_client.get(
        reverse("library-drafts-detail", args=[response.data["id"]])
    ).data


@pytest.mark.django_db
def test_create_draft_rejects_non_urn_safe_identity(admin_client):
    response = admin_client.post(
        reverse("library-drafts-list"),
        {"name": "Bad", "packager": "Not A Slug", "ref_id": "ok"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_identity_rename_rebases_the_document(admin_client):
    draft = _create_draft(admin_client)
    response = admin_client.patch(
        reverse("library-drafts-detail", args=[draft["id"]]),
        {"ref_id": "renamed"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    updated = admin_client.get(
        reverse("library-drafts-detail", args=[draft["id"]])
    ).data
    assert updated["urn"] == "urn:me:risk:library:renamed"
    assert updated["content"]["threats"][0]["urn"] == "urn:me:risk:threat:renamed:t1"


@pytest.mark.django_db
def test_malformed_content_is_rejected_at_every_door(admin_client):
    # Door 1: draft save — a 400 naming the offending path, not a stored
    # time bomb.
    draft = _create_draft(admin_client)
    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    bad_patch = admin_client.patch(
        detail_url, {"content": {"threats": "hello"}}, format="json"
    )
    assert bad_patch.status_code == status.HTTP_400_BAD_REQUEST
    assert "content.threats" in str(bad_patch.data)
    # the draft is untouched, and validate/publish still answer cleanly
    validate = admin_client.get(reverse("library-drafts-validate", args=[draft["id"]]))
    assert validate.status_code == status.HTTP_200_OK

    # Doors 2 and 3: adopt / clone from a structurally malformed stored
    # library (store_library_content only checks top-level fields).
    malformed_library = {
        **SOURCE_LIBRARY,
        "urn": "urn:acme:risk:library:malformed-lib",
        "ref_id": "malformed-lib",
        "name": "Malformed library",
        "objects": {"threats": ["not-an-object"]},
    }
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(malformed_library).encode()
    )
    assert error is None, error
    adopted = admin_client.post(
        reverse("library-drafts-adopt"),
        {"stored_library": str(stored.id)},
        format="json",
    )
    assert adopted.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert adopted.data["error"] == "adoptInvalidContent"
    imported = admin_client.post(
        reverse("library-drafts-import-objects", args=[draft["id"]]),
        {"source": str(stored.id)},
        format="json",
    )
    assert imported.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert imported.data["error"] == "sourceLibraryMalformed"


@pytest.mark.django_db
def test_check_identity_requires_draft_creation_permission(app_config):
    """Any authenticated account without library permissions (e.g. a
    third-party respondent) must not be able to probe the corpus."""
    user = User.objects.create_user("nobody@builder-tests.com")
    user.is_published = True
    user.save()
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    response = client.get(
        reverse("library-drafts-check-identity"),
        {"packager": "acme", "ref_id": "source-lib"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_check_identity_reports_conflicts_with_stored_libraries(admin_client):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(SOURCE_LIBRARY).encode()
    )
    assert error is None, error
    response = admin_client.get(
        reverse("library-drafts-check-identity"),
        {"packager": "acme", "ref_id": "source-lib"},
    )
    assert response.status_code == status.HTTP_200_OK
    kinds = {conflict["kind"] for conflict in response.data["conflicts"]}
    assert "stored_library" in kinds


@pytest.mark.django_db
def test_publish_loads_through_the_existing_import_path(admin_client):
    draft = _create_draft(
        admin_client,
        content={
            "threats": [
                {
                    "urn": "urn:me:risk:threat:mylib:t1",
                    "ref_id": "T1",
                    "name": "My threat",
                }
            ],
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:mylib",
                    "ref_id": "MYFW",
                    "name": "My framework",
                    "requirement_nodes": [
                        {
                            "urn": "urn:me:risk:req_node:mylib:r1",
                            "ref_id": "R1",
                            "name": "Requirement 1",
                            "assessable": True,
                            "depth": 1,
                            "threats": ["urn:me:risk:threat:mylib:t1"],
                        }
                    ],
                }
            ],
        },
    )
    response = admin_client.post(
        reverse("library-drafts-publish", args=[draft["id"]]), {}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    assert response.data["status"] == "success"

    # live objects exist, created by the loader
    library = LoadedLibrary.objects.get(urn="urn:me:risk:library:mylib")
    framework = Framework.objects.get(urn="urn:me:risk:framework:mylib")
    assert framework.library == library
    node = RequirementNode.objects.get(urn="urn:me:risk:req_node:mylib:r1")
    assert [t.urn for t in node.threats.all()] == ["urn:me:risk:threat:mylib:t1"]

    # identity is now frozen
    frozen = admin_client.patch(
        reverse("library-drafts-detail", args=[draft["id"]]),
        {"ref_id": "other"},
        format="json",
    )
    assert frozen.status_code == status.HTTP_400_BAD_REQUEST

    # re-publishing unchanged content is refused outright — no version bump
    # is suggested for identical bytes
    again = admin_client.post(
        reverse("library-drafts-publish", args=[draft["id"]]), {}, format="json"
    )
    assert again.status_code == status.HTTP_409_CONFLICT
    assert again.data["error"] == "nothingToPublish"

    # …changed content with bump_version updates the same URN in place
    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    current = admin_client.get(detail_url).data
    content = current["content"]
    content["frameworks"][0]["name"] = "My framework v2"
    patched = admin_client.patch(detail_url, {"content": content}, format="json")
    assert patched.status_code == status.HTTP_200_OK, patched.content
    republished = admin_client.post(
        reverse("library-drafts-publish", args=[draft["id"]]),
        {"bump_version": True},
        format="json",
    )
    assert republished.status_code == status.HTTP_200_OK, republished.content
    assert republished.data["version"] == 2
    framework.refresh_from_db()
    assert framework.name == "My framework v2"
    assert Framework.objects.filter(urn="urn:me:risk:framework:mylib").count() == 1


@pytest.mark.django_db
def test_publish_score_change_retry_keeps_the_same_version(admin_client):
    """The 409 score_change_detected contract: retrying with just the chosen
    strategy must succeed at the SAME version — the failed attempt leaves no
    stored row behind to trip the version guard."""
    from core.models import ComplianceAssessment
    from iam.models import Folder
    from core.models import Perimeter

    draft = _create_draft(
        admin_client,
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:mylib",
                    "ref_id": "MYFW",
                    "name": "My framework",
                    "min_score": 0,
                    "max_score": 100,
                    "requirement_nodes": [
                        {
                            "urn": "urn:me:risk:req_node:mylib:r1",
                            "ref_id": "R1",
                            "name": "Requirement 1",
                            "assessable": True,
                            "depth": 1,
                        }
                    ],
                }
            ],
        },
    )
    publish_url = reverse("library-drafts-publish", args=[draft["id"]])
    assert admin_client.post(publish_url, {}, format="json").status_code == 200

    # An audit pinned to the published score boundaries makes a boundary
    # change require a migration strategy.
    framework = Framework.objects.get(urn="urn:me:risk:framework:mylib")
    perimeter = Perimeter.objects.create(name="P1", folder=Folder.get_root_folder())
    ComplianceAssessment.objects.create(
        name="Audit",
        perimeter=perimeter,
        framework=framework,
        min_score=0,
        max_score=100,
        folder=Folder.get_root_folder(),
    )

    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    current = admin_client.get(detail_url).data
    content = current["content"]
    content["frameworks"][0]["max_score"] = 5
    assert (
        admin_client.patch(
            detail_url, {"content": content, "version": 2}, format="json"
        ).status_code
        == 200
    )

    conflict = admin_client.post(publish_url, {}, format="json")
    assert conflict.status_code == status.HTTP_409_CONFLICT, conflict.content
    assert conflict.data["error"] == "score_change_detected"
    assert {s["action"] for s in conflict.data["strategies"]} >= {"clamp"}
    # all-or-nothing: the failed attempt left no stored v2 behind
    assert not StoredLibrary.objects.filter(
        urn="urn:me:risk:library:mylib", version=2
    ).exists()

    # the documented retry — same version, strategy only — succeeds
    retried = admin_client.post(publish_url, {"strategy": "clamp"}, format="json")
    assert retried.status_code == status.HTTP_200_OK, retried.content
    assert retried.data["version"] == 2
    assert LoadedLibrary.objects.get(urn="urn:me:risk:library:mylib").version == 2


@pytest.mark.django_db
def test_publish_refuses_a_draft_with_unresolved_references(admin_client):
    draft = _create_draft(
        admin_client,
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:mylib",
                    "ref_id": "MYFW",
                    "name": "My framework",
                    "requirement_nodes": [
                        {
                            "urn": "urn:me:risk:req_node:mylib:r1",
                            "ref_id": "R1",
                            "name": "Requirement 1",
                            "assessable": True,
                            "depth": 1,
                            "threats": ["urn:nowhere:risk:threat:ghost:t1"],
                        }
                    ],
                }
            ],
        },
    )
    response = admin_client.post(
        reverse("library-drafts-publish", args=[draft["id"]]), {}, format="json"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.data["error"] == "draftValidationFailed"
    assert not StoredLibrary.objects.filter(urn="urn:me:risk:library:mylib").exists()


@pytest.mark.django_db
def test_adopt_preserves_identity_and_freezes_it(admin_client):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(SOURCE_LIBRARY).encode()
    )
    assert error is None, error
    response = admin_client.post(
        reverse("library-drafts-adopt"),
        {"stored_library": str(stored.id)},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    draft = response.data
    assert draft["urn"] == "urn:acme:risk:library:source-lib"
    assert draft["identity_locked"] is True
    assert draft["version"] == 3
    assert len(draft["content"]["frameworks"]) == 1

    # a second identity-preserving draft is refused
    again = admin_client.post(
        reverse("library-drafts-adopt"),
        {"stored_library": str(stored.id)},
        format="json",
    )
    assert again.status_code == status.HTTP_409_CONFLICT

    # the draft body stays editable, its identity does not
    rename = admin_client.patch(
        reverse("library-drafts-detail", args=[draft["id"]]),
        {"name": "Maintained in the builder"},
        format="json",
    )
    assert rename.status_code == status.HTTP_200_OK, rename.content
    frozen = admin_client.patch(
        reverse("library-drafts-detail", args=[draft["id"]]),
        {"packager": "someone-else"},
        format="json",
    )
    assert frozen.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_adopt_refuses_builtin_libraries(admin_client):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(SOURCE_LIBRARY).encode(), builtin=True
    )
    assert error is None, error
    response = admin_client.post(
        reverse("library-drafts-adopt"),
        {"stored_library": str(stored.id)},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "builtinLibrariesCannotBeAdopted"


@pytest.mark.django_db
def test_import_objects_clones_from_a_builtin_source(admin_client):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(SOURCE_LIBRARY).encode(), builtin=True
    )
    assert error is None, error
    draft = _create_draft(admin_client, content={})
    response = admin_client.post(
        reverse("library-drafts-import-objects", args=[draft["id"]]),
        {
            "source": str(stored.id),
            "object_types": ["frameworks"],
            "default_policy": "pull",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    content = response.data["draft"]["content"]
    assert content["frameworks"][0]["urn"] == "urn:me:risk:framework:mylib"
    node = content["frameworks"][0]["requirement_nodes"][1]
    assert node["threats"] == ["urn:me:risk:threat:mylib:t1"]
    # the external control reference was kept and turned into a dependency need
    assert "urn:other:risk:reference_control:ext-lib:x1" in node["reference_controls"]


# ---------------------------------------------------------------------------
# Framework editor bridge (library framework object ⟷ editor doc)
# ---------------------------------------------------------------------------


def test_framework_editor_doc_round_trip_preserves_everything():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    assert doc["framework_meta"]["name"] == "Source framework"
    assert doc["framework_meta"]["urn_namespace"] == "acme"
    assert len(doc["nodes"]) == 2
    assert len(doc["questions"]) == 1
    assert len(doc["choices"]) == 1

    rebuilt = fw_editor.editor_doc_to_framework_object(doc, existing=original)
    assert rebuilt["urn"] == original["urn"]
    nodes = {node["ref_id"]: node for node in rebuilt["requirement_nodes"]}
    node = nodes["A.1"]
    assert node["urn"] == "urn:acme:risk:req_node:source-lib:a.1"
    assert node["parent_urn"] == "urn:acme:risk:req_node:source-lib:a"
    # fields the editor does not model survive the round trip
    assert node["threats"] == ["urn:acme:risk:threat:source-lib:t1"]
    assert node["reference_controls"] == [
        "urn:acme:risk:reference_control:source-lib:c1",
        "urn:other:risk:reference_control:ext-lib:x1",
    ]
    # questions dict round-trips (same URN key, same choices)
    question = node["questions"]["urn:acme:risk:req_node:source-lib:a.1:question:1"]
    assert question["text"] == "Is it done?"
    assert question["choices"][0]["value"] == "Yes"


def test_framework_editor_doc_mints_urns_for_new_items():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    # A node created in the editor: local id, client-minted urn under a
    # foreign namespace, plus a question without urn.
    doc["nodes"].append(
        {
            "id": "tmp-node-1",
            "urn": "urn:custom:risk:req_node:whatever:b",
            "ref_id": "B",
            "name": "New requirement",
            "parent_urn": "urn:acme:risk:req_node:source-lib:a",
            "assessable": True,
            "order_id": 2,
        }
    )
    doc["questions"].append(
        {
            "id": "tmp-q-1",
            "urn": None,
            "ref_id": None,
            "text": "New question?",
            "type": "unique_choice",
            "order": 0,
            "requirement_node_id": "tmp-node-1",
        }
    )
    doc["choices"].append(
        {
            "id": "tmp-c-1",
            "urn": None,
            "value": "Yes",
            "order": 0,
            "question_id": "tmp-q-1",
        }
    )
    rebuilt = fw_editor.editor_doc_to_framework_object(doc, existing=original)
    nodes = {node["ref_id"]: node for node in rebuilt["requirement_nodes"]}
    new_node = nodes["B"]
    assert new_node["urn"] == "urn:acme:risk:req_node:source-lib:b"
    assert new_node["parent_urn"] == "urn:acme:risk:req_node:source-lib:a"
    question_urns = list(new_node["questions"].keys())
    assert question_urns == ["urn:acme:risk:req_node:source-lib:b:question:1"]
    choice = new_node["questions"][question_urns[0]]["choices"][0]
    assert choice["urn"] == "urn:acme:risk:req_node:source-lib:b:question:1:choice:1"


def test_new_question_never_overwrites_an_existing_one():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    node_urn = "urn:acme:risk:req_node:source-lib:a.1"
    # A question added in the editor: no urn, no ref_id — its minted leaf
    # must not collide with the node's existing ...question:1.
    doc["questions"].append(
        {
            "id": "tmp-q-new",
            "urn": None,
            "ref_id": None,
            "text": "Second question?",
            "type": "unique_choice",
            "order": 1,
            "requirement_node_id": node_urn,
        }
    )
    rebuilt = fw_editor.editor_doc_to_framework_object(doc, existing=original)
    questions = {
        node["urn"]: node.get("questions") or {}
        for node in rebuilt["requirement_nodes"]
    }[node_urn]
    assert len(questions) == 2
    existing = questions[f"{node_urn}:question:1"]
    assert existing["text"] == "Is it done?"  # untouched
    assert questions[f"{node_urn}:question:2"]["text"] == "Second question?"


def test_malformed_node_order_is_rejected():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    # Child listed before its parent: the pre-order invariant is violated —
    # only raw API payloads can produce this, and they must be rejected.
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    doc["nodes"].reverse()
    with pytest.raises(builder.BuilderError, match="Malformed node order"):
        fw_editor.editor_doc_to_framework_object(doc, existing=original)

    # A parent_urn pointing at no node in the document is equally malformed.
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    doc["nodes"][1]["parent_urn"] = "urn:acme:risk:req_node:source-lib:ghost"
    with pytest.raises(builder.BuilderError, match="unknown parent"):
        fw_editor.editor_doc_to_framework_object(doc, existing=original)


def test_new_choice_urns_avoid_collisions_and_stay_sequential():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    q_urn = "urn:acme:risk:req_node:source-lib:a.1:question:1"
    # Two choices added in the editor on the existing question (whose editor
    # id equals its urn — the double-bucket case): one ordered BEFORE the
    # kept ...choice:1, one after.
    doc["choices"].append(
        {
            "id": "tmp-c0",
            "urn": None,
            "value": "First",
            "order": -1,
            "question_id": q_urn,
        }
    )
    doc["choices"].append(
        {
            "id": "tmp-c1",
            "urn": None,
            "value": "Maybe",
            "order": 5,
            "question_id": q_urn,
        }
    )
    rebuilt = fw_editor.editor_doc_to_framework_object(doc, existing=original)
    node = next(
        n
        for n in rebuilt["requirement_nodes"]
        if n["urn"] == "urn:acme:risk:req_node:source-lib:a.1"
    )
    choices = node["questions"][q_urn]["choices"]
    by_value = {choice["value"]: choice["urn"] for choice in choices}
    # kept choice keeps its urn; minted ones never collide and don't skip
    # indexes (no duplicate-inflated positions)
    assert by_value["Yes"] == f"{q_urn}:choice:1"
    assert by_value["First"] == f"{q_urn}:choice:2"
    assert by_value["Maybe"] == f"{q_urn}:choice:3"
    assert len({choice["urn"] for choice in choices}) == 3


@pytest.mark.django_db
def test_framework_editor_endpoints_edit_the_document(admin_client):
    draft = _create_draft(
        admin_client, content=dict(SOURCE_LIBRARY["objects"]), packager="me"
    )
    url = reverse("library-drafts-framework-editor", args=[draft["id"]])

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.content
    doc = response.data["editing_draft"]
    assert response.data["framework_urn"] == "urn:acme:risk:framework:source-lib"
    assert len(doc["nodes"]) == 2

    doc["framework_meta"]["name"] = "Edited framework"
    doc["nodes"][1]["name"] = "Edited requirement"
    put = admin_client.put(url, {"editing_draft": doc}, format="json")
    assert put.status_code == status.HTTP_200_OK, put.content

    saved = admin_client.get(reverse("library-drafts-detail", args=[draft["id"]])).data
    framework = saved["content"]["frameworks"][0]
    assert framework["name"] == "Edited framework"
    node = framework["requirement_nodes"][1]
    assert node["name"] == "Edited requirement"
    # untouched by the editor, still there
    assert node["threats"] == ["urn:acme:risk:threat:source-lib:t1"]


def test_mapping_sets_always_mint_with_their_own_leaf():
    # A library legitimately holds several mapping sets (both directions of
    # a crosswalk): they never take the bare family URN, so importing them
    # one at a time can never collide.
    single = {
        "requirement_mapping_sets": [
            {"urn": "urn:x:risk:req_mapping_set:a-to-b", "ref_id": "a-to-b"}
        ]
    }
    urn_map = builder.build_urn_map(
        single, {"urn:x:risk:req_mapping_set:a-to-b"}, "me", "mylib"
    )
    assert urn_map["urn:x:risk:req_mapping_set:a-to-b"] == (
        "urn:me:risk:req_mapping_set:mylib:a-to-b"
    )


@pytest.mark.django_db
def test_single_framework_per_library_is_enforced(admin_client):
    draft = _create_draft(admin_client, content=dict(SOURCE_LIBRARY["objects"]))

    # add-framework on a draft that already has one
    added = admin_client.post(
        reverse("library-drafts-add-framework", args=[draft["id"]]),
        {"name": "Second"},
        format="json",
    )
    assert added.status_code == status.HTTP_400_BAD_REQUEST
    assert added.data["error"] == "singleObjectOfKindPerLibrary"

    # importing another framework from a second source
    other_library = {
        **SOURCE_LIBRARY,
        "urn": "urn:acme:risk:library:other-lib",
        "ref_id": "other-lib",
        "name": "Other library",
        "objects": {
            "framework": {
                "urn": "urn:acme:risk:framework:other-lib",
                "ref_id": "OTHER",
                "name": "Other framework",
                "requirement_nodes": [],
            }
        },
    }
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(other_library).encode()
    )
    assert error is None, error
    imported = admin_client.post(
        reverse("library-drafts-import-objects", args=[draft["id"]]),
        {"source": str(stored.id), "object_types": ["frameworks"]},
        format="json",
    )
    assert imported.status_code == status.HTTP_400_BAD_REQUEST
    assert imported.data["error"] == "singleObjectOfKindPerLibrary"


@pytest.mark.django_db
def test_add_framework_then_preview_reports_everything_as_added(admin_client):
    draft = _create_draft(admin_client, content={})
    created = admin_client.post(
        reverse("library-drafts-add-framework", args=[draft["id"]]),
        {"name": "Fresh framework", "ref_id": "FRESH"},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED, created.content
    assert created.data["framework_urn"] == "urn:me:risk:framework:mylib"

    url = reverse("library-drafts-framework-editor", args=[draft["id"]])
    doc = admin_client.get(url).data["editing_draft"]
    doc["nodes"].append(
        {
            "id": "tmp-1",
            "urn": None,
            "ref_id": "R1",
            "name": "Rule one",
            "parent_urn": None,
            "assessable": True,
            "order_id": 0,
        }
    )
    preview = admin_client.post(
        reverse("library-drafts-framework-editor-preview", args=[draft["id"]]),
        {"editing_draft": doc},
        format="json",
    )
    assert preview.status_code == status.HTTP_200_OK, preview.content
    assert preview.data["added"]["requirements"] == 1
    assert preview.data["removed"]["requirements"] == 0
    assert preview.data["affected_audits"] == []


# ---------------------------------------------------------------------------
# Preset (journey) editor bridge
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_preset_editor_round_trips_through_the_document(admin_client):
    draft = _create_draft(admin_client, content={})
    url = reverse("library-drafts-preset-editor", args=[draft["id"]])

    empty = admin_client.get(url)
    assert empty.status_code == status.HTTP_200_OK
    assert empty.data["editing_draft"]["steps"] == []
    assert empty.data["editing_draft"]["journey_meta"]["name"] == "My library"

    saved = admin_client.put(
        url,
        {
            "editing_draft": {
                "journey_meta": {"name": "My journey", "description": "Steps"},
                "scaffolded_objects": [],
                "steps": [
                    {
                        "key": "step-1",
                        "title": "Load the framework",
                        "target_model": "compliance-assessments",
                    }
                ],
            }
        },
        format="json",
    )
    assert saved.status_code == status.HTTP_200_OK, saved.content
    assert saved.data["editing_draft"]["journey_meta"]["name"] == "My journey"
    assert len(saved.data["editing_draft"]["steps"]) == 1

    detail = admin_client.get(reverse("library-drafts-detail", args=[draft["id"]])).data
    # The journey title is the preset's own, not the library's.
    assert detail["name"] == "My library"
    assert detail["content"]["preset"]["name"] == "My journey"
    assert detail["content"]["preset"]["journey"]["steps"][0]["key"] == "step-1"

    invalid = admin_client.put(
        url,
        {"editing_draft": {"journey_meta": {}, "steps": "nope"}},
        format="json",
    )
    assert invalid.status_code == status.HTTP_400_BAD_REQUEST

    preview = admin_client.post(
        reverse("library-drafts-preset-editor-preview", args=[draft["id"]]),
        {},
        format="json",
    )
    assert preview.status_code == status.HTTP_200_OK
    assert preview.data["deleted_steps"] == []


@pytest.mark.django_db
def test_preset_editor_round_trips_translations(admin_client):
    """journey_meta and step translations survive PUT → document → GET, and
    non-object translations are rejected."""
    draft = _create_draft(admin_client, content={})
    url = reverse("library-drafts-preset-editor", args=[draft["id"]])

    meta_tr = {"fr": {"name": "Mon parcours", "description": "Étapes"}}
    step_tr = {"fr": {"title": "Charger le référentiel"}}
    saved = admin_client.put(
        url,
        {
            "editing_draft": {
                "journey_meta": {
                    "name": "My journey",
                    "description": "Steps",
                    "translations": meta_tr,
                },
                "scaffolded_objects": [],
                "steps": [
                    {
                        "key": "step-1",
                        "title": "Load the framework",
                        "target_model": "compliance-assessments",
                        "translations": step_tr,
                    }
                ],
            }
        },
        format="json",
    )
    assert saved.status_code == status.HTTP_200_OK, saved.content
    assert saved.data["editing_draft"]["journey_meta"]["translations"] == meta_tr
    assert saved.data["editing_draft"]["steps"][0]["translations"] == step_tr

    detail = admin_client.get(reverse("library-drafts-detail", args=[draft["id"]])).data
    assert detail["content"]["preset"]["translations"] == meta_tr
    assert detail["content"]["preset"]["journey"]["steps"][0]["translations"] == step_tr

    invalid = admin_client.put(
        url,
        {
            "editing_draft": {
                "journey_meta": {"name": "X", "translations": "nope"},
                "scaffolded_objects": [],
                "steps": [],
            }
        },
        format="json",
    )
    assert invalid.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Leaf object editing (threats, reference controls, matrices)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_upsert_object_round_trips_translations(admin_client):
    """Leaf objects and matrices keep their translations dict through upsert,
    and a null translations payload clears it."""
    draft = _create_draft(admin_client, content={})
    url = reverse("library-drafts-upsert-object", args=[draft["id"]])

    threat_tr = {"fr": {"name": "Hameçonnage", "description": "Leurre"}}
    created = admin_client.post(
        url,
        {
            "field": "threats",
            "object": {
                "ref_id": "T1",
                "name": "Phishing",
                "translations": threat_tr,
            },
        },
        format="json",
    )
    assert created.status_code == status.HTTP_200_OK, created.content
    assert created.data["object"]["translations"] == threat_tr

    cleared = admin_client.post(
        url,
        {
            "field": "threats",
            "urn": created.data["object"]["urn"],
            "object": {"translations": None},
        },
        format="json",
    )
    assert cleared.status_code == status.HTTP_200_OK, cleared.content
    assert "translations" not in cleared.data["object"]


@pytest.mark.django_db
def test_upsert_object_mints_urn_and_validates(admin_client):
    draft = _create_draft(admin_client, content={})
    url = reverse("library-drafts-upsert-object", args=[draft["id"]])

    # A non-string field (unhashable) must be a clean 400, not a TypeError.
    bad_field = admin_client.post(
        url, {"field": [], "object": {"ref_id": "X"}}, format="json"
    )
    assert bad_field.status_code == status.HTTP_400_BAD_REQUEST
    assert bad_field.data["error"] == "unsupportedObjectField"

    created = admin_client.post(
        url,
        {
            "field": "threats",
            "object": {"ref_id": "T9", "name": "Phishing", "description": "Lure"},
        },
        format="json",
    )
    assert created.status_code == status.HTTP_200_OK, created.content
    assert created.data["object"]["urn"] == "urn:me:risk:threat:mylib:t9"

    # same ref_id again → URN collision
    again = admin_client.post(
        url,
        {"field": "threats", "object": {"ref_id": "T9", "name": "Dup"}},
        format="json",
    )
    assert again.status_code == status.HTTP_409_CONFLICT

    # loader-grade validation: bad category on a reference control
    bad = admin_client.post(
        url,
        {
            "field": "reference_controls",
            "object": {"ref_id": "C9", "category": "nonsense"},
        },
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST
    assert "category" in bad.data["error"]

    # update: merge fields, null clears, urn pinned
    updated = admin_client.post(
        url,
        {
            "field": "threats",
            "urn": "urn:me:risk:threat:mylib:t9",
            "object": {"name": "Spear phishing", "description": None},
        },
        format="json",
    )
    assert updated.status_code == status.HTTP_200_OK, updated.content
    assert updated.data["object"] == {
        "urn": "urn:me:risk:threat:mylib:t9",
        "ref_id": "T9",
        "name": "Spear phishing",
    }


@pytest.mark.django_db
def test_upsert_matrix_validates_the_definition(admin_client):
    draft = _create_draft(admin_client, content={})
    url = reverse("library-drafts-upsert-object", args=[draft["id"]])
    levels = [
        {"abbreviation": "L", "name": "Low", "hexcolor": "#0F0"},
        {"abbreviation": "H", "name": "High", "hexcolor": "#F00"},
    ]

    bad = admin_client.post(
        url,
        {
            "field": "risk_matrices",
            "object": {
                "ref_id": "m1",
                "probability": levels,
                "impact": levels,
                "risk": levels,
                "grid": [[0, 9], [0, 1]],  # 9 is not a risk level index
            },
        },
        format="json",
    )
    assert bad.status_code == status.HTTP_400_BAD_REQUEST

    good = admin_client.post(
        url,
        {
            "field": "risk_matrices",
            "object": {
                "ref_id": "m1",
                "name": "Small matrix",
                "probability": levels,
                "impact": levels,
                "risk": levels,
                "grid": [[0, 1], [1, 1]],
            },
        },
        format="json",
    )
    assert good.status_code == status.HTTP_200_OK, good.content
    # The single matrix of a library takes the bare family URN.
    assert good.data["object"]["urn"] == "urn:me:risk:matrix:mylib"
    assert good.data["draft"]["objects_meta"]["risk_matrices"] == 1

    # Single-object convention: a second matrix is refused.
    second = admin_client.post(
        url,
        {
            "field": "risk_matrices",
            "object": {
                "ref_id": "m2",
                "probability": levels,
                "impact": levels,
                "risk": levels,
                "grid": [[0, 1], [1, 1]],
            },
        },
        format="json",
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST
    assert second.data["error"] == "singleObjectOfKindPerLibrary"


@pytest.mark.django_db
def test_delete_object_blocks_on_references_unless_forced(admin_client):
    draft = _create_draft(admin_client, content=dict(SOURCE_LIBRARY["objects"]))
    url = reverse("library-drafts-delete-object", args=[draft["id"]])
    threat_urn = "urn:acme:risk:threat:source-lib:t1"

    blocked = admin_client.post(url, {"urn": threat_urn}, format="json")
    assert blocked.status_code == status.HTTP_409_CONFLICT
    assert blocked.data["references"] == ["urn:acme:risk:req_node:source-lib:a.1"]

    forced = admin_client.post(url, {"urn": threat_urn, "force": True}, format="json")
    assert forced.status_code == status.HTTP_200_OK, forced.content
    content = forced.data["draft"]["content"]
    assert [t["urn"] for t in content["threats"]] == [
        "urn:acme:risk:threat:source-lib:t2"
    ]
    node = content["frameworks"][0]["requirement_nodes"][1]
    assert node["threats"] == []

    # unreferenced object deletes without force, empty list key is dropped
    ok = admin_client.post(
        url, {"urn": "urn:acme:risk:reference_control:source-lib:c1"}, format="json"
    )
    assert ok.status_code == status.HTTP_409_CONFLICT  # still referenced by a.1
    ok = admin_client.post(
        url,
        {"urn": "urn:acme:risk:reference_control:source-lib:c1", "force": True},
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK
    assert "reference_controls" not in ok.data["draft"]["content"]


@pytest.mark.django_db
def test_export_returns_a_loadable_yaml(admin_client):
    draft = _create_draft(admin_client)
    export_url = reverse("library-drafts-export", args=[draft["id"]])

    # Not published yet: the download is a working copy, suffixed -draft.
    response = admin_client.get(export_url)
    assert response.status_code == status.HTTP_200_OK
    assert 'filename="mylib-v1-draft.yaml"' in response["Content-Disposition"]
    document = yaml.safe_load(response.content)
    assert document["urn"] == "urn:me:risk:library:mylib"
    assert document["objects"]["threats"][0]["ref_id"] == "T1"

    # Published and unchanged: the canonical artifact, no suffix.
    published = admin_client.post(
        reverse("library-drafts-publish", args=[draft["id"]]),
        {"load": False},
        format="json",
    )
    assert published.status_code == status.HTTP_200_OK, published.content
    response = admin_client.get(export_url)
    assert 'filename="mylib-v1.yaml"' in response["Content-Disposition"]


# ---------------------------------------------------------------------------
# Node links to threats / reference controls (the reference picker)
# ---------------------------------------------------------------------------


def test_editor_doc_exposes_and_edits_node_links():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    editor_node = next(n for n in doc["nodes"] if n["ref_id"] == "A.1")
    assert editor_node["threats"] == ["urn:acme:risk:threat:source-lib:t1"]
    assert editor_node["reference_controls"] == [
        "urn:acme:risk:reference_control:source-lib:c1",
        "urn:other:risk:reference_control:ext-lib:x1",
    ]

    # Attach a second threat, detach every control; duplicates and case
    # are normalized away.
    editor_node["threats"] = [
        "urn:acme:risk:threat:source-lib:t1",
        "URN:ACME:RISK:THREAT:SOURCE-LIB:T2",
        "urn:acme:risk:threat:source-lib:t2",
    ]
    editor_node["reference_controls"] = []
    rebuilt = fw_editor.editor_doc_to_framework_object(doc, existing=original)
    node = {n["ref_id"]: n for n in rebuilt["requirement_nodes"]}["A.1"]
    assert node["threats"] == [
        "urn:acme:risk:threat:source-lib:t1",
        "urn:acme:risk:threat:source-lib:t2",
    ]
    assert "reference_controls" not in node  # empty list detaches, key dropped


def test_editor_doc_without_link_keys_preserves_existing_links():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    # An older client that does not model links omits the keys entirely.
    for node in doc["nodes"]:
        node.pop("threats", None)
        node.pop("reference_controls", None)
    rebuilt = fw_editor.editor_doc_to_framework_object(doc, existing=original)
    node = {n["ref_id"]: n for n in rebuilt["requirement_nodes"]}["A.1"]
    assert node["threats"] == ["urn:acme:risk:threat:source-lib:t1"]
    assert node["reference_controls"] == [
        "urn:acme:risk:reference_control:source-lib:c1",
        "urn:other:risk:reference_control:ext-lib:x1",
    ]


def test_editor_doc_malformed_links_are_rejected():
    from library import framework_editor as fw_editor

    original = builder.normalize_objects(SOURCE_LIBRARY["objects"])["frameworks"][0]
    doc = fw_editor.framework_to_editor_doc(original, locale="en")
    next(n for n in doc["nodes"] if n["ref_id"] == "A.1")["threats"] = "not-a-list"
    with pytest.raises(builder.BuilderError, match="must be a list of URN strings"):
        fw_editor.editor_doc_to_framework_object(doc, existing=original)


@pytest.mark.django_db
def test_find_stored_owner_urn_inverts_urn_families(app_config):
    # Legacy type token (function) and stored-but-not-loaded library.
    assert (
        builder.find_stored_owner_urn("urn:intuitem:risk:function:doc-pol:pol.educ")
        == "urn:intuitem:risk:library:doc-pol"
    )
    assert builder.find_stored_owner_urn("urn:nobody:risk:threat:ghost:t1") is None
    assert builder.find_stored_owner_urn("not-a-urn") is None


@pytest.mark.django_db
def test_framework_editor_save_auto_declares_link_dependencies(admin_client):
    draft = _create_draft(admin_client, content=dict(SOURCE_LIBRARY["objects"]))
    url = reverse("library-drafts-framework-editor", args=[draft["id"]])
    doc = admin_client.get(url).data["editing_draft"]
    node = next(n for n in doc["nodes"] if n["ref_id"] == "A.1")
    # Link a control owned by a stored (not loaded, not declared) library.
    node["reference_controls"] = [
        "urn:acme:risk:reference_control:source-lib:c1",
        "urn:intuitem:risk:function:doc-pol:pol.educ",
    ]
    put = admin_client.put(url, {"editing_draft": doc}, format="json")
    assert put.status_code == status.HTTP_200_OK, put.content

    saved = admin_client.get(reverse("library-drafts-detail", args=[draft["id"]])).data
    assert "urn:intuitem:risk:library:doc-pol" in saved["dependencies"]
    node = saved["content"]["frameworks"][0]["requirement_nodes"][1]
    assert node["reference_controls"] == [
        "urn:acme:risk:reference_control:source-lib:c1",
        "urn:intuitem:risk:function:doc-pol:pol.educ",
    ]
    # The declared dependency satisfies reference integrity.
    validate = admin_client.get(reverse("library-drafts-validate", args=[draft["id"]]))
    assert not [e for e in validate.data["errors"] if "doc-pol" in e], validate.data[
        "errors"
    ]


@pytest.mark.django_db
def test_validate_asks_for_a_dependency_on_the_stored_owner(admin_client):
    content = dict(SOURCE_LIBRARY["objects"])
    draft = _create_draft(admin_client, content=content)
    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    current = admin_client.get(detail_url).data["content"]
    node = current["frameworks"][0]["requirement_nodes"][1]
    node["reference_controls"] = ["urn:intuitem:risk:function:doc-pol:pol.educ"]
    assert (
        admin_client.patch(detail_url, {"content": current}, format="json").status_code
        == status.HTTP_200_OK
    )
    validate = admin_client.get(reverse("library-drafts-validate", args=[draft["id"]]))
    assert any(
        "requires a dependency on urn:intuitem:risk:library:doc-pol" in e
        for e in validate.data["errors"]
    ), validate.data["errors"]


@pytest.mark.django_db
def test_reference_catalog_lists_draft_dependencies_and_libraries(admin_client):
    draft = _create_draft(
        admin_client,
        content=dict(SOURCE_LIBRARY["objects"]),
        dependencies=["urn:intuitem:risk:library:doc-pol"],
    )
    url = reverse("library-drafts-reference-catalog", args=[draft["id"]])
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.content

    sources = response.data["sources"]
    assert sources[0]["kind"] == "draft"
    assert {t["urn"] for t in sources[0]["threats"]} == {
        "urn:acme:risk:threat:source-lib:t1",
        "urn:acme:risk:threat:source-lib:t2",
    }
    dep = next(s for s in sources if s["kind"] == "dependency")
    assert dep["library_urn"] == "urn:intuitem:risk:library:doc-pol"
    dep_controls = {c["urn"] for c in dep["reference_controls"]}
    assert "urn:intuitem:risk:function:doc-pol:pol.educ" in dep_controls

    libraries = response.data["libraries"]
    assert libraries, "other stored libraries with linkable objects expected"
    listed = {lib["library_urn"] for lib in libraries}
    assert "urn:intuitem:risk:library:doc-pol" not in listed  # already a source
    assert draft["urn"] not in listed

    # Browse a specific undeclared library on demand.
    browsable = libraries[0]["library_urn"]
    browse = admin_client.get(url, {"library": browsable})
    assert browse.status_code == status.HTTP_200_OK
    assert browse.data["source"]["kind"] == "external"
    assert browse.data["source"]["library_urn"] == browsable

    missing = admin_client.get(url, {"library": "urn:nobody:risk:library:ghost"})
    assert missing.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_malformed_dependency_content_is_tolerated(admin_client):
    # Stored-library content is not shape-checked (the update-upload path
    # stores without loading): the catalog, the editor save and validate
    # must degrade gracefully, never 500.
    StoredLibrary.objects.create(
        urn="urn:junky:risk:library:junk",
        ref_id="junk",
        name="Junk library",
        locale="en",
        version=1,
        content={"threats": "garbage", "reference_controls": [["nested"]]},
        objects_meta={},
    )
    draft = _create_draft(
        admin_client,
        content=dict(SOURCE_LIBRARY["objects"]),
        dependencies=["urn:junky:risk:library:junk"],
    )
    catalog = admin_client.get(
        reverse("library-drafts-reference-catalog", args=[draft["id"]])
    )
    assert catalog.status_code == status.HTTP_200_OK, catalog.content
    dep = next(s for s in catalog.data["sources"] if s["kind"] == "dependency")
    assert dep["threats"] == [] and dep["reference_controls"] == []

    url = reverse("library-drafts-framework-editor", args=[draft["id"]])
    doc = admin_client.get(url).data["editing_draft"]
    put = admin_client.put(url, {"editing_draft": doc}, format="json")
    assert put.status_code == status.HTTP_200_OK, put.content

    validate = admin_client.get(reverse("library-drafts-validate", args=[draft["id"]]))
    assert validate.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_validate_never_suggests_depending_on_the_drafts_own_library(admin_client):
    # A published draft has a stored copy under its own URN; a reference to
    # an object deleted from the draft (but still in that copy) is a
    # dangling internal ref — not a reason to self-depend.
    content = {
        "frameworks": [
            {
                "urn": "urn:me:risk:framework:mylib",
                "ref_id": "FW",
                "name": "FW",
                "requirement_nodes": [
                    {
                        "urn": "urn:me:risk:req_node:mylib:a",
                        "assessable": True,
                        "depth": 1,
                        "threats": ["urn:me:risk:threat:mylib:gone"],
                    }
                ],
            }
        ]
    }
    draft = _create_draft(admin_client, content=content)
    StoredLibrary.objects.create(
        urn="urn:me:risk:library:mylib",
        ref_id="mylib",
        name="My library",
        locale="en",
        version=1,
        content={
            "threats": [
                {"urn": "urn:me:risk:threat:mylib:gone", "ref_id": "G", "name": "Gone"}
            ]
        },
        objects_meta={},
    )
    validate = admin_client.get(reverse("library-drafts-validate", args=[draft["id"]]))
    errors = validate.data["errors"]
    assert any(
        "unresolved reference urn:me:risk:threat:mylib:gone" in e for e in errors
    ), errors
    assert not any("requires a dependency on" in e for e in errors), errors

    # The editor save must not auto-declare the self-dependency either.
    url = reverse("library-drafts-framework-editor", args=[draft["id"]])
    doc = admin_client.get(url).data["editing_draft"]
    put = admin_client.put(url, {"editing_draft": doc}, format="json")
    assert put.status_code == status.HTTP_200_OK, put.content
    saved = admin_client.get(reverse("library-drafts-detail", args=[draft["id"]])).data
    assert saved["dependencies"] in ([], None)


@pytest.mark.django_db
def test_created_drafts_default_provider_to_packager(admin_client):
    draft = _create_draft(admin_client)
    assert draft["provider"] == "me"

    explicit = _create_draft(
        admin_client, ref_id="providedlib", provider="Some Provider"
    )
    assert explicit["provider"] == "Some Provider"


@pytest.fixture
def builder_only_client(app_config):
    """A builder-capable user with NO stored-library visibility.

    No shipped role has this shape (they all carry view_storedlibrary) —
    it can only exist as a custom role, which is exactly the scenario the
    folder-scoped read checks protect against.
    """
    user = User.objects.create_user("builder-only@builder-tests.com")
    user.is_published = True
    user.save()
    role = Role.objects.create(name="BuilderOnly", folder=Folder.get_root_folder())
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_folder",  # baseline of every real role
                "view_librarydraft",
                "add_librarydraft",
                "change_librarydraft",
                "delete_librarydraft",
            ]
        )
    )
    root = Folder.get_root_folder()
    group = UserGroup.objects.create(name="builder-only-group", folder=root)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group, role=role, folder=root, is_recursive=True
    )
    assignment.perimeter_folders.add(root)
    client = APIClient()
    token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.mark.django_db
def test_framework_editor_audits_are_rbac_scoped(app_config):
    """The framework editor only ever surfaces audits the caller may read:
    _readable_audits_on returns them for a privileged user and nothing for a
    builder user without view_complianceassessment (no cross-scope leak)."""
    from core.models import ComplianceAssessment, Perimeter
    from library.views import LibraryDraftViewSet

    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="Live FW", folder=root)
    perimeter = Perimeter.objects.create(name="P", folder=root)
    audit = ComplianceAssessment.objects.create(
        name="Secret audit", perimeter=perimeter, framework=framework, folder=root
    )

    admin = User.objects.create_superuser("audit-admin@builder-tests.com")
    builder = User.objects.create_user("nobody@builder-tests.com")
    builder.is_published = True
    builder.save()
    role = Role.objects.create(name="NoAudit", folder=root)
    role.permissions.set(Permission.objects.filter(codename="view_folder"))
    group = UserGroup.objects.create(name="no-audit-group", folder=root)
    group.user_set.add(builder)
    RoleAssignment.objects.create(
        user_group=group, role=role, folder=root, is_recursive=True
    ).perimeter_folders.add(root)

    admin_ids = [
        a.id for a in LibraryDraftViewSet._readable_audits_on(framework, admin)
    ]
    builder_ids = [
        a.id for a in LibraryDraftViewSet._readable_audits_on(framework, builder)
    ]
    assert audit.id in admin_ids
    assert builder_ids == []


@pytest.mark.django_db
def test_stored_library_reads_respect_rbac(builder_only_client):
    """Every stored-library read path follows the folder-scoped RBAC model:
    a user without view_storedlibrary sees no library, through any door."""
    source_urn = "urn:intuitem:risk:library:doc-pol"  # stored by startup

    # Draft-side doors -------------------------------------------------------
    created = builder_only_client.post(
        reverse("library-drafts-list"),
        {"name": "Mine", "packager": "me", "ref_id": "rbaclib", "content": {}},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED, created.content
    draft_id = created.data["id"]

    adopt = builder_only_client.post(
        reverse("library-drafts-adopt"),
        {"stored_library": source_urn},
        format="json",
    )
    assert adopt.status_code == status.HTTP_404_NOT_FOUND

    imported = builder_only_client.post(
        reverse("library-drafts-import-objects", args=[draft_id]),
        {"source": source_urn},
        format="json",
    )
    assert imported.status_code == status.HTTP_404_NOT_FOUND

    catalog_url = reverse("library-drafts-reference-catalog", args=[draft_id])
    catalog = builder_only_client.get(catalog_url)
    assert catalog.status_code == status.HTTP_200_OK, catalog.content
    assert catalog.data["libraries"] == []

    browse = builder_only_client.get(catalog_url, {"library": source_urn})
    assert browse.status_code == status.HTTP_404_NOT_FOUND

    patched = builder_only_client.patch(
        reverse("library-drafts-detail", args=[draft_id]),
        {"dependencies": [source_urn]},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK, patched.content
    catalog = builder_only_client.get(catalog_url)
    dep = next(s for s in catalog.data["sources"] if s["kind"] == "dependency")
    assert dep["missing"] is True and dep["reference_controls"] == []

    # Catalog-side doors -----------------------------------------------------
    for route in ("stored-libraries-detail", "stored-libraries-content"):
        response = builder_only_client.get(reverse(route, args=[source_urn]))
        assert response.status_code == status.HTTP_404_NOT_FOUND, route


@pytest.mark.django_db
def test_stored_library_reads_stay_open_for_standard_roles(admin_client):
    """Sanity: for roles holding view_storedlibrary (all shipped ones),
    the folder-scoped checks change nothing."""
    source_urn = "urn:intuitem:risk:library:doc-pol"
    detail = admin_client.get(reverse("stored-libraries-detail", args=[source_urn]))
    assert detail.status_code == status.HTTP_200_OK
    content = admin_client.get(reverse("stored-libraries-content", args=[source_urn]))
    assert content.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_validation_and_dependency_sync_read_with_the_users_eyes(builder_only_client):
    """A hidden stored library is never named by validation, never covers
    declared dependencies, and is never auto-declared by the editor save."""
    hidden_ref = "urn:intuitem:risk:function:doc-pol:pol.educ"
    content = {
        "frameworks": [
            {
                "urn": "urn:me:risk:framework:problib",
                "ref_id": "FW",
                "name": "FW",
                "requirement_nodes": [
                    {
                        "urn": "urn:me:risk:req_node:problib:a",
                        "assessable": True,
                        "depth": 1,
                        "name": "A",
                        "reference_controls": [hidden_ref],
                    }
                ],
            }
        ]
    }
    created = builder_only_client.post(
        reverse("library-drafts-list"),
        {"name": "Probe", "packager": "me", "ref_id": "problib", "content": content},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED, created.content
    draft_id = created.data["id"]
    detail_url = reverse("library-drafts-detail", args=[draft_id])
    validate_url = reverse("library-drafts-validate", args=[draft_id])

    # 1. No existence oracle: the reference comes back unresolved (echoing
    # the user's own input), never "requires a dependency on <hidden lib>".
    validation = builder_only_client.get(validate_url).data
    assert any("unresolved reference" in e for e in validation["errors"]), validation
    assert not any("requires a dependency" in e for e in validation["errors"]), (
        validation
    )

    # 2. Declaring the hidden library does not cover the reference.
    patched = builder_only_client.patch(
        detail_url,
        {"dependencies": ["urn:intuitem:risk:library:doc-pol"]},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK, patched.content
    validation = builder_only_client.get(validate_url).data
    assert any("unresolved reference" in e for e in validation["errors"]), validation

    # 3. The editor save never auto-declares the hidden library.
    assert (
        builder_only_client.patch(
            detail_url, {"dependencies": []}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )
    editor_url = reverse("library-drafts-framework-editor", args=[draft_id])
    doc = builder_only_client.get(editor_url).data["editing_draft"]
    put = builder_only_client.put(editor_url, {"editing_draft": doc}, format="json")
    assert put.status_code == status.HTTP_200_OK, put.content
    assert builder_only_client.get(detail_url).data["dependencies"] in ([], None)

    # 4. Same rule for LOADED libraries: loading doc-pol changes nothing
    # for a user who may not read its objects.
    assert (
        StoredLibrary.objects.get(urn="urn:intuitem:risk:library:doc-pol").load()
        is None
    )
    validation = builder_only_client.get(validate_url).data
    assert any("unresolved reference" in e for e in validation["errors"]), validation
    assert not any("requires a dependency" in e for e in validation["errors"]), (
        validation
    )
    put = builder_only_client.put(editor_url, {"editing_draft": doc}, format="json")
    assert put.status_code == status.HTTP_200_OK, put.content
    assert builder_only_client.get(detail_url).data["dependencies"] in ([], None)


@pytest.mark.django_db
def test_identity_conflict_oracle_is_scoped(builder_only_client):
    """Identity conflicts only surface objects the user may read: a hidden
    library never shows up through check-identity, conflicts or validate."""
    check = builder_only_client.get(
        reverse("library-drafts-check-identity"),
        {"packager": "intuitem", "ref_id": "doc-pol"},
    )
    assert check.status_code == status.HTTP_200_OK, check.content
    assert check.data["conflicts"] == []

    created = builder_only_client.post(
        reverse("library-drafts-list"),
        {"name": "Probe", "packager": "intuitem", "ref_id": "doc-pol", "content": {}},
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED, created.content
    draft_id = created.data["id"]

    conflicts = builder_only_client.get(
        reverse("library-drafts-conflicts", args=[draft_id])
    )
    assert conflicts.data["conflicts"] == []

    validation = builder_only_client.get(
        reverse("library-drafts-validate", args=[draft_id])
    ).data
    assert not any("Identity conflict" in w for w in validation["warnings"]), validation


# ---------------------------------------------------------------------------
# Adopt a library-less live framework (retired standalone editor output)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_adopt_live_framework_updates_rows_in_place(admin_client):
    from core.models import Question, QuestionChoice

    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="Homegrown", folder=root, urn=None)
    chapter = RequirementNode.objects.create(
        framework=framework,
        folder=root,
        name="Chapter A",
        ref_id="A",
        assessable=False,
        order_id=0,
    )
    requirement = RequirementNode.objects.create(
        framework=framework,
        folder=root,
        name="Req A.1",
        ref_id="A.1",
        assessable=True,
        order_id=1,
    )
    question = Question.objects.create(
        requirement_node=requirement,
        folder=root,
        type="unique_choice",
        text="Done?",
        order=0,
    )
    QuestionChoice.objects.create(question=question, folder=root, value="Yes", order=0)

    response = admin_client.post(
        reverse("library-drafts-adopt"),
        {"framework": str(framework.id)},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    draft_id = response.data["id"]
    assert response.data["identity_locked"] is True

    # Missing URNs were minted onto the live rows (adopt-in-place enabler).
    framework.refresh_from_db()
    chapter.refresh_from_db()
    requirement.refresh_from_db()
    question.refresh_from_db()
    assert framework.urn == "urn:custom:risk:framework:homegrown"
    assert chapter.urn and requirement.urn and question.urn

    # The document mirrors the live tree.
    content = response.data["content"]
    doc_nodes = content["frameworks"][0]["requirement_nodes"]
    assert [n["ref_id"] for n in doc_nodes] == ["A", "A.1"]
    assert question.urn in doc_nodes[1]["questions"]

    # Publishing goes through the loader and updates the SAME rows.
    publish = admin_client.post(
        reverse("library-drafts-publish", args=[draft_id]), {}, format="json"
    )
    assert publish.status_code == status.HTTP_200_OK, publish.content
    framework.refresh_from_db()
    requirement.refresh_from_db()
    assert framework.library is not None  # attached, not duplicated
    assert framework.library.urn == "urn:custom:risk:library:homegrown"
    assert Framework.objects.filter(name="Homegrown").count() == 1
    assert requirement.framework_id == framework.id


@pytest.mark.django_db
def test_adopt_live_framework_refuses_library_backed_ones(admin_client):
    stored = StoredLibrary.objects.get(urn="urn:intuitem:risk:library:doc-pol")
    assert stored.load() is None
    framework = Framework.objects.create(
        name="Lib-backed",
        folder=Folder.get_root_folder(),
        urn="urn:x:risk:framework:libbacked",
        library=LoadedLibrary.objects.get(urn="urn:intuitem:risk:library:doc-pol"),
    )
    response = admin_client.post(
        reverse("library-drafts-adopt"),
        {"framework": str(framework.id)},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "frameworkBelongsToALibrary"


# ---------------------------------------------------------------------------
# Review remediation regressions (2026-07-10)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_presets_list_endpoint_does_not_500(admin_client):
    """PresetReadSerializer must not reference the dropped editing_version."""
    response = admin_client.get(reverse("presets-list"))
    assert response.status_code == status.HTTP_200_OK, response.content


@pytest.mark.django_db
def test_publish_cannot_hijack_a_library_backed_framework(admin_client):
    """A draft whose framework URN collides with an already-loaded,
    library-backed framework must fail to publish — not silently re-home it
    and prune its nodes."""
    victim = _create_draft(
        admin_client,
        packager="me",
        ref_id="victimlib",
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:victimlib",
                    "ref_id": "V",
                    "name": "Victim",
                    "requirement_nodes": [
                        {
                            "urn": "urn:me:risk:req_node:victimlib:a",
                            "ref_id": "A",
                            "assessable": True,
                            "depth": 1,
                            "name": "Keep me",
                        }
                    ],
                }
            ]
        },
    )
    assert (
        admin_client.post(
            reverse("library-drafts-publish", args=[victim["id"]]), {}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )
    victim_fw = Framework.objects.get(urn="urn:me:risk:framework:victimlib")
    assert victim_fw.library is not None

    # An attacker library (different identity) declaring the same framework URN.
    attacker = _create_draft(
        admin_client,
        packager="me",
        ref_id="attackerlib",
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:victimlib",  # collision
                    "ref_id": "V",
                    "name": "Hijacked",
                    "requirement_nodes": [],
                }
            ]
        },
    )
    response = admin_client.post(
        reverse("library-drafts-publish", args=[attacker["id"]]), {}, format="json"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
        response.content
    )
    # The victim framework is untouched: same library, node still there.
    victim_fw.refresh_from_db()
    assert victim_fw.library.urn == "urn:me:risk:library:victimlib"
    assert victim_fw.name == "Victim"
    assert RequirementNode.objects.filter(
        urn="urn:me:risk:req_node:victimlib:a"
    ).exists()


_MATRIX_LEVELS = [
    {"abbreviation": "L", "name": "Low", "hexcolor": "#0F0"},
    {"abbreviation": "H", "name": "High", "hexcolor": "#F00"},
]
_MATRIX_OBJECT_FIELDS = {
    "probability": _MATRIX_LEVELS,
    "impact": _MATRIX_LEVELS,
    "risk": _MATRIX_LEVELS,
    "grid": [[0, 1], [0, 1]],
}


@pytest.mark.django_db
def test_publish_adopts_a_library_less_matrix_in_place(admin_client):
    """First publish of a draft whose matrix URN lives on a library-less row
    (migration-wrapped standalone-editor matrices) must adopt that very row —
    same id, so risk assessments built on it stay attached — instead of
    crashing on the URN unique constraint."""
    live = RiskMatrix.objects.create(
        folder=Folder.get_root_folder(),
        name="Wrapped matrix",
        urn="urn:me:risk:matrix:wrappedlib",
        ref_id="wrappedlib",
        json_definition=dict(_MATRIX_OBJECT_FIELDS),
    )
    draft = _create_draft(
        admin_client,
        packager="me",
        ref_id="wrappedlib",
        content={
            "risk_matrices": [
                {
                    "urn": "urn:me:risk:matrix:wrappedlib",
                    "ref_id": "wrappedlib",
                    "name": "Wrapped matrix v2",
                    **_MATRIX_OBJECT_FIELDS,
                }
            ]
        },
    )
    response = admin_client.post(
        reverse("library-drafts-publish", args=[draft["id"]]), {}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    live.refresh_from_db()  # the SAME row was adopted, not replaced
    assert live.library is not None
    assert live.library.urn == "urn:me:risk:library:wrappedlib"
    assert live.name == "Wrapped matrix v2"


@pytest.mark.django_db
def test_publish_cannot_hijack_a_library_backed_matrix(admin_client):
    """A draft whose matrix URN collides with an already-loaded,
    library-backed matrix must fail to publish, leaving the victim intact."""
    victim = _create_draft(
        admin_client,
        packager="me",
        ref_id="victimmatrix",
        content={
            "risk_matrices": [
                {
                    "urn": "urn:me:risk:matrix:victimmatrix",
                    "ref_id": "V",
                    "name": "Victim matrix",
                    **_MATRIX_OBJECT_FIELDS,
                }
            ]
        },
    )
    assert (
        admin_client.post(
            reverse("library-drafts-publish", args=[victim["id"]]), {}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )
    victim_matrix = RiskMatrix.objects.get(urn="urn:me:risk:matrix:victimmatrix")
    assert victim_matrix.library is not None

    attacker = _create_draft(
        admin_client,
        packager="me",
        ref_id="attackermatrix",
        content={
            "risk_matrices": [
                {
                    "urn": "urn:me:risk:matrix:victimmatrix",  # collision
                    "ref_id": "V",
                    "name": "Hijacked matrix",
                    **_MATRIX_OBJECT_FIELDS,
                }
            ]
        },
    )
    response = admin_client.post(
        reverse("library-drafts-publish", args=[attacker["id"]]), {}, format="json"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
        response.content
    )
    victim_matrix.refresh_from_db()
    assert victim_matrix.library.urn == "urn:me:risk:library:victimmatrix"
    assert victim_matrix.name == "Victim matrix"


@pytest.mark.django_db
def test_has_unpublished_changes_tracks_edits_after_publish(admin_client):
    """A published draft reads unchanged right after publish, flips to
    modified once edited, and back to unchanged after re-publishing."""
    draft = _create_draft(admin_client)
    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    publish_url = reverse("library-drafts-publish", args=[draft["id"]])

    # Never published yet.
    assert draft["has_unpublished_changes"] is False
    assert draft["last_published_version"] is None

    assert (
        admin_client.post(publish_url, {}, format="json").status_code
        == status.HTTP_200_OK
    )
    fresh = admin_client.get(detail_url).data
    assert fresh["has_unpublished_changes"] is False  # just published, unchanged
    assert fresh["last_published_version"] == fresh["version"]

    # Any edit to the publishable content changes the fingerprint.
    admin_client.patch(detail_url, {"description": "edited"}, format="json")
    assert admin_client.get(detail_url).data["has_unpublished_changes"] is True

    # Re-publishing (with a version bump) clears it again.
    admin_client.patch(detail_url, {"version": 2}, format="json")
    assert (
        admin_client.post(publish_url, {}, format="json").status_code
        == status.HTTP_200_OK
    )
    assert admin_client.get(detail_url).data["has_unpublished_changes"] is False


@pytest.mark.django_db
def test_publish_without_load_commits_only(admin_client):
    """publish {load: false} is the user's commit: identity frozen and
    snapshot recorded, nothing stored or loaded in the corpus. Re-committing
    unchanged content is refused; changed content demands a version bump."""
    draft = _create_draft(admin_client)
    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    publish_url = reverse("library-drafts-publish", args=[draft["id"]])

    committed = admin_client.post(publish_url, {"load": False}, format="json")
    assert committed.status_code == status.HTTP_200_OK, committed.content
    assert committed.data["loaded"] is False

    fresh = admin_client.get(detail_url).data
    assert fresh["identity_locked"] is True
    assert fresh["has_unpublished_changes"] is False
    urn = fresh["urn"]
    assert not StoredLibrary.objects.filter(urn=urn).exists()
    assert not LoadedLibrary.objects.filter(urn=urn).exists()

    # Unchanged content: nothing new to commit.
    again = admin_client.post(publish_url, {"load": False}, format="json")
    assert again.status_code == status.HTTP_409_CONFLICT
    assert again.data["error"] == "nothingToPublish"

    # Changed content under the same version: two different v1 artifacts
    # would exist in the wild — refused without a bump.
    admin_client.patch(detail_url, {"description": "edited"}, format="json")
    refused = admin_client.post(publish_url, {"load": False}, format="json")
    assert refused.status_code == status.HTTP_409_CONFLICT
    assert refused.data["error"] == "versionBumpRequired"

    bumped = admin_client.post(
        publish_url, {"load": False, "bump_version": True}, format="json"
    )
    assert bumped.status_code == status.HTTP_200_OK, bumped.content
    assert bumped.data["version"] == 2
    assert admin_client.get(detail_url).data["has_unpublished_changes"] is False

    # Committed but not loaded: loading is the pending work, so a full
    # publish (load=true) must go through even though nothing changed.
    loaded = admin_client.post(publish_url, {}, format="json")
    assert loaded.status_code == status.HTTP_200_OK, loaded.content
    assert LoadedLibrary.objects.filter(urn=urn, version=2).exists()

    # Unchanged AND already loaded: nothing to commit, nothing to load —
    # refused instead of prompting a pointless version bump.
    noop = admin_client.post(publish_url, {}, format="json")
    assert noop.status_code == status.HTTP_409_CONFLICT
    assert noop.data["error"] == "nothingToPublish"


@pytest.mark.django_db
def test_publish_refuses_when_another_draft_owns_the_urn(admin_client):
    """Two urn-less drafts can share an identity while editing (advisory
    conflict warnings only), but only ONE may publish it: the second publish
    must refuse cleanly, pointing at the owner, before touching the corpus."""
    first = _create_draft(admin_client)
    assert (
        admin_client.post(
            reverse("library-drafts-publish", args=[first["id"]]), {}, format="json"
        ).status_code
        == status.HTTP_200_OK
    )

    second = _create_draft(admin_client, name="Same identity")  # same packager/ref_id
    response = admin_client.post(
        reverse("library-drafts-publish", args=[second["id"]]), {}, format="json"
    )
    assert response.status_code == status.HTTP_409_CONFLICT, response.content
    assert response.data["error"] == "draftAlreadyExists"
    assert response.data["draft"] == first["id"]


@pytest.mark.django_db
def test_duplicate_urns_are_rejected_at_the_shape_door(admin_client):
    draft = _create_draft(admin_client, content={})
    content = {
        "frameworks": [
            {
                "urn": "urn:me:risk:framework:dup",
                "ref_id": "D",
                "name": "Dup",
                "requirement_nodes": [
                    {
                        "urn": "urn:me:risk:req_node:dup:a",
                        "assessable": True,
                        "depth": 1,
                    },
                    {
                        "urn": "urn:me:risk:req_node:dup:a",
                        "assessable": True,
                        "depth": 1,
                    },
                ],
            }
        ]
    }
    response = admin_client.patch(
        reverse("library-drafts-detail", args=[draft["id"]]),
        {"content": content},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "duplicate URN" in str(response.content)


@pytest.mark.django_db
def test_validate_flags_oversized_fields_and_dangling_depends_on(admin_client):
    content = {
        "frameworks": [
            {
                "urn": "urn:me:risk:framework:big",
                "ref_id": "B",
                "name": "B",
                "requirement_nodes": [
                    {
                        "urn": "urn:me:risk:req_node:big:a",
                        "ref_id": "A",
                        "assessable": True,
                        "depth": 1,
                        "name": "N" * 250,  # > 200
                        "questions": {
                            "urn:me:risk:req_node:big:a:question:1": {
                                "type": "unique_choice",
                                "text": "Q",
                                "depends_on": {"question": "urn:me:risk:missing:q"},
                            }
                        },
                    }
                ],
            }
        ]
    }
    draft = _create_draft(admin_client, packager="me", ref_id="big", content=content)
    errors = admin_client.get(
        reverse("library-drafts-validate", args=[draft["id"]])
    ).data["errors"]
    assert any("characters (max 200)" in e for e in errors), errors
    assert any("depends_on references question" in e for e in errors), errors


@pytest.mark.django_db
def test_validate_flags_a_structurally_broken_matrix(admin_client):
    content = {
        "risk_matrices": [
            {
                "urn": "urn:me:risk:matrix:mtx",
                "ref_id": "MTX",
                "name": "Broken",
                "probability": [{"name": "L"}, {"name": "H"}],
                "impact": [{"name": "L"}, {"name": "H"}],
                "risk": [{"name": "L"}, {"name": "H"}],
                "grid": [[0, 5], [0, 1]],  # cell 5 indexes past the risk array
            }
        ]
    }
    draft = _create_draft(admin_client, packager="me", ref_id="mtx", content=content)
    errors = admin_client.get(
        reverse("library-drafts-validate", args=[draft["id"]])
    ).data["errors"]
    assert any("risk_matrices[0]" in e for e in errors), errors


@pytest.mark.django_db
def test_check_identity_rejects_a_malformed_exclude_draft(admin_client):
    response = admin_client.get(
        reverse("library-drafts-check-identity"),
        {"packager": "me", "ref_id": "lib", "exclude_draft": "not-a-uuid"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_adopt_publish_preserves_mixed_case_and_dangling_nodes(admin_client):
    root = Folder.get_root_folder()
    framework = Framework.objects.create(name="Legacy", folder=root, urn=None)
    kept = RequirementNode.objects.create(
        framework=framework,
        folder=root,
        name="Mixed case",
        ref_id="A",
        assessable=True,
        order_id=0,
        urn="urn:custom:risk:req_node:LEGACY:A1",  # mixed case, API-writable
    )
    orphan = RequirementNode.objects.create(
        framework=framework,
        folder=root,
        name="Orphan",
        ref_id="B",
        assessable=True,
        order_id=1,
        urn="urn:custom:risk:req_node:legacy:b",
        parent_urn="urn:custom:risk:req_node:legacy:gone",  # dangling parent
    )
    framework.urn = "urn:custom:risk:framework:legacy"
    framework.save(update_fields=["urn"])

    adopt = admin_client.post(
        reverse("library-drafts-adopt"), {"framework": str(framework.id)}, format="json"
    )
    assert adopt.status_code == status.HTTP_201_CREATED, adopt.content
    draft_id = adopt.data["id"]

    # Mixed-case URN normalized in place; dangling node promoted (kept).
    kept.refresh_from_db()
    assert kept.urn == "urn:custom:risk:req_node:legacy:a1"
    doc_nodes = adopt.data["content"]["frameworks"][0]["requirement_nodes"]
    doc_urns = {n["urn"] for n in doc_nodes}
    assert "urn:custom:risk:req_node:legacy:a1" in doc_urns
    assert "urn:custom:risk:req_node:legacy:b" in doc_urns  # not dropped

    publish = admin_client.post(
        reverse("library-drafts-publish", args=[draft_id]), {}, format="json"
    )
    assert publish.status_code == status.HTTP_200_OK, publish.content
    # Both original live rows survive (same ids), nothing pruned.
    assert RequirementNode.objects.filter(id=kept.id).exists()
    assert RequirementNode.objects.filter(id=orphan.id).exists()


@pytest.mark.django_db
def test_publish_detaches_removed_reference_control_links(admin_client):
    # The control ships in the library and is materialized by publish — not
    # pre-created (which would collide on the loader's unique URN).
    content = {
        "reference_controls": [
            {
                "urn": "urn:me:risk:reference_control:linklib:c1",
                "ref_id": "C1",
                "name": "Ctrl",
            }
        ],
        "frameworks": [
            {
                "urn": "urn:me:risk:framework:linklib",
                "ref_id": "L",
                "name": "L",
                "requirement_nodes": [
                    {
                        "urn": "urn:me:risk:req_node:linklib:a",
                        "ref_id": "A",
                        "assessable": True,
                        "depth": 1,
                        "reference_controls": [
                            "urn:me:risk:reference_control:linklib:c1"
                        ],
                    }
                ],
            }
        ],
    }
    draft = _create_draft(
        admin_client, packager="me", ref_id="linklib", content=content
    )
    detail_url = reverse("library-drafts-detail", args=[draft["id"]])
    publish_url = reverse("library-drafts-publish", args=[draft["id"]])
    assert (
        admin_client.post(publish_url, {}, format="json").status_code
        == status.HTTP_200_OK
    )
    node = RequirementNode.objects.get(urn="urn:me:risk:req_node:linklib:a")
    control = ReferenceControl.objects.get(
        urn="urn:me:risk:reference_control:linklib:c1"
    )
    assert node.reference_controls.filter(id=control.id).exists()

    # Remove the link in the document and republish → live row must drop it.
    current = admin_client.get(detail_url).data["content"]
    current["frameworks"][0]["requirement_nodes"][0].pop("reference_controls", None)
    content_patch = admin_client.patch(detail_url, {"content": current}, format="json")
    assert content_patch.status_code == status.HTTP_200_OK, content_patch.content
    version_patch = admin_client.patch(detail_url, {"version": 2}, format="json")
    assert version_patch.status_code == status.HTTP_200_OK, version_patch.content
    republish = admin_client.post(publish_url, {}, format="json")
    assert republish.status_code == status.HTTP_200_OK, republish.content
    node.refresh_from_db()
    assert not node.reference_controls.filter(id=control.id).exists()


# ---------------------------------------------------------------------------
# Import a YAML file directly into an editable draft
# ---------------------------------------------------------------------------


def _yaml_upload(name, raw: bytes):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, raw, content_type="application/yaml")


@pytest.mark.django_db
def test_import_yaml_seeds_an_editable_draft(admin_client):
    raw = (LIBRARIES_DIR / "critical_risk_matrix_5x5.yaml").read_bytes()
    response = admin_client.post(
        reverse("library-drafts-import-yaml"),
        {"file": _yaml_upload("matrix.yaml", raw)},
        format="multipart",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    draft = response.data
    # Editable: not published anywhere, so identity is not frozen.
    assert draft["identity_locked"] is False
    assert draft["packager"] == "intuitem"
    assert draft["ref_id"] == "critical_risk_matrix_5x5"
    # Minted effective_urn matches the imported library's own URN family.
    assert draft["urn"] == "urn:intuitem:risk:library:critical_risk_matrix_5x5"
    assert draft["content"]["risk_matrices"][0]["urn"] == (
        "urn:intuitem:risk:matrix:critical_risk_matrix_5x5"
    )


@pytest.mark.django_db
def test_imported_draft_identity_is_renameable_and_rebases(admin_client):
    raw = (LIBRARIES_DIR / "critical_risk_matrix_5x5.yaml").read_bytes()
    draft_id = admin_client.post(
        reverse("library-drafts-import-yaml"),
        {"file": _yaml_upload("matrix.yaml", raw)},
        format="multipart",
    ).data["id"]

    detail_url = reverse("library-drafts-detail", args=[draft_id])
    renamed = admin_client.patch(
        detail_url, {"packager": "me", "ref_id": "mymatrix"}, format="json"
    )
    assert renamed.status_code == status.HTTP_200_OK, renamed.content

    updated = admin_client.get(detail_url).data
    assert updated["urn"] == "urn:me:risk:library:mymatrix"
    # The whole URN family rebased across the document.
    assert updated["content"]["risk_matrices"][0]["urn"] == (
        "urn:me:risk:matrix:mymatrix"
    )


@pytest.mark.django_db
def test_import_yaml_rejects_malformed_and_empty_files(admin_client):
    bad = admin_client.post(
        reverse("library-drafts-import-yaml"),
        {"file": _yaml_upload("bad.yaml", b"just: a: scalar: mess: [")},
        format="multipart",
    )
    assert bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    scalar = admin_client.post(
        reverse("library-drafts-import-yaml"),
        {"file": _yaml_upload("scalar.yaml", b"not a library")},
        format="multipart",
    )
    assert scalar.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    no_objects = admin_client.post(
        reverse("library-drafts-import-yaml"),
        {"file": _yaml_upload("empty.yaml", b"urn: urn:x:risk:library:x\nname: X\n")},
        format="multipart",
    )
    assert no_objects.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.django_db
def test_import_yaml_requires_a_file(admin_client):
    response = admin_client.post(
        reverse("library-drafts-import-yaml"), {}, format="multipart"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Clone objects from another draft (not just stored libraries)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_objects_clones_from_a_draft_source(admin_client):
    # A source draft holding a couple of threats.
    source = _create_draft(
        admin_client,
        packager="src",
        ref_id="sourcedraft",
        content={
            "threats": [
                {
                    "urn": "urn:src:risk:threat:sourcedraft:t1",
                    "ref_id": "T1",
                    "name": "T1",
                },
                {
                    "urn": "urn:src:risk:threat:sourcedraft:t2",
                    "ref_id": "T2",
                    "name": "T2",
                },
            ]
        },
    )
    target = _create_draft(admin_client, packager="me", ref_id="target", content={})
    response = admin_client.post(
        reverse("library-drafts-import-objects", args=[target["id"]]),
        {"source": f"draft:{source['id']}", "object_types": ["threats"]},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    # Copy-by-value, rebased onto the target's identity.
    threats = {t["urn"] for t in response.data["draft"]["content"]["threats"]}
    assert threats == {
        "urn:me:risk:threat:target:t1",
        "urn:me:risk:threat:target:t2",
    }


@pytest.mark.django_db
def test_import_objects_rejects_importing_from_self(admin_client):
    draft = _create_draft(
        admin_client,
        content={
            "threats": [
                {"urn": "urn:me:risk:threat:mylib:t1", "ref_id": "T1", "name": "T"}
            ]
        },
    )
    response = admin_client.post(
        reverse("library-drafts-import-objects", args=[draft["id"]]),
        {"source": f"draft:{draft['id']}"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "cannotImportFromSelf"


@pytest.mark.django_db
def test_import_objects_from_unknown_draft_is_not_found(admin_client):
    # The readable-draft gate reuses is_object_readable (RBAC covered by the
    # stored-library tests); here assert an unknown id resolves to a clean 404.
    target = _create_draft(admin_client, packager="me", ref_id="t", content={})
    response = admin_client.post(
        reverse("library-drafts-import-objects", args=[target["id"]]),
        {"source": "draft:00000000-0000-0000-0000-000000000000"},
        format="json",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Deleting a framework and a journey preset from a draft
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_object_removes_a_framework(admin_client):
    draft = _create_draft(
        admin_client,
        packager="me",
        ref_id="fwlib",
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:fwlib",
                    "ref_id": "F",
                    "name": "F",
                    "requirement_nodes": [],
                }
            ]
        },
    )
    response = admin_client.post(
        reverse("library-drafts-delete-object", args=[draft["id"]]),
        {"urn": "urn:me:risk:framework:fwlib"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    assert "frameworks" not in response.data["draft"]["content"]


@pytest.mark.django_db
def test_delete_framework_blocked_by_a_mapping_set(admin_client):
    draft = _create_draft(
        admin_client,
        packager="me",
        ref_id="mfw",
        content={
            "frameworks": [
                {
                    "urn": "urn:me:risk:framework:mfw",
                    "ref_id": "F",
                    "name": "F",
                    "requirement_nodes": [],
                }
            ],
            "requirement_mapping_sets": [
                {
                    "urn": "urn:me:risk:req_mapping_set:mfw:m1",
                    "ref_id": "M1",
                    "name": "M1",
                    "source_framework_urn": "urn:me:risk:framework:mfw",
                    "target_framework_urn": "urn:other:risk:framework:x",
                    "requirement_mappings": [],
                }
            ],
        },
    )
    response = admin_client.post(
        reverse("library-drafts-delete-object", args=[draft["id"]]),
        {"urn": "urn:me:risk:framework:mfw"},
        format="json",
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["error"] == "objectIsReferencedByMappingSet"


@pytest.mark.django_db
def test_delete_object_removes_the_journey_preset(admin_client):
    draft = _create_draft(
        admin_client,
        packager="me",
        ref_id="presetlib",
        content={"preset": {"name": "Onboarding", "journey": {"steps": []}}},
    )
    response = admin_client.post(
        reverse("library-drafts-delete-object", args=[draft["id"]]),
        {"field": "preset"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    assert "preset" not in response.data["draft"]["content"]

    # Removing it again is a clean 404.
    again = admin_client.post(
        reverse("library-drafts-delete-object", args=[draft["id"]]),
        {"field": "preset"},
        format="json",
    )
    assert again.status_code == status.HTTP_404_NOT_FOUND
