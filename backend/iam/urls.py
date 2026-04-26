import knox.views as knox_views  # type: ignore[import-untyped]
from django.urls import include, path

from .views import (
    AuthTokenDetailView,
    PersonalAccessTokenViewSet,
    ChangePasswordView,
    CurrentUserView,
    LoginView,
    PasswordResetView,
    ResetPasswordConfirmView,
    ServiceAccountDetailView,
    ServiceAccountKeyDetailView,
    ServiceAccountKeyFlatDetailView,
    ServiceAccountKeyFlatListCreateView,
    ServiceAccountKeyListCreateView,
    ServiceAccountListCreateView,
    SessionTokenView,
    SetPasswordView,
    RevokeOtherSessionsView,
)

urlpatterns = [
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
    # Service accounts
    path(
        "service-accounts/",
        ServiceAccountListCreateView.as_view(),
        name="service-accounts",
    ),
    path(
        "service-accounts/<uuid:pk>/",
        ServiceAccountDetailView.as_view(),
        name="service-account-detail",
    ),
    path(
        "service-accounts/<uuid:sa_pk>/keys/",
        ServiceAccountKeyListCreateView.as_view(),
        name="service-account-keys",
    ),
    path(
        "service-accounts/<uuid:sa_pk>/keys/<int:key_pk>/",
        ServiceAccountKeyDetailView.as_view(),
        name="service-account-key-detail",
    ),
    path(
        "service-account-keys/",
        ServiceAccountKeyFlatListCreateView.as_view(),
        name="service-account-keys-flat",
    ),
    path(
        "service-account-keys/<int:pk>/",
        ServiceAccountKeyFlatDetailView.as_view(),
        name="service-account-key-flat-detail",
    ),
]
