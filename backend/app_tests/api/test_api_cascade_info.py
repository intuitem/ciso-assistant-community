import pytest
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import AppliedControl, Asset, Comment, Policy, ReferenceControl
from core.views import FolderViewSet
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def target_folder(app_ready):
    folder = Folder.objects.create(
        name="Target", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )
    Asset.objects.create(name="CANARY-ASSET", folder=folder)
    return folder


def _scoped_client(email, role_name, folder, app_ready, is_recursive=True):
    user = User.objects.create_user(email)
    user.folder = app_ready
    user.save()
    group = UserGroup.objects.create(name=f"grp-{email}", folder=folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_name),
        folder=folder,
        is_recursive=is_recursive,
    )
    assignment.perimeter_folders.add(folder)
    return _client(user)


@pytest.fixture
def admin_client(app_ready):
    user = User.objects.create_user("admin@cascade.test")
    group = UserGroup.objects.get(name="BI-UG-ADM", folder=app_ready)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


def _url(folder):
    return f"/api/folders/{folder.id}/cascade-info/"


# Roles that hold view_folder but not delete_folder
@pytest.mark.parametrize(
    "role_name",
    ["BI-RL-AUD", "BI-RL-ANA", "BI-RL-APP", "BI-RL-ADE", "BI-RL-TPR", "BI-RL-TST"],
)
def test_view_only_roles_are_denied(app_ready, target_folder, role_name):
    client = _scoped_client(
        f"{role_name}@cascade.test", role_name, target_folder, app_ready
    )
    resp = client.get(_url(target_folder))
    assert resp.status_code == 403
    assert "CANARY-ASSET" not in resp.content.decode()


def test_user_without_role_is_denied(app_ready, target_folder):
    user = User.objects.create_user("norole@cascade.test")
    user.folder = app_ready
    user.save()
    resp = _client(user).get(_url(target_folder))
    assert resp.status_code in (403, 404)


def test_domain_manager_is_allowed(app_ready, target_folder):
    client = _scoped_client("dma@cascade.test", "BI-RL-DMA", target_folder, app_ready)
    resp = client.get(_url(target_folder))
    assert resp.status_code == 200
    assert "CANARY-ASSET" in resp.content.decode()


def test_admin_is_allowed(admin_client, target_folder):
    resp = admin_client.get(_url(target_folder))
    assert resp.status_code == 200
    assert "CANARY-ASSET" in resp.content.decode()


def test_cross_folder_m2m_endpoint_is_not_disclosed(app_ready, target_folder):
    # An M2M link reaching out of the deleted subtree bubbles both endpoints,
    # so the far object must be filtered out unless independently viewable.
    secret = Folder.objects.create(
        name="Secret", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )
    hidden_parent = Asset.objects.create(name="SECRET-PARENT-ASSET", folder=secret)
    child = Asset.objects.create(name="my-child", folder=target_folder)
    child.parent_assets.add(hidden_parent)

    client = _scoped_client("dma2@cascade.test", "BI-RL-DMA", target_folder, app_ready)
    resp = client.get(_url(target_folder))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "my-child" in body
    assert "SECRET-PARENT-ASSET" not in body
    assert str(hidden_parent.id) not in body


def test_role_assignment_emails_not_leaked_to_view_only_role(app_ready, target_folder):
    victim = User.objects.create_user("victim@cascade.test")
    victim.folder = app_ready
    victim.save()
    group = UserGroup.objects.create(name="victim-grp", folder=target_folder)
    group.user_set.add(victim)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-DMA"),
        folder=target_folder,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(target_folder)

    client = _scoped_client(
        "auditee@cascade.test", "BI-RL-ADE", target_folder, app_ready
    )
    resp = client.get(_url(target_folder))
    assert resp.status_code == 403
    assert "victim@cascade.test" not in resp.content.decode()


# ---------------------------------------------------------------------------
# Entity assessments: the destroy override deletes the linked audit when it
# lives in an enclave (third party workspace), even though the FK is SET_NULL. The preview must say so.
# ---------------------------------------------------------------------------


