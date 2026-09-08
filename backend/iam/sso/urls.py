from django.urls import path

from .slo import IdPLogoutURLView, IdPLogoutView
from .views import RedirectToProviderView

urlpatterns = [
    path("redirect/", RedirectToProviderView.as_view(), name="sso-redirect"),
    path("logout/", IdPLogoutView.as_view(), name="sso-logout"),
    path("logout-url/", IdPLogoutURLView.as_view(), name="sso-logout-url"),
]
