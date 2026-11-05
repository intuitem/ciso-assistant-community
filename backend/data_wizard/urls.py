from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import mapping, views

router = DefaultRouter()
router.register(r"mappings", mapping.ImportMappingViewSet, basename="import-mappings")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "load-file/",
        views.LoadFileView.as_view(),
        name="load-file",
    ),
    path("mapping/schema/", mapping.MappingSchemaView.as_view(), name="mapping-schema"),
    path(
        "mapping/schema/<str:model_type>/",
        mapping.MappingSchemaView.as_view(),
        name="mapping-schema-detail",
    ),
    path("mapping/analyze/", mapping.AnalyzeFileView.as_view(), name="mapping-analyze"),
    path("mapping/import/", mapping.MappedImportView.as_view(), name="mapping-import"),
    path(
        "templates/<str:model_type>/",
        views.ImportTemplateView.as_view(),
        name="import-template",
    ),
]
