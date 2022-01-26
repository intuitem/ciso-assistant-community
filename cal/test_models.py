from .models import *
import pytest

@pytest.mark.django_db
def test_event():
    Event.objects.create(title="Event", description="A simple event", start_time="2022-1-20", end_time="2022-1-27")
    event = Event.objects.get(title="Event")
    assert event.get_html_url == '<a class="bg-blue-100" href=""> Event </a>'
    
