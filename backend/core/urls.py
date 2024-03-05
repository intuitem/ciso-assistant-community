from .views import *
from django.contrib.auth import views as auth_views
from library.views import LibraryViewSet


from django.urls import include, path
from rest_framework import routers

from ciso_assistant.settings import DEBUG

router = routers.DefaultRouter()
router.register(r"folders", FolderViewSet, basename="folders")
router.register(r"projects", ProjectViewSet, basename="projects")
router.register(r"risk-matrices", RiskMatrixViewSet, basename="risk-matrices")
router.register(r"risk-assessments", RiskAssessmentViewSet, basename="risk-assessments")
router.register(r"threats", ThreatViewSet, basename="threats")
router.register(r"risk-scenarios", RiskScenarioViewSet, basename="risk-scenarios")
router.register(r"applied-controls", AppliedControlViewSet, basename="applied-controls")
router.register(r"policies", PolicyViewSet, basename="policies")
router.register(r"risk-acceptances", RiskAcceptanceViewSet, basename="risk-acceptances")
router.register(
    r"reference-controls", ReferenceControlViewSet, basename="reference-controls"
)
router.register(r"assets", AssetViewSet, basename="assets")

router.register(r"users", UserViewSet, basename="users")
router.register(r"user-groups", UserGroupViewSet, basename="user-groups")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"role-assignments", RoleAssignmentViewSet, basename="role-assignments")
router.register(r"frameworks", FrameworkViewSet, basename="frameworks")
router.register(r"evidences", EvidenceViewSet, basename="evidences")
router.register(
    r"compliance-assessments",
    ComplianceAssessmentViewSet,
    basename="compliance-assessments",
)
router.register(r"requirement-nodes", RequirementViewSet, basename="requirement-nodes")
router.register(
    r"requirement-levels", RequirementLevelViewSet, basename="requirement-levels"
)
router.register(
    r"requirement-assessments",
    RequirementAssessmentViewSet,
    basename="requirement-assessments",
)
router.register(r"libraries", LibraryViewSet, basename="libraries")


urlpatterns = [
    path("", include(router.urls)),
    path("iam/", include("iam.urls")),
    path("serdes/", include("serdes.urls")),
    path("csrf/", get_csrf_token, name="get_csrf_token"),
    path("build/", get_build, name="get_build"),
    path("license/", license, name="license"),
    path("evidences/<uuid:pk>/upload/", UploadAttachmentView.as_view(), name="upload"),
    path("get_counters/", get_counters_view, name="get_counters_view"),
    path("agg_data/", get_agg_data, name="get_agg_data"),
    path("composer_data/", get_composer_data, name="get_composer_data"),
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "first_connexion/<uidb64>/<token>/",
        FirstConnexionPasswordConfirmView.as_view(),
        name="first_connexion_confirm",
    ),
]

if DEBUG:
    # Browsable API is only available in DEBUG mode
    urlpatterns += [
        path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    ]
