import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import AppliedControl, Asset, Policy, ReferenceControl
from core.views import FolderViewSet
from custom_fields.models import CustomFieldDefinition
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


def _carried_names(payload: dict) -> set[str]:
    return {
        o["name"]
        for group in payload["carried"]["grouped_objects"]
        for o in group["objects"]
    }


def test_single_delete_preview_still_names_what_a_non_recursive_role_destroys(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """The move preview hides sub-domain content from a non-recursive role; deleting
    a domain must keep naming it, as the delete modal shows no hidden count."""
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
    names = [
        o["name"]
        for group in payload["carried"]["grouped_objects"]
        for o in group["objects"]
    ]
    assert sorted(names) == sorted(set(names))
    assert {"SUB-SUB-DOMAIN", "CANARY-ASSET", "SUB-ASSET", "SUB-SUB-ASSET"} <= set(
        names
    )
    assert not {"Target", "SUB-DOMAIN"} & set(names)
    assert payload["carried"]["count"] == len(names)

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


def _group(payload: dict, model: str) -> dict | None:
    return next(
        (g for g in payload["carried"]["grouped_objects"] if g["model"] == model),
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
    domains = _group(res.json(), "Folder.DO")
    assert domains["verbose_name"] == "Domain"
    assert {o["name"] for o in domains["objects"]} == {"SUB-DOMAIN", "SUB-SUB-DOMAIN"}
    enclaves = _group(res.json(), "Folder.EN")
    assert [o["name"] for o in enclaves["objects"]] == ["SOME-ENCLAVE"]


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


def test_move_preview_caps_the_names_but_not_the_count(
    admin_client: APIClient, domain_tree: dict[str, Folder], monkeypatch
) -> None:
    monkeypatch.setattr(FolderViewSet, "MOVE_PREVIEW_NAMES_PER_GROUP", 2)

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    assets = _group(res.json(), "Asset")
    assert assets["count"] == 3
    assert len(assets["objects"]) == 2


def test_move_preview_lists_a_policy_once(
    admin_client: APIClient, target_folder: Folder
) -> None:
    """A policy is an applied control seen through a proxy: one row, one entry."""
    Policy.objects.create(name="LOCAL-POLICY", folder=target_folder)

    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(target_folder.id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    names = [
        o["name"]
        for group in res.json()["carried"]["grouped_objects"]
        for o in group["objects"]
    ]
    assert names.count("LOCAL-POLICY") == 1


def test_move_preview_masks_principals_the_caller_cannot_view(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """Viewing a role assignment does not reveal a user or group the caller could
    not read on its own."""
    victim = User.objects.create_user("hidden-principal@cascade.test")
    RoleAssignment.objects.create(
        user=victim, role=Role.objects.get(name="BI-RL-ANA"), folder=domain_tree["sub"]
    )
    mover = Role.objects.create(name="RA-MOVER", folder=app_ready)
    mover.permissions.set(
        Permission.objects.filter(
            codename__in=["view_folder", "change_folder", "view_roleassignment"]
        )
    )
    client = _scoped_client(
        "ra-mover@cascade.test", "RA-MOVER", domain_tree["target"], app_ready
    )

    res = client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    assignments = _group(res.json(), "RoleAssignment")
    assert assignments["count"] == 2
    assert "hidden-principal@cascade.test" not in res.content.decode()
    assert "grp-ra-mover@cascade.test" not in res.content.decode()


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
    assert "SUB-SUB-ASSET" in _carried_names(res.json())


def test_move_preview_names_only_the_models_the_caller_may_view(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """view_folder shows the sub-domains, not what they hold: a role allowed to move
    a domain without view_asset or view_roleassignment only gets counts for those."""
    mover = Role.objects.create(name="BLIND-MOVER", folder=app_ready)
    mover.permissions.set(
        Permission.objects.filter(codename__in=["view_folder", "change_folder"])
    )
    client = _scoped_client(
        "blind-mover@cascade.test", "BLIND-MOVER", domain_tree["target"], app_ready
    )

    res = client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    payload = res.json()
    assert _carried_names(payload) == {"SUB-DOMAIN", "SUB-SUB-DOMAIN"}
    # Three assets, plus the mover's own role assignment and group in Target.
    assert payload["carried"]["hidden_count"] == 5
    assert "blind-mover@cascade.test" not in res.content.decode()


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
    carried = _carried_names(res.json())
    assert "LOCAL-REFERENCE" in carried
    assert "FOREIGN-CONTROL" not in carried


def test_move_preview_only_names_what_the_caller_may_view(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """A non-recursive role grants nothing on the sub-domains: their names and
    content stay hidden, but the preview still says that something moves along."""
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
    names = _carried_names(payload)
    assert "CANARY-ASSET" in names
    assert not {"SUB-DOMAIN", "SUB-SUB-DOMAIN", "SUB-ASSET", "SUB-SUB-ASSET"} & names
    # The four above, plus the caller's role assignment: the role lacks
    # view_roleassignment.
    assert payload["carried"]["hidden_count"] == 5


def test_move_preview_does_not_name_custom_field_values(
    app_ready: Folder, domain_tree: dict[str, Folder]
) -> None:
    """Custom field values have no folder of their own: they must not slip past the
    visibility check of the object they describe."""
    definition = CustomFieldDefinition.objects.create(
        content_type=ContentType.objects.get_for_model(Asset),
        key="vendor_contract",
        label="Vendor contract",
        field_type="text",
    )
    Asset.objects.get(name="SUB-ASSET").set_custom_field(definition, "SECRET-4242")
    client = _scoped_client(
        "non-recursive-cf@cascade.test",
        "BI-RL-DMA",
        domain_tree["target"],
        app_ready,
        is_recursive=False,
    )

    res = client.post(
        MOVE_PREVIEW_URL, {"ids": [str(domain_tree["target"].id)]}, format="json"
    )

    assert res.status_code == 200, res.content
    assert "SECRET-4242" not in res.content.decode()


def test_move_preview_refuses_builtin_domains(
    admin_client: APIClient, app_ready: Folder
) -> None:
    res = admin_client.post(
        MOVE_PREVIEW_URL, {"ids": [str(app_ready.id)]}, format="json"
    )

    assert res.status_code == 403
