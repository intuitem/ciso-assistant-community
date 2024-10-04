from django.urls import include, path


from .views import LicenseStatusView, get_build

urlpatterns = [
    path("build/", get_build, name="get_build"),
    path("license-status/", LicenseStatusView.as_view(), name="license-status"),
]
