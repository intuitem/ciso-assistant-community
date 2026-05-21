"""End-to-end tests for the AppliedControl /merge/ action: direct M2M union,
reverse-M2M rewire, FK rewire, permission gating, dry-run preview,
ManagedDocument conflict detection + resolution, source-count cap, and
registry-drift guards."""

import pytest

from core.models import (
    AppliedControl,
    Asset,
    Comment,
    Evidence,
    Framework,
    RequirementAssessment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
)
from iam.models import Folder

MERGE_URL = "/api/applied-controls/merge/"


# --- helpers -----------------------------------------------------------------


def _make_control(folder, name, **kwargs):
    return AppliedControl.objects.create(name=name, folder=folder, **kwargs)


def _make_compliance_assessment(folder):
    """Create a minimal ComplianceAssessment + RequirementAssessment for rewire tests."""
    from core.models import ComplianceAssessment

    framework = Framework.objects.create(
        urn="urn:test:framework:merge", folder=folder, name="merge-test"
    )
    req = RequirementNode.objects.create(
        urn="urn:test:framework:merge:r1",
        folder=folder,
        framework=framework,
        assessable=True,
    )
    audit = ComplianceAssessment.objects.create(
        name="audit", folder=folder, framework=framework
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=audit, requirement=req, folder=folder
    )
    return ra


def _make_risk_scenario(folder):
    matrix_lib_urn = "urn:intuitem:risk:library:critical_risk_matrix_3x3"
    matrix = RiskMatrix.objects.filter(
        urn__icontains="critical_risk_matrix_3x3"
    ).first() or RiskMatrix.objects.create(
        urn=matrix_lib_urn,
        folder=folder,
        name="3x3",
        json_definition={
            "type": "risk_matrix",
            "name": "3x3",
            "description": "",
            "probability": [
                {"abbreviation": "L", "name": "Low", "description": ""},
                {"abbreviation": "M", "name": "Medium", "description": ""},
                {"abbreviation": "H", "name": "High", "description": ""},
            ],
            "impact": [
                {"abbreviation": "L", "name": "Low", "description": ""},
                {"abbreviation": "M", "name": "Medium", "description": ""},
                {"abbreviation": "H", "name": "High", "description": ""},
            ],
            "risk": [
                {
                    "abbreviation": "VL",
                    "name": "Very Low",
                    "description": "",
                    "hexcolor": "#fff",
                },
                {
                    "abbreviation": "L",
                    "name": "Low",
                    "description": "",
                    "hexcolor": "#fff",
                },
                {
                    "abbreviation": "H",
                    "name": "High",
                    "description": "",
                    "hexcolor": "#fff",
                },
            ],
            "grid": [[0, 1, 2], [0, 1, 2], [0, 1, 2]],
        },
    )
    risk_assessment = RiskAssessment.objects.create(
        name="ra", folder=folder, risk_matrix=matrix
    )
    return RiskScenario.objects.create(
        name="scn", folder=folder, risk_assessment=risk_assessment
    )


@pytest.fixture
def folder(db):
    return Folder.objects.create(name="merge-test-folder")


@pytest.fixture
def other_folder(db):
    return Folder.objects.create(name="merge-test-folder-2")


# --- core rewire contract ---------------------------------------------------


