import pytest
from core.models import Asset, RiskMatrix
from ebios_rm.models import EbiosRMStudy

from ebios_rm.tests.fixtures import *
from tprm.models import Entity


@pytest.mark.django_db
class TestEbiosRMStudy:
    @pytest.mark.usefixtures("ebios_rm_matrix_fixture")
    def test_create_ebios_rm_study_basic(self):
        study = EbiosRMStudy.objects.create(
            name="test study",
            description="test study description",
            risk_matrix=RiskMatrix.objects.get(
                urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
            ),
        )
        assert study.name == "test study"
        assert study.description == "test study description"
        assert study.risk_matrix == RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        )
        assert study.assets.count() == 0
        assert study.reference_entity == Entity.get_main_entity()

    @pytest.mark.usefixtures("ebios_rm_matrix_fixture", "basic_assets_tree_fixture")
    def test_create_ebios_rm_study_with_assets(self):
        study = EbiosRMStudy.objects.create(
            name="test study",
            description="test study description",
            risk_matrix=RiskMatrix.objects.get(
                urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
            ),
        )
        study.assets.set(Asset.objects.filter(name="Primary Asset 1"))
        assert study.name == "test study"
        assert study.description == "test study description"
        assert study.risk_matrix == RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        )

        assert study.assets.count() == 1
        assert study.assets.filter(name="Primary Asset 1").exists()
