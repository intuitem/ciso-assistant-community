import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Asset
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


def _scoped_client(email, role_name, folder, app_ready):
    user = User.objects.create_user(email)
    user.folder = app_ready
    user.save()
    group = UserGroup.objects.create(name=f"grp-{email}", folder=folder)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role_name),
        folder=folder,
        is_recursive=True,
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


def _bucket_names(bucket):
    return {o["name"] for o in bucket["related_objects"]}


def test_entity_assessment_preview_reports_enclave_audit_as_deleted(
    admin_client, target_folder
):
    ea = _entity_assessment_with_audit(target_folder, enclave=True)
    res = admin_client.get(f"/api/entity-assessments/{ea.id}/cascade-info/")
    assert res.status_code == 200
    assert "VENDOR-AUDIT" in _bucket_names(res.json()["deleted"])
    assert "VENDOR-AUDIT" not in _bucket_names(res.json()["affected"])


def test_entity_assessment_preview_keeps_non_enclave_audit_as_affected(
    admin_client, target_folder
):
    ea = _entity_assessment_with_audit(target_folder, enclave=False)
    res = admin_client.get(f"/api/entity-assessments/{ea.id}/cascade-info/")
    assert res.status_code == 200
    assert "VENDOR-AUDIT" in _bucket_names(res.json()["affected"])
    assert "VENDOR-AUDIT" not in _bucket_names(res.json()["deleted"])