def _entity_assessment_with_audit(folder, enclave: bool):
    import uuid

    from core.models import ComplianceAssessment, Framework, Perimeter
    from tprm.models import Entity, EntityAssessment

    perimeter = Perimeter.objects.create(name="Perimeter", folder=folder)
    entity = Entity.objects.create(name="Vendor", folder=folder)
    framework = Framework.objects.create(
        folder=Folder.get_root_folder(),
        name="fw",
        urn=f"urn:test:framework:{uuid.uuid4().hex[:12]}",
        ref_id="fw",
    )
    audit_folder = folder
    if enclave:
        audit_folder = Folder.objects.create(
            name="Vendor",
            parent_folder=folder,
            content_type=Folder.ContentType.ENCLAVE,
        )
    audit = ComplianceAssessment.objects.create(
        name="VENDOR-AUDIT",
        folder=audit_folder,
        framework=framework,
        perimeter=None if enclave else perimeter,
    )
    return EntityAssessment.objects.create(
        name="EA",
        folder=folder,
        perimeter=perimeter,
        entity=entity,
        compliance_assessment=audit,
    )


def _bucket_names(bucket: dict) -> set[str]:
    return {o["name"] for o in bucket["related_objects"]}


def test_entity_assessment_preview_reports_enclave_audit_as_deleted(
    admin_client, target_folder
):
    ea = _entity_assessment_with_audit(target_folder, enclave=True)
    res = admin_client.get(f"/api/entity-assessments/{ea.id}/cascade-info/")
    assert res.status_code == 200
    assert "VENDOR-AUDIT" in _bucket_names(res.json()["deleted"])
    assert "VENDOR-AUDIT" not in _bucket_names(res.json()["affected"])


def test_entity_assessment_preview_in_shared_enclave_only_deletes_own_audit(
    admin_client, target_folder
):
    from core.models import ComplianceAssessment

    ea = _entity_assessment_with_audit(target_folder, enclave=True)
    ComplianceAssessment.objects.create(
        name="SIBLING-AUDIT",
        folder=ea.compliance_assessment.folder,
        framework=ea.compliance_assessment.framework,
    )
    res = admin_client.get(f"/api/entity-assessments/{ea.id}/cascade-info/")
    assert res.status_code == 200
    deleted = _bucket_names(res.json()["deleted"])
    assert "VENDOR-AUDIT" in deleted
    assert "SIBLING-AUDIT" not in deleted


def test_entity_assessment_preview_keeps_non_enclave_audit_as_affected(
    admin_client, target_folder
):
    ea = _entity_assessment_with_audit(target_folder, enclave=False)
    res = admin_client.get(f"/api/entity-assessments/{ea.id}/cascade-info/")
    assert res.status_code == 200
    assert "VENDOR-AUDIT" in _bucket_names(res.json()["affected"])
    assert "VENDOR-AUDIT" not in _bucket_names(res.json()["deleted"])


@pytest.fixture
def domain_tree(target_folder: Folder) -> dict[str, Folder]:
    sub = Folder.objects.create(
        name="SUB-DOMAIN",
        parent_folder=target_folder,
        content_type=Folder.ContentType.DOMAIN,
    )
    sub_sub = Folder.objects.create(
        name="SUB-SUB-DOMAIN", parent_folder=sub, content_type=Folder.ContentType.DOMAIN
    )
    Asset.objects.create(name="SUB-ASSET", folder=sub)
    Asset.objects.create(name="SUB-SUB-ASSET", folder=sub_sub)
    return {"target": target_folder, "sub": sub, "sub_sub": sub_sub}


MOVE_PREVIEW_URL = "/api/folders/move-preview/"


def _counts(payload: dict) -> dict[str, int]:
    return {g["label"]: g["count"] for g in payload["carried"]["groups"]}