@pytest.mark.django_db
def test_merge_target_new_unions_m2ms_and_rewires_reverse_relations(
    authenticated_client, folder
):
    """target=new: direct M2Ms unioned, reverse M2M (RA) rewired, sources deleted."""
    asset_a = Asset.objects.create(name="asset-a", folder=folder)
    asset_b = Asset.objects.create(name="asset-b", folder=folder)
    evidence = Evidence.objects.create(name="ev", folder=folder)

    src1 = _make_control(folder, "src-1")
    src1.assets.add(asset_a)
    src1.evidences.add(evidence)
    src2 = _make_control(folder, "src-2")
    src2.assets.add(asset_b)

    ra = _make_compliance_assessment(folder)
    ra.applied_controls.add(src1)

    payload = {
        "source_ids": [str(src1.id), str(src2.id)],
        "target": {
            "type": "new",
            "fields": {"name": "merged", "folder": str(folder.id)},
        },
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")

    assert resp.status_code == 200, resp.json()
    body = resp.json()
    target = AppliedControl.objects.get(id=body["target_id"])
    assert target.name == "merged"
    assert set(target.assets.values_list("id", flat=True)) == {asset_a.id, asset_b.id}
    assert set(target.evidences.values_list("id", flat=True)) == {evidence.id}
    assert ra.applied_controls.filter(id=target.id).exists()
    assert not AppliedControl.objects.filter(id__in=[src1.id, src2.id]).exists()
    assert body["rewired"]["RequirementAssessment"] == 1
    assert body["target_is_new"] is True


@pytest.mark.django_db
def test_merge_target_existing_survivor(authenticated_client, folder):
    """target=existing where target is one of the originally-selected rows."""
    survivor = _make_control(folder, "keep-me")
    src = _make_control(folder, "absorb-me")
    asset = Asset.objects.create(name="x", folder=folder)
    src.assets.add(asset)

    payload = {
        # serializer strips the target id from source_ids → survivor merge
        "source_ids": [str(survivor.id), str(src.id)],
        "target": {"type": "existing", "id": str(survivor.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")

    assert resp.status_code == 200, resp.json()
    survivor.refresh_from_db()
    assert survivor.name == "keep-me"  # scalars untouched on existing target
    assert set(survivor.assets.values_list("id", flat=True)) == {asset.id}
    assert not AppliedControl.objects.filter(id=src.id).exists()


@pytest.mark.django_db
def test_replace_a_with_b_single_source(authenticated_client, folder):
    """Replace flow: one source, target = unrelated existing control."""
    src = _make_control(folder, "old")
    target = _make_control(folder, "new")
    Comment.objects.create(applied_control=src, body="hi", author_id=None)

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")

    assert resp.status_code == 200, resp.json()
    assert not AppliedControl.objects.filter(id=src.id).exists()
    assert Comment.objects.filter(applied_control=target).count() == 1


@pytest.mark.django_db
def test_through_table_dedup(authenticated_client, folder):
    """When the same RA already references both source and target, no duplicate after merge."""
    src = _make_control(folder, "src")
    target = _make_control(folder, "tgt")
    ra = _make_compliance_assessment(folder)
    ra.applied_controls.add(src, target)
    assert ra.applied_controls.count() == 2

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    assert ra.applied_controls.count() == 1
    assert ra.applied_controls.first().id == target.id


@pytest.mark.django_db
def test_risk_scenario_existing_vs_added_are_independent(authenticated_client, folder):
    """RiskScenario has TWO M2Ms to AppliedControl (applied_controls + existing_applied_controls).
    Both should be rewired but kept separate."""
    scn = _make_risk_scenario(folder)
    src = _make_control(folder, "src")
    target = _make_control(folder, "tgt")
    scn.applied_controls.add(src)
    scn.existing_applied_controls.add(src)

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    assert scn.applied_controls.filter(id=target.id).exists()
    assert scn.existing_applied_controls.filter(id=target.id).exists()


# --- guards -----------------------------------------------------------------


@pytest.mark.django_db
def test_too_many_sources_rejected(authenticated_client, folder):
    target = _make_control(folder, "tgt")
    sources = [_make_control(folder, f"s{i}") for i in range(21)]
    payload = {
        "source_ids": [str(s.id) for s in sources],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 400
    # All 21 sources still present
    assert AppliedControl.objects.filter(id__in=[s.id for s in sources]).count() == 21


@pytest.mark.django_db
def test_dry_run_does_not_modify_state(authenticated_client, folder):
    src = _make_control(folder, "src")
    target = _make_control(folder, "tgt")
    asset = Asset.objects.create(name="a", folder=folder)
    src.assets.add(asset)

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
        "dry_run": True,
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert "rewired_preview" in body
    assert "unioned_m2m_preview" in body
    # State unchanged
    assert AppliedControl.objects.filter(id=src.id).exists()
    assert not target.assets.filter(id=asset.id).exists()


@pytest.mark.django_db
def test_folder_mismatch_flag(authenticated_client, folder, other_folder):
    src = _make_control(folder, "src")
    target = _make_control(other_folder, "tgt")
    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
        "dry_run": True,
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    assert resp.json()["folder_mismatch"] is True


# --- managed-document conflict ----------------------------------------------


@pytest.mark.django_db
def test_managed_document_conflict_detected_on_dry_run(authenticated_client, folder):
    """When two sources each have a managed document, dry-run flags a conflict."""
    from doc_management.models import ManagedDocument

    src1 = _make_control(folder, "p1")
    src2 = _make_control(folder, "p2")
    target = _make_control(folder, "tgt")
    doc1 = ManagedDocument.objects.create(name="doc1", policy_id=src1.id, folder=folder)
    doc2 = ManagedDocument.objects.create(name="doc2", policy_id=src2.id, folder=folder)

    payload = {
        "source_ids": [str(src1.id), str(src2.id)],
        "target": {"type": "existing", "id": str(target.id)},
        "dry_run": True,
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    conflict = resp.json()["managed_document_conflict"]
    assert conflict is not None
    candidate_ids = {c["id"] for c in conflict["candidates"]}
    assert {str(doc1.id), str(doc2.id)}.issubset(candidate_ids)


@pytest.mark.django_db
def test_managed_document_conflict_blocks_real_merge_without_resolution(
    authenticated_client, folder
):
    from doc_management.models import ManagedDocument

    src1 = _make_control(folder, "p1")
    src2 = _make_control(folder, "p2")
    target = _make_control(folder, "tgt")
    ManagedDocument.objects.create(name="doc1", policy_id=src1.id, folder=folder)
    ManagedDocument.objects.create(name="doc2", policy_id=src2.id, folder=folder)

    payload = {
        "source_ids": [str(src1.id), str(src2.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 400
    assert "managed_document" in str(resp.content).lower()
    # Sources untouched
    assert AppliedControl.objects.filter(id__in=[src1.id, src2.id]).count() == 2


@pytest.mark.django_db
def test_managed_document_resolution_keeps_one_unlinks_others(
    authenticated_client, folder
):
    from doc_management.models import ManagedDocument

    src1 = _make_control(folder, "p1")
    src2 = _make_control(folder, "p2")
    target = _make_control(folder, "tgt")
    keep_doc = ManagedDocument.objects.create(
        name="keep", policy_id=src1.id, folder=folder
    )
    drop_doc = ManagedDocument.objects.create(
        name="drop", policy_id=src2.id, folder=folder
    )

    payload = {
        "source_ids": [str(src1.id), str(src2.id)],
        "target": {"type": "existing", "id": str(target.id)},
        "managed_document_resolution": {"keep": str(keep_doc.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()

    keep_doc.refresh_from_db()
    drop_doc.refresh_from_db()
    assert keep_doc.policy_id == target.id
    assert drop_doc.policy_id is None  # unlinked, not deleted
    assert ManagedDocument.objects.filter(id=drop_doc.id).exists()


@pytest.mark.django_db
def test_single_source_with_docs_no_conflict_just_repoints(
    authenticated_client, folder
):
    """1 source with multiple docs is NOT a conflict — siblings stay siblings on target."""
    from doc_management.models import ManagedDocument

    src = _make_control(folder, "src")
    target = _make_control(folder, "tgt")
    # ManagedDocument enforces unique (policy, locale) — different locales to coexist.
    doc1 = ManagedDocument.objects.create(
        name="d1", policy_id=src.id, folder=folder, locale="en"
    )
    doc2 = ManagedDocument.objects.create(
        name="d2", policy_id=src.id, folder=folder, locale="fr"
    )

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    doc1.refresh_from_db()
    doc2.refresh_from_db()
    assert doc1.policy_id == target.id
    assert doc2.policy_id == target.id


# --- policy proxy path ------------------------------------------------------


POLICY_MERGE_URL = "/api/policies/merge/"


@pytest.mark.django_db
def test_policy_merge_target_new_keeps_category_policy(authenticated_client, folder):
    """Merging policies via /policies/merge/ with target=new must produce a row
    classified as a policy so it still appears in the Policies list view."""
    from core.models import Policy

    src1 = Policy.objects.create(name="pol-1", folder=folder)
    src2 = Policy.objects.create(name="pol-2", folder=folder)

    payload = {
        "source_ids": [str(src1.id), str(src2.id)],
        "target": {
            "type": "new",
            "fields": {"name": "merged-policy", "folder": str(folder.id)},
        },
    }
    resp = authenticated_client.post(POLICY_MERGE_URL, payload, format="json")

    assert resp.status_code == 200, resp.json()
    target_id = resp.json()["target_id"]
    # The merged row must be visible through the Policy proxy (category='policy').
    assert Policy.objects.filter(id=target_id).exists()
    assert AppliedControl.objects.get(id=target_id).category == "policy"
    assert not AppliedControl.objects.filter(id__in=[src1.id, src2.id]).exists()


@pytest.mark.django_db
def test_policy_merge_target_new_overrides_caller_category(
    authenticated_client, folder
):
    """Even if the caller passes a non-policy category on /policies/merge/,
    the endpoint must force category='policy' so the result stays visible in
    the Policies list."""
    from core.models import Policy

    src = Policy.objects.create(name="pol-a", folder=folder)

    payload = {
        "source_ids": [str(src.id)],
        "target": {
            "type": "new",
            "fields": {
                "name": "still-policy",
                "folder": str(folder.id),
                # Caller tries to sneak in a different category.
                "category": "technical",
            },
        },
    }
    resp = authenticated_client.post(POLICY_MERGE_URL, payload, format="json")
    assert resp.status_code == 200, resp.json()
    target_id = resp.json()["target_id"]
    assert Policy.objects.filter(id=target_id).exists()
    assert AppliedControl.objects.get(id=target_id).category == "policy"


# --- permission denial paths ------------------------------------------------


def _patch_perm_denial(monkeypatch, denied_codename: str):
    """Make RoleAssignment.is_access_allowed return False for the given
    permission codename, True otherwise. Used to simulate a user who can see
    the rows but lacks specific change/delete/add rights."""
    from iam.models import RoleAssignment

    def fake(user, perm, folder, **kwargs):
        return perm.codename != denied_codename

    monkeypatch.setattr(RoleAssignment, "is_access_allowed", staticmethod(fake))


@pytest.mark.django_db
def test_merge_denied_when_user_lacks_change_on_source_folder(
    authenticated_client, folder, monkeypatch
):
    src = _make_control(folder, "src")
    target = _make_control(folder, "tgt")
    _patch_perm_denial(monkeypatch, "change_appliedcontrol")

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 403, resp.content
    # No mutation — both controls still present
    assert AppliedControl.objects.filter(id__in=[src.id, target.id]).count() == 2


@pytest.mark.django_db
def test_merge_denied_when_user_lacks_delete_on_source_folder(
    authenticated_client, folder, monkeypatch
):
    src = _make_control(folder, "src")
    target = _make_control(folder, "tgt")
    _patch_perm_denial(monkeypatch, "delete_appliedcontrol")

    payload = {
        "source_ids": [str(src.id)],
        "target": {"type": "existing", "id": str(target.id)},
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 403, resp.content
    assert AppliedControl.objects.filter(id__in=[src.id, target.id]).count() == 2


@pytest.mark.django_db
def test_merge_new_target_denied_when_user_lacks_add_on_target_folder(
    authenticated_client, folder, monkeypatch
):
    """target=new must refuse if the user can't create AppliedControls in the
    target folder, and the new row must not be persisted."""
    src = _make_control(folder, "src")
    before_count = AppliedControl.objects.count()
    _patch_perm_denial(monkeypatch, "add_appliedcontrol")

    payload = {
        "source_ids": [str(src.id)],
        "target": {
            "type": "new",
            "fields": {"name": "would-be-target", "folder": str(folder.id)},
        },
    }
    resp = authenticated_client.post(MERGE_URL, payload, format="json")
    assert resp.status_code == 403, resp.content
    # Source untouched, no orphan target created (the security-refactor guarantee).
    assert AppliedControl.objects.filter(id=src.id).exists()
    assert AppliedControl.objects.count() == before_count


# --- rewire-registry drift guards -------------------------------------------


@pytest.mark.django_db
def test_reverse_m2m_registry_covers_all_introspected_relations():
    """Every reverse M2M on AppliedControl must be registered in
    _reverse_m2m_through_tables(), else it will silently orphan through-rows."""
    from core.applied_controls_helper import (
        _expected_reverse_m2m_throughs,
        _registered_reverse_m2m_throughs,
    )

    missing = _expected_reverse_m2m_throughs() - _registered_reverse_m2m_throughs()
    assert not missing, (
        f"Reverse M2M(s) on AppliedControl not registered for merge rewire: "
        f"{[m.__name__ for m in missing]}"
    )


@pytest.mark.django_db
def test_direct_m2m_fields_covers_all_declared_fields():
    """Every M2M declared on AppliedControl must be listed in DIRECT_M2M_FIELDS
    so the target inherits those relations during merge."""
    from core.applied_controls_helper import (
        DIRECT_M2M_FIELDS,
        _expected_direct_m2m_fields,
    )

    missing = _expected_direct_m2m_fields() - set(DIRECT_M2M_FIELDS)
    assert not missing, (
        f"Direct M2M field(s) on AppliedControl not in DIRECT_M2M_FIELDS: {missing}"
    )
