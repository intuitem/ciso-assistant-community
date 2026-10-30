from rest_framework import routers

from .views import (
    DocumentAttachmentViewSet,
    DocumentContainerViewSet,
    DocumentRevisionViewSet,
    DocumentTemplateViewSet,
    ManagedDocumentViewSet,
)

router = routers.DefaultRouter()
router.register(
    r"document-containers", DocumentContainerViewSet, basename="document-containers"
)
router.register(
    r"document-templates", DocumentTemplateViewSet, basename="document-templates"
)
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
