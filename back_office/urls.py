from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analysis-registry/', login_required(views.RiskAnalysisListView.as_view()), name='ra-list'),
    path('risk-instances/', login_required(views.RiskInstanceListView.as_view()), name='ri-list'),
    path('mitigations/', login_required(views.MitigationListView.as_view()), name='mtg-list'),
    path('risk-acceptances/', login_required(views.RiskAcceptanceListView.as_view()), name='acceptance-list'),

    path('project-domains/', login_required(views.ProjectsGroupListView.as_view()), name='pd-list'),
    path('projects/', login_required(views.ProjectTreeView.as_view()), name='project-tree'),

    path('users/', login_required(views.UserListView.as_view()), name='user-list'),
    path('groups/', login_required(views.GroupListView.as_view()), name='group-list'),

    path('RA/create', login_required(views.RiskAnalysisCreateView.as_view()), name='ra-create'),
    path('RA/<int:parent_analysis>/RI/create', login_required(views.RiskInstanceCreateView.as_view()), name='ri-create'),

    path('PD/create', login_required(views.ProjectsGroupCreateView.as_view()), name='pd-create'),
    path('PRJ/create', login_required(views.ProjectCreateView.as_view()), name='project-create'),
    
    path('users/create', login_required(views.UserCreateView.as_view()), name='user-create'),
    
    path('RI/create-modal', login_required(views.RiskInstanceCreateViewModal.as_view()), name='ri-create-modal'),
    
    path('RA/<int:pk>', login_required(views.RiskAnalysisUpdateView.as_view()), name='ra-update'),
    path('RI/<int:pk>', login_required(views.RiskInstanceUpdateView.as_view()), name='ri-update'),
    path('MTG/<int:pk>', login_required(views.MitigationUpdateView.as_view()), name='mtg-update'),
    path('PD/<int:pk>', login_required(views.ProjectsGroupUpdateView.as_view()), name='pd-update'),
    path('PRJ/<int:pk>', login_required(views.ProjectUpdateView.as_view()), name='project-update'),
    
    path('RA/<int:pk>/delete/', login_required(views.RiskAnalysisDeleteView.as_view()), name='ra-delete'),
]