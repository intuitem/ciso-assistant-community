from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analysis-registry/', login_required(views.RiskAnalysisListView.as_view()), name='ra-list'),
    path('risk-instances/', login_required(views.RiskInstanceListView.as_view()), name='ri-list'),
    path('mitigations/', login_required(views.MitigationListView.as_view()), name='mtg-list'),
    path('risk-acceptances/', login_required(views.RiskAcceptanceListView.as_view()), name='acceptance-list'),

    path('RA/<int:pk>', login_required(views.RiskAnalysisUpdateView.as_view()), name='ra-update'),
    path('RI/<int:pk>', login_required(views.RiskInstanceUpdateView.as_view()), name='ri-update'),
]