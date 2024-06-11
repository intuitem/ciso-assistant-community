from django.urls import include, path
from rest_framework import routers

from .views import IdentityProviderViewSet


router = routers.DefaultRouter()

router.register(
    r"identity-providers", IdentityProviderViewSet, basename="identity-providers"
)

urlpatterns = [
    path("", include(router.urls)),
]
