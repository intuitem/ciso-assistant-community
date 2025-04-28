import knox.views as knox_views
from django.urls import include, path
from rest_framework import routers

from .views import (
    AuthTokenViewSet,
    ChangePasswordView,
    CurrentUserView,
    LoginView,
    PasswordResetView,
    ResetPasswordConfirmView,
    SessionTokenView,
    SetPasswordView,
)

router = routers.DefaultRouter()
router.register(r"auth-tokens", AuthTokenViewSet, basename="auth-tokens")

urlpatterns = [
    path("", include(router.urls)),
    path(r"login/", LoginView.as_view(), name="knox_login"),
    path(r"logout/", knox_views.LogoutView.as_view(), name="knox_logout"),
    path(r"logoutall/", knox_views.LogoutAllView.as_view(), name="knox_logoutall"),
    path("current-user/", CurrentUserView.as_view(), name="current-user"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        ResetPasswordConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("set-password/", SetPasswordView.as_view(), name="set-password"),
    path("sso/", include("iam.sso.urls")),
    path(
        "session-token/",
        SessionTokenView.as_view(),
        name="session-token",
    ),
]
