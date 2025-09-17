from base64 import urlsafe_b64decode
from datetime import timedelta

import structlog
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model, login, logout
from django.db import models
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from knox import crypto
from knox.auth import TokenAuthentication, get_token_model, knox_settings
from knox.models import AuthToken
from knox.views import DateTimeField
from knox.views import LoginView as KnoxLoginView
from rest_framework import permissions, serializers, status, views
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_202_ACCEPTED,
    HTTP_401_UNAUTHORIZED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from ciso_assistant.settings import EMAIL_HOST, EMAIL_HOST_RESCUE

from .models import Folder, PersonalAccessToken, Role, RoleAssignment
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PersonalAccessTokenReadSerializer,
    ResetPasswordConfirmSerializer,
    SetPasswordSerializer,
)

logger = structlog.get_logger(__name__)

User = get_user_model()


class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return super(LoginView, self).post(request, format=None)


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request) -> Response:
        try:
            logger.info("logout request", user=request.user)
            try:
                auth_header = request.META.get("HTTP_AUTHORIZATION")
                if auth_header and " " in auth_header:
                    access_token = auth_header.split(" ")[1]
                    digest = crypto.hash_token(access_token)
                    auth_token = AuthToken.objects.get(digest=digest)
                    auth_token.delete()
                else:
                    logger.warning(
                        "No valid authorization header found during logout",
                        user=request.user,
                    )
            except Exception as e:
                logger.error(
                    "Error deleting token during logout",
                    user=request.user,
                    error=str(e),
                )
            logout(request)
            logger.info("logout successful", user=request.user)
        except Exception as e:
            logger.error("logout failed", user=request.user, error=e)
        return Response({"message": "Logged out successfully."}, status=HTTP_200_OK)


