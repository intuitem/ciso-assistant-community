from django.urls import path
from django.urls.conf import include

from . import views
import cal.views as cv
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('analyses-registery', login_required(views.AnalysisListView.as_view()), name='analysis_list'),
    path('i18n/', include('django.conf.urls.i18n')),

    path('analyses-registery/<analysis>/', login_required(views.RiskAnalysisView.as_view()), name='RA'),
    path('analysis/<analysis>.pdf', login_required(views.generate_ra_pdf), name='RA-PDF'),
    path('analysis/<analysis>.csv', login_required(views.export_risks_csv), name='RA-CSV'),

    path('analyses-registery/plan/<folder>/', login_required(views.SecurityMeasurePlanView.as_view()), name='MP'),
    path('treatment/<analysis>.pdf', login_required(views.generate_mp_pdf), name='MP-PDF'),
    path('treatment/<analysis>.csv', login_required(views.export_mp_csv), name='MP-CSV'),

    path('analytics/', login_required(views.global_analytics), name='analytics'),
    path('calendar/', login_required(cv.CalendarView.as_view()), name='calendar'),
    path('my-projects/', login_required(views.MyProjectsListView.as_view()), name='my_projects'),
    path('composer/', login_required(views.ComposerListView.as_view()), name='composer'),

    path('scoring-assistant/', login_required(views.scoring_assistant), name='scoring'),
    path('risk-matrix/', login_required(views.show_risk_matrix), name='matrix'),

    path('browser/', login_required(views.Browser.as_view()), name='browser'),
]