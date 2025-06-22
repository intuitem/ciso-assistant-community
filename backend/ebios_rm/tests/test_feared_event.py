import pytest
from ebios_rm.models import EbiosRMStudy, FearedEvent

from ebios_rm.tests.fixtures import *


@pytest.mark.django_db
class TestFearedEvent:
    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_create_feared_event_basic(self):
        feared_event = FearedEvent.objects.create(
            name="test feared event",
            description="test feared event description",
            ebios_rm_study=EbiosRMStudy.objects.get(name="test study"),
        )
        assert feared_event.name == "test feared event"
        assert feared_event.description == "test feared event description"
        assert feared_event.ebios_rm_study == EbiosRMStudy.objects.get(
            name="test study"
        )
