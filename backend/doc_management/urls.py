from rest_framework import routers

from .views import (
    DocumentAttachmentViewSet,
    DocumentRevisionViewSet,
    ManagedDocumentViewSet,
)

router = routers.DefaultRouter()
router.register(
    r"managed-documents", ManagedDocumentViewSet, basename="managed-documents"
)
router.register(
    r"document-revisions",
    DocumentRevisionViewSet,
    basename="document-revisions",
)
router.register(
    r"document-attachments",
    DocumentAttachmentViewSet,
    basename="document-attachments",
)

urlpatterns = router.urls