def test_single_delete_preview_still_names_what_a_non_recursive_role_destroys(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """Deleting a domain names what it destroys, sub-domain content included, even
    for a non-recursive role."""
    client = _scoped_client(
        "non-recursive-delete@cascade.test",
        "BI-RL-DMA",
        domain_tree["target"],
        app_ready,
        is_recursive=False,
    )

    res = client.get(_url(domain_tree["target"]))

    assert res.status_code == 200, res.content
    deleted = res.json()["deleted"]
    assert {"SUB-ASSET", "SUB-SUB-ASSET"} <= _bucket_names(deleted)
    assert "hidden_count" not in deleted


def test_move_preview_lists_sub_domains_and_their_content_once(
    admin_client: APIClient, domain_tree: dict[str, Folder]
) -> None:
    """Selecting a domain and one of its descendants must not count the shared
    subtree twice, and the selected domains are the subjects, not what they carry."""
    res = admin_client.post(
        MOVE_PREVIEW_URL,
        {"ids": [str(domain_tree["target"].id), str(domain_tree["sub"].id)]},
        format="json",
    )

    assert res.status_code == 200, res.content
    payload = res.json()
    counts = _counts(payload)
    assert counts["domains"] == 1
    assert counts["assets"] == 3
    assert payload["carried"]["count"] == sum(counts.values())

    subjects = {s["name"]: s for s in payload["subjects"]}
    assert subjects["SUB-DOMAIN"]["below_selected"] is True
    assert subjects["Target"]["below_selected"] is False


def test_move_preview_is_denied_to_a_view_only_role(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    client = _scoped_client(
        "aud-batch@cascade.test", "BI-RL-AUD", domain_tree["target"], app_ready
    )
    res = client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 403
    assert "CANARY-ASSET" not in res.content.decode()


def test_entity_assessment_batch_delete_removes_enclave_audit(
    admin_client, target_folder
):
    from core.models import ComplianceAssessment

    ea = _entity_assessment_with_audit(target_folder, enclave=True)
    audit_id = ea.compliance_assessment_id
    res = admin_client.post(
        "/api/entity-assessments/batch-action/",
        {"action": "delete", "ids": [str(ea.id)]},
        format="json",
    )
    assert res.status_code == 200, res.content
    assert res.json()["failed"] == []
    assert not ComplianceAssessment.objects.filter(pk=audit_id).exists()


def _group(payload: dict, label: str) -> dict | None:
    return next(
        (g for g in payload["carried"]["groups"] if g["label"] == label),
        None,
    )


def test_carried_folders_are_grouped_by_type(
    admin_client: APIClient, domain_tree: dict[str, Folder]
) -> None:
    """An enclave moves with its domain, so it is listed, apart from the domains."""
    Folder.objects.create(
        name="SOME-ENCLAVE",
        parent_folder=domain_tree["target"],
        content_type=Folder.ContentType.ENCLAVE,
    )

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    assert _counts(res.json())["domains"] == 2
    assert _counts(res.json())["enclaves"] == 1


def test_move_preview_only_takes_domains_as_subjects(
    admin_client: APIClient, domain_tree: dict[str, Folder]
) -> None:
    enclave = Folder.objects.create(
        name="SELECTED-ENCLAVE",
        parent_folder=domain_tree["target"],
        content_type=Folder.ContentType.ENCLAVE,
    )

    alone = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(enclave.id)]}, format="json"
    )
    mixed = admin_client.post(
        MOVE_PREVIEW_URL,
        {"ids": [str(enclave.id), str(domain_tree["sub"].id)]},
        format="json",
    )

    assert alone.status_code == 403
    assert mixed.status_code == 200, mixed.content
    assert [s["name"] for s in mixed.json()["subjects"]] == ["SUB-DOMAIN"]


def test_move_preview_stops_counting_at_the_cap(
    admin_client: APIClient, domain_tree: dict[str, Folder], monkeypatch
) -> None:
    monkeypatch.setattr(FolderViewSet, "MOVE_PREVIEW_COUNT_CAP", 2)

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    payload = res.json()
    assets = _group(payload, "assets")
    assert (assets["count"], assets["capped"]) == (2, True)
    domains = _group(payload, "domains")
    assert (domains["count"], domains["capped"]) == (2, False)
    assert payload["carried"]["capped"] is True


