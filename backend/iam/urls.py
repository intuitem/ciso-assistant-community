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
    ServiceAccountViewSet,
    SocialAppViewSet,
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
    path(
        "service-accounts/",
        ServiceAccountViewSet.as_view({"get": "list", "post": "create"}),
        name="service-accounts",
    ),
    path(
        "service-accounts/permissions/",
        ServiceAccountViewSet.as_view({"get": "permissions_catalog"}),
        name="service-account-permissions",
    ),
    path(
        "service-accounts/roles/",
        ServiceAccountViewSet.as_view({"get": "builtin_roles"}),
        name="service-account-roles",
    ),
    path(
        "service-accounts/social-apps/",
        ServiceAccountViewSet.as_view({"get": "social_apps_catalog"}),
        name="service-account-social-apps",
    ),
    path(
        "service-accounts/<uuid:pk>/",
        ServiceAccountViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="service-account-detail",
    ),
    path(
        "service-accounts/<uuid:pk>/rotate-secret/",
        ServiceAccountViewSet.as_view({"post": "rotate_secret"}),
        name="service-account-rotate-secret",
    ),
    path(
        "social-apps/",
        SocialAppViewSet.as_view({"get": "list", "post": "create"}),
        name="social-apps",
    ),
    path(
        "social-apps/<int:pk>/",
        SocialAppViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="social-app-detail",
    ),
    path("scim-token/", SCIMTokenViewSet.as_view(), name="scim-token"),
    path(
        "scim-token/<int:token_id>/",
        SCIMTokenDeleteView.as_view(),
        name="scim-token-delete",
    ),
]
