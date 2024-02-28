from django.urls import path

from core.views import FirstConnexionPasswordConfirmView

from .views import *

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("current-user/", CurrentUserView.as_view(), name="current-user"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        ResetPasswordConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("set-password/", SetPasswordView.as_view(), name="set-password"),
    path(
        "first_connexion/<uidb64>/<token>/",
        FirstConnexionPasswordConfirmView.as_view(),
        name="first_connexion_confirm",
    ),
]
