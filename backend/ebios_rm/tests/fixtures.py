import pytest

from core.models import RiskMatrix, StoredLibrary, Asset
from ebios_rm.models import RoTo, EbiosRMStudy, FearedEvent


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
