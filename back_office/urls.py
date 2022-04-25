from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # LIST VIEWS
    path('analyses-registry/', login_required(views.RiskAnalysisListView.as_view()), name='ra-list'),
    path('risk-instances/', login_required(views.RiskInstanceListView.as_view()), name='ri-list'),
    path('mitigations/', login_required(views.MitigationListView.as_view()), name='mtg-list'),
    path('risk-acceptances/', login_required(views.RiskAcceptanceListView.as_view()), name='acceptance-list'),

    path('projects-domains/', login_required(views.ProjectsGroupListView.as_view()), name='pd-list'),
    path('projects/', login_required(views.ProjectListView.as_view()), name='project-list'),
    path('threats/', login_required(views.ParentRiskListView.as_view()), name='threat-list'),
    path('security-functions/', login_required(views.SecurityFunctionListView.as_view()), name='security-function-list'),

    path('users/', login_required(views.UserListView.as_view()), name='user-list'),
    path('groups/', login_required(views.GroupListView.as_view()), name='group-list'),

    # CREATE VIEWS
    path('RA/create', login_required(views.RiskAnalysisCreateView.as_view()), name='ra-create'),
    path('RA/create_modal/', login_required(views.RiskAnalysisCreateView.as_view()), name='analysis-create-modal'),
    
    path('MSR/create_modal/', login_required(views.MeasureCreateViewModal.as_view()), name='measure-create-modal'),
    
    path('SF/create_modal/', login_required(views.SecurityFunctionCreateViewModal.as_view()), name='security-function-create-modal'),

    path('RA/<int:parent_analysis>/RI/create', login_required(views.RiskInstanceCreateView.as_view()), name='ri-create'),

    path('PD/create', login_required(views.ProjectsGroupCreateView.as_view()), name='pd-create'),
    path('PD/create_modal/', login_required(views.ProjectsGroupCreateViewModal.as_view()), name='pd-create-modal'),

    path('PRJ/create', login_required(views.ProjectCreateView.as_view()), name='project-create'),
    path('PRJ/create_modal/', login_required(views.ProjectCreateViewModal.as_view()), name='project-create-modal'),
    
    path('users/create', login_required(views.UserCreateView.as_view()), name='user-create'),
    
    # path('RI/create-modal', login_required(views.RiskInstanceCreateViewModal.as_view()), name='ri-create-modal'),
    
    # UPDATE VIEWS
    path('RA/<int:pk>', login_required(views.RiskAnalysisUpdateView.as_view()), name='ra-update'),
    path('RI/<int:pk>', login_required(views.RiskInstanceUpdateView.as_view()), name='ri-update'),
    path('MTG/<int:pk>', login_required(views.MitigationUpdateView.as_view()), name='mtg-update'),

    path('PD/<int:pk>', login_required(views.ProjectsGroupUpdateView.as_view()), name='pd-update'),
    path('PRJ/<int:pk>', login_required(views.ProjectUpdateView.as_view()), name='project-update'),
    
    # DELETE VIEWS
    path('RA/<int:pk>/delete/', login_required(views.RiskAnalysisDeleteView.as_view()), name='ra-delete'),
    path('PRJ/<int:pk>/delete/', login_required(views.ProjectDeleteView.as_view()), name='project-delete'),
    path('D/<int:pk>/delete/', login_required(views.ProjectsGroupDeleteView.as_view()), name='pd-delete'),
]