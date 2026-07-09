from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    ResourceTypeDetailView,
    ResourceTypesView,
    SCIMGroupViewSet,
    SCIMUserViewSet,
    SchemaDetailView,
    SchemasView,
    ServiceProviderConfigView,
)

router = SimpleRouter(trailing_slash=False)
router.register(r"Users", SCIMUserViewSet, basename="scim-users")
router.register(r"Groups", SCIMGroupViewSet, basename="scim-groups")

urlpatterns = [
    path(
        "ServiceProviderConfig",
        ServiceProviderConfigView.as_view(),
        name="scim-spc",
    ),
    path("Schemas", SchemasView.as_view(), name="scim-schemas"),
    # Schema URNs contain colons (e.g. urn:ietf:params:scim:schemas:core:2.0:User),
    # so use the `path` converter which captures slashes and colons.
    path(
        "Schemas/<path:schema_id>",
        SchemaDetailView.as_view(),
        name="scim-schema-detail",
    ),
    path("ResourceTypes", ResourceTypesView.as_view(), name="scim-resource-types"),
    path(
        "ResourceTypes/<str:resource_id>",
        ResourceTypeDetailView.as_view(),
        name="scim-resource-type-detail",
    ),
] + router.urls
