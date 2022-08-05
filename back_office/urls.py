from django.urls import path
from django.urls.conf import include
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('', login_required(views.index), name='index'),
    path('i18n/', include('django.conf.urls.i18n')),

    path('quick-start', login_required(views.QuickStartView.as_view()), name='quick_start'),

    # LIST VIEWS
    path('analyses-registry/', login_required(views.RiskAnalysisListView.as_view()), name='ra-list'),
    path('risk-scenarios/', login_required(views.RiskInstanceListView.as_view()), name='ri-list'),
    path('measures/', login_required(views.MitigationListView.as_view()), name='mtg-list'),
    path('risk-acceptances/', login_required(views.RiskAcceptanceListView.as_view()), name='acceptance-list'),

    path('projects-domains/', login_required(views.ProjectsGroupListView.as_view()), name='pd-list'),
    path('projects/', login_required(views.ProjectListView.as_view()), name='project-list'),
    path('assets/', login_required(views.AssetListView.as_view()), name='asset-list'),
    path('threats/', login_required(views.ParentRiskListView.as_view()), name='threat-list'),
    path('security-functions/', login_required(views.SecurityFunctionListView.as_view()), name='security-function-list'),

    path('users/', login_required(views.UserListView.as_view()), name='user-list'),
    path('groups/', login_required(views.GroupListView.as_view()), name='group-list'),
    path('roles/', login_required(views.RoleAssignmentListView.as_view()), name='role-list'),

    # CREATE VIEWS
    path('RA/create', login_required(views.RiskAnalysisCreateView.as_view()), name='ra-create'),
    path('RA/create_modal/', login_required(views.RiskAnalysisCreateView.as_view()), name='analysis-create-modal'),
    
    path('MSR/create_modal/', login_required(views.MeasureCreateViewModal.as_view()), name='measure-create-modal'),
    
    path('RAC/create_modal/', login_required(views.RiskAcceptanceCreateViewModal.as_view()), name='acceptance-create-modal'),
    
    path('SF/create_modal/', login_required(views.SecurityFunctionCreateViewModal.as_view()), name='security-function-create-modal'),
    
    path('TH/create_modal/', login_required(views.ThreatCreateViewModal.as_view()), name='threat-create-modal'),

    path('RA/<int:parent_analysis>/RS/create', login_required(views.RiskInstanceCreateView.as_view()), name='ri-create'),
    path('RS/create', login_required(views.RiskScenarioCreateViewModal.as_view()), name='risk-scenario-create-modal'),

    path('PD/create', login_required(views.ProjectsGroupCreateView.as_view()), name='pd-create'),
    path('PD/create_modal/', login_required(views.ProjectsGroupCreateViewModal.as_view()), name='pd-create-modal'),

    path('PRJ/create', login_required(views.ProjectCreateView.as_view()), name='project-create'),
    path('PRJ/create_modal/', login_required(views.ProjectCreateViewModal.as_view()), name='project-create-modal'),
    
    path('AST/create_modal/', login_required(views.AssetCreateViewModal.as_view()), name='asset-create-modal'),
    
    path('users/create', login_required(views.UserCreateView.as_view()), name='user-create'),
    path('groups/create', login_required(views.GroupCreateView.as_view()), name='group-create'),
    
    # path('RS/create-modal', login_required(views.RiskInstanceCreateViewModal.as_view()), name='ri-create-modal'),
    
    # UPDATE VIEWS
    path('RA/<int:pk>', login_required(views.RiskAnalysisUpdateView.as_view()), name='ra-update'),
    path('RS/<int:pk>', login_required(views.RiskInstanceUpdateView.as_view()), name='ri-update'),
    path('MSR/<int:pk>', login_required(views.MitigationUpdateView.as_view()), name='mtg-update'),
    path('RAC/<int:pk>', login_required(views.RiskAcceptanceUpdateView.as_view()), name='acceptance-update'),
    path('TH/<int:pk>', login_required(views.ThreatUpdateView.as_view()), name='threat-update'),
    path('SF/<int:pk>', login_required(views.SecurityFunctionUpdateView.as_view()), name='security-function-update'),

    path('PD/<int:pk>', login_required(views.ProjectsGroupUpdateView.as_view()), name='pd-update'),
    path('PRJ/<int:pk>', login_required(views.ProjectUpdateView.as_view()), name='project-update'),
    path('AST/<int:pk>', login_required(views.AssetUpdateView.as_view()), name='asset-update'),

    path('users/<int:pk>', login_required(views.UserUpdateView.as_view()), name='user-update'),
    path('users/<int:pk>/password', login_required(views.AdminPasswordChangeView.as_view()), name='admin-password-change'),
    path('groups/<int:pk>', login_required(views.GroupUpdateView.as_view()), name='group-update'),
    path('roles/<int:pk>', login_required(views.RoleAssignmentUpdateView.as_view()), name='role-update'),
    
    # DELETE VIEWS
    path('RA/<int:pk>/delete/', login_required(views.RiskAnalysisDeleteView.as_view()), name='analysis-delete'),
    path('RS/<int:pk>/delete/', login_required(views.RiskScenarioDeleteView.as_view()), name='risk-scenario-delete'),
    path('RAC/<int:pk>/delete/', login_required(views.RiskAcceptanceDeleteView.as_view()), name='risk-acceptance-delete'),
    path('MSR/<int:pk>/delete/', login_required(views.MeasureDeleteView.as_view()), name='measure-delete'),
    path('PRJ/<int:pk>/delete/', login_required(views.ProjectDeleteView.as_view()), name='project-delete'),
    path('AST/<int:pk>/delete/', login_required(views.AssetDeleteView.as_view()), name='asset-delete'),
    path('SF/<int:pk>/delete/', login_required(views.SecurityFunctionDeleteView.as_view()), name='security-function-delete'),
    path('PD/<int:pk>/delete/', login_required(views.ProjectsGroupDeleteView.as_view()), name='pd-delete'),
    path('TH/<int:pk>/delete/', login_required(views.ThreatDeleteView.as_view()), name='threat-delete'),

    path('users/<int:pk>/delete', login_required(views.UserDeleteView.as_view()), name='user-delete'),
    path('groups/<int:pk>/delete', login_required(views.GroupDeleteView.as_view()), name='group-delete'),
]