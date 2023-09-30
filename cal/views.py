from datetime import datetime, timedelta, date
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, request
from django.views import generic
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import get_language
import calendar

from .models import *
from iam.models import RoleAssignment
from .utils import Calendar
from .forms import EventForm
from core.models import SecurityMeasure
from core.views import BaseContextMixin


def index(request):
    return HttpResponse('hello')


class CalendarView(BaseContextMixin, generic.ListView):
    model = SecurityMeasure
    template_name = 'core/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = get_date(self.request.GET.get('month', None))

        # TODO: implement a more elegant security_function
        cal_lang = get_language()
        cal_country = 'US' if (cal_lang == 'en') else cal_lang.split('-')[0].upper()
        cal_locale = cal_lang + '_' + cal_country + '.UTF-8'

        cal = Calendar(d.year, d.month, calendar.MONDAY, cal_locale)
        html_cal = cal.formatmonth(withyear=True)
        context['calendar'] = format_html(html_cal)
        context['prev_month'] = prev_month(d)
        context['next_month'] = next_month(d)
        # print('Calendar Locale: '+ cal_locale ) # DEBUG
        return context


def get_date(req_month):
    if req_month:
        year, month = (int(x) for x in req_month.split('-'))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = 'month=' + str(prev_month.year) + '-' + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'month=' + str(next_month.year) + '-' + str(next_month.month)
    return month
