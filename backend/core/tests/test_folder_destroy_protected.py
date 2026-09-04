"""
Regression test for CA-1797: deleting a Folder that (via cascade) contains an
ElementaryAction still referenced by a KillChain (on_delete=PROTECT) used to
raise an uncaught ProtectedError, surfacing as a 500. FolderViewSet.destroy
now catches it and returns a structured 409 instead.
"""

import pytest
from ebios_rm.models import (
    AttackPath,
    EbiosRMStudy,
    ElementaryAction,
    FearedEvent,
    KillChain,
    OperatingMode,
    OperationalScenario,
    RoTo,
    StrategicScenario,
)
from ebios_rm.tests.fixtures import ebios_rm_matrix_fixture
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Terminology


@pytest.fixture
def admin_client():
    startup(sender=None)
    admin = User.objects.create_superuser(
        "admin@folder-destroy-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.mark.django_db
def test_destroy_folder_blocked_by_kill_chain_returns_409(
    admin_client, ebios_rm_matrix_fixture
):
    domain = Folder.objects.create(
        name="CA-1797 domain",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    study = EbiosRMStudy.objects.create(
        name="CA-1797 study", folder=domain, risk_matrix=ebios_rm_matrix_fixture
    )
    FearedEvent.objects.create(name="CA-1797 feared event", ebios_rm_study=study)
    ro_to = RoTo.objects.create(
        ebios_rm_study=study,
        risk_origin=Terminology.objects.filter(
            field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN
        ).first(),
        target_objective="CA-1797 target objective",
    )
    strategic_scenario = StrategicScenario.objects.create(
        name="CA-1797 strategic scenario", ebios_rm_study=study, ro_to_couple=ro_to
    )
    attack_path = AttackPath.objects.create(
        name="CA-1797 attack path",
        strategic_scenario=strategic_scenario,
        ebios_rm_study=study,
    )
    operational_scenario = OperationalScenario.objects.create(
        ebios_rm_study=study, attack_path=attack_path
    )
    operating_mode = OperatingMode.objects.create(
        name="CA-1797 operating mode", operational_scenario=operational_scenario
    )
    elementary_action = ElementaryAction.objects.create(
        name="CA-1797 elementary action", folder=domain
    )
    KillChain.objects.create(
        operating_mode=operating_mode, elementary_action=elementary_action
    )

    response = admin_client.delete(f"/api/folders/{domain.id}/")

    assert response.status_code == 409
    assert "detail" in response.data
    assert Folder.objects.filter(id=domain.id).exists()


@pytest.mark.django_db
def test_destroy_empty_folder_still_succeeds(admin_client):
    domain = Folder.objects.create(
        name="CA-1797 empty domain",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )

    response = admin_client.delete(f"/api/folders/{domain.id}/")

    assert response.status_code == 204
    assert not Folder.objects.filter(id=domain.id).exists()
