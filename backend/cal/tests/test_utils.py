from cal.models import *
from cal.utils import *

"""
class test_Calendar(LocaleHTMLCalendar):
    def __init__(self, year=None, month=None, *args, **kwargs):
        self.year = year
        self.month = month
        super(Calendar, self).__init__(*args, **kwargs)

@pytest.mark.django_db
def test_formatday():
        Event.objects.create(title="Event", description="A simple event", start_time="2022-1-20", end_time="2022-1-27")
        Event.objects.create(title="SecondEvent", description="A second event", start_time="2022-1-20", end_time="2022-1-27")
        calendar = Calendar(LocaleHTMLCalendar)
        list = {
        "mtg":Event.objects.get(title="Event"),
        "ra":Event.objects.get(title="SecondEvent")
        }
        day = '2022-1-24'
        print(Calendar.formatday(calendar, day, list))
"""
