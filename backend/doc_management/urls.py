from rest_framework import routers

from .views import DocumentRevisionViewSet, ManagedDocumentViewSet

router = routers.DefaultRouter()
router.register(
    r"managed-documents", ManagedDocumentViewSet, basename="managed-documents"
)
router.register(
    r"document-revisions",
    DocumentRevisionViewSet,
    basename="document-revisions",
)

urlpatterns = router.urls
