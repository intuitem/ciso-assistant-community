from .views import *
from tprm.views import (
    EntityViewSet,
    RepresentativeViewSet,
    SolutionViewSet,
    EntityAssessmentViewSet,
)
from library.views import StoredLibraryViewSet, LoadedLibraryViewSet
import importlib


from django.urls import include, path
from rest_framework import routers

from ciso_assistant.settings import DEBUG
from django.conf import settings

router = routers.DefaultRouter()
router.register(r"folders", FolderViewSet, basename="folders")
router.register(r"entities", EntityViewSet, basename="entities")
router.register(
    r"entity-assessments", EntityAssessmentViewSet, basename="entity-assessments"
)
router.register(r"solutions", SolutionViewSet, basename="solutions")
router.register(r"representatives", RepresentativeViewSet, basename="representatives")
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
    r"requirement-assessments",
    RequirementAssessmentViewSet,
    basename="requirement-assessments",
)
router.register(r"stored-libraries", StoredLibraryViewSet, basename="stored-libraries")
router.register(r"loaded-libraries", LoadedLibraryViewSet, basename="loaded-libraries")
router.register(
    r"requirement-mapping-sets",
    RequirementMappingSetViewSet,
    basename="requirement-mapping-sets",
)

ROUTES = settings.ROUTES
MODULES = settings.MODULES.values()

for route in ROUTES:
    view_module = importlib.import_module(ROUTES[route]["viewset"].rsplit(".", 1)[0])
    router.register(
        route,
        getattr(view_module, ROUTES[route]["viewset"].rsplit(".")[-1]),
        basename=ROUTES[route].get("basename"),
    )

urlpatterns = [
    path("", include(router.urls)),
    path("iam/", include("iam.urls")),
    path("serdes/", include("serdes.urls")),
    path("settings/", include("global_settings.urls")),
    path("csrf/", get_csrf_token, name="get_csrf_token"),
    path("build/", get_build, name="get_build"),
    path("evidences/<uuid:pk>/upload/", UploadAttachmentView.as_view(), name="upload"),
    path("get_counters/", get_counters_view, name="get_counters_view"),
    path("get_metrics/", get_metrics_view, name="get_metrics_view"),
    path("agg_data/", get_agg_data, name="get_agg_data"),
    path("composer_data/", get_composer_data, name="get_composer_data"),
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "accounts/saml/", include("iam.sso.saml.urls")
    ),  # NOTE: This has to be placed before the allauth urls, otherwise our ACS implementation will not be used
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    path(
        "requirement-assessments/<uuid:pk>/suggestions/applied-controls/",
        RequirementAssessmentViewSet.create_suggested_applied_controls,
    ),
]

# Additional modules take precedence over the default modules
for index, module in enumerate(MODULES):
    urlpatterns.insert(index, (path(module["path"], include(module["module"]))))

if DEBUG:
    # Browsable API is only available in DEBUG mode
    urlpatterns += [
        path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    ]
