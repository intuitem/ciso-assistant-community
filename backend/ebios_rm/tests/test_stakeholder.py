import pytest
from ebios_rm.models import EbiosRMStudy, FearedEvent, RoTo, Stakeholder
from core.models import Terminology

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
        category = Terminology.objects.get(
            name="supplier", field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP
        )
        stakeholder = Stakeholder.objects.create(
            entity=entity,
            category=category,
            ebios_rm_study=study,
        )

        assert stakeholder in study.stakeholders.all()
        assert stakeholder.entity == entity
        assert stakeholder.category == category

        assert stakeholder.current_criticality == 0
        assert stakeholder.residual_criticality == 0
