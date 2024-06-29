from django.urls import path

from .views import RedirectToProviderView

urlpatterns = [
    path("redirect/", RedirectToProviderView.as_view(), name="sso-redirect"),
]
