from cal.models import *
import pytest


@pytest.mark.django_db
def test_event():
    Event.objects.create(
        name="Event",
        description="A simple event",
        start_time="2022-1-20",
        end_time="2022-1-27",
    )
    event = Event.objects.get(name="Event")
