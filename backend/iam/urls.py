from django.urls import path

from ciso_assistant.settings import AUTHENTICATION_METHOD
from core.views import FirstConnexionPasswordConfirmView

from .views import *
from .knox.views import LoginView as KnoxLoginView
import knox.views as knox_views

authentication_urls = {
    "session": [
        path("login/", LoginView.as_view(), name="login"),
        path("logout/", LogoutView.as_view(), name="logout"),
        path("current-user/", CurrentUserView.as_view(), name="current-user"),
    ],
    "knox": [
        path(r"login/", KnoxLoginView.as_view(), name="knox_login"),
        path(r"logout/", knox_views.LogoutView.as_view(), name="knox_logout"),
        path(r"logoutall/", knox_views.LogoutAllView.as_view(), name="knox_logoutall"),
    ],
}

urlpatterns = [
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

urlpatterns += authentication_urls[AUTHENTICATION_METHOD]

print(urlpatterns)
