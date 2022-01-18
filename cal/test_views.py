from django.http.request import HttpRequest
from django.test import TestCase
from django.http import HttpResponse
from datetime import datetime, timedelta, date

import calendar
from .models import *
from .views import *
from .utils import Calendar
from .forms import EventForm

# Create your tests here.
class CalendarTest(TestCase):

    def test_next_month(self):
        d = date(2021, 11, 23)
        self.assertEqual(next_month(d), 'month=2021-12')

    def test_pre_month(self):
        d = date(2021, 11, 23)
        self.assertEqual(prev_month(d), 'month=2021-10')

    def test_get_date(self):
        d = date(2021, 11, 1)
        self.assertEqual(get_date("2021-11"), d)
