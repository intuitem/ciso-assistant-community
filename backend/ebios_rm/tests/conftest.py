import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Asset, RiskMatrix, StoredLibrary
from ebios_rm.models import EbiosRMStudy, ElementaryAction, FearedEvent, RoTo
from iam.models import User, UserGroup


@pytest.fixture
def ebios_rm_matrix_fixture():
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
    ).last()
    assert library is not None
    library.load()
    return RiskMatrix.objects.get(
        urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
    )


@pytest.fixture
def basic_assets_tree_fixture():
    primary_asset_1 = Asset.objects.create(name="Primary Asset 1")
    primary_asset_2 = Asset.objects.create(name="Primary Asset 2")
    supporting_asset = Asset.objects.create(
        name="Supporting Asset 1", type=Asset.Type.SUPPORT
    )
    supporting_asset.parent_assets.add(primary_asset_1, primary_asset_2)
    return primary_asset_1, primary_asset_2, supporting_asset


@pytest.fixture
def basic_ebios_rm_study_fixture(ebios_rm_matrix_fixture, basic_assets_tree_fixture):
    study = EbiosRMStudy.objects.create(
        name="test study",
        description="test study description",
        risk_matrix=ebios_rm_matrix_fixture,
    )
    study.assets.set(basic_assets_tree_fixture)
    return study


@pytest.fixture
def basic_feared_event_fixture(basic_ebios_rm_study_fixture):
    feared_event = FearedEvent.objects.create(
        name="test feared event",
        description="test feared event description",
        ebios_rm_study=basic_ebios_rm_study_fixture,
    )
    asset = Asset.objects.get(name="Primary Asset 1")
    feared_event.assets.add(asset)


@pytest.fixture
def basic_roto_fixture(basic_ebios_rm_study_fixture, basic_feared_event_fixture):
    roto = RoTo.objects.create(
        risk_origin=RoTo.RiskOrigin.STATE,
        target_objective="test target objectives",
        ebios_rm_study=basic_ebios_rm_study_fixture,
    )
    roto.feared_events.set(FearedEvent.objects.filter(name="test feared event"))
    return roto


@pytest.fixture
def admin_client():
    startup(sender=None)
    admin = User.objects.create_superuser("admin@kill-chain-steps-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def elementary_actions_fixture():
    know = ElementaryAction.objects.create(
        name="Reconnaissance", attack_stage=ElementaryAction.AttackStage.KNOW
    )
    enter = ElementaryAction.objects.create(
        name="Phishing", attack_stage=ElementaryAction.AttackStage.ENTER
    )
    exploit = ElementaryAction.objects.create(
        name="Exfiltration", attack_stage=ElementaryAction.AttackStage.EXPLOIT
    )
    return know, enter, exploit
