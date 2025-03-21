from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PurposeViewSet,
    PersonalDataViewSet,
    DataSubjectViewSet,
    DataRecipientViewSet,
    DataContractorViewSet,
    DataTransferViewSet,
    ProcessingViewSet,
)

router = DefaultRouter()
router.register(r"purposes", PurposeViewSet, basename="purposes")
router.register(r"personal-data", PersonalDataViewSet, basename="personal-data")
router.register(r"data-subjects", DataSubjectViewSet, basename="data-subjects")
router.register(r"data-recipients", DataRecipientViewSet, basename="data-recipients")
router.register(r"data-contractors", DataContractorViewSet, basename="data-contractors")
router.register(r"data-transfers", DataTransferViewSet, basename="data-transfers")
router.register(r"processings", ProcessingViewSet, basename="processings")

urlpatterns = [
    path("", include(router.urls)),
]