def test_move_preview_queries_do_not_grow_with_the_selection(
    admin_client: APIClient, app_ready: Folder
) -> None:
    """The selected domains may not cost a query each."""
    domains = []
    for i in range(4):
        domain = Folder.objects.create(
            name=f"QC-{i}",
            parent_folder=app_ready,
            content_type=Folder.ContentType.DOMAIN,
        )
        Asset.objects.create(name=f"QC-ASSET-{i}", folder=domain)
        RoleAssignment.objects.create(
            user=User.objects.create_user(f"qc-{i}@cascade.test"),
            role=Role.objects.get(name="BI-RL-ANA"),
            folder=domain,
        )
        domains.append(domain)

    def queries(selected: list[Folder]) -> int:
        with CaptureQueriesContext(connection) as ctx:
            res = admin_client.post(
                MOVE_PREVIEW_URL,
                {"ids": [str(d.id) for d in selected]},
                format="json",
            )
        assert res.status_code == 200, res.content
        return len(ctx.captured_queries)

    queries(domains[:1])
    assert queries(domains) == queries(domains[:1])


def test_move_preview_lists_a_policy_once(
    admin_client: APIClient, target_folder: Folder
) -> None:
    """A policy is an applied control seen through a proxy: one row, counted once."""
    Policy.objects.create(name="LOCAL-POLICY", folder=target_folder)

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(target_folder.id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    assert _counts(res.json())["appliedControls"] == 1


def test_move_preview_needs_the_change_permission_not_the_delete_one(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    mover = Role.objects.create(name="MOVER", folder=app_ready)
    mover.permissions.set(
        Permission.objects.filter(
            codename__in=["view_folder", "change_folder", "view_asset"]
        )
    )
    client = _scoped_client(
        "mover@cascade.test", "MOVER", domain_tree["target"], app_ready
    )

    res = client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["sub"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    assert _counts(res.json())["assets"] == 2


def test_move_preview_leaves_out_what_stays_in_other_domains(
    admin_client: APIClient, app_ready: Folder, target_folder: Folder
) -> None:
    elsewhere = Folder.objects.create(
        name="ELSEWHERE",
        parent_folder=app_ready,
        content_type=Folder.ContentType.DOMAIN,
    )
    reference = ReferenceControl.objects.create(
        name="LOCAL-REFERENCE", folder=target_folder
    )
    AppliedControl.objects.create(
        name="FOREIGN-CONTROL", folder=elsewhere, reference_control=reference
    )

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(target_folder.id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    counts = _counts(res.json())
    assert counts["referenceControls"] == 1
    assert "appliedControls" not in counts


def test_move_preview_counts_without_naming(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """A non-recursive role grants nothing on the sub-domains: what they hold still
    counts, as it moves too, but no object is ever named."""
    client = _scoped_client(
        "non-recursive@cascade.test",
        "BI-RL-DMA",
        domain_tree["target"],
        app_ready,
        is_recursive=False,
    )

    res = client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    payload = res.json()
    assert (_counts(payload)["domains"], _counts(payload)["assets"]) == (2, 3)
    assert all(
        set(g) == {"label", "count", "capped"} for g in payload["carried"]["groups"]
    )
    for name in [
        "CANARY-ASSET",
        "SUB-DOMAIN",
        "SUB-ASSET",
        "non-recursive@cascade.test",
    ]:
        assert name not in res.content.decode()


def test_move_preview_refuses_builtin_domains(
    admin_client: APIClient, app_ready: Folder
) -> None:
    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(app_ready.id)]}, format="json"
    )

    assert res.status_code == 403


def test_move_preview_sums_the_other_types_in_one_capped_group(
    admin_client: APIClient, target_folder: Folder, monkeypatch
) -> None:
    """Only the types a user knows get a line of their own: the others are summed,
    and their count stops at the cap too."""
    monkeypatch.setattr(FolderViewSet, "MOVE_PREVIEW_COUNT_CAP", 2)
    control = AppliedControl.objects.create(name="AC", folder=target_folder)
    for body in ["one", "two", "three"]:
        Comment.objects.create(body=body, applied_control=control, folder=target_folder)

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(target_folder.id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    payload = res.json()
    others = _group(payload, "otherObjects")
    assert (others["count"], others["capped"]) == (2, True)
    assert payload["carried"]["groups"][-1] == others
    assert "comments" not in _counts(payload)
