from django.urls import path
from django.urls.conf import include

from . import views
import cal.views as cv
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('assessment-reports/', login_required(views.HomeView.as_view()), name='home'),
    path('assessment-reports/<uuid:pk>/', login_required(views.AssessmentDetailView.as_view()), name='assessment-report'),
    path('', RedirectView.as_view(url='assessment-reports/')),

    path('i18n/', include('django.conf.urls.i18n')),
    path('search/', login_required(views.SearchResults.as_view()), name='search'),

    path('password_reset', views.password_reset_request, name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.ResetPasswordConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('first_connexion/<uidb64>/<token>/', views.FirstConnexionPasswordConfirmView.as_view(), name='first_connexion_confirm'),

    path('overview/', login_required(views.global_overview), name='overview'),
    path('calendar/', login_required(cv.CalendarView.as_view()), name='calendar'),
    path('overview/composer/', login_required(views.ComposerListView.as_view()), name='composer'),

    path('license/', login_required(views.license_overview), name='lic-management'),

    path('quick-start', login_required(views.QuickStartView.as_view()), name='quick_start'),

    # LIST VIEWS
    path('assessments/', login_required(views.AssessmentListView.as_view()), name='assessment-list'),
    path('assessments/<assessment>.zip', login_required(views.export), name='export-assessment'),
    path('frameworks/', login_required(views.FrameworkListView.as_view()), name='framework-list'),
    path('requirements/', login_required(views.RequirementListView.as_view()), name='requirement-list'),
    path('evidence/', login_required(views.EvidenceListView.as_view()), name='evidence-list'),
    path('evidence/<evidence_id>/download', login_required(views.evidence_attachment_download), name='evidence-download'),
    path('evidence/<evidence_id>/preview', login_required(views.evidence_attachment_preview), name='evidence-preview'),
    path('requirement-assessments/', login_required(views.RequirementAssessmentListView.as_view()), name='requirementassessment-list'),
    path('security-measures/', login_required(views.SecurityMeasureListView.as_view()), name='securitymeasure-list'),
    path('projects-domains/', login_required(views.FolderListView.as_view()), name='folder-list'),
    path('projects/', login_required(views.ProjectListView.as_view()), name='project-list'),
    path('threats/', login_required(views.ThreatListView.as_view()), name='threat-list'),
    path('security-functions/', login_required(views.SecurityFunctionListView.as_view()), name='securityfunction-list'),

    path('users/', login_required(views.UserListView.as_view()), name='user-list'),
    path('user_groups/', login_required(views.UserGroupListView.as_view()), name='usergroup-list'),
    path('roles/', login_required(views.RoleAssignmentListView.as_view()), name='role-list'),
    path('profile', login_required(views.MyProfileDetailView.as_view()), name='user-detail'),

    # CREATE VIEWS
    path('assessments/create/', login_required(views.AssessmentCreateView.as_view()), name='assessment-create-modal'),
    path('requirements/create/', login_required(views.RequirementCreateView.as_view()), name='requirement-create-modal'),
    path('evidence/create/', login_required(views.EvidenceCreateView.as_view()), name='evidence-create'),
    path('evidence/create_modal/', login_required(views.EvidenceCreateViewModal.as_view()), name='evidence-create-modal'),
    path('requirement-assessments/create/', login_required(views.RequirementAssessmentCreateView.as_view()), name='requirementassessment-create-modal'),
    path('security-measures/create-modal/', login_required(views.SecurityMeasureCreateViewModal.as_view()), name='securitymeasure-create-modal'),
    
    path('security-functions/create-modal/', login_required(views.SecurityFunctionCreateViewModal.as_view()), name='securityfunction-create-modal'),
    
    path('threats/create-modal/', login_required(views.ThreatCreateViewModal.as_view()), name='threat-create-modal'),

    path('projects-domains/create', login_required(views.FolderCreateView.as_view()), name='folder-create'),
    path('projects-domains/create_modal/', login_required(views.FolderCreateViewModal.as_view()), name='folder-create-modal'),

    path('projects/create', login_required(views.ProjectCreateView.as_view()), name='project-create'),
    path('projects/create_modal/', login_required(views.ProjectCreateViewModal.as_view()), name='project-create-modal'),
    
    path('users/create', login_required(views.UserCreateView.as_view()), name='user-create'),
    path('user-groups/create', login_required(views.UserGroupCreateView.as_view()), name='usergroup-create'),

    path('role-assignments/create', login_required(views.RoleAssignmentCreateView.as_view()), name='roleassignment-create'),
    
    # UPDATE VIEWS
    path('assessments/<uuid:pk>/edit/', login_required(views.AssessmentUpdateView.as_view()), name='assessment-update'),
    path('requirements/<uuid:pk>/edit/', login_required(views.RequirementUpdateView.as_view()), name='requirement-update'),
    path('evidence/<uuid:pk>/edit/', login_required(views.EvidenceUpdateView.as_view()), name='evidence-update'),
    path('requirement-assessments/<uuid:pk>/edit/', login_required(views.RequirementAssessmentUpdateView.as_view()), name='requirementassessment-update'),
    path('requirement-assessments/update_modal', login_required(views.RequirementAssessmentUpdateViewModal.as_view()), name='requirementassessment-update-modal'),
    path('security-measures/<uuid:pk>/edit/', login_required(views.SecurityMeasureUpdateView.as_view()), name='securitymeasure-update'),
    path('threats/<uuid:pk>/edit/', login_required(views.ThreatUpdateView.as_view()), name='threat-update'),
    path('security-functions/<uuid:pk>/edit/', login_required(views.SecurityFunctionUpdateView.as_view()), name='securityfunction-update'),

    path('projects-domains/<uuid:pk>/edit/', login_required(views.FolderUpdateView.as_view()), name='folder-update'),
    path('projects/<uuid:pk>/edit/', login_required(views.ProjectUpdateView.as_view()), name='project-update'),

    path('users/<uuid:pk>/edit/', login_required(views.UserUpdateView.as_view()), name='user-update'),
    path('my-profile/<uuid:pk>/edit/', login_required(views.MyProfileUpdateView.as_view()), name='me-update'),
    path('users/<uuid:pk>/password', login_required(views.UserPasswordChangeView.as_view()), name='password-change'),
    path('user-groups/<uuid:pk>/edit/', login_required(views.UserGroupUpdateView.as_view()), name='usergroup-update'),
    path('role-assignments/<uuid:pk>/edit/', login_required(views.RoleAssignmentUpdateView.as_view()), name='roleassignment-update'),
    
    # DELETE VIEWS
    path('assessments/<uuid:pk>/delete/', login_required(views.AssessmentDeleteView.as_view()), name='assessment-delete'),
    path('frameworks/<uuid:pk>/delete/', login_required(views.FrameworkDeleteView.as_view()), name='framework-delete'),
    path('requirements/<uuid:pk>/delete/', login_required(views.RequirementDeleteView.as_view()), name='requirement-delete'),
    path('evidence/<uuid:pk>/delete/', login_required(views.EvidenceDeleteView.as_view()), name='evidence-delete'),
    path('requirement-assessments/<uuid:pk>/delete/', login_required(views.RequirementAssessmentDeleteView.as_view()),name='requirementassessment-delete'),
    path('security-measures/<uuid:pk>/delete/', login_required(views.SecurityMeasureDeleteView.as_view()), name='securitymeasure-delete'),
    path('projects/<uuid:pk>/delete/', login_required(views.ProjectDeleteView.as_view()), name='project-delete'),
    path('security-functions/<uuid:pk>/delete/', login_required(views.SecurityFunctionDeleteView.as_view()), name='securityfunction-delete'),
    path('projects-domains/<uuid:pk>/delete/', login_required(views.FolderDeleteView.as_view()), name='folder-delete'),
    path('threats/<uuid:pk>/delete/', login_required(views.ThreatDeleteView.as_view()), name='threat-delete'),

    path('users/<uuid:pk>/delete', login_required(views.UserDeleteView.as_view()), name='user-delete'),
    path('user-groups/<uuid:pk>/delete', login_required(views.UserGroupDeleteView.as_view()), name='usergroup-delete'),

    path('role-assignments/<uuid:pk>/delete', login_required(views.RoleAssignmentDeleteView.as_view()), name='role-assignment-delete'),

    # DETAIL VIEWS
    path('assessments/<uuid:pk>', login_required(views.AssessmentDetailView.as_view()), name='assessment-detail'),
    path('frameworks/<uuid:pk>', login_required(views.FrameworkDetailView.as_view()), name='framework-detail'),
    path('requirements/<uuid:pk>', login_required(views.RequirementDetailView.as_view()), name='requirement-detail'),
    path('evidence/<uuid:pk>', login_required(views.EvidenceDetailView.as_view()), name='evidence-detail'),
    path('requirement-assessments/<uuid:pk>', login_required(views.RequirementAssessmentDetailView.as_view()), name='requirementassessment-detail'),
    path('security-measures/<uuid:pk>', login_required(views.SecurityMeasureDetailView.as_view()), name='securitymeasure-detail'),
    path('projects-domains/<uuid:pk>', login_required(views.FolderDetailView.as_view()), name='folder-detail'),
    path('projects/<uuid:pk>', login_required(views.ProjectDetailView.as_view()), name='project-detail'),
    path('threats/<uuid:pk>', login_required(views.ThreatDetailView.as_view()), name='threat-detail'),
    path('security-functions/<uuid:pk>', login_required(views.SecurityFunctionDetailView.as_view()), name='securityfunction-detail'),

    path('users/<uuid:pk>', login_required(views.UserDetailView.as_view()), name='user-detail'),

]