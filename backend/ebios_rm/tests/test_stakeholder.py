import pytest
from ebios_rm.models import EbiosRMStudy, FearedEvent, RoTo, Stakeholder

from tprm.models import Entity

from ebios_rm.tests.fixtures import *


@pytest.mark.django_db
class TestStakeholder:
    @pytest.mark.usefixtures(
        "basic_ebios_rm_study_fixture",
    )
    def test_create_stakeholder_basic(self):
        study = EbiosRMStudy.objects.get(name="test study")
        entity = Entity.objects.create(name="Entity")
        stakeholder = Stakeholder.objects.create(
            entity=entity,
            category=Stakeholder.Category.SUPPLIER,
            ebios_rm_study=study,
        )

        assert stakeholder in study.stakeholders.all()
        assert stakeholder.entity == entity
        assert stakeholder.category == Stakeholder.Category.SUPPLIER

        assert stakeholder.current_criticality == 0
        assert stakeholder.residual_criticality == 0
