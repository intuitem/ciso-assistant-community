import pytest
from ebios_rm.models import EbiosRMStudy, FearedEvent, RoTo
from core.models import Terminology

from ebios_rm.tests.fixtures import *


@pytest.mark.django_db
class TestRoTo:
    @pytest.mark.usefixtures(
        "basic_ebios_rm_study_fixture", "basic_feared_event_fixture"
    )
    def test_create_roto_basic(self):
        roto = RoTo.objects.create(
            risk_origin=Terminology.objects.get(name="state"),
            target_objective="test target objectives",
            ebios_rm_study=EbiosRMStudy.objects.get(name="test study"),
        )
        roto.feared_events.set(FearedEvent.objects.filter(name="test feared event"))

        assert roto.risk_origin == Terminology.objects.get(name="state")
        assert roto.target_objective == "test target objectives"

        assert roto.feared_events.count() == 1
        assert roto.feared_events.filter(name="test feared event").exists()
        assert (
            roto.ebios_rm_study
            == FearedEvent.objects.get(name="test feared event").ebios_rm_study
        )