class PersonalAccessTokenViewSet(views.APIView):
    def get_queryset(self):
        return PersonalAccessToken.objects.filter(auth_token__user=self.request.user)

    def get_context(self):
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_token_prefix(self):
        return knox_settings.TOKEN_PREFIX

    def get_token_limit_per_user(self):
        return 5

    def get_expiry_datetime_format(self):
        return knox_settings.EXPIRY_DATETIME_FORMAT

    def format_expiry_datetime(self, expiry):
        datetime_format = self.get_expiry_datetime_format()
        return DateTimeField(format=datetime_format).to_representation(expiry)

    def create_token(self, expiry):
        token_prefix = self.get_token_prefix()
        return get_token_model().objects.create(
            user=self.request.user, expiry=expiry, prefix=token_prefix
        )

    def get_post_response_data(self, request, token, name, instance):
        data = {
            "name": name,
            "expiry": self.format_expiry_datetime(instance.expiry),
            "token": token,
        }
        return data

    def get_post_response(self, request, token, name, instance):
        data = self.get_post_response_data(request, token, name, instance)
        return Response(data)

    def post(self, request, format=None):
        token_limit_per_user = self.get_token_limit_per_user()
        name = request.data.get("name")
        try:
            expiry_days = int(request.data.get("expiry", 30))
            if expiry_days <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"error": "Expiry must be a positive integer (days)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if token_limit_per_user is not None:
            now = timezone.now()
            token = request.user.auth_token_set.filter(expiry__gt=now).filter(
                personalaccesstoken__isnull=False
            )
            if token.count() >= token_limit_per_user:
                return Response(
                    {"error": "errorMaxPatAmountExceeded"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        instance, token = self.create_token(timedelta(days=int(expiry_days)))
        pat = PersonalAccessToken.objects.create(auth_token=instance, name=name)
        return self.get_post_response(request, token, pat.name, pat.auth_token)

    def get(self, request, *args, **kwargs):
        """
        Get all personal access tokens for the user.
        """
        queryset = self.get_queryset()
        serializer = PersonalAccessTokenReadSerializer(
            queryset, many=True, context=self.get_context()
        )
        return Response(serializer.data)


class AuthTokenDetailView(views.APIView):
    def delete(self, request, *args, **kwargs):
        try:
            token = AuthToken.objects.get(digest=kwargs["pk"])
            if token.user != request.user:
                return Response(
                    {"error": "You do not have permission to delete this token."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            token.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except AuthToken.DoesNotExist:
            logger.info(
                "Attempt to delete non-existent token",
                digest=kwargs["pk"],
                user=request.user.id,
            )
            return Response(
                {"error": "Token not found or already deleted."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "Error deleting token",
                error=str(e),
                digest=kwargs["pk"],
                user=request.user.id,
            )
            return Response(
                {"error": "Failed to delete token due to an internal error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CurrentUserView(views.APIView):
    # Is this condition really necessary if we have permission_classes = [permissions.IsAuthenticated] ?
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {"error": "You are not logged in. Please ensure you are logged in."},
                status=HTTP_401_UNAUTHORIZED,
            )

        # getting only what we need
        user_groups_data = list(request.user.user_groups.values("name", "builtin"))
        user_groups = [(ug["name"], ug["builtin"]) for ug in user_groups_data]

        accessible_domains = RoleAssignment.get_accessible_folders(
            Folder.get_root_folder(), request.user, Folder.ContentType.DOMAIN
        )

        domain_permissions = RoleAssignment.get_permissions_per_folder(
            principal=request.user, recursive=True
        )
        domain_permissions = {
            k: list(v) for k, v in domain_permissions.items()
        }  # this what matters

        res_data = {
            "id": request.user.id,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "is_active": request.user.is_active,
            "date_joined": request.user.date_joined,
            "user_groups": user_groups,
            "roles": request.user.get_roles(),
            "permissions": request.user.permissions,
            "is_third_party": request.user.is_third_party,
            "is_admin": request.user.is_admin(),
            "is_local": request.user.is_local,
            "accessible_domains": [str(f) for f in accessible_domains],
            "domain_permissions": domain_permissions,
            "root_folder_id": Folder.get_root_folder().id,
            "preferences": request.user.preferences,
        }
        return Response(res_data, status=HTTP_200_OK)


class SessionTokenView(views.APIView):
    """
    API Endpoint for getting the session token from an access token
    This is needed for allauth's authentication flows.
    """

    def post(self, request):
        access_token = request.META.get("HTTP_AUTHORIZATION").split(" ")[1]
        if not access_token:
            return Response(
                {"error": "No access token provided"}, status=HTTP_401_UNAUTHORIZED
            )
        # Get user from token
        auth = TokenAuthentication()
        user, _ = auth.authenticate_credentials(access_token.encode())
        if not user:
            return Response(
                {"error": "Invalid access token"}, status=HTTP_401_UNAUTHORIZED
            )
        # Log the user in and get the session token
        # This token is used for allauth's authentication flows
        login(request, user)
        session_token = request.session.session_key
        return Response({"token": session_token})


class PasswordResetView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request):
        email = request.data["email"]  # type: ignore
        associated_user = User.objects.filter(email=email).first()
        if EMAIL_HOST or EMAIL_HOST_RESCUE:
            if associated_user is not None and associated_user.is_local:
                try:
                    associated_user.mailing(
                        email_template_name="registration/password_reset_email.html",
                        subject=_("CISO Assistant: Password Reset"),
                    )
                    print("Sending reset mail to", email)
                except Exception as e:
                    print(e)
            return Response(status=HTTP_202_ACCEPTED)
        return Response(
            data={
                "error": "Email server not configured, please contact your administrator"
            },
            status=HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ResetPasswordConfirmView(views.APIView):
    """
    API Endpoint for reset password confirm
    """

    default_token_generator = PasswordResetTokenGenerator()
    permission_classes = [permissions.AllowAny]
    serialier_class = ResetPasswordConfirmSerializer
    token_generator = default_token_generator

    def get_user(self, uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_b64decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
            user = None
        return user

    @method_decorator(ensure_csrf_cookie)
    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uidb64 = serializer.validated_data.get("uidb64")
        token = serializer.validated_data.get("token")
        new_password = serializer.validated_data.get("new_password")
        user = self.get_user(uidb64)
        if (
            user is not None and user.is_local
        ):  # Only local user can reset their password.
            if self.token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response(status=status.HTTP_200_OK)
        return Response(
            data={"error": "The link is invalid or has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ChangePasswordView(views.APIView):
    """
    An endpoint for changing password.
    """

    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.request.user
        old_password = serializer.validated_data.get("old_password")
        new_password = serializer.validated_data.get("new_password")
        if not user.check_password(old_password):
            raise serializers.ValidationError(
                "Your old password was entered incorrectly. Please enter it again."
            )
        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_200_OK)


class SetPasswordView(views.APIView):
    """
    An endpoint for setting a password as an administrator.
    """

    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = SetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if RoleAssignment.has_role(
            self.request.user, Role.objects.get(name="BI-RL-ADM")
        ):
            new_password = serializer.validated_data.get("new_password")
            user = serializer.validated_data.get("user")
            user.set_password(new_password)
            user.save()
            try:
                email_address = EmailAddress.objects.get(user=user, primary=True)
                email_address.verified = True
                email_address.save()
            except Exception as e:
                logger.error(
                    "Error setting email address as verified",
                    user=user,
                    error=e,
                )
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_401_UNAUTHORIZED)
