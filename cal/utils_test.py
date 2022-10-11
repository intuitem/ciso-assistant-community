from .models import *
from .utils import *
from calendar import LocaleHTMLCalendar
from core.models import SecurityMeasure, RiskAcceptance
import pytest

"""
class test_Calendar(LocaleHTMLCalendar):
    def __init__(self, year=None, month=None, *args, **kwargs):
        self.year = year
        self.month = month
        super(Calendar, self).__init__(*args, **kwargs)

@pytest.mark.django_db
def test_formatday():
        Event.objects.create(name="Event", description="A simple event", start_time="2022-1-20", end_time="2022-1-27")
        Event.objects.create(name="SecondEvent", description="A second event", start_time="2022-1-20", end_time="2022-1-27")
        calendar = Calendar(LocaleHTMLCalendar)
        list = {
        "mtg":Event.objects.get(name="Event"),
        "ra":Event.objects.get(name="SecondEvent")
        }
        day = '2022-1-24'
        print(Calendar.formatday(calendar, day, list))
"""
