import knox.views as knox_views  # type: ignore[import-untyped]
from django.urls import include, path

from .views import (
    AuthTokenDetailView,
    PersonalAccessTokenViewSet,
    ChangePasswordView,
    CurrentUserView,
    PasswordResetView,
    DisableMFAView,
    ResetPasswordConfirmView,
    SessionTokenView,
    SetPasswordView,
    RevokeOtherSessionsView,
    SCIMTokenViewSet,
    SCIMTokenDeleteView,
)

urlpatterns = [
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
    path("disable-mfa/", DisableMFAView.as_view(), name="disable-mfa"),
    path("revoke-sessions/", RevokeOtherSessionsView.as_view()),
    path("sso/", include("iam.sso.urls")),
    path(
        "session-token/",
        SessionTokenView.as_view(),
        name="session-token",
    ),
    path("auth-tokens/", PersonalAccessTokenViewSet.as_view(), name="auth-tokens"),
    path(
        "auth-tokens/<str:pk>/",
        AuthTokenDetailView.as_view(),
        name="auth-token-detail",
    ),
    path("scim-token/", SCIMTokenViewSet.as_view(), name="scim-token"),
    path(
        "scim-token/<int:token_id>/",
        SCIMTokenDeleteView.as_view(),
        name="scim-token-delete",
    ),
]
