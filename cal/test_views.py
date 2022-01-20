from datetime import date

from .models import *
from .views import *


# Create your tests here.
def test_next_month():
    d = date(2021, 11, 23)
    assert next_month(d) == 'month=2021-12'

def test_pre_month():
    d = date(2021, 11, 23)
    assert prev_month(d) == 'month=2021-10'

def test_get_date():
    d = date(2021, 11, 1)
    assert get_date("2021-11") == d
