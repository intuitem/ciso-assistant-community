from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PostureAssessmentViewSet

router = DefaultRouter()
router.register(
    r"posture-assessments",
    PostureAssessmentViewSet,
    basename="posture-assessments",
)

urlpatterns = [
    path("", include(router.urls)),
]
